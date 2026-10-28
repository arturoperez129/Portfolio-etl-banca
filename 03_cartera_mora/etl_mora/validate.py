"""Validaciones de calidad sobre la cartera limpia."""
import pandas as pd


def validar(df: pd.DataFrame) -> list[str]:
    fallas = []
    if df["id_credito"].duplicated().any():
        fallas.append("id_credito duplicado")
    for c in ("saldo_capital", "monto_desembolsado", "ingreso_mensual", "tasa_anual", "edad"):
        if df[c].isna().any():
            fallas.append(f"nulos en {c}")
    if (df["saldo_capital"] < 0).any():
        fallas.append("saldo negativo")
    if (df["saldo_capital"] > df["monto_desembolsado"]).any():
        fallas.append("saldo mayor al monto desembolsado")
    if (df["dias_atraso"] < 0).any():
        fallas.append("días de atraso negativos")
    if df["tramo_mora"].isna().any():
        fallas.append("créditos sin tramo de mora")
    if not df["producto"].isin(["CONSUMO", "TARJETA", "PYME", "HIPOTECARIO"]).all():
        fallas.append("producto no reconocido")
    return fallas
