-- ============================================================
-- FILE: sql/etl_load.sql
-- Popola il Data Warehouse dal Reconciled Layer via postgres_fdw
-- Eseguire su DB cinema_dw dopo che cinema_reconciled è popolato
-- e dopo aver eseguito sql/dw_ddl.sql
-- ============================================================

\set ON_ERROR_STOP on

-- ---- Setup postgres_fdw (eseguito solo se non già presente) ----
-- postgres_fdw permette di leggere le tabelle di cinema_reconciled
-- da dentro cinema_dw senza dump/restore intermedi.
--
-- ESECUZIONE (non serve parametro utente):
--   psql -d cinema_dw -f sql/etl_load.sql
-- Usa SQL dinamico per serializzare current_user come literal dell'opzione FDW.
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

CREATE SERVER IF NOT EXISTS reconciled_srv
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (host 'localhost', port '5432', dbname 'cinema_reconciled');

-- L'opzione postgres_fdw `user` richiede un literal stringa, non l'espressione SQL CURRENT_USER.
-- SQL dinamico: current_user viene valutato da PostgreSQL e passato a format(... %L ...).
DO $$
BEGIN
    EXECUTE format(
        'CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER SERVER reconciled_srv OPTIONS (user %L)',
        current_user
    );
END $$;

-- Rimuovi eventuali foreign tables residue da run precedenti (idempotente)
DO $$
DECLARE tname text;
BEGIN
    FOR tname IN
        SELECT foreign_table_name FROM information_schema.foreign_tables
        WHERE foreign_table_schema = 'public'
    LOOP
        EXECUTE format('DROP FOREIGN TABLE IF EXISTS %I CASCADE', tname);
    END LOOP;
END $$;

IMPORT FOREIGN SCHEMA public
    FROM SERVER reconciled_srv
    INTO public;
-- Ora le tabelle di cinema_reconciled sono accessibili come foreign tables locali


-- ============================================================
-- 1. Carica dim_time
-- ============================================================
-- Creates one row per distinct release year in the Reconciled Layer.
-- NOTE: Year is the conformed temporal grain across both sources.
-- IMDb provides only the release year; Kaggle ships a full release_date,
-- intentionally reduced to year during cleaning (etl/02_clean_kaggle.py).
-- day=1, month=1, quarter=1 are intentional stubs — the analytic levels
-- are year → decade → era. Documented limitation (README).
INSERT INTO dim_time (release_date, day, month, quarter, year, decade, era)
SELECT DISTINCT
    MAKE_DATE(f.release_year, 1, 1)              AS release_date,
    1                                             AS day,    -- stub: year-only grain
    1                                             AS month,  -- stub: year-only grain
    1                                             AS quarter, -- stub: derived from stub month
    f.release_year                                AS year,
    (f.release_year / 10) * 10                   AS decade,
    CASE
        WHEN f.release_year < 1930 THEN 'Silent Era'
        WHEN f.release_year < 1960 THEN 'Golden Age'
        WHEN f.release_year < 1980 THEN 'New Hollywood'
        WHEN f.release_year < 2000 THEN 'Blockbuster Era'
        ELSE                            'Modern'
    END                                           AS era
FROM film f
WHERE f.release_year IS NOT NULL
  AND f.release_year BETWEEN 1900 AND 2030;  -- filtro sanità

-- Verifica
SELECT era, COUNT(*) AS anni, MIN(year), MAX(year)
FROM dim_time GROUP BY era ORDER BY MIN(year);


-- ============================================================
-- 2. Carica dim_genre
-- ============================================================
INSERT INTO dim_genre (source_genre_id, genre_name, genre_group)
SELECT DISTINCT
    g.genre_id,
    g.genre_name,
    CASE
        WHEN g.genre_name IN ('Action','Adventure','Thriller')       THEN 'Action/Thriller'
        WHEN g.genre_name IN ('Drama','Romance','Family')            THEN 'Drama/Romance'
        WHEN g.genre_name IN ('Comedy','Animation')                  THEN 'Comedy/Animation'
        WHEN g.genre_name IN ('Horror','Mystery')                    THEN 'Horror/Mystery'
        WHEN g.genre_name IN ('Sci-Fi','Fantasy','Science Fiction')  THEN 'Sci-Fi/Fantasy'
        ELSE 'Other'
    END AS genre_group
FROM genre g;

SELECT genre_group, COUNT(*) FROM dim_genre GROUP BY genre_group;


-- ============================================================
-- 3. Carica dim_production
-- ============================================================
-- Denormalizza company → production country → continent in un'unica tabella.
-- Motivazione: Kaggle non espone origin_country affidabile per production_company;
-- production_countries è invece disponibile a livello film. La dimensione rappresenta
-- quindi il contesto geografico di produzione osservato per la coppia film-company.
INSERT INTO dim_production
    (source_company_id, source_country_id, company_name, country_iso, country_name, continent)
SELECT DISTINCT
    pc.company_id,
    c.country_id::INT,
    pc.company_name,
    c.iso_code,
    c.country_name,
    c.continent
FROM production_company pc
JOIN film_company fc ON fc.company_id = pc.company_id
JOIN film_country fco ON fco.film_id = fc.film_id
JOIN country c ON c.country_id = fco.country_id

UNION

-- Mantieni company collegate a film senza production country, senza perdere copertura fact.
SELECT DISTINCT
    pc.company_id,
    NULL::INT AS source_country_id,
    pc.company_name,
    NULL::CHAR(2) AS country_iso,
    NULL::VARCHAR(100) AS country_name,
    NULL::VARCHAR(50) AS continent
