"""
etl/02_clean_kaggle.py
Pulisce il dataset Kaggle (budget, revenue, production info, lingue).
Output: data/processed/kaggle_movies.parquet
"""
import ast
import logging
import re
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_KAG   = REPO_ROOT / 'data' / 'raw' / 'kaggle'
PROCESSED = REPO_ROOT / 'data' / 'processed'

IMDB_ID_RE = re.compile(r'^tt([0-9]+)$', re.IGNORECASE)


def safe_parse(val) -> list:
    """
    Parsa un campo che contiene una stringa Python-dict o lista.
    Kaggle usa apici singoli ([{'id': 16, 'name': 'Animation'}]), non JSON valido —
    ast.literal_eval gestisce il formato, json.loads fallirebbe.
    Ritorna lista vuota in caso di errore.
    """
    try:
        if pd.notna(val) and val != '':
            result = ast.literal_eval(val)
            return result if isinstance(result, list) else []
        return []
    except (ValueError, SyntaxError):
        return []


def normalize_imdb_id(value) -> str | None:
    """Restituisce un IMDb ID canonico oppure None per valori mancanti/non validi."""
    if pd.isna(value):
        return None
    match = IMDB_ID_RE.fullmatch(str(value).strip())
    return f'tt{match.group(1)}' if match else None


def extract_genres(genres: list) -> list[str]:
    """Normalizza i nomi genere Kaggle al vocabolario usato da IMDb."""
    names = []
    seen = set()
    for genre in genres:
        if not isinstance(genre, dict) or not genre.get('name'):
            continue
        name = str(genre['name']).strip()
        if name == 'Science Fiction':
            name = 'Sci-Fi'
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)

    logging.info('=== STEP 1: Caricamento movies_metadata.csv ===')
    meta = pd.read_csv(RAW_KAG / 'movies_metadata.csv', low_memory=False)
    logging.info(f'Righe raw: {len(meta):,}')
    meta['_source_row'] = range(len(meta))

    # Conserva l'identificatore dichiarato dalla fonte, ma solo se sintatticamente valido.
    meta['source_imdb_id'] = meta['imdb_id'].apply(normalize_imdb_id)

    # Alcune righe hanno id non numerico (es. '/collection/...')
    # id non numerici = righe artefatto del CSV, non film validi
    meta['id'] = pd.to_numeric(meta['id'], errors='coerce')
    meta = meta.dropna(subset=['id'])
    meta['id'] = meta['id'].astype(int)
    logging.info(f'Righe dopo filtro id numerico: {len(meta):,}')

    # Budget e revenue: cast a numeric; 0 → None
    # budget=0 in Kaggle = dato mancante, non budget reale — tenere 0 distorcerebbe ROI
    for col in ['budget', 'revenue']:
        meta[col] = pd.to_numeric(meta[col], errors='coerce')
        meta[col] = meta[col].where(meta[col] > 0, other=None)
    logging.info(f'Film con budget disponibile: {meta["budget"].notna().sum():,}')
    logging.info(f'Film con revenue disponibile: {meta["revenue"].notna().sum():,}')

    # Anno di uscita da release_date — float64 con NaN (compatibile parquet/SQLAlchemy)
    meta['release_year'] = pd.to_datetime(
        meta['release_date'], errors='coerce'
    ).dt.year

    meta['runtime'] = pd.to_numeric(meta['runtime'], errors='coerce')

    logging.info('=== STEP 2: Parsing campi JSON ===')
    meta['genres_parsed']      = meta['genres'].apply(safe_parse)
    meta['companies_parsed']   = meta['production_companies'].apply(safe_parse)
    meta['countries_parsed']   = meta['production_countries'].apply(safe_parse)
    meta['languages_parsed']   = meta['spoken_languages'].apply(safe_parse)

    meta['genre_names'] = meta['genres_parsed'].apply(extract_genres)
    meta['original_language'] = meta.get('original_language', pd.Series(dtype=str))
    logging.info(f'Campi JSON parsati. Esempio companies: {meta["companies_parsed"].iloc[0] if len(meta) > 0 else []}')

    # Un TMDB ID deve produrre una sola riga. Preferiamo un source ID valido e poi
    # la riga piu' completa; l'ordine sorgente e' solo l'ultimo tie-break stabile.
    scalar_quality_cols = [
        'title', 'original_title', 'release_year', 'runtime', 'budget', 'revenue',
        'original_language',
    ]
    list_quality_cols = [
        'genre_names', 'companies_parsed', 'countries_parsed', 'languages_parsed',
    ]
    meta['_record_quality'] = sum(
        (
            meta[col].notna() & meta[col].astype(str).str.strip().ne('')
        ).astype('int8')
        for col in scalar_quality_cols
    )
    meta['_record_quality'] += sum(
        meta[col].apply(bool).astype('int8')
        for col in list_quality_cols
    )
    meta['_has_source_imdb_id'] = meta['source_imdb_id'].notna()
    before_meta_dedup = len(meta)
    meta = (
        meta.sort_values(
            ['id', '_has_source_imdb_id', '_record_quality', '_source_row'],
            ascending=[True, False, False, True],
            kind='mergesort',
        )
        .drop_duplicates(subset=['id'], keep='first')
    )
    logging.info(
        f'Metadata duplicati tmdb_id rimossi deterministicamente: '
        f'{before_meta_dedup - len(meta):,}'
    )

    result_columns = [
        'id', 'source_imdb_id', 'title', 'original_title', 'release_year', 'runtime',
        'budget', 'revenue', 'original_language',
        'genre_names', 'companies_parsed', 'countries_parsed', 'languages_parsed',
    ]
    result = pd.DataFrame(meta.loc[:, result_columns]).rename(columns={
        'id':     'tmdb_id',
        'budget': 'budget_usd',
        'revenue':'revenue_usd',
    })
    result = result.sort_values('tmdb_id', kind='mergesort').reset_index(drop=True)

    result.to_parquet(PROCESSED / 'kaggle_movies.parquet', index=False)
    logging.info(f'kaggle_movies.parquet: {len(result):,} righe')
    logging.info('=== 02_clean_kaggle.py COMPLETATO ===')


if __name__ == '__main__':
    main()
