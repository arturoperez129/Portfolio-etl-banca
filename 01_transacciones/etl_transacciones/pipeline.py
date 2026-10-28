"""Orquestador: extract -> transform -> validate -> load, con logs y reporte de métricas."""
import json
import logging
from pathlib import Path

from . import extract, load, transform, validate

RAIZ = Path(__file__).resolve().parents[1]
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("transacciones")


def main() -> dict:
    df = extract.leer_csv(RAIZ / "data/raw/transacciones.csv")
    log.info("Extraídas %s filas", f"{len(df):,}")

    limpio, rechazado, metricas = transform.transformar(df)
    fallas = validate.validar(limpio)
    if fallas:
        raise ValueError(f"Falló la validación de calidad: {fallas}")

    (RAIZ / "data/rejected").mkdir(parents=True, exist_ok=True)
    rechazado.to_csv(RAIZ / "data/rejected/transacciones_rechazadas.csv", index=False)
    load.a_parquet(limpio, RAIZ / "data/processed/transacciones.parquet")
    load.a_sqlite(limpio, RAIZ / "data/processed/banco.db", "transacciones")

    resumen = (
        limpio.groupby(["anio_mes", "categoria"], as_index=False)
        .agg(transacciones=("id_transaccion", "count"), monto_neto_pyg=("monto_con_signo", "sum"))
    )
    (RAIZ / "reports").mkdir(exist_ok=True)
    resumen.to_csv(RAIZ / "reports/resumen_mensual_categoria.csv", index=False)
    (RAIZ / "reports/metricas.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False))
    log.info("Métricas: %s", json.dumps(metricas, ensure_ascii=False))
    return metricas


if __name__ == "__main__":
    main()
