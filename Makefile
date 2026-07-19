PYTHON ?= .venv/bin/python

.PHONY: help download etl-reconciled etl-dw olap all clean

help:
	@echo "DataMan_Cinema — Makefile"
	@echo ""
	@echo "Target:"
	@echo "  download           Scarica dataset raw IMDb + Kaggle"
	@echo "  etl-reconciled     Pipeline completa Reconciled Layer (DDL → clean → reconcile → load)"
	@echo "  etl-dw             Costruisce Data Warehouse (DDL → FDW → ETL)"
	@echo "  olap               Esegue tutte le query OLAP + export CSV"
	@echo "  all                Esecuzione end-to-end (download → olap)"
	@echo "  clean              Rimuove dati raw/processed (mantiene .gitkeep)"

download:
	bash data/download_data.sh

etl-reconciled: download
	psql -X -v ON_ERROR_STOP=1 -d cinema_reconciled -f sql/reconciled_ddl.sql
	$(PYTHON) etl/01_clean_imdb.py
	$(PYTHON) etl/02_clean_kaggle.py
	$(PYTHON) etl/03_reconcile_ids.py
	$(PYTHON) etl/04_load_reconciled.py

etl-dw:
	psql -X -v ON_ERROR_STOP=1 -d cinema_dw -f sql/dw_ddl.sql
	psql -X -v ON_ERROR_STOP=1 -d cinema_dw -f sql/etl_load.sql

olap:
	$(PYTHON) scripts/run_olap.py

all: etl-reconciled etl-dw olap

clean:
	rm -f data/raw/imdb/*.tsv data/raw/kaggle/*.csv data/raw/kaggle/*.json data/processed/*.parquet
	touch data/raw/imdb/.gitkeep data/raw/kaggle/.gitkeep data/processed/.gitkeep
	@echo "Pulito. I .gitkeep sono preservati."
