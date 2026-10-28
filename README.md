# Portafolio ETL y calidad de datos para banca y finanzas

[![CI](https://github.com/arturoperez129/Portfolio-etl-banca/actions/workflows/ci.yml/badge.svg)](https://github.com/arturoperez129/Portfolio-etl-banca/actions)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

Cuatro proyectos de **extracción, transformación y limpieza de datos** con Python, pensados para casos reales de un banco o financiera. Cada proyecto parte de datos sucios, aplica reglas de negocio, separa los registros rechazados, valida el resultado y publica métricas de calidad.

> **Todos los datos son sintéticos.** Se generan con scripts reproducibles (semilla fija) que inyectan errores a propósito. No contienen información real de clientes, cédulas ni cuentas.

## Proyectos

| # | Proyecto | Problema de negocio | Técnicas | Resultado clave |
|---|----------|--------------------|----------|-----------------|
| 1 | [Pipeline de transacciones](01_transacciones) | Transacciones con duplicados, fechas inválidas y montos mal formateados distorsionan reportes y analítica | Parseo de fechas y montos, normalización de categorías, cuarentena de rechazos, carga a Parquet/SQLite | 5.150 → 4.896 filas limpias; 254 rechazos con motivo |
| 2 | [Limpieza y deduplicación de clientes (KYC)](02_kyc_clientes) | Un mismo cliente cargado varias veces con datos inconsistentes | Estandarización de cédula, RUC (dígito verificador), teléfono, email; fuzzy matching con blocking; golden record | Precisión 100 % y recall 95,8 % en detección de duplicados |
| 3 | [Cartera de créditos y mora](03_cartera_mora) | Medir morosidad y preparar variables para scoring con datos incompletos | Imputación, outliers por IQR, días de atraso, tramos, previsión, features | Índice de morosidad 4,0 % (>90 días) |
| 4 | [Conciliación bancaria](04_conciliacion) | Cruzar extracto vs libro contable y explicar cada diferencia | Matching por etapas, tolerancias, clasificación de partidas, identidad de saldos | 96,5 % conciliado; diferencia de saldos explicada al 100 % |

Cada carpeta tiene su propio README con el problema de negocio, el flujo, las reglas aplicadas y los resultados.

## Cómo ejecutarlo

```bash
git clone https://github.com/arturoperez129/Portfolio-etl-banca.git
cd Portfolio-etl-banca
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux
pip install -r requirements-dev.txt
```

Con `make` (Mac/Linux): `make data`, `make run` y `make test`.

Sin `make` (Windows), para cada proyecto, por ejemplo el primero:

```bash
python 01_transacciones/scripts/generate_data.py
cd 01_transacciones
python -m etl_transacciones.pipeline
cd ..
```

Los módulos de cada proyecto son `etl_transacciones`, `etl_kyc`, `etl_mora` y `etl_conciliacion`. Para los tests, desde la carpeta principal: `pytest -q`.

## Estructura

```
.
├── 01_transacciones/
├── 02_kyc_clientes/
├── 03_cartera_mora/
├── 04_conciliacion/
│   Cada proyecto contiene:
│   ├── etl_<nombre>/      extract, transform, validate, load, pipeline
│   ├── scripts/           generate_data.py (datos sintéticos)
│   ├── tests/
│   ├── data/raw/
│   └── reports/           metricas.json
├── .github/workflows/ci.yml   lint + tests + ejecución de pipelines
└── pyproject.toml · requirements*.txt · Makefile
```

## Principios de diseño

- **Funciones puras** de transformación, testeables sin tocar disco.
- **Nada se descarta en silencio:** los registros rechazados se guardan con su `motivo_rechazo`.
- **Validaciones post-carga** que detienen el pipeline si se rompe una regla de calidad.
- **Métricas por ejecución** (`reports/metricas.json`) para auditar cuánto se limpió y por qué.
- **Reproducible:** semilla fija y CI en GitHub Actions (Python 3.10 y 3.12).

## Stack

`pandas` · `numpy` · `rapidfuzz` · `pyarrow` · `sqlite3` · `pytest` · `ruff` · GitHub Actions

## Aviso

Proyecto con fines educativos y de portafolio. Las reglas, umbrales y porcentajes de previsión son ilustrativos y no reflejan normativa vigente del BCP ni políticas de ninguna entidad.
