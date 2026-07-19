"""
etl/04_load_reconciled.py
Carica i dati puliti nel PostgreSQL Reconciled Layer (cinema_reconciled).
Rispetta rigorosamente l'ordine FK:
  country → language → genre → production_company → film → person →
  film_genre → film_language → film_country → film_company → film_role

Legge DATABASE_URL dall'ambiente (o fallback a stringa di default).
"""
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED = REPO_ROOT / 'data' / 'processed'

load_dotenv(REPO_ROOT / '.env')

DB_URL = os.environ.get(
    'DATABASE_URL',
    f'postgresql://{os.environ.get("USER","postgres")}@localhost:5432/cinema_reconciled'
)

# Motivazione: Kaggle espone production_countries come ISO alpha-2; il DW richiede il roll-up a continent.
ISO_CONTINENT = {
    'AF': 'Asia',    # Afghanistan
    'AO': 'Africa', 'BJ': 'Africa', 'BW': 'Africa',
    'BF': 'Africa', 'BI': 'Africa', 'CM': 'Africa', 'CV': 'Africa',
    'CF': 'Africa', 'TD': 'Africa', 'KM': 'Africa', 'CG': 'Africa',
    'CD': 'Africa', 'DJ': 'Africa', 'EG': 'Africa', 'GQ': 'Africa',
    'ER': 'Africa', 'ET': 'Africa', 'GA': 'Africa', 'GM': 'Africa',
    'GH': 'Africa', 'GN': 'Africa', 'GW': 'Africa', 'CI': 'Africa',
    'KE': 'Africa', 'LS': 'Africa', 'LR': 'Africa', 'LY': 'Africa',
    'MG': 'Africa', 'MW': 'Africa', 'ML': 'Africa', 'MR': 'Africa',
    'MU': 'Africa', 'MA': 'Africa', 'MZ': 'Africa', 'NA': 'Africa',
    'NE': 'Africa', 'NG': 'Africa', 'RW': 'Africa', 'ST': 'Africa',
    'SN': 'Africa', 'SL': 'Africa', 'SO': 'Africa', 'ZA': 'Africa',
    'SS': 'Africa', 'SD': 'Africa', 'SZ': 'Africa', 'TZ': 'Africa',
    'TG': 'Africa', 'TN': 'Africa', 'UG': 'Africa', 'ZM': 'Africa',
    'ZW': 'Africa', 'DZ': 'Africa',
    'AG': 'North America', 'BS': 'North America', 'BB': 'North America',
    'BZ': 'North America', 'CA': 'North America', 'CR': 'North America',
    'CU': 'North America', 'DM': 'North America', 'DO': 'North America',
    'SV': 'North America', 'GD': 'North America', 'GT': 'North America',
    'HT': 'North America', 'HN': 'North America', 'JM': 'North America',
    'MX': 'North America', 'NI': 'North America', 'PA': 'North America',
    'PR': 'North America', 'KN': 'North America', 'LC': 'North America',
    'VC': 'North America', 'TT': 'North America', 'US': 'North America',
    'AR': 'South America', 'BO': 'South America', 'BR': 'South America',
    'CL': 'South America', 'CO': 'South America', 'EC': 'South America',
    'GY': 'South America', 'PY': 'South America', 'PE': 'South America',
    'SR': 'South America', 'UY': 'South America', 'VE': 'South America',
    'AL': 'Europe', 'AD': 'Europe', 'AT': 'Europe', 'BY': 'Europe',
    'BE': 'Europe', 'BA': 'Europe', 'BG': 'Europe', 'HR': 'Europe',
    'CY': 'Europe', 'CZ': 'Europe', 'DK': 'Europe', 'EE': 'Europe',
    'FI': 'Europe', 'FR': 'Europe', 'DE': 'Europe', 'GR': 'Europe',
    'HU': 'Europe', 'IS': 'Europe', 'IE': 'Europe', 'IT': 'Europe',
    'XK': 'Europe', 'LV': 'Europe', 'LI': 'Europe', 'LT': 'Europe',
    'LU': 'Europe', 'MK': 'Europe', 'MT': 'Europe', 'MD': 'Europe',
    'MC': 'Europe', 'ME': 'Europe', 'NL': 'Europe', 'NO': 'Europe',
    'PL': 'Europe', 'PT': 'Europe', 'RO': 'Europe', 'RU': 'Europe',
    'SM': 'Europe', 'RS': 'Europe', 'SK': 'Europe', 'SI': 'Europe',
    'ES': 'Europe', 'SE': 'Europe', 'CH': 'Europe', 'UA': 'Europe',
    'GB': 'Europe', 'VA': 'Europe',
    'AM': 'Asia', 'AZ': 'Asia', 'BH': 'Asia',
    'BD': 'Asia', 'BT': 'Asia', 'BN': 'Asia', 'KH': 'Asia',
    'CN': 'Asia', 'GE': 'Asia', 'HK': 'Asia', 'IN': 'Asia',
    'ID': 'Asia', 'IR': 'Asia', 'IQ': 'Asia', 'IL': 'Asia',
    'JP': 'Asia', 'JO': 'Asia', 'KZ': 'Asia', 'KW': 'Asia',
    'KG': 'Asia', 'LA': 'Asia', 'LB': 'Asia', 'MO': 'Asia',
    'MY': 'Asia', 'MV': 'Asia', 'MN': 'Asia', 'MM': 'Asia',
    'NP': 'Asia', 'KP': 'Asia', 'OM': 'Asia', 'PK': 'Asia',
    'PS': 'Asia', 'PH': 'Asia', 'QA': 'Asia', 'SA': 'Asia',
    'SG': 'Asia', 'KR': 'Asia', 'LK': 'Asia', 'SY': 'Asia',
    'TW': 'Asia', 'TJ': 'Asia', 'TH': 'Asia', 'TL': 'Asia',
    'TR': 'Asia', 'TM': 'Asia', 'AE': 'Asia', 'UZ': 'Asia',
    'VN': 'Asia', 'YE': 'Asia',
    'AU': 'Oceania', 'FJ': 'Oceania', 'KI': 'Oceania', 'MH': 'Oceania',
    'FM': 'Oceania', 'NR': 'Oceania', 'NZ': 'Oceania', 'PW': 'Oceania',
    'PG': 'Oceania', 'WS': 'Oceania', 'SB': 'Oceania', 'TO': 'Oceania',
    'TV': 'Oceania', 'VU': 'Oceania',
}

