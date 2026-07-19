"""
Esegue le 7 query OLAP definite in sql/olap_queries.sql sul DW e salva i
risultati in exports/. Richiede che cinema_dw sia popolato.
"""

import logging
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPORTS = REPO_ROOT / 'exports'
CANONICAL_OLAP_SQL = REPO_ROOT / 'sql' / 'olap_queries.sql'

EXPECTED_COLUMNS: dict[str, tuple[str, ...]] = {
    'q1_revenue_genre_decade': (
        'decade', 'genre_group', 'avg_revenue_m',
        'total_revenue_b', 'num_films',
    ),
    'q2_roi_production_drilldown': (
        'production_level', 'continent', 'country_name', 'company_name',
        'avg_roi_pct', 'avg_budget_m', 'total_revenue_b', 'num_films',
    ),
    'q3_rating_era_language_family': (
        'era', 'language_family', 'mean_rating', 'avg_votes', 'num_films',
    ),
    'q4_roi_studio_size': (
        'size_band', 'avg_roi_pct', 'avg_rating', 'avg_budget_m', 'num_films',
    ),
    'q5_budget_quartile_rating': (
        'budget_quartile', 'min_budget_m', 'max_budget_m', 'avg_budget_m',
        'avg_rating', 'num_rated_films', 'num_films', 'mean_roi_pct',
        'median_roi_pct', 'max_roi_pct', 'high_outlier_count',
    ),
    'q6_cumulative_revenue_genre': (
        'decade', 'genre_name', 'decade_revenue_b', 'cumulative_revenue_b',
    ),
    'q7_top_films_by_decade': (
        'decade', 'rank_in_decade', 'film_title', 'avg_rating', 'num_votes',
    ),
}
EXPECTED_NAMES = tuple(EXPECTED_COLUMNS)
EXPORT_MARKER_PREFIX = '-- EXPORT: '

load_dotenv(REPO_ROOT / '.env')

DW_URL = os.environ.get(
    'DW_DATABASE_URL',
    f'postgresql://{os.environ.get("USER", "postgres")}@localhost:5432/cinema_dw'
)


def load_queries(
    sql_path: Path = CANONICAL_OLAP_SQL,
) -> list[tuple[str, str]]:
    """Load and validate the seven export blocks from the canonical SQL file."""
    source_path = Path(sql_path)
    lines = source_path.read_text(encoding='utf-8').splitlines(keepends=True)
    markers: list[tuple[int, str]] = []

    for line_number, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(EXPORT_MARKER_PREFIX):
            markers.append(
                (line_number, stripped.removeprefix(EXPORT_MARKER_PREFIX).strip())
            )

    marker_names = tuple(name for _line_number, name in markers)
    if marker_names != EXPECTED_NAMES:
        raise ValueError(
            f'Expected OLAP markers {EXPECTED_NAMES}, found {marker_names}'
        )

    queries: list[tuple[str, str]] = []
    for index, (marker_line, name) in enumerate(markers):
        block_start = marker_line + 1
        block_end = (
            markers[index + 1][0] if index + 1 < len(markers) else len(lines)
        )
        sql = ''.join(lines[block_start:block_end]).strip()
        if not sql:
            raise ValueError(f'Empty OLAP query block for {name} in {source_path}')
        queries.append((name, sql))

    return queries


def main() -> None:
    EXPORTS.mkdir(parents=True, exist_ok=True)
    frames: dict[str, pd.DataFrame] = {}
    engine = create_engine(DW_URL)

    try:
        with engine.connect() as conn, conn.begin():
            conn.execute(text('SET TRANSACTION READ ONLY'))
            for name, sql in load_queries():
                frame = pd.read_sql(text(sql), conn)
                if frame.empty:
                    raise ValueError(f'{name} returned no rows')
                if tuple(frame.columns) != EXPECTED_COLUMNS[name]:
                    raise ValueError(f'{name} returned an invalid schema')
                frames[name] = frame

        for name, frame in frames.items():
            output = EXPORTS / f'{name}.csv'
            frame.to_csv(output, index=False)
            logging.info(f'{name}: {len(frame)} rows -> {output}')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
