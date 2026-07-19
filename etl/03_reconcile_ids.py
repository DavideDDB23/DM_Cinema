"""
etl/03_reconcile_ids.py
Riconcilia gli identificatori IMDb e TMDB con una traccia audit per ogni riga.

Ordine di riconciliazione:
  1. source_imdb_id valido e presente nel dataset IMDb eleggibile
  2. titolo normalizzato + anno con un solo candidato
  3. miglior candidato fuzzy univoco nello stesso anno (cutoff 0.85)

Output:
  - data/processed/reconciled_index.parquet
  - data/processed/reconciliation_audit.csv
  - data/processed/unmatched_tmdb.csv
  - data/processed/reconciliation_quarantine.csv
"""
import difflib
import logging
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED = REPO_ROOT / 'data' / 'processed'

FUZZY_CUTOFF = 0.85
IMDB_ID_RE = re.compile(r'^tt([0-9]+)$', re.IGNORECASE)
METHOD_PRIORITY = {'source_id': 3, 'exact': 2, 'fuzzy': 1}
AUDIT_COLUMNS = [
    'tmdb_id', 'source_imdb_id', 'imdb_id', 'candidate_imdb_id',
    'method', 'status', 'reason',
    'source_title', 'source_year', 'candidate_title', 'candidate_year',
    'score', 'runner_up_score', 'margin', 'candidate_count',
    'winner_tmdb_id',
]


class Candidate(NamedTuple):
    imdb_id: str
    title: str | None
    year: int | None
    normalized_title: str


def normalize_imdb_id(value) -> str | None:
    """Restituisce un IMDb ID canonico oppure None."""
    if pd.isna(value):
        return None
    match = IMDB_ID_RE.fullmatch(str(value).strip())
    return f'tt{match.group(1)}' if match else None


def normalize_title(value) -> str:
    """Normalizza maiuscole, apostrofi, punteggiatura e spazi per il confronto."""
    if pd.isna(value):
        return ''
    title = unicodedata.normalize('NFKC', str(value)).casefold()
    title = re.sub(r"['`\u2018\u2019]", '', title)
    title = re.sub(r'[\W_]+', ' ', title, flags=re.UNICODE)
    return ' '.join(title.split())


def normalize_year(value) -> int | None:
    """Converte un anno intero in int, lasciando nulli i valori non validi."""
    if pd.isna(value):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return int(numeric) if numeric.is_integer() else None


def build_imdb_indexes(imdb: pd.DataFrame) -> tuple[dict, dict, dict]:
    """Costruisce indici deterministici per ID, titolo+anno e anno."""
    imdb = imdb.copy()
    imdb['source_order'] = range(len(imdb))
    imdb['imdb_id'] = imdb['imdb_id'].apply(normalize_imdb_id)
    invalid_ids = imdb['imdb_id'].isna().sum()
    imdb = imdb.dropna(subset=['imdb_id'])

    imdb['normalized_title'] = imdb['title'].apply(normalize_title)
    imdb['match_year'] = imdb['release_year'].apply(normalize_year)
    imdb['record_quality'] = (
        imdb['normalized_title'].ne('').astype('int8')
        + imdb['match_year'].notna().astype('int8')
    )

    before_dedup = len(imdb)
    imdb = (
        imdb.sort_values(
            ['imdb_id', 'record_quality', 'normalized_title', 'match_year', 'source_order'],
            ascending=[True, False, True, True, True],
            kind='mergesort',
            na_position='last',
        )
        .drop_duplicates(subset=['imdb_id'], keep='first')
    )
    logging.info(
        f'IMDb ID non validi esclusi: {invalid_ids:,} | '
        f'duplicati IMDb ID rimossi: {before_dedup - len(imdb):,}'
    )

    by_id: dict[str, Candidate] = {}
    exact_lookup: dict[tuple[str, int], list[Candidate]] = defaultdict(list)
    candidates_by_year: dict[int, list[Candidate]] = defaultdict(list)

    columns = ['imdb_id', 'title', 'match_year', 'normalized_title']
    for imdb_id, title, year, normalized_title in imdb[columns].itertuples(
        index=False,
        name=None,
    ):
        year = normalize_year(year)
        candidate = Candidate(
            imdb_id=imdb_id,
            title=None if pd.isna(title) else str(title),
            year=year,
            normalized_title=normalized_title,
        )
        by_id[imdb_id] = candidate
        if normalized_title and year is not None:
            exact_lookup[(normalized_title, year)].append(candidate)
            candidates_by_year[year].append(candidate)

    for candidates in exact_lookup.values():
        candidates.sort(key=lambda candidate: candidate.imdb_id)
    for candidates in candidates_by_year.values():
        candidates.sort(key=lambda candidate: candidate.imdb_id)

    return by_id, exact_lookup, candidates_by_year


