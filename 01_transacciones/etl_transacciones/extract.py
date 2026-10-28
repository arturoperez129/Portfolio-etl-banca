"""Extracción: lee el CSV crudo sin inferir tipos (todo como texto)."""
from pathlib import Path

import pandas as pd


def leer_csv(ruta: Path) -> pd.DataFrame:
    """Lee el archivo crudo; dtype=str evita que pandas 'adivine' mal montos y fechas."""
    return pd.read_csv(ruta, dtype=str)
