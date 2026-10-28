"""Extracción de la cartera de créditos."""
from pathlib import Path

import pandas as pd


def leer_cartera(ruta: Path) -> pd.DataFrame:
    return pd.read_csv(ruta, dtype=str)
