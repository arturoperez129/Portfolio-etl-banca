"""Carga: Parquet (analítica) y SQLite (consulta SQL). Cambiar a PostgreSQL con SQLAlchemy."""
import sqlite3
from pathlib import Path

import pandas as pd


def a_parquet(df: pd.DataFrame, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ruta, index=False)


def a_sqlite(df: pd.DataFrame, ruta: Path, tabla: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(ruta) as con:
        df.assign(fecha=df["fecha"].astype(str)).to_sql(tabla, con, if_exists="replace", index=False)