def set_candidate(
    proposal: dict,
    candidate: Candidate,
    score: float,
    runner_up_score: float | None = None,
) -> None:
    proposal['candidate_imdb_id'] = candidate.imdb_id
    proposal['candidate_title'] = candidate.title
    proposal['candidate_year'] = candidate.year
    proposal['score'] = score
    proposal['runner_up_score'] = runner_up_score
    proposal['margin'] = (
        score - runner_up_score if runner_up_score is not None else None
    )


def propose_match(
    tmdb_id: int,
    raw_source_imdb_id,
    raw_title,
    raw_year,
    row_order: int,
    imdb_by_id: dict[str, Candidate],
    exact_lookup: dict[tuple[str, int], list[Candidate]],
    candidates_by_year: dict[int, list[Candidate]],
) -> dict:
    """Produce una proposta completa, inclusi i motivi di rifiuto o quarantena."""
    source_imdb_id = normalize_imdb_id(raw_source_imdb_id)
    source_title = None if pd.isna(raw_title) else str(raw_title)
    normalized_title = normalize_title(raw_title)
    source_year = normalize_year(raw_year)
    proposal = {
        'tmdb_id': tmdb_id,
        'source_imdb_id': source_imdb_id,
        'imdb_id': None,
        'candidate_imdb_id': None,
        'method': None,
        'status': 'unmatched',
        'reason': None,
        'source_title': source_title,
        'source_year': source_year,
        'candidate_title': None,
        'candidate_year': None,
        'score': None,
        'runner_up_score': None,
        'margin': None,
        'candidate_count': 0,
        'winner_tmdb_id': None,
        '_row_order': row_order,
    }

    if source_imdb_id is not None:
        proposal['method'] = 'source_id'
        proposal['candidate_imdb_id'] = source_imdb_id
        candidate = imdb_by_id.get(source_imdb_id)
        if candidate is None:
            proposal['status'] = 'quarantined'
            proposal['reason'] = 'source_id_not_in_eligible_imdb'
            return proposal

        set_candidate(proposal, candidate, score=1.0)
        proposal['imdb_id'] = candidate.imdb_id
        proposal['status'] = 'matched'
        proposal['reason'] = 'source_id_found'
        proposal['candidate_count'] = 1
        return proposal

    if not normalized_title and source_year is None:
        proposal['reason'] = 'missing_title_and_year'
        return proposal
    if not normalized_title:
        proposal['reason'] = 'missing_title'
        return proposal
    if source_year is None:
        proposal['reason'] = 'missing_year'
        return proposal

    exact_candidates = exact_lookup.get((normalized_title, source_year), [])
    if len(exact_candidates) == 1:
        candidate = exact_candidates[0]
        proposal['method'] = 'exact'
        proposal['candidate_count'] = 1
        set_candidate(proposal, candidate, score=1.0)
        proposal['imdb_id'] = candidate.imdb_id
        proposal['status'] = 'matched'
        proposal['reason'] = 'unique_exact_title_year'
        return proposal

    if len(exact_candidates) > 1:
        proposal['method'] = 'exact'
        proposal['status'] = 'quarantined'
        proposal['reason'] = 'ambiguous_exact_candidates'
        proposal['candidate_count'] = len(exact_candidates)
        set_candidate(
            proposal,
            exact_candidates[0],
            score=1.0,
            runner_up_score=1.0,
        )
        return proposal

    year_candidates = candidates_by_year.get(source_year, [])
    proposal['method'] = 'fuzzy'
    if not year_candidates:
        proposal['reason'] = 'no_same_year_candidates'
        return proposal

    matcher = difflib.SequenceMatcher()
    matcher.set_seq2(normalized_title)
    ranked = []
    for candidate in year_candidates:
        matcher.set_seq1(candidate.normalized_title)
        ranked.append((matcher.ratio(), candidate))
    ranked.sort(key=lambda item: (-item[0], item[1].imdb_id))

    top_score, top_candidate = ranked[0]
    runner_up_score = ranked[1][0] if len(ranked) > 1 else None
    proposal['candidate_count'] = sum(
        score >= FUZZY_CUTOFF for score, _ in ranked
    )
    set_candidate(proposal, top_candidate, top_score, runner_up_score)

    if top_score < FUZZY_CUTOFF:
        proposal['reason'] = 'no_fuzzy_candidate_above_cutoff'
        return proposal

    if runner_up_score is not None and abs(top_score - runner_up_score) <= 1e-12:
        proposal['status'] = 'quarantined'
        proposal['reason'] = 'ambiguous_fuzzy_best'
        return proposal

    proposal['imdb_id'] = top_candidate.imdb_id
    proposal['status'] = 'matched'
    proposal['reason'] = 'unique_best_fuzzy'
    return proposal


