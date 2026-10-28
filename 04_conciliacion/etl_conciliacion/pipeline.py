"""Pipeline de conciliación bancaria."""
import json
import logging
from pathlib import Path

from . import extract, match, transform, validate

RAIZ = Path(__file__).resolve().parents[1]
SALDO_INICIAL = 3_000_000_000  # saldo de apertura (mismo valor que usa el generador)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("conciliacion")


def main() -> dict:
    libro = transform.normalizar_libro(extract.leer_libro(RAIZ / "data/raw/libro_contable.csv"))
    banco = transform.normalizar_extracto(extract.leer_extracto(RAIZ / "data/raw/extracto_bancario.csv"))

    conciliadas, pend_l, pend_b = match.conciliar(libro, banco)
    pend_l, pend_b = match.clasificar_pendientes(pend_l, pend_b)
    res = match.resumen(libro, banco, conciliadas, pend_l, pend_b, SALDO_INICIAL)
    res["pendientes_libro_por_causa"] = pend_l["causa_probable"].value_counts().to_dict()
    res["pendientes_banco_por_causa"] = pend_b["causa_probable"].value_counts().to_dict()

    fallas = validate.validar(libro, banco, conciliadas, pend_l, pend_b, res)
    if fallas:
        raise ValueError(f"Falló la validación de integridad: {fallas}")

    for carpeta in ("data/processed", "reports"):
        (RAIZ / carpeta).mkdir(parents=True, exist_ok=True)
    conciliadas.to_csv(RAIZ / "data/processed/conciliadas.csv", index=False)
    pend_l.to_csv(RAIZ / "data/processed/pendientes_libro.csv", index=False)
    pend_b.to_csv(RAIZ / "data/processed/pendientes_banco.csv", index=False)
    (RAIZ / "reports/metricas.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    log.info("Resumen: %s", json.dumps(res, ensure_ascii=False))
    return res


if __name__ == "__main__":
    main()
