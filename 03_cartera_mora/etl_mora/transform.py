"""Limpieza de cartera, cálculo de días de atraso, tramos de mora y variables para scoring."""
import numpy as np
import pandas as pd

FECHA_CORTE = pd.Timestamp("2025-06-30")

TRAMOS_BINS = [-1, 0, 30, 60, 90, 180, np.inf]
TRAMOS_LABELS = ["0_AL_DIA", "1_30", "31_60", "61_90", "91_180", "MAS_180"]
# Porcentajes ILUSTRATIVOS de previsión por tramo. No reflejan la normativa vigente del BCP.
PREVISION_PCT = {"0_AL_DIA": 0.01, "1_30": 0.03, "31_60": 0.10, "61_90": 0.25,
                 "91_180": 0.50, "MAS_180": 1.00}
EDAD_MIN, EDAD_MAX = 18, 80


def limpiar_tasa(s: pd.Series) -> pd.Series:
    """'18,5%' -> 18.5 ; '22.0' -> 22.0"""
    t = s.astype("string").str.replace("%", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(t.str.strip(), errors="coerce")


def tramo_mora(dias: pd.Series) -> pd.Series:
    return pd.cut(dias, bins=TRAMOS_BINS, labels=TRAMOS_LABELS).astype("string")


def dias_atraso(fecha_impago: pd.Series, fecha_corte: pd.Timestamp = FECHA_CORTE) -> pd.Series:
    """Días entre la cuota impaga más antigua y la fecha de corte (0 si está al día)."""
    return (fecha_corte - fecha_impago).dt.days.clip(lower=0).fillna(0).astype(int)


def limites_iqr(s: pd.Series, k: float = 3.0) -> tuple[float, float]:
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def cuota_estimada(monto: pd.Series, tasa_anual: pd.Series, plazo: pd.Series) -> pd.Series:
    """Cuota nivelada (sistema francés)."""
    r = tasa_anual / 100 / 12
    n = plazo
    return (monto * r / (1 - (1 + r) ** (-n))).round(0)


def transformar(df: pd.DataFrame, fecha_corte: pd.Timestamp = FECHA_CORTE) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    df = df.copy()
    n0 = len(df)

    es_dup = df.duplicated(subset="id_credito", keep="first")
    dup = df[es_dup].assign(motivo_rechazo="duplicado")
    df = df[~es_dup].copy()

    # Tipificación
    df["producto"] = df["producto"].str.strip().str.upper()
    df["tasa_anual"] = limpiar_tasa(df["tasa_anual"])
    for c in ("monto_desembolsado", "saldo_capital", "ingreso_mensual", "edad",
              "plazo_meses", "antiguedad_laboral_meses"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["fecha_desembolso"] = pd.to_datetime(df["fecha_desembolso"], errors="coerce")
    df["fecha_primer_vencimiento_impago"] = pd.to_datetime(
        df["fecha_primer_vencimiento_impago"], errors="coerce"
    )

    # Rechazos por reglas de negocio
    incoherente = (
        df["fecha_primer_vencimiento_impago"].notna()
        & (df["fecha_primer_vencimiento_impago"] < df["fecha_desembolso"])
    )
    df["motivo_rechazo"] = np.select(
        [df["saldo_capital"].isna() | (df["saldo_capital"] < 0),
         df["fecha_desembolso"].isna(),
         incoherente],
        ["saldo_invalido", "fecha_desembolso_invalida", "impago_anterior_a_desembolso"],
        default="",
    )
    rechazado = pd.concat([dup, df[df["motivo_rechazo"] != ""]], ignore_index=True)
    df = df[df["motivo_rechazo"] == ""].drop(columns="motivo_rechazo").copy()

    # Edades imposibles -> nulo -> imputación por mediana
    edad_mala = ~df["edad"].between(EDAD_MIN, EDAD_MAX)
    df["edad_imputada"] = edad_mala
    df.loc[edad_mala, "edad"] = np.nan
    df["edad"] = df["edad"].fillna(df["edad"].median())

    # Ingreso: outliers (winsorización por producto) y nulos (mediana por producto)
    df["ingreso_outlier"] = False
    for prod, g in df.groupby("producto"):
        lo, hi = limites_iqr(g["ingreso_mensual"].dropna())
        mask = (df["producto"] == prod) & (df["ingreso_mensual"] > hi)
        df.loc[mask, "ingreso_outlier"] = True
        df.loc[mask, "ingreso_mensual"] = hi
    df["ingreso_imputado"] = df["ingreso_mensual"].isna()
    df["ingreso_mensual"] = df["ingreso_mensual"].fillna(
        df.groupby("producto")["ingreso_mensual"].transform("median")
    )

    # Mora y previsión
    df["dias_atraso"] = dias_atraso(df["fecha_primer_vencimiento_impago"], fecha_corte)
    df["tramo_mora"] = tramo_mora(df["dias_atraso"])
    df["en_mora_90"] = df["dias_atraso"] > 90
    df["prevision_pct"] = df["tramo_mora"].map(PREVISION_PCT)
    df["prevision_monto"] = (df["saldo_capital"] * df["prevision_pct"]).round(0)

    # Variables para scoring
    df["cuota_estimada"] = cuota_estimada(df["monto_desembolsado"], df["tasa_anual"], df["plazo_meses"])
    df["ratio_cuota_ingreso"] = (df["cuota_estimada"] / df["ingreso_mensual"]).round(4)
    df["antiguedad_credito_meses"] = ((fecha_corte - df["fecha_desembolso"]).dt.days / 30.4).round(1)
    df["pct_capital_pendiente"] = (df["saldo_capital"] / df["monto_desembolsado"]).clip(0, 1).round(4)
    df = df.reset_index(drop=True)

    saldo_total = df["saldo_capital"].sum()
    metricas = {
        "fecha_corte": str(fecha_corte.date()),
        "filas_entrada": n0,
        "creditos_limpios": len(df),
        "rechazados_por_motivo": rechazado["motivo_rechazo"].value_counts().to_dict(),
        "ingresos_imputados": int(df["ingreso_imputado"].sum()),
        "ingresos_outlier_ajustados": int(df["ingreso_outlier"].sum()),
        "edades_corregidas": int(df["edad_imputada"].sum()),
        "saldo_cartera_total_pyg": int(saldo_total),
        "indice_morosidad_pct": round(100 * df.loc[df["en_mora_90"], "saldo_capital"].sum() / saldo_total, 2),
        "prevision_total_pyg": int(df["prevision_monto"].sum()),
        "creditos_por_tramo": df["tramo_mora"].value_counts().reindex(TRAMOS_LABELS).fillna(0).astype(int).to_dict(),
    }
    return df, rechazado, metricas


def resumen_por_producto_tramo(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["producto", "tramo_mora"], observed=True, as_index=False)
        .agg(creditos=("id_credito", "count"), saldo_capital=("saldo_capital", "sum"),
             prevision=("prevision_monto", "sum"))
    )
