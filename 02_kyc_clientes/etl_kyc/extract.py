"""Extracción de la base de clientes (todo como texto para no perder ceros ni formatos)."""
from pathlib import Path

import pandas as pd


def leer_clientes(ruta: Path) -> pd.DataFrame:
    return pd.read_csv(ruta, dtype=str)
