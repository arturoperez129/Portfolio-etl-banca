"""Transformación y limpieza de transacciones. Funciones puras, fáciles de testear."""
import unicodedata

import numpy as np
import pandas as pd

TIPO_CAMBIO_USD = 7500.0  # PYG por USD (valor fijo de ejemplo)
MONEDAS_VALIDAS = {"PYG", "USD"}
SINONIMOS_CATEGORIA = {"SUPER": "SUPERMERCADO", "COMBUSTIBLES": "COMBUSTIBLE"}
CATEGORIAS_VALIDAS = {
    "SUPERMERCADO", "COMBUSTIBLE", "SERVICIOS", "RESTAURANTE",
    "SALUD", "TRANSFERENCIA", "SALARIO", "RETIRO_ATM",
}


def limpiar_monto(s: pd.Series) -> pd.Series:
    """'1.250.000' -> 1250000.0 ; '1250.50' -> 1250.5 ; texto inválido -> NaN."""
    s = s.astype("string").str.strip().str.replace(" ", "", regex=False)
    con_miles = s.str.match(r"^-?\d{1,3}(\.\d{3})+$").fillna(False)
    s = s.mask(con_miles, s.str.replace(".", "", regex=False))
    return pd.to_numeric(s, errors="coerce").astype(float)


def parsear_fechas(s: pd.Series) -> pd.Series:
    """Acepta 'YYYY-MM-DD HH:MM:SS' y 'DD/MM/YYYY'. Fechas imposibles -> NaT."""
    s = s.astype("string").str.strip()
    iso = pd.to_datetime(s, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    latino = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    return iso.fillna(latino)


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def normalizar_categoria(s: pd.Series) -> pd.Series:
    """Mayúsculas, sin acentos, espacios -> '_' y unificación de sinónimos."""
    def _norm(v):
        if pd.isna(v) or not str(v).strip():
            return "SIN_CATEGORIA"
        v = _sin_acentos(str(v)).upper().strip().replace(" ", "_")
        v = SINONIMOS_CATEGORIA.get(v, v)
        return v if v in CATEGORIAS_VALIDAS else "SIN_CATEGORIA"

    return s.map(_norm)


def transformar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Devuelve (limpio, rechazado, metricas)."""
    df = df.copy()
    n_inicial = len(df)

    # 1) Duplicados por id_transaccion (se conserva la primera aparición)
    es_dup = df.duplicated(subset="id_transaccion", keep="first")
    duplicados = df[es_dup].assign(motivo_rechazo="duplicado")
    df = df[~es_dup].copy()

    # 2) Tipificación
    df["fecha"] = parsear_fechas(df["fecha"])
    df["monto"] = limpiar_monto(df["monto"])
    for col in ("moneda", "tipo", "canal"):
        df[col] = df[col].astype("string").str.strip().str.upper()
    df["categoria"] = normalizar_categoria(df["categoria"])

    # 3) Corrección de signo: el sentido lo define 'tipo', el monto siempre es positivo
    df["monto_corregido"] = df["monto"] < 0
    n_signo = int(df["monto_corregido"].sum())
    df["monto"] = df["monto"].abs()

    # 4) Reglas de rechazo (se evalúan en orden de prioridad)
    motivo = np.select(
        [
            df["id_transaccion"].isna(),
            df["fecha"].isna(),
            df["monto"].isna() | (df["monto"] == 0),
            ~df["moneda"].isin(MONEDAS_VALIDAS),
        ],
        ["id_nulo", "fecha_invalida", "monto_invalido", "moneda_invalida"],
        default="",
    )
    df["motivo_rechazo"] = motivo
    rechazado = pd.concat([duplicados, df[df["motivo_rechazo"] != ""]], ignore_index=True)
    limpio = df[df["motivo_rechazo"] == ""].drop(columns="motivo_rechazo").copy()

    # 5) Enriquecimiento
    limpio["monto_pyg"] = np.where(
        limpio["moneda"] == "USD", limpio["monto"] * TIPO_CAMBIO_USD, limpio["monto"]
    ).round(0)
    limpio["monto_con_signo"] = np.where(limpio["tipo"] == "DEBITO", -1, 1) * limpio["monto_pyg"]
    limpio["anio_mes"] = limpio["fecha"].dt.strftime("%Y-%m")
    limpio = limpio.reset_index(drop=True)

    motivos = rechazado["motivo_rechazo"].value_counts().to_dict()
    metricas = {
        "filas_entrada": n_inicial,
        "filas_limpias": len(limpio),
        "filas_rechazadas": len(rechazado),
        "rechazos_por_motivo": motivos,
        "montos_con_signo_corregido": n_signo,
        "pct_duplicados": round(100 * len(duplicados) / n_inicial, 2),
        "categorias_sin_clasificar": int((limpio["categoria"] == "SIN_CATEGORIA").sum()),
    }
    return limpio, rechazado, metricas
