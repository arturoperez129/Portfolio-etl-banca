"""Pipeline de cartera: extraer -> limpiar -> mora/previsión -> features -> validar -> cargar."""
import json
import logging
from pathlib import Path

from . import extract, transform, validate

RAIZ = Path(__file__).resolve().parents[1]
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("mora")


def main() -> dict:
    df = extract.leer_cartera(RAIZ / "data/raw/cartera_creditos.csv")
    limpio, rechazado, metricas = transform.transformar(df)
    fallas = validate.validar(limpio)
    if fallas:
        raise ValueError(f"Falló la validación de calidad: {fallas}")

    for carpeta in ("data/processed", "data/rejected", "reports"):
        (RAIZ / carpeta).mkdir(parents=True, exist_ok=True)
    limpio.to_parquet(RAIZ / "data/processed/cartera_limpia.parquet", index=False)
    rechazado.to_csv(RAIZ / "data/rejected/cartera_rechazada.csv", index=False)
    features = limpio[["id_credito", "id_cliente", "producto", "edad", "ingreso_mensual",
                       "antiguedad_laboral_meses", "ratio_cuota_ingreso", "antiguedad_credito_meses",
                       "pct_capital_pendiente", "dias_atraso", "en_mora_90"]]
    features.to_csv(RAIZ / "data/processed/features_scoring.csv", index=False)
    transform.resumen_por_producto_tramo(limpio).to_csv(RAIZ / "reports/resumen_producto_tramo.csv", index=False)
    (RAIZ / "reports/metricas.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False))
    log.info("Métricas: %s", json.dumps(metricas, ensure_ascii=False))
    return metricas


if __name__ == "__main__":
    main()
