PYTHON ?= .venv/bin/python

.PHONY: help download etl-reconciled etl-dw olap all clean

help:
	@echo "DataMan_Cinema — Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  download           Download raw IMDb + Kaggle datasets"
	@echo "  etl-reconciled     Full Reconciled Layer pipeline (DDL → clean → reconcile → load)"
	@echo "  etl-dw             Build the Data Warehouse (DDL → FDW → ETL)"
	@echo "  olap               Run all OLAP queries and export CSVs"
	@echo "  all                End-to-end run (download → olap)"
	@echo "  clean              Remove raw/processed data (keeps .gitkeep)"

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
	@echo "Cleaned. .gitkeep files are preserved."