# Motivazione: Q3 deve fare DICE su una gerarchia linguistica, non solo su codici ISO atomici.
LANG_FAMILY = {
    'en': 'Indo-European/Germanic', 'de': 'Indo-European/Germanic',
    'nl': 'Indo-European/Germanic', 'sv': 'Indo-European/Germanic',
    'da': 'Indo-European/Germanic', 'no': 'Indo-European/Germanic',
    'is': 'Indo-European/Germanic', 'af': 'Indo-European/Germanic',
    'fr': 'Indo-European/Romance', 'es': 'Indo-European/Romance',
    'pt': 'Indo-European/Romance', 'it': 'Indo-European/Romance',
    'ro': 'Indo-European/Romance', 'ca': 'Indo-European/Romance',
    'ru': 'Indo-European/Slavic', 'pl': 'Indo-European/Slavic',
    'cs': 'Indo-European/Slavic', 'sk': 'Indo-European/Slavic',
    'uk': 'Indo-European/Slavic', 'bg': 'Indo-European/Slavic',
    'sr': 'Indo-European/Slavic', 'hr': 'Indo-European/Slavic',
    'sl': 'Indo-European/Slavic',
    'hi': 'Indo-European/Indo-Iranian', 'ur': 'Indo-European/Indo-Iranian',
    'bn': 'Indo-European/Indo-Iranian', 'pa': 'Indo-European/Indo-Iranian',
    'fa': 'Indo-European/Indo-Iranian',
    'el': 'Indo-European/Other', 'lt': 'Indo-European/Other',
    'lv': 'Indo-European/Other',
    'zh': 'Sino-Tibetan', 'yue': 'Sino-Tibetan',
    'ja': 'Japonic', 'ko': 'Koreanic',
    'ar': 'Afro-Asiatic', 'he': 'Afro-Asiatic',
    'tr': 'Turkic', 'az': 'Turkic', 'kk': 'Turkic', 'uz': 'Turkic',
    'fi': 'Uralic', 'hu': 'Uralic', 'et': 'Uralic',
    'id': 'Austronesian', 'ms': 'Austronesian', 'tl': 'Austronesian',
    'vi': 'Austroasiatic', 'km': 'Austroasiatic', 'th': 'Kra-Dai',
}


