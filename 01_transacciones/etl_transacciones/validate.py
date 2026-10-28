"""Validaciones de calidad sobre el dataset ya limpio (post-condiciones del pipeline)."""
import pandas as pd


def validar(df: pd.DataFrame) -> list[str]:
    """Devuelve la lista de reglas incumplidas (vacía si todo está bien)."""
    fallas = []
    if df["id_transaccion"].isna().any() or df["id_transaccion"].duplicated().any():
        fallas.append("id_transaccion nulo o duplicado")
    if (df["monto"] <= 0).any():
        fallas.append("existen montos <= 0")
    if df["fecha"].isna().any():
        fallas.append("existen fechas nulas")
    if not df["tipo"].isin(["DEBITO", "CREDITO"]).all():
        fallas.append("tipo fuera de DEBITO/CREDITO")
    if not df["moneda"].isin(["PYG", "USD"]).all():
        fallas.append("moneda fuera de PYG/USD")
    return fallas