def arbitrate_duplicate_targets(audit: pd.DataFrame) -> int:
    """Mantiene un solo TMDB per IMDb con priorita' e tie-break espliciti."""
    accepted = pd.DataFrame(audit.loc[audit['status'] == 'matched']).copy()
    if accepted.empty:
        return 0

    accepted['method_priority'] = [
        METHOD_PRIORITY[method]
        for method in accepted['method']
    ]
    accepted = accepted.sort_values(
        by=[
            'candidate_imdb_id', 'method_priority', 'score',
            'tmdb_id', '_row_order',
        ],
        ascending=[True, False, False, True, True],
        kind='mergesort',
    )
    winners = accepted.drop_duplicates(subset=['candidate_imdb_id'], keep='first')
    winner_tmdb_by_imdb = dict(
        zip(winners['candidate_imdb_id'], winners['tmdb_id'])
    )
    loser_indices = accepted.index[
        accepted.duplicated(subset=['candidate_imdb_id'], keep='first')
    ]
    if len(loser_indices) == 0:
        return 0

    audit.loc[loser_indices, 'winner_tmdb_id'] = [
        winner_tmdb_by_imdb[candidate_imdb_id]
        for candidate_imdb_id in audit.loc[
            loser_indices,
            'candidate_imdb_id',
        ]
    ]
    audit.loc[loser_indices, 'imdb_id'] = None
    audit.loc[loser_indices, 'status'] = 'quarantined'
    audit.loc[loser_indices, 'reason'] = 'duplicate_imdb_resolution'
    return len(loser_indices)


