"""Genera transacciones bancarias SINTÉTICAS con errores intencionales.

Todos los datos son ficticios. Errores inyectados: duplicados, fechas inválidas y en
formatos mixtos, montos con separador de miles, montos negativos en créditos, montos
en cero, categorías inconsistentes y nulas, monedas inválidas.
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N = 5000
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "transacciones.csv"

COMERCIOS = {
    "SUPERMERCADO": ["Supermercado El Ahorro", "Mercado Central Express", "Super Familia"],
    "COMBUSTIBLE": ["Estación Ruta 2", "Estación Costanera", "Combustibles del Sur"],
    "SERVICIOS": ["Distribuidora Eléctrica", "Agua Potable SA", "Telefonía Guaraní"],
    "RESTAURANTE": ["Parrilla Don Mario", "Burger Plaza", "Pizzería La Esquina"],
    "SALUD": ["Farmacia Salud Total", "Clínica Santa Rosa"],
    "TRANSFERENCIA": ["Transferencia interbancaria"],
    "SALARIO": ["Acreditación de haberes"],
    "RETIRO_ATM": ["Cajero automático"],
}
CATEGORIAS = list(COMERCIOS)
PESOS = np.array([0.22, 0.12, 0.14, 0.12, 0.06, 0.14, 0.06, 0.14])
CREDITOS = {"SALARIO", "TRANSFERENCIA"}
CANALES = ["APP", "WEB", "ATM", "POS", "SUCURSAL"]


def main() -> None:
    rng = np.random.default_rng(SEED)
    cat = rng.choice(CATEGORIAS, N, p=PESOS / PESOS.sum())
    es_credito = np.isin(cat, list(CREDITOS)) & (rng.random(N) < 0.9) | (cat == "SALARIO")
    tipo = np.where(es_credito, "CREDITO", "DEBITO")

    base = rng.lognormal(12.0, 0.9, N)
    base = np.where(cat == "SALARIO", rng.uniform(2_800_000, 9_000_000, N), base)
    monto = np.round(base / 1000) * 1000
    moneda = np.where(rng.random(N) < 0.08, "USD", "PYG")
    monto = np.where(moneda == "USD", np.round(monto / 7500, 2), monto)

    inicio = pd.Timestamp("2025-01-01")
    fechas = inicio + pd.to_timedelta(rng.integers(0, 181 * 86400, N), unit="s")

    df = pd.DataFrame(
        {
            "id_transaccion": [f"TX{i:07d}" for i in range(1, N + 1)],
            "id_cuenta": [f"PY-{c:08d}" for c in rng.integers(10_000_000, 10_000_300, N)],
            "fecha": fechas.strftime("%Y-%m-%d %H:%M:%S"),
            "monto": monto.astype(object),
            "moneda": moneda,
            "tipo": tipo,
            "categoria": cat,
            "comercio": [rng.choice(COMERCIOS[c]) for c in cat],
            "canal": rng.choice(CANALES, N, p=[0.35, 0.15, 0.15, 0.3, 0.05]),
        }
    )

    # --- Ensuciar datos -------------------------------------------------
    idx = np.arange(N)
    # 1) fechas en formato dd/mm/YYYY (10%) e inválidas (1.2%)
    f_lat = rng.choice(idx, int(N * 0.10), replace=False)
    df.loc[f_lat, "fecha"] = pd.to_datetime(df.loc[f_lat, "fecha"]).dt.strftime("%d/%m/%Y")
    f_bad = rng.choice(idx, int(N * 0.012), replace=False)
    df.loc[f_bad, "fecha"] = rng.choice(["31/02/2025", "2025-13-45", "", "N/A"], len(f_bad))

    # 2) montos PYG con separador de miles latino (15%), montos como texto
    pyg = df.index[df["moneda"] == "PYG"]
    m_str = rng.choice(pyg, int(len(pyg) * 0.15), replace=False)
    df.loc[m_str, "monto"] = [f"{int(float(v)):,}".replace(",", ".") for v in df.loc[m_str, "monto"]]
    # 3) créditos con signo negativo (2%) y montos en cero (0.5%)
    cred = df.index[(df["tipo"] == "CREDITO") & (df["moneda"] == "PYG") & ~df.index.isin(m_str)]
    m_neg = rng.choice(cred, int(len(cred) * 0.02), replace=False)
    df.loc[m_neg, "monto"] = df.loc[m_neg, "monto"].astype(float) * -1
    m_zero = rng.choice(idx, int(N * 0.005), replace=False)
    df.loc[m_zero, "monto"] = 0

    # 4) categorías inconsistentes (mayúsculas/minúsculas, espacios, sinónimos) y nulas (3%)
    c_var = rng.choice(idx, int(N * 0.20), replace=False)
    df.loc[c_var, "categoria"] = [
        rng.choice([v.lower(), f" {v} ", v.replace("_", " ").title()])
        for v in df.loc[c_var, "categoria"]
    ]
    sinonimo = rng.random(N) < 0.05
    df.loc[sinonimo, "categoria"] = df.loc[sinonimo, "categoria"].replace(
        {"SUPERMERCADO": "SUPER", "COMBUSTIBLE": "COMBUSTIBLES"}
    )
    c_null = rng.choice(idx, int(N * 0.03), replace=False)
    df.loc[c_null, "categoria"] = None

    # 5) monedas inválidas (0.4%) y canal en minúsculas
    m_bad = rng.choice(idx, int(N * 0.004), replace=False)
    df.loc[m_bad, "moneda"] = "XXX"
    c_low = rng.choice(idx, int(N * 0.1), replace=False)
    df.loc[c_low, "canal"] = df.loc[c_low, "canal"].str.lower()

    # 6) duplicados exactos (3%) y desorden
    dup = df.sample(int(N * 0.03), random_state=SEED)
    df = pd.concat([df, dup]).sample(frac=1, random_state=SEED).reset_index(drop=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Generado {OUT} -> {len(df):,} filas")


if __name__ == "__main__":
    main()