def safe_list(val) -> list:
    """
    Converte colonne parquet (numpy.ndarray, lista Python, None/NaN) in lista Python.
    pandas+pyarrow restituisce list-of-dict come ndarray; operatori bool su ndarray
    multi-elemento alzano ValueError.
    """
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, np.ndarray):
        return val.tolist()
    if hasattr(val, 'tolist'):
        return val.tolist()
    try:
        if pd.isna(val):
            return []
    except (TypeError, ValueError):
        pass
    return []


def normalize_code(value) -> str:
    """Normalizza un codice sorgente scalare, trattando None/NaN come assente."""
    if value is None:
        return ''
    try:
        if pd.isna(value):
            return ''
    except (TypeError, ValueError):
        return ''
    return str(value).lower().strip()


def canonical_genre(value) -> str:
    """Restituisce il vocabolario genere canonico condiviso da IMDb e Kaggle."""
    if value is None:
        return ''
    try:
        if pd.isna(value):
            return ''
    except (TypeError, ValueError):
        return ''
    name = str(value).strip()
    return 'Sci-Fi' if name == 'Science Fiction' else name


def validate_reconciliation_keys(
    imdb: pd.DataFrame,
    kaggle: pd.DataFrame,
    reconciled: pd.DataFrame,
) -> None:
    keys = (
        ('IMDb', imdb, 'imdb_id'),
        ('Kaggle', kaggle, 'tmdb_id'),
        ('reconciliation TMDB', reconciled, 'tmdb_id'),
        ('reconciliation IMDb', reconciled, 'imdb_id'),
    )

    for name, frame, column in keys:
        values = frame[column]
        if values.isna().any() or values.duplicated().any():
            raise ValueError(f'{name}: invalid {column} key')

    unknown_tmdb = set(reconciled['tmdb_id']) - set(kaggle['tmdb_id'])
    if unknown_tmdb:
        raise ValueError('Reconciliation references unknown TMDB IDs')

    unknown_imdb = set(reconciled['imdb_id']) - set(imdb['imdb_id'])
    if unknown_imdb:
        raise ValueError('Reconciliation references unknown IMDb IDs')


def get_engine():
    return create_engine(DB_URL)


def load_countries(conn, kaggle: pd.DataFrame) -> dict:
    """Ritorna mapping iso_code → country_id appena inserito."""
    logging.info('=== Caricamento country ===')
    rows = []
    seen: set = set()
    for _, row in kaggle.iterrows():
        for c in safe_list(row['countries_parsed']):
            if isinstance(c, dict) and 'iso_3166_1' in c:
                iso = c['iso_3166_1'].upper()
                if iso and iso not in seen:
                    seen.add(iso)
                    rows.append({
                        'iso_code':     iso,
                        'country_name': c.get('name', iso),
                        'continent':    ISO_CONTINENT.get(iso, 'Other'),
                    })
    df = pd.DataFrame(rows)
    before_dedup = len(df)
    df = df.drop_duplicates('iso_code')
    logging.info(f'  country duplicati iso_code rimossi: {before_dedup - len(df):,}')
    df.to_sql('country', conn, if_exists='append', index=False, method='multi', chunksize=500)
    logging.info(f'  → {len(df)} paesi caricati')

    result = pd.read_sql('SELECT country_id, iso_code FROM country', conn)
    return dict(zip(result['iso_code'].str.strip(), result['country_id']))