def reconcile():
    logging.info('=== Caricamento parquet ===')
    imdb = pd.read_parquet(
        PROCESSED / 'imdb_movies.parquet',
        columns=['imdb_id', 'title', 'release_year'],
    )
    kaggle = pd.read_parquet(
        PROCESSED / 'kaggle_movies.parquet',
        columns=['tmdb_id', 'source_imdb_id', 'title', 'release_year'],
    )
    logging.info(f'IMDb movies: {len(imdb):,} | Kaggle movies: {len(kaggle):,}')

    numeric_tmdb_ids = pd.Series(
        pd.to_numeric(kaggle['tmdb_id'], errors='coerce'),
        index=kaggle.index,
    )
    if numeric_tmdb_ids.isna().any():
        raise ValueError('kaggle_movies.parquet contiene tmdb_id non numerici')
    kaggle = kaggle.copy()
    kaggle['tmdb_id'] = numeric_tmdb_ids.astype('int64')
    if kaggle['tmdb_id'].duplicated().any():
        raise ValueError('kaggle_movies.parquet contiene tmdb_id duplicati')

    imdb_by_id, exact_lookup, candidates_by_year = build_imdb_indexes(imdb)
    logging.info(
        f'IMDb eleggibili: {len(imdb_by_id):,} | '
        f'chiavi titolo+anno: {len(exact_lookup):,}'
    )

    proposals = []
    columns = ['tmdb_id', 'source_imdb_id', 'title', 'release_year']
    for row_order, row in enumerate(kaggle[columns].itertuples(index=False, name=None)):
        tmdb_id, source_imdb_id, title, release_year = row
        proposals.append(
            propose_match(
                tmdb_id=tmdb_id,
                raw_source_imdb_id=source_imdb_id,
                raw_title=title,
                raw_year=release_year,
                row_order=row_order,
                imdb_by_id=imdb_by_id,
                exact_lookup=exact_lookup,
                candidates_by_year=candidates_by_year,
            )
        )

    audit = pd.DataFrame(proposals)
    duplicate_losers = arbitrate_duplicate_targets(audit)
    audit = audit.sort_values(
        ['tmdb_id', '_row_order'],
        kind='mergesort',
    ).reset_index(drop=True)

    for column in [
        'tmdb_id', 'source_year', 'candidate_year',
        'candidate_count', 'winner_tmdb_id',
    ]:
        audit[column] = pd.array(list(audit[column]), dtype='Int64')

    matched_df = (
        audit.loc[audit['status'] == 'matched', ['tmdb_id', 'imdb_id', 'method']]
        .rename(columns={'method': 'match_type'})
        .sort_values('tmdb_id', kind='mergesort')
        .reset_index(drop=True)
    )
    matched_df['tmdb_id'] = matched_df['tmdb_id'].astype('int64')
    unmatched_df = audit.loc[audit['status'] == 'unmatched', AUDIT_COLUMNS]
    quarantine_df = audit.loc[audit['status'] == 'quarantined', AUDIT_COLUMNS]
    audit_output = audit[AUDIT_COLUMNS]

    total = len(audit)
    matched_counts = matched_df['match_type'].value_counts()
    n_source = int(matched_counts.get('source_id', 0))
    n_exact = int(matched_counts.get('exact', 0))
    n_fuzzy = int(matched_counts.get('fuzzy', 0))
    match_rate = len(matched_df) / total * 100 if total else 0.0
    logging.info(f'Match source ID: {n_source:,}')
    logging.info(f'Match esatti:    {n_exact:,}')
    logging.info(f'Match fuzzy:     {n_fuzzy:,}')
    logging.info(f'Non matchati:    {len(unmatched_df):,}')
    logging.info(
        f'Quarantena:      {len(quarantine_df):,} '
        f'(duplicati risolti: {duplicate_losers:,})'
    )
    logging.info(f'Match rate totale: {match_rate:.1f}%')

    matched_df.to_parquet(PROCESSED / 'reconciled_index.parquet', index=False)
    audit_output.to_csv(
        PROCESSED / 'reconciliation_audit.csv',
        index=False,
        na_rep='',
        float_format='%.12g',
    )
    unmatched_df.to_csv(
        PROCESSED / 'unmatched_tmdb.csv',
        index=False,
        na_rep='',
        float_format='%.12g',
    )
    quarantine_df.to_csv(
        PROCESSED / 'reconciliation_quarantine.csv',
        index=False,
        na_rep='',
        float_format='%.12g',
    )

    logging.info(f'reconciled_index.parquet: {len(matched_df):,} righe')
    logging.info(f'reconciliation_audit.csv: {len(audit_output):,} righe')
    logging.info(f'unmatched_tmdb.csv: {len(unmatched_df):,} righe')
    logging.info(f'reconciliation_quarantine.csv: {len(quarantine_df):,} righe')
    logging.info('=== 03_reconcile_ids.py COMPLETATO ===')


if __name__ == '__main__':
    reconcile()
