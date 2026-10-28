# Portafolio ETL y calidad de datos para banca y finanzas

[!\[CI](https://github.com/<tu-usuario>/portafolio-etl-banca/actions/workflows/ci.yml/badge.svg)](https://github.com/<arturoperez129>/portafolio-etl-banca/actions)
!\[Python](https://img.shields.io/badge/python-3.10%2B-blue)

Cuatro proyectos de **extracción, transformación y limpieza de datos** con Python, pensados para casos reales de un banco o financiera. Cada proyecto parte de datos sucios, aplica reglas de negocio, separa los registros rechazados, valida el resultado y publica métricas de calidad.

> \\\*\\\*Todos los datos son sintéticos.\\\*\\\* Se generan con scripts reproducibles que inyectan errores a propósito. No contienen información real de clientes, cédulas ni cuentas.

## Proyectos

|#|Proyecto|Problema de negocio|Técnicas|Resultado clave|
|-|-|-|-|-|
|1|[Pipeline de transacciones](01_transacciones)|Transacciones con duplicados, fechas inválidas y montos mal formateados distorsionan reportes y analítica|Parseo de fechas y montos, normalización de categorías, cuarentena de rechazos, carga a Parquet/SQLite|5.150 → 4.896 filas limpias; 254 rechazos con motivo|
|2|[Limpieza y deduplicación de clientes (KYC)](02_kyc_clientes)|Un mismo cliente cargado varias veces con datos inconsistentes|Estandarización de cédula, RUC (dígito verificador), teléfono, email; fuzzy matching con blocking; golden record|Precisión 100 % y recall 95,8 % en detección de duplicados|
|3|[Cartera de créditos y mora](03_cartera_mora)|Medir morosidad y preparar variables para scoring con datos incompletos|Imputación, outliers por IQR, días de atraso, tramos, previsión, features|Índice de morosidad 4,0 % (>90 días)|
|4|[Conciliación bancaria](04_conciliacion)|Cruzar extracto vs libro contable y explicar cada diferencia|Matching por etapas, tolerancias, clasificación de partidas, identidad de saldos|96,5 % conciliado; diferencia de saldos explicada al 100 %|

## Cómo Funciona

```bash
git clone https://github.com/<arturoperez129>/portafolio-etl-banca.git
cd portafolio-etl-banca
python -m venv .venv \\\&\\\& source .venv/bin/activate   # Windows: .venv\\\\Scripts\\\\activate
make setup      # instala dependencias
make data       # regenera los datasets sintéticos
make run        # ejecuta los 4 pipelines
make test       # corre los tests
```

Sin `make`: `pip install -r requirements-dev.txt`, luego dentro de cada carpeta `python -m etl\\\_<nombre>.pipeline`.

## Estructura

```
.
├── 01\\\_transacciones/    ├── etl\\\_transacciones/ (extract, transform, validate, load, pipeline)
├── 02\\\_kyc\\\_clientes/     ├── scripts/generate\\\_data.py   <- datos sintéticos
├── 03\\\_cartera\\\_mora/     ├── tests/
├── 04\\\_conciliacion/     ├── data/raw/ · reports/metricas.json
├── .github/workflows/ci.yml   <- lint + tests + ejecución de pipelines
└── pyproject.toml · requirements\\\*.txt · Makefile
```

## Principios de diseño

* **Funciones puras** de transformación, testeables sin tocar disco.
* **Nada se descarta en silencio:** los registros rechazados se guardan con su `motivo\\\_rechazo`.
* **Validaciones post-carga** que detienen el pipeline si se rompe una regla de calidad.
* **Métricas por ejecución** (`reports/metricas.json`) para auditar cuánto se limpió y por qué.
* **Reproducible:** semilla fija, CI en GitHub Actions (Python 3.10 y 3.12).

## Stack

`pandas` · `numpy` · `rapidfuzz` · `pyarrow` · `sqlite3` · `pytest` · `ruff` · GitHub Actions

## Aviso

Proyecto con fines educativos y de portafolio. Las reglas, umbrales y porcentajes de previsión son ilustrativos y no reflejan normativa vigente del BCP ni políticas de ninguna entidad.

