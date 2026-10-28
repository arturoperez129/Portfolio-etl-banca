"""Validaciones de calidad sobre la base de clientes únicos."""
import pandas as pd


def validar(unicos: pd.DataFrame) -> list[str]:
    fallas = []
    if unicos["id_cliente"].duplicated().any():
        fallas.append("id_cliente duplicado en clientes únicos")
    ced = unicos["cedula"].dropna()
    if ced.duplicated().any():
        fallas.append("cédula repetida entre clientes únicos")
    if not ced.str.fullmatch(r"\d{5,8}").all():
        fallas.append("cédula con formato inválido")
    tel = unicos["telefono"].dropna()
    if not tel.str.fullmatch(r"\+595 9\d{2} \d{6}").all():
        fallas.append("teléfono con formato inválido")
    return fallas
