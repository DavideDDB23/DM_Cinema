#!/usr/bin/env bash
# ============================================================
# FILE: data/download_data.sh
# Scarica i dataset raw IMDb + Kaggle.
# Eseguire una sola volta. La dimensione effettiva è riportata al termine.
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAW_IMDB="${SCRIPT_DIR}/raw/imdb"
RAW_KAGGLE="${SCRIPT_DIR}/raw/kaggle"

mkdir -p "${RAW_IMDB}" "${RAW_KAGGLE}"

# --- Pre-checks ---------------------------------------------------------------
if ! command -v wget >/dev/null 2>&1; then
    echo "ERROR: wget non trovato. Installa con 'brew install wget' (macOS) o 'apt-get install wget' (Linux)."
    exit 1
fi

# --- IMDb ---------------------------------------------------------------------
echo "==> Downloading IMDb datasets to ${RAW_IMDB}..."
IMDB_FILES=(
    "title.basics.tsv.gz"
    "title.ratings.tsv.gz"
    "title.crew.tsv.gz"
    "title.principals.tsv.gz"
    "name.basics.tsv.gz"
)
for f in "${IMDB_FILES[@]}"; do
    if [ -f "${RAW_IMDB}/${f%.gz}" ] || [ -f "${RAW_IMDB}/${f}" ]; then
        echo "  - ${f} già presente, skip."
    else
        echo "  - downloading ${f}..."
        wget -q --show-progress -P "${RAW_IMDB}" "https://datasets.imdbws.com/${f}"
    fi
done

echo "==> Decompressing IMDb TSV files..."
# gunzip -k keep original .gz; -f force overwrite if uncompressed already exists
for f in "${IMDB_FILES[@]}"; do
    if [ -f "${RAW_IMDB}/${f}" ]; then
        gunzip -kf "${RAW_IMDB}/${f}"
        rm -f "${RAW_IMDB}/${f}"
    fi
done

# --- Kaggle -------------------------------------------------------------------
echo "==> Downloading Kaggle 'The Movies Dataset' to ${RAW_KAGGLE}..."
if [ -f "${RAW_KAGGLE}/movies_metadata.csv" ] && [ -f "${RAW_KAGGLE}/credits.csv" ]; then
    echo "  - movies_metadata.csv e credits.csv già presenti, skip."
else
    if ! command -v kaggle >/dev/null 2>&1; then
        echo "ERROR: kaggle CLI non trovato. Installa con 'pip install kaggle' e configura ~/.kaggle/kaggle.json"
        echo "       (vedi README.md sezione Prerequisiti)"
        exit 1
    fi
    if [ ! -f "${HOME}/.kaggle/kaggle.json" ]; then
        echo "ERROR: ~/.kaggle/kaggle.json non trovato. Crea API token su https://www.kaggle.com/settings/account"
        exit 1
    fi
    kaggle datasets download -d rounakbanik/the-movies-dataset -p "${RAW_KAGGLE}/"
    echo "==> Unzipping Kaggle archive..."
    unzip -o -q "${RAW_KAGGLE}/the-movies-dataset.zip" -d "${RAW_KAGGLE}/"
    rm -f "${RAW_KAGGLE}/the-movies-dataset.zip"
fi

# --- Sanity check -------------------------------------------------------------
echo ""
echo "==> Done. Files:"
ls -lh "${RAW_IMDB}/"*.tsv 2>/dev/null || true
ls -lh "${RAW_KAGGLE}/"*.csv 2>/dev/null || true
echo ""
echo "Pipeline pronta. Prossimo step: 'python etl/01_clean_imdb.py'"
echo ""
echo "==> Dimensione totale dataset raw:"
du -sh "${SCRIPT_DIR}/raw"
