"""
etl/01_clean_imdb.py
Pulisce e filtra i dataset IMDb.
Output: data/processed/imdb_movies.parquet
        data/processed/imdb_persons.parquet
        data/processed/imdb_roles.parquet
"""
import ast
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

REPO_ROOT  = Path(__file__).resolve().parent.parent
RAW_IMDB   = REPO_ROOT / 'data' / 'raw' / 'imdb'
PROCESSED  = REPO_ROOT / 'data' / 'processed'


def load_basics() -> pd.DataFrame:
    logging.info('=== STEP 1: Caricamento title.basics.tsv ===')
    # na_values='\\N' converte il marker NULL di IMDb in NaN
    df = pd.read_csv(RAW_IMDB / 'title.basics.tsv', sep='\t', na_values='\\N', low_memory=False)
    logging.info(f'Righe raw basics: {len(df):,}')

    # solo film — titleType=movie esclude TV, videoGame e altro (>50% righe)
    df = df[df['titleType'] == 'movie'].copy()
    logging.info(f'Righe dopo filtro titleType=movie: {len(df):,}')

    # float64 con NaN è compatibile con Parquet e con la conversione SQLAlchemy→NULL.
    df['startYear'] = pd.to_numeric(df['startYear'], errors='coerce')

    df['runtimeMinutes'] = pd.to_numeric(df['runtimeMinutes'], errors='coerce')

    # genres: 'Action,Adventure,Sci-Fi' → lista Python; film senza genere → lista vuota
    df['genres_list'] = df['genres'].apply(
        lambda x: x.split(',') if pd.notna(x) else []
    )

    return df


def load_ratings() -> pd.DataFrame:
    logging.info('=== STEP 2: Caricamento title.ratings.tsv ===')
    df = pd.read_csv(RAW_IMDB / 'title.ratings.tsv', sep='\t', na_values='\\N')
    df['averageRating'] = df['averageRating'].astype(float)
    df['numVotes'] = df['numVotes'].astype(int)
    logging.info(f'Ratings: {len(df):,} righe')
    return df


def load_crew() -> pd.DataFrame:
    logging.info('=== STEP 3: Caricamento title.crew.tsv ===')
    df = pd.read_csv(RAW_IMDB / 'title.crew.tsv', sep='\t', na_values='\\N')
    # directors: 'nm0001234,nm0005678' → lista
    df['directors_list'] = df['directors'].apply(
        lambda x: x.split(',') if pd.notna(x) else []
    )
    logging.info(f'Crew: {len(df):,} righe')
    return df


def load_names() -> pd.DataFrame:
    logging.info('=== STEP 4: Caricamento name.basics.tsv (persone) ===')
    df = pd.read_csv(
        RAW_IMDB / 'name.basics.tsv', sep='\t',
        na_values='\\N', low_memory=False,
        usecols=['nconst', 'primaryName', 'birthYear']
    )
    df['birthYear'] = pd.to_numeric(df['birthYear'], errors='coerce')
    logging.info(f'Persone: {len(df):,} righe')
    return df


def load_principals(movie_tconsts: set) -> pd.DataFrame:
    """
    title.principals.tsv contiene circa 100 milioni di righe.
    Strategia: lettura a chunk + filtro anticipato per:
       1. Solo tconst appartenenti ai film (non TV)
       2. Solo category rilevanti (director, actor, actress, writer)
    così evita di caricare l'intero dataset in memoria.
    """
    logging.info('=== STEP 5: Caricamento title.principals.tsv (chunked) ===')
    relevant_categories = {'director', 'actor', 'actress', 'writer'}
    chunks = []
    total_raw = 0
    total_kept = 0
    chunk_size = 500_000

    for chunk in pd.read_csv(
        RAW_IMDB / 'title.principals.tsv',
        sep='\t', na_values='\\N',
        chunksize=chunk_size,
        low_memory=False,
        usecols=['tconst', 'nconst', 'category', 'characters']
    ):
        total_raw += len(chunk)
        chunk = chunk[
            chunk['tconst'].isin(movie_tconsts) &
            chunk['category'].isin(relevant_categories)
        ]
        total_kept += len(chunk)
        if len(chunk) > 0:
            chunks.append(chunk)

    logging.info(f'Principals raw: {total_raw:,} | filtrati (movie+category): {total_kept:,}')
    if not chunks:
        return pd.DataFrame(columns=['tconst', 'nconst', 'category', 'characters'])

    result = pd.concat(chunks, ignore_index=True)

    # characters: stringa '["Han Solo"]' → primo personaggio o None
    def parse_character(val):
        if pd.isna(val):
            return None
        try:
            lst = ast.literal_eval(val)
            return lst[0] if lst else None
        except Exception:
            # formato malformato o stringa vuota
            return None

    result['character_name'] = result['characters'].apply(parse_character)
    result = result.drop(columns=['characters'])
    return result


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)

    basics   = load_basics()
    ratings  = load_ratings()
    crew     = load_crew()
    names    = load_names()

    logging.info('=== STEP 6: Join basics + ratings + crew ===')
    movies = basics.merge(ratings, on='tconst', how='left')
    logging.info(f'Film con rating: {movies["averageRating"].notna().sum():,}')
    logging.info(f'Film senza rating: {movies["averageRating"].isna().sum():,}')

    movies = movies.merge(crew[['tconst', 'directors_list']], on='tconst', how='left')
    logging.info(f'Film totali nel dataset finale: {len(movies):,}')

    movies = movies[[
        'tconst', 'primaryTitle', 'originalTitle', 'startYear',
        'runtimeMinutes', 'genres_list', 'averageRating', 'numVotes',
        'directors_list'
    ]].rename(columns={
        'tconst': 'imdb_id',
        'primaryTitle': 'title',
        'originalTitle': 'original_title',
        'startYear': 'release_year',
        'runtimeMinutes': 'runtime_min',
        'averageRating': 'avg_rating',
        'numVotes': 'num_votes',
    })

    # Principals (roles) — usiamo l'insieme di tconst dei film filtrati
    movie_tconsts = set(basics['tconst'].values)
    roles = load_principals(movie_tconsts)
    roles = roles.rename(columns={'category': 'role_type'})
    # Motivazione: IMDb separa actor/actress, il modello riconciliato unifica in role_type='actor'
    roles['role_type'] = roles['role_type'].replace({'actress': 'actor'})

    logging.info('=== STEP 7: Salvataggio parquet ===')
    movies.to_parquet(PROCESSED / 'imdb_movies.parquet', index=False)
    logging.info(f'imdb_movies.parquet: {len(movies):,} righe')

    names.to_parquet(PROCESSED / 'imdb_persons.parquet', index=False)
    logging.info(f'imdb_persons.parquet: {len(names):,} righe')

    roles.to_parquet(PROCESSED / 'imdb_roles.parquet', index=False)
    logging.info(f'imdb_roles.parquet: {len(roles):,} righe')

    logging.info('=== 01_clean_imdb.py COMPLETATO ===')


if __name__ == '__main__':
    main()