def load_languages(conn, kaggle: pd.DataFrame) -> dict:
    logging.info('=== Caricamento language ===')
    rows = []
    seen: set = set()
    # Prima conserva i nomi disponibili in spoken_languages.
    for _, row in kaggle.iterrows():
        for l in safe_list(row['languages_parsed']):
            if isinstance(l, dict):
                iso = normalize_code(l.get('iso_639_1'))
                if iso and iso not in seen:
                    seen.add(iso)
                    raw_name = l.get('name')
                    name = raw_name.strip() if isinstance(raw_name, str) else ''
                    rows.append({
                        'iso_code':        iso,
                        'language_name':   name or iso,
                        'language_family': LANG_FAMILY.get(iso, 'Other'),
                    })

    # original_language puo' contenere codici assenti da spoken_languages.
    for value in kaggle['original_language']:
        iso = normalize_code(value)
        if iso and iso not in seen:
            seen.add(iso)
            rows.append({
                'iso_code':        iso,
                'language_name':   iso,
                'language_family': LANG_FAMILY.get(iso, 'Other'),
            })

    df = pd.DataFrame(
        rows,
        columns=['iso_code', 'language_name', 'language_family'],
    )
    before_dedup = len(df)
    df = df.drop_duplicates('iso_code')
    logging.info(f'  language duplicati iso_code rimossi: {before_dedup - len(df):,}')
    df = df[df['iso_code'] != '']
    df.to_sql('language', conn, if_exists='append', index=False, method='multi', chunksize=500)
    logging.info(f'  → {len(df)} lingue caricate')

    result = pd.read_sql('SELECT language_id, iso_code FROM language', conn)
    # Motivazione: CHAR(8) in PostgreSQL padda con spazi; strip evita mismatch sulle bridge table.
    return dict(zip(result['iso_code'].str.strip(), result['language_id']))


def load_genres(conn, imdb: pd.DataFrame, kaggle: pd.DataFrame) -> dict:
    logging.info('=== Caricamento genre ===')
    all_genres: set = set()
    for lst in imdb['genres_list']:
        all_genres.update(canonical_genre(value) for value in safe_list(lst))
    for lst in kaggle['genre_names']:
        all_genres.update(canonical_genre(value) for value in safe_list(lst))
    all_genres.discard('')
    df = pd.DataFrame({'genre_name': sorted(all_genres)})
    df.to_sql('genre', conn, if_exists='append', index=False)
    logging.info(f'  → {len(df)} generi caricati')

    result = pd.read_sql('SELECT genre_id, genre_name FROM genre', conn)
    return dict(zip(result['genre_name'], result['genre_id']))


def load_persons(conn, persons: pd.DataFrame,
                 referenced_nconsts: set[str]) -> dict:
    logging.info('=== Caricamento person ===')
    df = persons.loc[
        persons['nconst'].isin(list(referenced_nconsts)),
        ['nconst', 'primaryName', 'birthYear'],
    ].copy()
    df.columns = ['imdb_nconst', 'name', 'birth_year']
    logging.info(f'  Persone referenziate dai film caricati: {len(df):,}')
    before_drop = len(df)
    df = df.dropna(subset=['name'])
    logging.info(f"  Drop persone senza name: {before_drop - len(df)}")
    df.to_sql('person', conn, if_exists='append', index=False, method='multi', chunksize=5000)
    logging.info(f'  → {len(df)} persone caricate')

    result = pd.read_sql('SELECT person_id, imdb_nconst FROM person WHERE imdb_nconst IS NOT NULL', conn)
    return dict(zip(result['imdb_nconst'], result['person_id']))


def load_companies(conn, kaggle: pd.DataFrame) -> dict:
    logging.info('=== Caricamento production_company ===')
    rows = []
    seen: set = set()
    for _, row in kaggle.iterrows():
        for c in safe_list(row['companies_parsed']):
            if isinstance(c, dict) and c.get('name'):
                name = str(c['name']).strip()
                if name and name not in seen:
                    seen.add(name)
                    rows.append({'company_name': name})
    df = pd.DataFrame(rows)
    df.to_sql('production_company', conn, if_exists='append', index=False, method='multi', chunksize=1000)
    logging.info(f'  → {len(df)} production companies caricate')

    result = pd.read_sql('SELECT company_id, company_name FROM production_company', conn)
    return dict(zip(result['company_name'], result['company_id']))


