-- ============================================================
-- FILE: sql/olap_queries.sql
-- OLAP Sessions — 7 query sul Data Warehouse cinema_dw (Q1-Q6 + Q7 BONUS)
-- Eseguire su cinema_dw dopo sql/etl_load.sql
-- Ogni query ha: [OLAP: tipo-operazione] + Insight
-- ============================================================
-- NOTA SUL DESIGN DEL FATTO (M:N denormalizzato):
-- La granularità di fact_film_performance è (film × genre × company × production_country × director × language).
-- Le misure (revenue_usd, budget_usd, avg_rating, num_votes, roi) sono attributi del film,
-- ma vengono replicate in ogni riga della combinazione. Aggregando direttamente con
-- AVG/SUM si introduce un BIAS: i film con più generi/company/direttori pesano di più.
-- Esempio: "Furious 7" ha 40 righe nel fatto, quindi SUM(revenue) conta $1.506B × 40.
-- Mitigazione: ogni query usa una CTE che fa SELECT DISTINCT (film_id, dim_attrs, measure)
-- prima di aggregare. Così ogni film contribuisce una volta per (film × dim_target).
-- Documentato nel README, sezione "DFM and Star Schema" (../README.md#dfm-and-star-schema).
-- ============================================================


-- EXPORT: q1_revenue_genre_decade
-- ============================================================
-- Q1: Revenue medio per GenreGroup per decade
-- [OLAP: ROLL-UP Time(year→decade) + Genre(genre_name→genre_group)]
-- Insight: nel 2010 Sci-Fi/Fantasy guida il revenue medio ($220.44M),
--          Action/Thriller il totale ($156.18B), Drama/Romance il volume (1,378 film).
-- ============================================================
WITH film_decade_genre AS (
    -- Deduplicazione: un film con N generi nello stesso GenreGroup, M company, K direttori
    -- contribuisce una sola volta per (film, decade, genre_group).
    SELECT DISTINCT f.film_id, dt.decade, dg.genre_group, f.revenue_usd
    FROM fact_film_performance f
    JOIN dim_time  dt ON f.time_id  = dt.time_id
    JOIN dim_genre dg ON f.genre_id = dg.genre_id
    WHERE f.revenue_usd IS NOT NULL
      AND dt.decade >= 1970   -- decadi pre-1970 hanno dati revenue molto scarsi
)
SELECT
    decade,
    genre_group,
    ROUND(AVG(revenue_usd) / 1e6, 2)   AS avg_revenue_M,
    ROUND(SUM(revenue_usd) / 1e9, 2)   AS total_revenue_B,
    COUNT(*)                            AS num_films
FROM film_decade_genre
GROUP BY decade, genre_group
ORDER BY decade, avg_revenue_M DESC;


-- EXPORT: q2_roi_production_drilldown
-- ============================================================
-- Q2: ROI medio per drill-down nel contesto di produzione del film
-- [OLAP: DRILL-DOWN Production(continent→country_name→company_name) + SLICE(budget_usd > 1M)]
-- Insight: il percorso e' non-strict e descrive associazioni di produzione del film, non il
--          domicilio della company. Un film e una company possono quindi contribuire a piu'
--          paesi. Ogni livello viene deduplicato separatamente, evitando che il fan-out delle
--          company alteri le metriche dei livelli continent e country.
-- ============================================================
WITH eligible_production AS (
    SELECT DISTINCT
        f.film_id,
        dp.continent,
        dp.country_name,
        dp.company_name,
        f.roi,
        f.budget_usd,
        f.revenue_usd
    FROM fact_film_performance f
    JOIN dim_production dp ON f.production_id = dp.production_id
    WHERE f.budget_usd > 1000000   -- escludi micro-budget: ROI distorto
      AND f.roi IS NOT NULL
      AND dp.continent IS NOT NULL
      AND dp.country_name IS NOT NULL
),
continent_films AS (
    -- Un film contribuisce una sola volta per continent, indipendentemente da paesi e company.
    SELECT DISTINCT film_id, continent, roi, budget_usd, revenue_usd
    FROM eligible_production
),
country_films AS (
    -- Un film contribuisce una sola volta per (continent, production country).
    SELECT DISTINCT film_id, continent, country_name, roi, budget_usd, revenue_usd
    FROM eligible_production
),
company_films AS (
    -- La company e' osservata nel contesto (continent, production country), non per domicilio.
    SELECT DISTINCT
        film_id, continent, country_name, company_name, roi, budget_usd, revenue_usd
    FROM eligible_production
    WHERE company_name IS NOT NULL
),
production_levels AS (
    SELECT
        'continent'::text                  AS production_level,
        continent,
        NULL::varchar(100)                 AS country_name,
        NULL::varchar(150)                 AS company_name,
        ROUND(AVG(roi), 1)                 AS avg_roi_pct,
        ROUND(AVG(budget_usd) / 1e6, 1)    AS avg_budget_m,
        ROUND(SUM(revenue_usd) / 1e9, 2)   AS total_revenue_b,
        COUNT(*)                           AS num_films
    FROM continent_films
    GROUP BY continent

    UNION ALL

    SELECT
        'country'::text                    AS production_level,
        continent,
        country_name,
        NULL::varchar(150)                 AS company_name,
        ROUND(AVG(roi), 1)                 AS avg_roi_pct,
        ROUND(AVG(budget_usd) / 1e6, 1)    AS avg_budget_m,
        ROUND(SUM(revenue_usd) / 1e9, 2)   AS total_revenue_b,
        COUNT(*)                           AS num_films
    FROM country_films
    GROUP BY continent, country_name

    UNION ALL

    SELECT
        'company'::text                    AS production_level,
        continent,
        country_name,
        company_name,
        ROUND(AVG(roi), 1)                 AS avg_roi_pct,
        ROUND(AVG(budget_usd) / 1e6, 1)    AS avg_budget_m,
        ROUND(SUM(revenue_usd) / 1e9, 2)   AS total_revenue_b,
        COUNT(*)                           AS num_films
    FROM company_films
    GROUP BY continent, country_name, company_name
    HAVING COUNT(*) >= 5
)
SELECT
    production_level,
    continent,
    country_name,
    company_name,
    avg_roi_pct,
    avg_budget_m,
    total_revenue_b,
    num_films
FROM production_levels
ORDER BY
    CASE production_level
        WHEN 'continent' THEN 1
        WHEN 'country'   THEN 2
        WHEN 'company'   THEN 3
    END,
    continent,
    country_name NULLS FIRST,
    avg_roi_pct DESC,
    company_name NULLS FIRST;


-- EXPORT: q3_rating_era_language_family
-- ============================================================
-- Q3: Rating medio per Era e LanguageFamily
-- [OLAP: DICE era IN ('Blockbuster Era', 'Modern') + language_family IN (...)]
-- Insight: in Blockbuster Era, Sino-Tibetan (7.24; 51 film) e Slavic (7.19; 187)
--          hanno le medie più alte. In Modern, Koreanic (6.69; 290) precede
--          Japonic (6.68; 480).
--          Il risultato è descrittivo e non identifica una causa delle differenze osservate.
-- Nota modello: language_family è derivata da un mapping ISO 639-1 → famiglia linguistica
--          hardcoded in etl/04_load_reconciled.py (dizionario LANG_FAMILY, 15 famiglie).
--          La gerarchia Language → LanguageFamily è una dimensione aggiuntiva rispetto
--          allo schema base, introdotta per abilitare questo DICE.
-- ============================================================
WITH film_era_lang AS (
    -- Deduplicazione: ogni film contribuisce una volta per (era, language_family).
    SELECT DISTINCT f.film_id, dt.era, dl.language_family, f.avg_rating, f.num_votes
    FROM fact_film_performance f
    JOIN dim_time     dt ON f.time_id     = dt.time_id
    JOIN dim_language dl ON f.language_id = dl.language_id
    WHERE dt.era IN ('Blockbuster Era', 'Modern')
      AND dl.language_family IN (
          'Indo-European/Germanic', 'Indo-European/Romance',
          'Indo-European/Slavic', 'Indo-European/Indo-Iranian',
          'Sino-Tibetan', 'Japonic', 'Koreanic'
      )
      AND f.avg_rating IS NOT NULL
      AND dl.language_family IS NOT NULL
)
SELECT
    era,
    language_family,
    ROUND(AVG(avg_rating), 2)           AS mean_rating,
    ROUND(AVG(num_votes), 0)            AS avg_votes,
    COUNT(*)                             AS num_films
FROM film_era_lang
GROUP BY era, language_family
HAVING COUNT(*) >= 20  -- soglia minima di 20 film per mostrare una famiglia nell'output
ORDER BY era, mean_rating DESC;


-- EXPORT: q4_roi_studio_size
-- ============================================================
-- Q4: ROI per dimensione studio (piccolo/medio/grande)
-- [OLAP: SLICE(roi IS NOT NULL AND budget >= 50k) + CTE aggregazione per size_band]
-- Insight: ROI medio Small 548.17% (3,380 film) > Medium 463.68% (2,701 film)
--          > Large 413.22% (3,542 film), dopo deduplicazione M:N in film_size.
--          Il confronto è descrittivo; il filtro budget >= $50k esclude artefatti Kaggle
--          (budget=1$) senza attribuire cause al pattern osservato.
-- ============================================================
WITH company_size AS (
    -- Classifica company per numero di film prodotti (distinct film_id per company)
    SELECT
        dp.source_company_id,
        CASE
            WHEN COUNT(DISTINCT f.film_id) < 10  THEN 'Small (<10 film)'
            WHEN COUNT(DISTINCT f.film_id) < 50  THEN 'Medium (10-50 film)'
            ELSE                                    'Large (50+ film)'
        END AS size_band
    FROM fact_film_performance f
    JOIN dim_production dp ON f.production_id = dp.production_id
    GROUP BY dp.source_company_id
),
film_size AS (
    -- Deduplicazione: un film prodotto da N company del medesimo size_band contribuisce una volta.
    -- Se è co-prodotto da company Small e Large, contribuisce sia a Small sia a Large.
    SELECT DISTINCT f.film_id, cs.size_band, f.roi, f.avg_rating, f.budget_usd
    FROM fact_film_performance f
    JOIN dim_production dp ON f.production_id = dp.production_id
    JOIN company_size cs ON dp.source_company_id = cs.source_company_id
    WHERE f.roi IS NOT NULL
      AND f.budget_usd >= 50000
)
SELECT
    size_band,
    ROUND(AVG(roi), 2)                  AS avg_roi_pct,
    ROUND(AVG(avg_rating), 2)           AS avg_rating,
    ROUND(AVG(budget_usd) / 1e6, 1)    AS avg_budget_M,
    COUNT(*)                             AS num_films
FROM film_size
GROUP BY size_band
ORDER BY avg_roi_pct DESC;


-- EXPORT: q5_budget_quartile_rating
-- ============================================================
-- Q5: Distribuzione del ROI per quartile di budget
-- [OLAP: NTILE(4) window + PERCENTILE_CONT + filtro outlier IQR]
-- Insight: media, mediana, massimo e conteggio degli outlier alti rendono visibile la forte
--          asimmetria del ROI. Il confronto tra quartili e' descrittivo: la media da sola puo'
--          essere dominata da pochi film estremi e non implica un andamento tipico monotono.
--          Snapshot: 5,194 film ROI-available, 5,183 rated; Q1 mean 2,092,053.9%
--          vs median 218.8%; 395 high-IQR outlier complessivi.
-- ============================================================
WITH film_budget AS (
    -- Popolazione primaria: tutti e soli i film distinti con ROI disponibile.
    SELECT DISTINCT film_id, budget_usd, avg_rating, roi
    FROM fact_film_performance
    WHERE roi IS NOT NULL
),
budget_quartiles AS (
    -- film_id risolve deterministicamente i pareggi di budget.
    SELECT
        film_id, budget_usd, avg_rating, roi,
        NTILE(4) OVER (ORDER BY budget_usd, film_id) AS budget_quartile
    FROM film_budget
),
roi_fences AS (
    -- Fence alto specifico del quartile: Q3(ROI) + 1.5 * IQR(ROI).
    SELECT
        budget_quartile,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY roi) AS roi_q1,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY roi) AS roi_q3
    FROM budget_quartiles
    GROUP BY budget_quartile
)
SELECT
    bq.budget_quartile,
    ROUND(MIN(bq.budget_usd) / 1e6, 1)  AS min_budget_m,
    ROUND(MAX(bq.budget_usd) / 1e6, 1)  AS max_budget_m,
    ROUND(AVG(bq.budget_usd) / 1e6, 1)  AS avg_budget_m,
    ROUND(AVG(bq.avg_rating), 2)        AS avg_rating,
    COUNT(bq.avg_rating)                AS num_rated_films,
    COUNT(*)                            AS num_films,
    ROUND(AVG(bq.roi), 1)               AS mean_roi_pct,
    ROUND(
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY bq.roi)::numeric,
        1
    )                                   AS median_roi_pct,
    ROUND(MAX(bq.roi), 1)               AS max_roi_pct,
    COUNT(*) FILTER (
        WHERE bq.roi > rf.roi_q3 + 1.5 * (rf.roi_q3 - rf.roi_q1)
    )                                   AS high_outlier_count
