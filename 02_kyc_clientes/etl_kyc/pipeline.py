"""Pipeline KYC: extraer -> estandarizar -> detectar duplicados -> consolidar -> validar."""
import json
import logging
from pathlib import Path

import pandas as pd

from . import dedupe, extract, transform, validate

RAIZ = Path(__file__).resolve().parents[1]
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("kyc")


def main() -> dict:
    df = extract.leer_clientes(RAIZ / "data/raw/clientes.csv")
    limpio, m_transf = transform.transformar(df)
    pares = dedupe.encontrar_pares(limpio, umbral=92.0)
    con_maestro, unicos = dedupe.consolidar(limpio, pares)

    fallas = validate.validar(unicos)
    if fallas:
        raise ValueError(f"Falló la validación de calidad: {fallas}")

    metricas = {
        **m_transf,
        "pares_duplicados_detectados": len(pares),
        "pares_por_regla": pares["regla"].value_counts().to_dict() if len(pares) else {},
        "clientes_unicos": len(unicos),
        "registros_fusionados": len(df) - len(unicos),
        "pct_duplicados": round(100 * (len(df) - len(unicos)) / len(df), 2),
    }
    gt = RAIZ / "data/raw/clientes_ground_truth.csv"
    if gt.exists():
        metricas["evaluacion_vs_ground_truth"] = dedupe.evaluar(limpio, pares, pd.read_csv(gt))

    salida = RAIZ / "data/processed"
    salida.mkdir(parents=True, exist_ok=True)
    con_maestro.to_csv(salida / "clientes_limpios.csv", index=False)
    unicos.to_csv(salida / "clientes_unicos.csv", index=False)
    pares.drop(columns=["idx_a", "idx_b"]).to_csv(salida / "pares_duplicados.csv", index=False)
    (RAIZ / "reports").mkdir(exist_ok=True)
    (RAIZ / "reports/metricas.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False))
    log.info("Métricas: %s", json.dumps(metricas, ensure_ascii=False))
    return metricas


if __name__ == "__main__":
    main()
