-- ============================================================
-- FILE: sql/dw_ddl.sql
-- Data Warehouse (layer 3 of 3: raw → reconciled → warehouse; see README) — Star Schema
-- Eseguire su DB cinema_dw prima di sql/etl_load.sql
-- ============================================================

-- Pulisci se esiste già
DROP TABLE IF EXISTS fact_film_performance CASCADE;
DROP TABLE IF EXISTS dim_language   CASCADE;
DROP TABLE IF EXISTS dim_director   CASCADE;
DROP TABLE IF EXISTS dim_production CASCADE;
DROP TABLE IF EXISTS dim_genre      CASCADE;
DROP TABLE IF EXISTS dim_time       CASCADE;

-- ---- Dimensioni ----

CREATE TABLE dim_time (
    time_id      SERIAL PRIMARY KEY,
    release_date DATE,
    day          SMALLINT,
    month        SMALLINT,
    quarter      SMALLINT,
    year         SMALLINT,
    decade       SMALLINT,
    era          VARCHAR(30)
    -- Era labels: 'Silent Era' <1930, 'Golden Age' 1930-1959,
    --             'New Hollywood' 1960-1979, 'Blockbuster Era' 1980-1999,
    --             'Modern' >=2000
);

CREATE TABLE dim_genre (
    genre_id    SERIAL PRIMARY KEY,
    source_genre_id INT,
    genre_name  VARCHAR(50),
    genre_group VARCHAR(50)
    -- GenreGroups: 'Action/Thriller', 'Drama/Romance', 'Comedy/Animation',
    --              'Horror/Mystery', 'Sci-Fi/Fantasy', 'Other'
);

CREATE TABLE dim_production (
    production_id SERIAL PRIMARY KEY,
    source_company_id INT,
    source_country_id INT,
    company_name  VARCHAR(150),
    country_iso   CHAR(2),
    country_name  VARCHAR(100),
    continent     VARCHAR(50)
);

CREATE TABLE dim_director (
    director_id   SERIAL PRIMARY KEY,
    source_person_id INT,
    director_name VARCHAR(150),
    birth_year    SMALLINT,
    nationality   VARCHAR(100),
    region        VARCHAR(50)
    -- Regions: 'North America', 'W. Europe', 'Asia', 'Other'
);

-- dim_language: non presente nello schema base ma necessaria per Q3 OLAP (DICE su language_family)
CREATE TABLE dim_language (
    language_id     SERIAL PRIMARY KEY,
    source_language_id INT,
    language_name   VARCHAR(100),
    language_family VARCHAR(80)
);

-- ---- Tabella dei fatti ----

CREATE TABLE fact_film_performance (
    fact_id       SERIAL PRIMARY KEY,
    film_id       INT  NOT NULL,           -- FK logica verso reconciled.film.film_id
    film_title    TEXT,
    time_id       INT  NOT NULL REFERENCES dim_time(time_id),
    genre_id      INT  NOT NULL REFERENCES dim_genre(genre_id),
    production_id INT  NOT NULL REFERENCES dim_production(production_id),
    director_id   INT  REFERENCES dim_director(director_id),
    language_id   INT  REFERENCES dim_language(language_id),
    revenue_usd   BIGINT,
    budget_usd    BIGINT,
    roi           NUMERIC(15,2),  -- ampio per ROI estremi (Blair Witch: +413.000%)
    avg_rating    NUMERIC(3,1),
    num_votes     INT,
    CONSTRAINT ck_fact_roi_consistency CHECK (
        CASE
            WHEN budget_usd > 0 AND revenue_usd IS NOT NULL THEN
                roi IS NOT NULL
                AND ABS(
                    roi - ROUND(
                        (revenue_usd::NUMERIC - budget_usd::NUMERIC)
                        / budget_usd::NUMERIC * 100,
                        2
                    )
                ) <= 0.01
            ELSE roi IS NULL
        END
    )
);

CREATE UNIQUE INDEX uq_fact_film_performance_grain
ON fact_film_performance (
    film_id,
    time_id,
    genre_id,
    production_id,
    COALESCE(director_id, 0),
    COALESCE(language_id, 0)
);

-- ---- Indici per query OLAP ----

CREATE INDEX idx_fact_time       ON fact_film_performance(time_id);
CREATE INDEX idx_fact_genre      ON fact_film_performance(genre_id);
CREATE INDEX idx_fact_production ON fact_film_performance(production_id);
CREATE INDEX idx_fact_director   ON fact_film_performance(director_id);
CREATE INDEX idx_fact_language   ON fact_film_performance(language_id);
CREATE INDEX idx_fact_revenue    ON fact_film_performance(revenue_usd);
CREATE INDEX idx_fact_roi        ON fact_film_performance(roi);
CREATE INDEX idx_fact_film_id    ON fact_film_performance(film_id);
CREATE INDEX idx_dim_genre_source      ON dim_genre(source_genre_id);
CREATE INDEX idx_dim_production_source ON dim_production(source_company_id, source_country_id);
CREATE INDEX idx_dim_director_source   ON dim_director(source_person_id);
CREATE INDEX idx_dim_language_source   ON dim_language(source_language_id);

\echo 'dw_ddl.sql: Star Schema creato con successo su cinema_dw.'