FROM production_company pc
JOIN film_company fc ON fc.company_id = pc.company_id
WHERE NOT EXISTS (
    SELECT 1 FROM film_country fco WHERE fco.film_id = fc.film_id
);

SELECT continent, COUNT(*) FROM dim_production GROUP BY continent ORDER BY COUNT(*) DESC;


-- ============================================================
-- 4. Carica dim_director
-- ============================================================
-- Solo persone con role_type='director' nel Reconciled Layer
-- INTENTIONAL VESTIGIAL MAPPING (nationality → region): person.nationality
-- is never populated — IMDb name.basics has no nationality field
-- (see etl/01_clean_imdb.py, etl/04_load_reconciled.py). The WHEN branches
-- below are therefore unreachable and region is constantly 'Other'.
-- Column reserved for future enrichment; limitation documented in README
-- and slides.
INSERT INTO dim_director (source_person_id, director_name, birth_year, nationality, region)
SELECT DISTINCT
    p.person_id,
    p.name                                        AS director_name,
    p.birth_year,
    p.nationality,
    CASE
        WHEN p.nationality IN ('USA','Canada','Mexico')           THEN 'North America'
        WHEN p.nationality IN ('UK','France','Germany','Italy',
                               'Spain','Netherlands','Sweden',
                               'Denmark','Belgium','Switzerland',
                               'Norway','Austria','Poland')       THEN 'W. Europe'
        WHEN p.nationality IN ('Japan','South Korea','China',
                               'India','Hong Kong','Taiwan',
                               'Iran')                            THEN 'Asia'
        ELSE 'Other'
    END                                           AS region
FROM person p
JOIN film_role fr ON p.person_id = fr.person_id
WHERE fr.role_type = 'director';

-- Returns a single 'Other' region by design (vestigial mapping above).
SELECT region, COUNT(*) FROM dim_director GROUP BY region ORDER BY COUNT(*) DESC;


-- ============================================================
-- 5. Carica dim_language
-- ============================================================
INSERT INTO dim_language (source_language_id, language_name, language_family)
SELECT DISTINCT
    l.language_id,
    l.language_name,
    l.language_family
FROM language l
WHERE l.language_name IS NOT NULL;

SELECT language_family, COUNT(*) FROM dim_language GROUP BY language_family ORDER BY COUNT(*) DESC;


-- ============================================================
-- 6. Carica fact_film_performance
-- ============================================================
-- Granularità: (film, genere, production company, production country, director, lingua originale)
-- ROI calcolato direttamente; NULL se budget=0 o non disponibile
INSERT INTO fact_film_performance
    (film_id, film_title, time_id, genre_id, production_id, director_id,
     language_id, revenue_usd, budget_usd, roi, avg_rating, num_votes)
SELECT
    f.film_id,
    f.title                                        AS film_title,
    dt.time_id,
    dg.genre_id,
    dp.production_id,
    dd.director_id,
    dl.language_id,
    f.revenue_usd,
    f.budget_usd,
    CASE
        WHEN f.budget_usd > 0
        THEN ROUND(
            (f.revenue_usd - f.budget_usd)::NUMERIC / f.budget_usd * 100,
            2
        )
        ELSE NULL
    END                                            AS roi,
    f.avg_rating,
    f.num_votes
FROM film f

-- Join dimensione tempo
JOIN dim_time dt
    ON dt.year = f.release_year

-- Join dimensione genere
JOIN film_genre fg
    ON fg.film_id = f.film_id
JOIN genre g
    ON g.genre_id = fg.genre_id
JOIN dim_genre dg
    ON dg.source_genre_id = g.genre_id

-- Join dimensione produzione
JOIN film_company fc
    ON fc.film_id = f.film_id
JOIN production_company pc
    ON pc.company_id = fc.company_id
LEFT JOIN film_country fco
    ON fco.film_id = f.film_id
JOIN dim_production dp
    ON dp.source_company_id = pc.company_id
   AND (
        dp.source_country_id = fco.country_id
        OR (dp.source_country_id IS NULL AND fco.country_id IS NULL)
   )

-- Join dimensione regista
LEFT JOIN film_role fr
    ON fr.film_id = f.film_id
    AND fr.role_type = 'director'
LEFT JOIN person p
    ON p.person_id = fr.person_id
LEFT JOIN dim_director dd
    ON dd.source_person_id = p.person_id

-- Join dimensione lingua (lingua originale del film)
LEFT JOIN film_language fl
    ON fl.film_id = f.film_id
    AND fl.is_original = TRUE
LEFT JOIN language l
    ON l.language_id = fl.language_id
LEFT JOIN dim_language dl
    ON dl.source_language_id = l.language_id;

-- Verifica finale
SELECT COUNT(*)                                       AS total_fact_rows       FROM fact_film_performance;
SELECT COUNT(DISTINCT film_id)                        AS film_distinti         FROM fact_film_performance;
SELECT COUNT(*) FILTER (WHERE roi IS NOT NULL)        AS righe_con_roi         FROM fact_film_performance;
SELECT COUNT(*) FILTER (WHERE avg_rating IS NOT NULL) AS righe_con_rating      FROM fact_film_performance;
SELECT COUNT(*) FILTER (WHERE language_id IS NOT NULL) AS righe_con_lingua     FROM fact_film_performance;
