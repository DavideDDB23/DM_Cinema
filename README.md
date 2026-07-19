# Cinema Analytics Data Warehouse

## Overview

Cinema Analytics integrates IMDb and Kaggle's "The Movies Dataset" into a
reproducible PostgreSQL warehouse for seven OLAP analyses.

The three persisted layers are `Raw sources (IMDb TSV + Kaggle CSV) ->
Reconciled Layer (cinema_reconciled, 3NF) -> Data Warehouse (cinema_dw,
star schema)`.

CSV exports, the plotting notebook, diagrams, and slides consume the warehouse;
they are not additional data layers. This README is the sole maintained project
document. Executable SQL and ETL files remain the authoritative implementation.

## Prerequisites and Setup

- macOS or Linux with `make`, `bash`, `wget`, `gunzip`, and `unzip`;
- Python 3.11 and the dependencies in [`requirements.txt`](requirements.txt);
- PostgreSQL 14+ with `createdb` and `psql` available;
- Kaggle credentials at `~/.kaggle/kaggle.json` with permissions `600`;
- roughly 7 GB for raw sources, plus intermediate and database storage.

```bash
git clone <repo-url> DataMan_Cinema
cd DataMan_Cinema
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
createdb cinema_reconciled
createdb cinema_dw
```

When PostgreSQL defaults are insufficient, create `.env` in the repository root:

```dotenv
DATABASE_URL=postgresql://<user>@localhost:5432/cinema_reconciled
DW_DATABASE_URL=postgresql://<user>@localhost:5432/cinema_dw
```

The Python processes read these variables. Makefile `psql` commands and
`postgres_fdw` use local PostgreSQL defaults and the current role. That role must
access both databases and be allowed to create the FDW extension and mapping.

### Data files

Raw and processed datasets are not uploaded to this repository. In particular,
the generated files under `data/processed/` exceed GitHub's repository file-size
limit. Run the canonical workflow below to download the source data and recreate
the processed files locally.

## Canonical Workflow

The single end-to-end workflow is:

```bash
PATH="$PWD/.venv/bin:$PATH" make all
```

It performs the following stages in order:

| Stage | Canonical operation |
|---|---|
| Download | [`data/download_data.sh`](data/download_data.sh) acquires five IMDb TSV files and two Kaggle CSV files. |
| Reconciled DDL | [`sql/reconciled_ddl.sql`](sql/reconciled_ddl.sql) recreates `cinema_reconciled`. |
| Clean | [`etl/01_clean_imdb.py`](etl/01_clean_imdb.py) and [`etl/02_clean_kaggle.py`](etl/02_clean_kaggle.py) create Parquet intermediates. |
| Reconcile | [`etl/03_reconcile_ids.py`](etl/03_reconcile_ids.py) resolves IMDb-TMDB identities and writes audit outputs. |
| Load 3NF | [`etl/04_load_reconciled.py`](etl/04_load_reconciled.py) loads entities and M:N bridges. |
| Load DW | [`sql/dw_ddl.sql`](sql/dw_ddl.sql) and [`sql/etl_load.sql`](sql/etl_load.sql) rebuild dimensions and fact via `postgres_fdw`. |
| OLAP | [`scripts/run_olap.py`](scripts/run_olap.py) executes Q1-Q7 and atomically publishes their CSV exports. |

Useful secondary targets are `make help`, `make olap`, and `make clean`.

The runner reads complete query blocks from `sql/olap_queries.sql`, checks their
order and expected columns, and replaces exports only after all seven succeed.

## Reconciliation and 3NF Layer

For each cleaned TMDB movie, reconciliation follows `source-ID -> exact ->
fuzzy` order:

1. A valid Kaggle `source_imdb_id` present in eligible IMDb data is accepted. A
   valid but absent source ID is quarantined rather than overridden by text.
2. Only a missing or invalid source ID permits a unique exact match on normalized
   title and year; ambiguous exact candidates are quarantined.
3. Otherwise, fuzzy matching compares titles within the same year. The best
   candidate must score at least `0.85` and strictly beat the runner-up.

One IMDb ID can map to only one TMDB ID. Conflict arbitration prefers source ID,
then exact, then fuzzy proposals, with deterministic tie-breaks.

`reconciliation_audit.csv` records a reasoned outcome for every cleaned TMDB ID.
`reconciliation_quarantine.csv` isolates authoritative-but-unverifiable IDs and
ambiguous decisions for review. `unmatched_tmdb.csv` keeps records for which no
candidate satisfies the rules. These artifacts make exclusions observable;
quarantined or unmatched Kaggle films may still load with a null IMDb identity.

The 3NF layer stores `film`, referenced `person` records, `genre`,
`production_company`, `country`, and `language`. Bridge tables preserve film
genres, languages, countries, companies, and director/actor/writer roles without
forcing multi-valued relationships into a single row.

## DFM and Star Schema

The dimensional fact is `FilmPerformance`; see the
[`DFM diagram`](docs/diagrams/dfm_schema.png) and
[`star-schema diagram`](docs/diagrams/star_schema.png).