FROM budget_quartiles bq
JOIN roi_fences rf USING (budget_quartile)
GROUP BY bq.budget_quartile, rf.roi_q1, rf.roi_q3
ORDER BY bq.budget_quartile;


-- EXPORT: q6_cumulative_revenue_genre
-- ============================================================
-- Q6: Revenue cumulativo per genere nel tempo (window function BONUS)
-- [OLAP: ROLL-UP Time(year→decade) + SUM() OVER (PARTITION BY genre ORDER BY decade)]
-- Insight: al 2010 il cumulato finale è Adventure $233.26B, Action $206.92B,
--          Comedy $179.53B e Drama $174.36B. Action resta sotto Drama nel 2000
--          ($106.61B vs $116.85B) e lo supera nell'ultima decade osservata.
--          Ogni genere è una serie cumulativa indipendente; i valori non sono impilati.
-- BONUS: dimostra uso di window function SUM OVER PARTITION BY ROWS BETWEEN UNBOUNDED PRECEDING
-- ============================================================
WITH film_decade_genre AS (
    -- Deduplicazione: ogni film contribuisce una volta per (decade, genre_name).
    -- Un film multi-genere contribuisce una volta a OGNI suo genere (allocazione piena).
    SELECT DISTINCT f.film_id, dt.decade, dg.genre_name, f.revenue_usd
    FROM fact_film_performance f
    JOIN dim_time  dt ON f.time_id  = dt.time_id
    JOIN dim_genre dg ON f.genre_id = dg.genre_id
    WHERE f.revenue_usd IS NOT NULL
      AND dg.genre_name IN ('Action','Drama','Comedy','Sci-Fi','Horror','Animation','Adventure')
),
decade_genre AS (
    -- Aggrega revenue per (decade, genre_name) — base per window function
    SELECT decade, genre_name, SUM(revenue_usd) AS decade_revenue
    FROM film_decade_genre
    GROUP BY decade, genre_name
)
SELECT
    decade,
    genre_name,
    ROUND(decade_revenue / 1e9, 2) AS decade_revenue_B,
    ROUND(
        SUM(decade_revenue) OVER (
            PARTITION BY genre_name
            ORDER BY decade
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) / 1e9,
        2
    ) AS cumulative_revenue_B
