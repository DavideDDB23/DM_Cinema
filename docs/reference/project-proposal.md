# Data Management 2025/2026: Project Proposal

## Group Members
*   **Davide De Blasio** (2082600)
*   **Enrico Battistoni** (2272055)

## Project Type
Data Warehousing (DW) Multi-source ETL + DFM Model + Star Schema + OLAP Analysis

## Datasets

| Source | Description | Link |
| :--- | :--- | :--- |
| **IMDb Public Datasets** | Title basics, ratings, crew, cast (TSV format, updated weekly) | [https://datasets.imdbws.com](https://datasets.imdbws.com) |
| **The Movies Dataset (Kaggle)** | Budget, revenue, production companies, languages, countries, keywords | [https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) |

## Description of Intended Work
We intend to design and implement a Data Warehouse for analyzing the film industry, integrating two heterogeneous data sources: IMDb Public Datasets and The Movies Dataset from Kaggle. 

The two sources will be reconciled through an ETL pipeline (Python scripts + SQL) that handles ID mapping between IMDb and TMDB identifiers, data cleaning, genre normalization, and NULL management, producing a unified Reconciled Layer in PostgreSQL. 

Starting from this layer, we will design the Dimensional Fact Model (DFM) with at least four non-trivial dimensions, each featuring structured hierarchies suitable for OLAP drill-down and roll-up operations:
*   **Time**: Day → Month → Quarter → Year → Decade
*   **Genre**: Genre → GenreGroup
*   **Production**: Film Company → Country → Continent
*   **Director**: Director → Nationality Region

We will then implement the Star Schema in PostgreSQL, motivating the design choice, and populate it via SQL ETL queries from the reconciled layer. 

Finally, we will conduct OLAP sessions to extract non-trivial insights such as:
*   Revenue trends by genre over decades
*   ROI patterns across production company sizes
*   The relationship between production budget and audience rating