def load_films(conn, kaggle: pd.DataFrame, imdb: pd.DataFrame,
               reconciled: pd.DataFrame) -> dict:
    """
    Ritorna mapping tmdb_id → film_id (PK assegnato da PostgreSQL).
    Strategia: part dai film Kaggle che hanno budget/revenue (il nostro dato chiave),
    arricchisci con imdb_id + rating/votes tramite reconciled_index.
    """
    logging.info('=== Caricamento film ===')
    merged = kaggle.merge(
        reconciled[['tmdb_id', 'imdb_id']],
        on='tmdb_id',
        how='left',
        validate='one_to_one',
    )

    imdb_sub = imdb[['imdb_id', 'avg_rating', 'num_votes', 'release_year',
                      'runtime_min', 'title', 'original_title']].copy()
    merged = merged.merge(
        imdb_sub,
        on='imdb_id',
        how='left',
        suffixes=('_kg', '_imdb'),
        validate='many_to_one',
    )

    # Motivazione: IMDb e' piu' canonico per titolo/anno, Kaggle resta fonte dei dati economici.
    merged['final_title']    = merged['title_imdb'].combine_first(merged['title_kg'])
    merged['final_year']     = merged['release_year_imdb'].combine_first(merged['release_year_kg'])
    # Motivazione: Kaggle ha runtime piu' completo; IMDb e' fallback quando manca.
    merged['final_runtime']  = merged['runtime'].combine_first(merged['runtime_min'])
    merged['final_og_title'] = merged['original_title_imdb'].combine_first(merged['original_title_kg'])

    films_df = pd.DataFrame({
        'imdb_id':        merged['imdb_id'],
        'tmdb_id':        merged['tmdb_id'],
        'title':          merged['final_title'],
        'original_title': merged['final_og_title'],
        'release_year':   merged['final_year'],
        'runtime_min':    merged['final_runtime'],
        'budget_usd':     merged['budget_usd'],
        'revenue_usd':    merged['revenue_usd'],
        'avg_rating':     merged['avg_rating'],
        'num_votes':      merged['num_votes'],
    })
    before_drop_title = len(films_df)
    # Motivazione: senza titolo il film non e' presentabile ne' utile in demo/report.
    films_df = films_df.dropna(subset=['title'])
    logging.info(f'  Film dopo drop title: {len(films_df):,} (rimossi {before_drop_title - len(films_df):,})')

    films_df.to_sql('film', conn, if_exists='append', index=False, method='multi', chunksize=1000)
    logging.info(f'  → {len(films_df)} film caricati')

    result = pd.read_sql('SELECT film_id, tmdb_id FROM film WHERE tmdb_id IS NOT NULL', conn)
    return dict(zip(result['tmdb_id'].astype(int), result['film_id']))


def load_film_genres(conn, kaggle: pd.DataFrame, imdb: pd.DataFrame,
                     reconciled: pd.DataFrame, film_map: dict,
                     genre_map: dict):
    logging.info('=== Caricamento film_genre ===')
    imdb_genres = dict(zip(imdb['imdb_id'], imdb['genres_list']))
    kag_genres = kaggle[['tmdb_id', 'genre_names']].merge(
        reconciled[['tmdb_id', 'imdb_id']],
        on='tmdb_id',
        how='left',
        validate='one_to_one',
    )

    rows = []
    for _, row in kag_genres.iterrows():
        film_id = film_map.get(int(row['tmdb_id']))
        if film_id is None:
            continue
        imdb_id = row.get('imdb_id')
        # Motivazione: safe_list normalizza ndarray/None prodotti da parquet prima dell'iterazione.
        genres = [
            genre_name
            for value in safe_list(imdb_genres.get(imdb_id))
            if (genre_name := canonical_genre(value))
        ] if pd.notna(imdb_id) else []
        if not genres:
            # Motivazione: IMDb e' preferito per i generi; Kaggle copre i film senza match IMDb.
            genres = [
                genre_name
                for value in safe_list(row['genre_names'])
                if (genre_name := canonical_genre(value))
            ]
        for genre_name in genres:
            gid = genre_map.get(genre_name)
            if gid is None:
                raise ValueError(
                    f'Genre {genre_name!r} for tmdb_id {row["tmdb_id"]} '
                    'is missing from the genre dimension'
                )
            rows.append({'film_id': film_id, 'genre_id': gid})

    df = pd.DataFrame(rows)
    before_dedup = len(df)
    # Motivazione: lo stesso genere puo' arrivare da sorgenti multiple; la bridge table vuole coppie uniche.
    df = df.drop_duplicates()
    logging.info(f'  film_genre duplicati rimossi: {before_dedup - len(df):,}')
    df.to_sql('film_genre', conn, if_exists='append', index=False, method='multi', chunksize=2000)
    logging.info(f'  → {len(df)} film_genre righe caricate')