FROM decade_genre
ORDER BY genre_name, decade;


-- EXPORT: q7_top_films_by_decade
-- ============================================================
-- Q7: Top-5 film per rating in ogni decade (BONUS — RANK window function)
-- [OLAP: RANK() OVER (PARTITION BY decade ORDER BY rating DESC) + SLICE num_votes >= 1000]
-- Insight: nelle decadi più recenti il numero di voti richiesto per comparire in classifica
--          è molto più alto (pubblico IMDb cresce). I film con ratings più alti nelle decadi
--          più vecchie (1950-1970) tendono a essere cult con pochi ma fedeli votanti.
-- BONUS: dimostra uso di RANK() con PARTITION BY, diverso da NTILE (Q5) e SUM OVER (Q6).
-- ============================================================
WITH film_decade AS (
    -- Deduplicazione: MAX è idempotente su avg_rating/num_votes (stesso valore per ogni riga).
    -- GROUP BY collassa le righe duplicate del fan-out genere×company×director.
    SELECT
        f.film_id,
        f.film_title,
        dt.decade,
        MAX(f.avg_rating)  AS avg_rating,
        MAX(f.num_votes)   AS num_votes
    FROM fact_film_performance f
    JOIN dim_time dt ON f.time_id = dt.time_id
    WHERE f.avg_rating IS NOT NULL
      AND f.num_votes >= 1000   -- minimo voti per stabilità statistica
      AND dt.decade >= 1950
    GROUP BY f.film_id, f.film_title, dt.decade
),
ranked_films AS (
    SELECT
        film_id, film_title, decade, avg_rating, num_votes,
        RANK() OVER (
            PARTITION BY decade
            ORDER BY avg_rating DESC, num_votes DESC
        ) AS rank_in_decade
    FROM film_decade
)
SELECT
    decade,
    rank_in_decade,
    film_title,
    avg_rating,
    num_votes
FROM ranked_films
WHERE rank_in_decade <= 5
ORDER BY decade, rank_in_decade;
