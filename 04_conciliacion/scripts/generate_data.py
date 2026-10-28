"""Genera un libro contable y un extracto bancario SINTÉTICOS (junio 2025, montos en PYG).

Escenarios inyectados sobre las partidas del libro:
  - coinciden exactas (con referencia escrita distinto en el banco: 'TRX-000123' vs 'trx000123')
  - el banco las acredita/debita con 1 a 3 días de diferencia
  - el banco registra un monto distinto (comisión retenida)
  - sin referencia en el banco (se concilian por monto + fecha)
  - solo en el libro (cheques / depósitos en tránsito)
Además se agregan movimientos que solo existen en el banco (comisiones, intereses, débitos automáticos).
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 7
N = 1200
SALDO_INICIAL = 3_000_000_000
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
INGRESOS = ["COBRO CLIENTE", "TRANSFERENCIA RECIBIDA", "DEPOSITO EN EFECTIVO"]
EGRESOS = ["PAGO PROVEEDOR", "PAGO SERVICIOS", "PAGO NOMINA", "CHEQUE EMITIDO"]
TERCEROS = ["Comercial Norte", "Distribuidora Sur", "Servicios Delta", "Importadora Este",
            "Agro Chaco", "Tecno Guaraní", "Logística Ñandutí"]


def main() -> None:
    rng = np.random.default_rng(SEED)
    es_ing = rng.random(N) < 0.52
    tipo = np.where(es_ing, rng.choice(INGRESOS, N), rng.choice(EGRESOS, N))
    monto = np.round(rng.lognormal(15.4, 0.9, N) / 1000) * 1000
    firmado = np.where(es_ing, monto, -monto).astype(np.int64)
    fecha = pd.Timestamp("2025-06-01") + pd.to_timedelta(rng.integers(0, 30, N), unit="D")

    libro = pd.DataFrame({
        "id_asiento": [f"A{i:05d}" for i in range(1, N + 1)],
        "fecha": fecha,
        "referencia": [f"TRX-{i:06d}" for i in range(1, N + 1)],
        "descripcion": [f"{t} - {rng.choice(TERCEROS)}" for t in tipo],
        "debe": np.where(firmado > 0, firmado, 0),    # ingresos a la cuenta bancaria
        "haber": np.where(firmado < 0, -firmado, 0),  # egresos
    })

    escenario = rng.choice(["exacto", "fecha", "monto", "solo_libro"], N, p=[0.89, 0.06, 0.015, 0.035])
    banco = libro[escenario != "solo_libro"].copy()
    esc = escenario[escenario != "solo_libro"]
    banco["firmado"] = (banco["debe"] - banco["haber"]).to_numpy()
    n_f = int((esc == "fecha").sum())
    banco.loc[esc == "fecha", "fecha"] += pd.to_timedelta(rng.integers(1, 4, n_f), unit="D")
    m = esc == "monto"
    banco.loc[m, "firmado"] -= np.sign(banco.loc[m, "firmado"]) * rng.integers(5, 30, int(m.sum())) * 1000

    # referencia escrita distinto en el banco; 5% sin referencia
    banco["referencia"] = banco["referencia"].map(
        lambda r: r.lower().replace("-", "") if rng.random() < 0.30 else r
    )
    sin_ref = (esc == "exacto") & (rng.random(len(banco)) < 0.05)
    banco.loc[sin_ref, "referencia"] = ""

    # movimientos solo en el banco
    extra = []
    for i in range(45):
        k = rng.choice(["COMISION MANTENIMIENTO CUENTA", "INTERES GANADO", "DEBITO AUTOMATICO SEGURO",
                        "IVA COMISION"], p=[0.3, 0.2, 0.25, 0.25])
        val = {"COMISION MANTENIMIENTO CUENTA": -35_000, "INTERES GANADO": int(rng.integers(5, 90) * 1000),
               "DEBITO AUTOMATICO SEGURO": -int(rng.integers(100, 900) * 1000),
               "IVA COMISION": -3_500}[k]
        extra.append({"fecha": pd.Timestamp("2025-06-01") + pd.Timedelta(days=int(rng.integers(0, 30))),
                      "referencia": f"BCO-{i:04d}", "descripcion": k, "firmado": val})
    banco = pd.concat([banco, pd.DataFrame(extra)], ignore_index=True).sort_values("fecha").reset_index(drop=True)
    banco["saldo"] = SALDO_INICIAL + banco["firmado"].cumsum()
    extracto = pd.DataFrame({
        "fecha": banco["fecha"].dt.strftime("%d/%m/%Y"),
        "referencia": banco["referencia"],
        "descripcion": banco["descripcion"].str.upper(),
        "debito": np.where(banco["firmado"] < 0, -banco["firmado"], 0),
        "credito": np.where(banco["firmado"] > 0, banco["firmado"], 0),
        "saldo": banco["saldo"],
    })

    RAW.mkdir(parents=True, exist_ok=True)
    libro.assign(fecha=libro["fecha"].dt.strftime("%Y-%m-%d")).to_csv(RAW / "libro_contable.csv", index=False)
    extracto.to_csv(RAW / "extracto_bancario.csv", index=False)
    print(f"Generado libro ({len(libro):,}) y extracto ({len(extracto):,}) en {RAW}")


if __name__ == "__main__":
    main()
