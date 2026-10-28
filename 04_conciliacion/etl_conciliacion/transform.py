"""Normaliza ambas fuentes a un esquema común: id, fecha, referencia, monto con signo, descripción.

Convención de signo: ingreso a la cuenta bancaria = positivo; egreso = negativo.
  - Libro:  monto = debe - haber
  - Banco:  monto = credito - debito
"""
import re

import pandas as pd


def normalizar_referencia(valor) -> str:
    """'TRX-000123' y 'trx000123' -> 'TRX000123'. Vacío si no hay referencia."""
    if pd.isna(valor):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(valor).upper())


def normalizar_libro(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "id_libro": df["id_asiento"],
        "fecha": pd.to_datetime(df["fecha"], format="%Y-%m-%d"),
        "ref": df["referencia"].map(normalizar_referencia),
        "monto": (df["debe"].astype("int64") - df["haber"].astype("int64")),
        "descripcion": df["descripcion"],
    })


def normalizar_extracto(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "id_banco": [f"B{i:05d}" for i in range(1, len(df) + 1)],
        "fecha": pd.to_datetime(df["fecha"], format="%d/%m/%Y"),
        "ref": df["referencia"].map(normalizar_referencia),
        "monto": (df["credito"].astype("int64") - df["debito"].astype("int64")),
        "descripcion": df["descripcion"],
    })
