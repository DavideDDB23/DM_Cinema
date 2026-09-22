-- ============================================================
-- FILE: sql/reconciled_ddl.sql
-- Reconciled Layer (layer 2 of 3: raw → reconciled → warehouse; see README) — schema 3NF
-- Eseguire su DB cinema_reconciled prima di 04_load_reconciled.py
-- Ordine rispetta dipendenze FK
-- ============================================================

-- Pulisci se esiste già (utile per reset durante sviluppo)
DROP TABLE IF EXISTS film_role       CASCADE;
DROP TABLE IF EXISTS film_company    CASCADE;
DROP TABLE IF EXISTS film_country    CASCADE;
DROP TABLE IF EXISTS film_language   CASCADE;
DROP TABLE IF EXISTS film_genre      CASCADE;
DROP TABLE IF EXISTS film            CASCADE;
DROP TABLE IF EXISTS production_company CASCADE;
DROP TABLE IF EXISTS person          CASCADE;
DROP TABLE IF EXISTS genre           CASCADE;
DROP TABLE IF EXISTS language        CASCADE;
DROP TABLE IF EXISTS country         CASCADE;

-- ---- Entità base (nessuna FK verso altre tabelle) ----

CREATE TABLE country (
    country_id   SERIAL PRIMARY KEY,
    iso_code     CHAR(2)       UNIQUE NOT NULL,
    country_name VARCHAR(100)  NOT NULL,
    continent    VARCHAR(50)
);

CREATE TABLE language (
    language_id     SERIAL PRIMARY KEY,
    iso_code        CHAR(8)       UNIQUE NOT NULL,
    language_name   VARCHAR(100)  NOT NULL,
    language_family VARCHAR(80)
);

CREATE TABLE genre (
    genre_id    SERIAL PRIMARY KEY,
    genre_name VARCHAR(50) UNIQUE NOT NULL,
    CONSTRAINT ck_genre_canonical_name
        CHECK (genre_name <> 'Science Fiction')
);

CREATE TABLE person (
    person_id   SERIAL PRIMARY KEY,
    imdb_nconst VARCHAR(12) UNIQUE,
    name        TEXT        NOT NULL,
    birth_year  SMALLINT,
    nationality VARCHAR(100)
);

-- ---- Entità dipendenti ----

CREATE TABLE production_company (
    company_id   SERIAL PRIMARY KEY,
    company_name VARCHAR(150) NOT NULL
);

CREATE TABLE film (
    film_id        SERIAL PRIMARY KEY,
    imdb_id        VARCHAR(12) UNIQUE,
    tmdb_id        INT         UNIQUE,
    title          TEXT        NOT NULL,
    original_title TEXT,
    release_year   SMALLINT,
    runtime_min    SMALLINT,
    budget_usd     BIGINT,
    revenue_usd    BIGINT,
    avg_rating     NUMERIC(3,1),
    num_votes      INT
);

-- ---- Tabelle di relazione M:N ----

CREATE TABLE film_genre (
    film_id  INT REFERENCES film(film_id)   ON DELETE CASCADE,
    genre_id INT REFERENCES genre(genre_id) ON DELETE CASCADE,
    PRIMARY KEY (film_id, genre_id)
);

CREATE TABLE film_language (
    film_id     INT REFERENCES film(film_id)         ON DELETE CASCADE,
    language_id INT REFERENCES language(language_id) ON DELETE CASCADE,
    is_original BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (film_id, language_id)
);

CREATE TABLE film_country (
    film_id    INT REFERENCES film(film_id)       ON DELETE CASCADE,
    country_id INT REFERENCES country(country_id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (film_id, country_id)
);

CREATE TABLE film_company (
    film_id    INT REFERENCES film(film_id)                   ON DELETE CASCADE,
    company_id INT REFERENCES production_company(company_id)  ON DELETE CASCADE,
    PRIMARY KEY (film_id, company_id)
);

CREATE TABLE film_role (
    film_id        INT REFERENCES film(film_id)     ON DELETE CASCADE,
    person_id      INT REFERENCES person(person_id) ON DELETE CASCADE,
    role_type VARCHAR(20) NOT NULL,
    CONSTRAINT ck_film_role_type
        CHECK (role_type IN ('director', 'actor', 'writer')),
    character_name TEXT,
    PRIMARY KEY (film_id, person_id, role_type)
);

-- ---- Indici per ETL e query ----

CREATE INDEX idx_film_release_year ON film(release_year);
CREATE INDEX idx_film_imdb_id      ON film(imdb_id);
CREATE INDEX idx_film_tmdb_id      ON film(tmdb_id);
CREATE INDEX idx_film_role_type    ON film_role(role_type);
CREATE INDEX idx_person_nconst     ON person(imdb_nconst);
CREATE INDEX idx_company_name      ON production_company(company_name);
CREATE INDEX idx_film_country_country ON film_country(country_id);
CREATE UNIQUE INDEX idx_film_language_one_original
    ON film_language(film_id)
    WHERE is_original;

\echo 'reconciled_ddl.sql: schema creato con successo.'
