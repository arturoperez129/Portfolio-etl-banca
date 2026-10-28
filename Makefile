PROYECTOS = 01_transacciones:etl_transacciones 02_kyc_clientes:etl_kyc 03_cartera_mora:etl_mora 04_conciliacion:etl_conciliacion

setup:
	pip install -r requirements-dev.txt

data:
	@for p in $(PROYECTOS); do d=$${p%%:*}; python $$d/scripts/generate_data.py; done

run:
	@for p in $(PROYECTOS); do d=$${p%%:*}; k=$${p##*:}; (cd $$d && python -m $$k.pipeline); done

test:
	pytest -q

lint:
	ruff check .