def load_film_languages(conn, kaggle: pd.DataFrame,
                         film_map: dict, lang_map: dict):
    logging.info('=== Caricamento film_language ===')
    rows = []
    expected_original_films: set = set()
    for _, row in kaggle.iterrows():
        film_id = film_map.get(int(row['tmdb_id']))
        if film_id is None:
            continue
        orig_iso = normalize_code(row.get('original_language'))
        for l in safe_list(row['languages_parsed']):
            if not isinstance(l, dict):
                continue
            iso = normalize_code(l.get('iso_639_1'))
            lid = lang_map.get(iso)
            if lid is not None:
                rows.append({
                    'film_id':     film_id,
                    'language_id': lid,
                    'is_original': (iso == orig_iso),
                })

        if orig_iso:
            original_language_id = lang_map.get(orig_iso)
            if original_language_id is None:
                raise ValueError(
                    f'Original language {orig_iso!r} for tmdb_id '
                    f'{row["tmdb_id"]} is missing from the language dimension'
                )
            expected_original_films.add(film_id)
            rows.append({
                'film_id': film_id,
                'language_id': original_language_id,
                'is_original': True,
            })

    df = pd.DataFrame(
        rows,
        columns=['film_id', 'language_id', 'is_original'],
    )
    before_dedup = len(df)
    # max() conserva True se la stessa lingua arriva sia come spoken che original.
    df = df.groupby(
        ['film_id', 'language_id'],
        as_index=False,
        sort=False,
    )['is_original'].max()
    logging.info(f'  film_language duplicati rimossi: {before_dedup - len(df):,}')

    original_counts = df.loc[df['is_original']].groupby('film_id').size()
    multiple_originals = original_counts[original_counts > 1]
    if not multiple_originals.empty:
        sample = ', '.join(str(value) for value in multiple_originals.index[:5])
        raise ValueError(
            'film_language invariant violated: more than one original '
            f'language for film_id values including {sample}'
        )

    actual_original_films = set(df.loc[df['is_original'], 'film_id'])
    missing_originals = expected_original_films.difference(actual_original_films)
    if missing_originals:
        sample = ', '.join(str(value) for value in list(missing_originals)[:5])
        raise ValueError(
            'film_language invariant violated: source original_language was '
            f'not preserved for film_id values including {sample}'
        )

    df.to_sql('film_language', conn, if_exists='append', index=False, method='multi', chunksize=2000)
    logging.info(f'  → {len(df)} film_language righe caricate')


def load_film_countries(conn, kaggle: pd.DataFrame,
                        film_map: dict, country_map: dict):
    logging.info('=== Caricamento film_country ===')
    rows = []
    for _, row in kaggle.iterrows():
        film_id = film_map.get(int(row['tmdb_id']))
        if film_id is None:
            continue

        countries = safe_list(row['countries_parsed'])
        for idx, c in enumerate(countries):
            if not isinstance(c, dict):
                continue
            iso = str(c.get('iso_3166_1', '')).upper().strip()
            country_id = country_map.get(iso)
            if country_id:
                rows.append({
                    'film_id': film_id,
                    'country_id': country_id,
    # primo paese nella lista = primary production country
                    'is_primary': idx == 0,
                })

    df = pd.DataFrame(rows)
    before_dedup = len(df)
    # Motivazione: paesi ripetuti nel JSON non devono moltiplicare il fact table.
    df = df.drop_duplicates(subset=['film_id', 'country_id'])
    logging.info(f'  film_country duplicati rimossi: {before_dedup - len(df):,}')
    df.to_sql('film_country', conn, if_exists='append', index=False, method='multi', chunksize=2000)
    logging.info(f'  → {len(df)} film_country righe caricate')


def load_film_companies(conn, kaggle: pd.DataFrame,
                        film_map: dict, company_map: dict):
    logging.info('=== Caricamento film_company ===')
    rows = []
    for _, row in kaggle.iterrows():
        film_id = film_map.get(int(row['tmdb_id']))
        if film_id is None:
            continue
        for c in safe_list(row['companies_parsed']):
            if isinstance(c, dict) and c.get('name'):
                cid = company_map.get(str(c['name']).strip())
                if cid:
                    rows.append({'film_id': film_id, 'company_id': cid})
    df = pd.DataFrame(rows)
    before_dedup = len(df)
    # Motivazione: company ripetute nel JSON vanno compresse in una bridge table senza duplicati.
    df = df.drop_duplicates()
    logging.info(f'  film_company duplicati rimossi: {before_dedup - len(df):,}')
    df.to_sql('film_company', conn, if_exists='append', index=False, method='multi', chunksize=2000)
    logging.info(f'  → {len(df)} film_company righe caricate')