The conceptual DFM exposes Film plus five analytical dimensions. The physical
star keeps `film_id` and `film_title` in the fact as a degenerate Film dimension
and implements the other dimensions as tables. Its logical grain is **film x
genre x company x production country x optional director x optional original
language**; Time is functionally determined by the film's release year.

| Dimension | Analytical hierarchy and role |
|---|---|
| Film (degenerate) | `Film -> title`, with the identifier and descriptive title stored directly in the fact. |
| Time (`dim_time`) | `Year -> Decade -> Era`, the common temporal level retained across IMDb and Kaggle. |
| Genre (`dim_genre`) | `Genre -> GenreGroup`. |
| Production (`dim_production`) | `ProductionContext -> Company` and `ProductionContext -> ProductionCountry -> Continent`. |
| Director (`dim_director`) | Flat, optional, and multi-valued; birth year is descriptive rather than a roll-up level. |
| Language (`dim_language`) | `Language -> LanguageFamily`; only original language is used and it is optional. |

`ProductionContext` is the observed film-level company-country tuple represented
by one `dim_production` row. Company and production country are separate branches:
the model does not assert that a company has one country of legal domicile.

`revenue_usd`, `budget_usd`, `roi`, `avg_rating`, and `num_votes` are movie-level
measures replicated across fan-out combinations. They are non-additive across
that fan-out: direct `SUM` or `AVG` would overweight movies with more genres,
company-country contexts, or directors. OLAP queries first deduplicate each
movie at the target analytical grain; multi-valued membership remains full.
Revenue, budget, and votes can be summed only after that deduplication, while ROI
and rating use `AVG`, `MIN`, or `MAX`, never `SUM`.

A star schema is preferred over a snowflake because this read-heavy ROLAP
workload benefits from fewer joins and hierarchies visible within each dimension.
The modest dimensional redundancy is preferable to extra normalized-level joins.

## OLAP Q1-Q7

Canonical implementations are in
[`sql/olap_queries.sql`](sql/olap_queries.sql); the
[`plot notebook`](notebooks/insights_plots.ipynb) reads their exported CSV files.

| Query | Operation | Intent |
|---|---|---|
| Q1 | Roll-up on Time and Genre | Compare average revenue, total revenue, and movie volume by `GenreGroup` and decade from 1970. |
| Q2 | Production drill-down + slice | Compare ROI across continent, country, and company context for budgets above USD 1 million. |
| Q3 | Dice | Compare ratings across two eras and seven selected language families. |
| Q4 | Slice + CTE classification | Compare ROI, rating, and budget for small, medium, and large production companies above the budget floor. |
| Q5 | `NTILE` + percentiles/IQR | Describe ROI by budget quartile and expose skew and high outliers. |
| Q6 | Roll-up + `SUM OVER` | Build independent cumulative revenue series by genre and decade. |
| Q7 | `RANK` + slice | Return the top-rated movies per decade from 1950 with at least 1,000 votes. |

Each query handles fact fan-out at its own analytical grain. Q2 deduplicates each
production level independently, while Q7 uses idempotent movie-level aggregates.

## Current Snapshot

These delivery counts describe the current source snapshot and may change after
a new download:

| Area | Metric | Rows |
|---|---|---:|
| Reconciliation | Accepted | **39,096** |
| Reconciliation | Quarantined | **6,327** |
| Reconciliation | Unmatched | **10** |
| 3NF | Reconciled films | **45,431** |
| 3NF | Referenced people | **183,082** |
| 3NF | Film roles | **474,054** |
| Warehouse | Fact rows | **268,615** |
| Warehouse | Distinct fact films | **33,418** |

The fact covers 73.6% of reconciled films and averages 8.04 rows per included
movie because dimensions with M:N relationships expand the declared grain.

## Limitations and Manual Verification

- Source releases are mutable, so counts and analytical results are snapshots.
- Kaggle budget and revenue values can contain missing or implausible entries;
  non-positive markers become null, and ROI requires a positive budget.
- The warehouse deliberately retains release year, the temporal level shared by
  both sources; day, month, and quarter remain unused physical stubs.
- IMDb does not provide director nationality, so Director remains a flat optional
  dimension; `Language -> LanguageFamily` supplies the fourth populated hierarchy.
- Production geography is a movie context and must not be read as company
  domicile; full multi-valued membership also prevents causal interpretation.
DDL constraints and loader checks block row-level/local integrity errors.
Cross-row measure consistency and fact coverage are checked manually for the
delivery snapshot. A rebuild therefore requires repeating those manual checks;
they are not continuously enforced across replicated fact rows.

## Repository Structure

```text
DataMan_Cinema/
|-- README.md                     sole maintained project document
|-- Makefile                      canonical workflow targets
|-- requirements.txt              Python dependencies
|-- data/                         downloader plus ignored raw/processed data
|-- etl/                          cleaning, reconciliation, and 3NF loaders
|-- sql/                          3NF/DW DDL, DW load, and OLAP Q1-Q7
|-- scripts/                      diagram generator and OLAP export runner
|-- notebooks/insights_plots.ipynb
|-- exports/                      current Q1-Q7 CSV files and plots
|-- docs/diagrams/                ER, DFM, and star-schema images
|-- docs/reference/               course and project reference material
`-- slides.html                   canonical presentation deck
```
