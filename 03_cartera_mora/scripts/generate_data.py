"""Genera una cartera de créditos SINTÉTICA (montos en guaraníes) con problemas de calidad.

Problemas inyectados: ingresos nulos y outliers, edades imposibles, saldos negativos,
productos con distinto formato, tasas como texto ('18,5%'), duplicados y fechas incoherentes.
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2025
N = 3000
FECHA_CORTE = pd.Timestamp("2025-06-30")
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "cartera_creditos.csv"

PRODUCTOS = {  # monto (min, max), tasa anual % (min, max), plazos posibles
    "CONSUMO": ((5e6, 60e6), (18, 32), [12, 24, 36, 48]),
    "TARJETA": ((2e6, 30e6), (30, 45), [12, 24]),
    "PYME": ((30e6, 400e6), (12, 22), [24, 36, 60]),
    "HIPOTECARIO": ((150e6, 900e6), (9, 14), [120, 180, 240]),
}


def main() -> None:
    rng = np.random.default_rng(SEED)
    prod = rng.choice(list(PRODUCTOS), N, p=[0.45, 0.20, 0.20, 0.15])
    monto, tasa, plazo = np.zeros(N), np.zeros(N), np.zeros(N, dtype=int)
    for p, ((m0, m1), (t0, t1), plazos) in PRODUCTOS.items():
        m = prod == p
        monto[m] = np.round(rng.uniform(m0, m1, m.sum()) / 100_000) * 100_000
        tasa[m] = np.round(rng.uniform(t0, t1, m.sum()), 1)
        plazo[m] = rng.choice(plazos, m.sum())

    desembolso = FECHA_CORTE - pd.to_timedelta(rng.integers(40, 1500, N), unit="D")
    ingreso = np.round(rng.lognormal(15.4, 0.45, N) / 10_000) * 10_000  # ~4.9M PYG mediana
    edad = rng.integers(21, 70, N)
    antig = rng.integers(0, 240, N)

    # Mora: 82% al día; el resto tiene una cuota impaga con cierta antigüedad
    tramo = rng.choice(["AL_DIA", "1_30", "31_60", "61_90", "91_180", "MAS_180"], N,
                       p=[0.82, 0.07, 0.04, 0.025, 0.025, 0.02])
    rangos = {"1_30": (1, 30), "31_60": (31, 60), "61_90": (61, 90),
              "91_180": (91, 180), "MAS_180": (181, 420)}
    dias = np.array([0 if t == "AL_DIA" else rng.integers(*rangos[t]) for t in tramo])
    fecha_impaga = pd.Series(FECHA_CORTE - pd.to_timedelta(dias, unit="D"))
    fecha_impaga[dias == 0] = pd.NaT
    # la primera cuota impaga no puede ser anterior al desembolso
    fecha_impaga = fecha_impaga.where(fecha_impaga.isna() | (fecha_impaga > desembolso + pd.Timedelta(days=30)))

    pct_pend = rng.uniform(0.25, 1.0, N)
    saldo = np.round(monto * pct_pend / 1000) * 1000

    df = pd.DataFrame({
        "id_credito": [f"CR{i:06d}" for i in range(1, N + 1)],
        "id_cliente": [f"C{c:06d}" for c in rng.integers(1, 2400, N)],
        "producto": prod,
        "monto_desembolsado": monto.astype(np.int64),
        "saldo_capital": saldo.astype(np.int64),
        "tasa_anual": tasa.astype(object),
        "plazo_meses": plazo,
        "fecha_desembolso": desembolso.strftime("%Y-%m-%d"),
        "fecha_primer_vencimiento_impago": fecha_impaga.dt.strftime("%Y-%m-%d"),
        "ingreso_mensual": ingreso.astype(object),
        "edad": edad.astype(object),
        "antiguedad_laboral_meses": antig,
    })

    idx = np.arange(N)
    pick = lambda frac: rng.choice(idx, int(N * frac), replace=False)  # noqa: E731

    df.loc[pick(0.08), "ingreso_mensual"] = None                       # nulos
    out = pick(0.01)
    df.loc[out, "ingreso_mensual"] = df.loc[out, "ingreso_mensual"].astype(float) * 100  # outliers
    df.loc[pick(0.02), "edad"] = None
    df.loc[pick(0.005), "edad"] = rng.choice([0, 7, 150, 999], int(N * 0.005))
    df.loc[pick(0.005), "saldo_capital"] = -df["saldo_capital"].abs()  # saldos negativos
    t_txt = pick(0.15)
    df.loc[t_txt, "tasa_anual"] = [f"{str(v).replace('.', ',')}%" for v in df.loc[t_txt, "tasa_anual"]]
    p_var = pick(0.2)
    df.loc[p_var, "producto"] = [rng.choice([v.title(), f" {v} ", v.lower()]) for v in df.loc[p_var, "producto"]]
    # fecha de impago anterior al desembolso (incoherente)
    inc = pick(0.005)
    df.loc[inc, "fecha_primer_vencimiento_impago"] = (desembolso[inc] - pd.Timedelta(days=15)).strftime("%Y-%m-%d")

    df = pd.concat([df, df.sample(int(N * 0.01), random_state=SEED)]).sample(frac=1, random_state=SEED)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Generado {OUT} -> {len(df):,} filas | fecha de corte {FECHA_CORTE.date()}")


if __name__ == "__main__":
    main()
