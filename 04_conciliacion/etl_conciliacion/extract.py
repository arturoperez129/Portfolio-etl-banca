"""Extracción del libro contable y del extracto bancario (layouts distintos)."""
from pathlib import Path

import pandas as pd


def leer_libro(ruta: Path) -> pd.DataFrame:
    return pd.read_csv(ruta, dtype={"referencia": str, "id_asiento": str}, keep_default_na=False)


def leer_extracto(ruta: Path) -> pd.DataFrame:
    return pd.read_csv(ruta, dtype={"referencia": str}, keep_default_na=False)