def load_film_roles(conn, roles: pd.DataFrame,
                    film_map_by_imdb: dict, person_map: dict):
    """
    film_map_by_imdb: imdb_id → film_id
    person_map: imdb_nconst → person_id
    """
    logging.info('=== Caricamento film_role ===')
    roles_f = roles[roles['tconst'].isin(film_map_by_imdb)].copy()
    logging.info(f'  Roles con film corrispondente: {len(roles_f):,}')

    roles_f['film_id']   = roles_f['tconst'].map(film_map_by_imdb)
    roles_f['person_id'] = roles_f['nconst'].map(person_map)

    # Motivazione: senza person_id la FK non e' rispettabile in film_role.
    before_fk_drop = len(roles_f)
    roles_f = roles_f.dropna(subset=['film_id', 'person_id'])
    logging.info(f'  Roles droppati per FK mancanti: {before_fk_drop - len(roles_f):,}')
    roles_f['film_id']   = roles_f['film_id'].astype(int)
    roles_f['person_id'] = roles_f['person_id'].astype(int)

    df = roles_f[['film_id', 'person_id', 'role_type', 'character_name']].copy()
    before_dedup = len(df)
    # Motivazione: una persona ripetuta nello stesso film/ruolo deve produrre una sola relazione.
    df = df.drop_duplicates(subset=['film_id', 'person_id', 'role_type'])
    logging.info(f'  film_role duplicati rimossi: {before_dedup - len(df):,}')

    df.to_sql('film_role', conn, if_exists='append', index=False, method='multi', chunksize=2000)
    logging.info(f'  → {len(df)} film_role righe caricate')


def main():
    logging.info('=== Caricamento parquet ===')
    imdb       = pd.read_parquet(PROCESSED / 'imdb_movies.parquet')
    kaggle     = pd.read_parquet(PROCESSED / 'kaggle_movies.parquet')
    persons    = pd.read_parquet(PROCESSED / 'imdb_persons.parquet')
    roles      = pd.read_parquet(PROCESSED / 'imdb_roles.parquet')
    reconciled = pd.read_parquet(PROCESSED / 'reconciled_index.parquet')
    validate_reconciliation_keys(imdb, kaggle, reconciled)
    logging.info(f'IMDb: {len(imdb):,} | Kaggle: {len(kaggle):,} | Persons: {len(persons):,} | Roles: {len(roles):,} | Reconciled: {len(reconciled):,}')

    engine = get_engine()
    try:
        with engine.begin() as conn:
            logging.info('Connessione PostgreSQL OK')
            country_map = load_countries(conn, kaggle)
            lang_map = load_languages(conn, kaggle)
            genre_map = load_genres(conn, imdb, kaggle)
            company_map = load_companies(conn, kaggle)
            film_map = load_films(conn, kaggle, imdb, reconciled)

            film_ids_df = pd.read_sql(
                'SELECT film_id, imdb_id FROM film WHERE imdb_id IS NOT NULL',
                conn,
            )
            film_map_by_imdb = dict(
                zip(film_ids_df['imdb_id'], film_ids_df['film_id'])
            )

            roles_for_loaded_films = roles[
                roles['tconst'].isin(film_map_by_imdb)
            ].copy()
            referenced_nconsts = set(roles_for_loaded_films['nconst'].dropna())
            person_map = load_persons(conn, persons, referenced_nconsts)

            load_film_genres(conn, kaggle, imdb, reconciled, film_map, genre_map)
            load_film_languages(conn, kaggle, film_map, lang_map)
            load_film_countries(conn, kaggle, film_map, country_map)
            load_film_companies(conn, kaggle, film_map, company_map)
            load_film_roles(
                conn,
                roles_for_loaded_films,
                film_map_by_imdb,
                person_map,
            )
    finally:
        engine.dispose()

    logging.info('=== 04_load_reconciled.py COMPLETATO ===')


if __name__ == '__main__':
    main()
