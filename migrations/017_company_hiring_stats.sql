-- ============================================================
-- Jobly company hiring statistics
--
-- Product-facing hiring activity is derived from:
--
--     jobs.posted_at
--     jobs.active
--
-- tracking_started_at is used only as an observation-maturity
-- gate. Snapshots and AI enrichment are NOT used here.
--
-- Statistics are recalculated from source-of-truth job rows.
-- They are never incrementally accumulated, so refreshing the
-- table repeatedly is safe and idempotent.
-- ============================================================


-- ============================================================
-- Repair older company rows that predate tracking_started_at.
--
-- Prefer the first time Jobly actually observed one of the
-- company's jobs. Fall back to company creation time.
-- ============================================================

UPDATE companies AS c

SET tracking_started_at = COALESCE(
    c.tracking_started_at,

    (
        SELECT MIN(j.first_seen_at)

        FROM jobs AS j

        WHERE j.company_id = c.id
    ),

    c.created_at
)

WHERE c.tracking_started_at IS NULL;


-- ============================================================
-- Precomputed company statistics
-- ============================================================

CREATE TABLE IF NOT EXISTS company_hiring_stats (

    company_id BIGINT PRIMARY KEY
        REFERENCES companies(id)
        ON DELETE CASCADE,


    -- --------------------------------------------------------
    -- Current career-site inventory
    -- --------------------------------------------------------

    current_open_jobs BIGINT
        NOT NULL DEFAULT 0,


    -- --------------------------------------------------------
    -- Posting-date data quality
    -- --------------------------------------------------------

    total_jobs_seen BIGINT
        NOT NULL DEFAULT 0,

    jobs_with_posted_at BIGINT
        NOT NULL DEFAULT 0,

    jobs_without_posted_at BIGINT
        NOT NULL DEFAULT 0,

    posted_at_coverage NUMERIC(6, 4)
        NOT NULL DEFAULT 0,


    -- --------------------------------------------------------
    -- Today vs yesterday
    -- --------------------------------------------------------

    posted_today BIGINT
        NOT NULL DEFAULT 0,

    posted_yesterday BIGINT
        NOT NULL DEFAULT 0,

    daily_change BIGINT
        NOT NULL DEFAULT 0,


    -- --------------------------------------------------------
    -- Latest 7 days vs previous 7 days
    -- --------------------------------------------------------

    posted_last_7_days BIGINT
        NOT NULL DEFAULT 0,

    posted_previous_7_days BIGINT
        NOT NULL DEFAULT 0,

    weekly_change BIGINT
        NOT NULL DEFAULT 0,

    weekly_growth_percent NUMERIC(12, 2),


    -- --------------------------------------------------------
    -- Initial 15-day statistics
    -- --------------------------------------------------------

    posted_last_15_days BIGINT
        NOT NULL DEFAULT 0,

    active_from_last_15_days BIGINT
        NOT NULL DEFAULT 0,

    removed_from_last_15_days BIGINT
        NOT NULL DEFAULT 0,


    -- --------------------------------------------------------
    -- Long-running currently active postings
    -- --------------------------------------------------------

    active_30_plus_days BIGINT
        NOT NULL DEFAULT 0,

    active_45_plus_days BIGINT
        NOT NULL DEFAULT 0,

    active_90_plus_days BIGINT
        NOT NULL DEFAULT 0,


    -- --------------------------------------------------------
    -- Posting timeline
    -- --------------------------------------------------------

    latest_posted_at TIMESTAMPTZ,

    oldest_active_posted_at TIMESTAMPTZ,


    -- --------------------------------------------------------
    -- Observation maturity / publication gate
    -- --------------------------------------------------------

    tracking_days INTEGER
        NOT NULL DEFAULT 0,

    is_publishable BOOLEAN
        NOT NULL DEFAULT FALSE,

    publishable_reason TEXT,


    -- --------------------------------------------------------
    -- Refresh metadata
    -- --------------------------------------------------------

    calculated_at TIMESTAMPTZ
        NOT NULL DEFAULT NOW()
);


-- ============================================================
-- Supporting job indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS
jobs_company_posted_at_idx
ON jobs (
    company_id,
    posted_at
);


CREATE INDEX IF NOT EXISTS
jobs_company_active_posted_at_idx
ON jobs (
    company_id,
    active,
    posted_at
);


-- ============================================================
-- API-facing statistics indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS
company_hiring_stats_publishable_7d_idx
ON company_hiring_stats (
    is_publishable,
    posted_last_7_days DESC
);


CREATE INDEX IF NOT EXISTS
company_hiring_stats_open_idx
ON company_hiring_stats (
    current_open_jobs DESC
);


CREATE INDEX IF NOT EXISTS
company_hiring_stats_weekly_growth_idx
ON company_hiring_stats (
    weekly_growth_percent DESC
);


-- ============================================================
-- Pipeline-run metrics
-- ============================================================

ALTER TABLE pipeline_runs
ADD COLUMN IF NOT EXISTS
company_stats_refreshed INTEGER;


ALTER TABLE pipeline_runs
ADD COLUMN IF NOT EXISTS
company_stats_publishable INTEGER;


ALTER TABLE pipeline_runs
ADD COLUMN IF NOT EXISTS
company_stats_unpublishable INTEGER;


-- ============================================================
-- Refresh function
--
-- p_company_id = NULL
--     refresh every company
--
-- p_company_id = company id
--     refresh only that company
--
-- Current publication rule:
--
--     Jobly tracking >= 15 days
--     at least one exact posted_at
--     posted_at coverage >= 80%
--
-- The 80% threshold is deliberately conservative.
-- ============================================================

CREATE OR REPLACE FUNCTION refresh_company_hiring_stats(
    p_company_id BIGINT DEFAULT NULL
)

RETURNS INTEGER

LANGUAGE plpgsql

AS $$

DECLARE

    v_rows INTEGER := 0;

    v_min_tracking_days
        CONSTANT INTEGER := 15;

    v_min_posted_at_coverage
        CONSTANT NUMERIC := 0.80;

BEGIN

    -- --------------------------------------------------------
    -- Prevent two statistics refreshes from overlapping.
    -- The lock automatically releases with the transaction.
    -- --------------------------------------------------------

    PERFORM pg_advisory_xact_lock(
        170017001
    );


    WITH aggregated AS (

        SELECT
            c.id AS company_id,

            c.tracking_started_at,


            -- ------------------------------------------------
            -- Inventory
            -- ------------------------------------------------

            COUNT(j.id)
                AS total_jobs_seen,


            COUNT(j.id) FILTER (
                WHERE j.active = TRUE
            )
                AS current_open_jobs,


            -- ------------------------------------------------
            -- Posting-date coverage
            -- ------------------------------------------------

            COUNT(j.id) FILTER (
                WHERE j.posted_at IS NOT NULL
            )
                AS jobs_with_posted_at,


            COUNT(j.id) FILTER (
                WHERE j.posted_at IS NULL
            )
                AS jobs_without_posted_at,


            -- ------------------------------------------------
            -- Today
            --
            -- Explicit UTC day boundaries prevent statistics
            -- from changing depending on DB/server timezone.
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE
                    (
                        j.posted_at
                        AT TIME ZONE 'UTC'
                    )::date

                    =

                    (
                        NOW()
                        AT TIME ZONE 'UTC'
                    )::date
            )
                AS posted_today,


            -- ------------------------------------------------
            -- Yesterday
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE
                    (
                        j.posted_at
                        AT TIME ZONE 'UTC'
                    )::date

                    =

                    (
                        (
                            NOW()
                            AT TIME ZONE 'UTC'
                        )::date
                        - 1
                    )
            )
                AS posted_yesterday,


            -- ------------------------------------------------
            -- Latest rolling 7 days
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE
                    j.posted_at
                    >= NOW() - INTERVAL '7 days'
            )
                AS posted_last_7_days,


            -- ------------------------------------------------
            -- Previous rolling 7 days
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE
                    j.posted_at
                    >= NOW() - INTERVAL '14 days'

                    AND

                    j.posted_at
                    < NOW() - INTERVAL '7 days'
            )
                AS posted_previous_7_days,


            -- ------------------------------------------------
            -- Latest rolling 15 days
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE
                    j.posted_at
                    >= NOW() - INTERVAL '15 days'
            )
                AS posted_last_15_days,


            -- ------------------------------------------------
            -- Last-15-day cohort still active
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE
                    j.posted_at
                    >= NOW() - INTERVAL '15 days'

                    AND

                    j.active = TRUE
            )
                AS active_from_last_15_days,


            -- ------------------------------------------------
            -- Last-15-day cohort no longer active
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE
                    j.posted_at
                    >= NOW() - INTERVAL '15 days'

                    AND

                    j.active = FALSE
            )
                AS removed_from_last_15_days,


            -- ------------------------------------------------
            -- Long-running active postings
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE
                    j.active = TRUE

                    AND

                    j.posted_at
                    <= NOW() - INTERVAL '30 days'
            )
                AS active_30_plus_days,


            COUNT(j.id) FILTER (

                WHERE
                    j.active = TRUE

                    AND

                    j.posted_at
                    <= NOW() - INTERVAL '45 days'
            )
                AS active_45_plus_days,


            COUNT(j.id) FILTER (

                WHERE
                    j.active = TRUE

                    AND

                    j.posted_at
                    <= NOW() - INTERVAL '90 days'
            )
                AS active_90_plus_days,


            -- ------------------------------------------------
            -- Timeline
            -- ------------------------------------------------

            MAX(
                j.posted_at
            )
                AS latest_posted_at,


            MIN(
                j.posted_at
            ) FILTER (
                WHERE
                    j.active = TRUE
                    AND j.posted_at IS NOT NULL
            )
                AS oldest_active_posted_at


        FROM companies AS c


        LEFT JOIN jobs AS j
            ON j.company_id = c.id


        WHERE
            p_company_id IS NULL

            OR

            c.id = p_company_id


        GROUP BY
            c.id,
            c.tracking_started_at
    ),


    calculated AS (

        SELECT
            company_id,

            current_open_jobs,

            total_jobs_seen,

            jobs_with_posted_at,

            jobs_without_posted_at,


            -- ------------------------------------------------
            -- Exact posting timestamp coverage
            -- ------------------------------------------------

            CASE

                WHEN total_jobs_seen = 0
                THEN 0::numeric

                ELSE ROUND(
                    jobs_with_posted_at::numeric
                    /
                    total_jobs_seen::numeric,
                    4
                )

            END
                AS posted_at_coverage,


            posted_today,

            posted_yesterday,


            (
                posted_today
                -
                posted_yesterday
            )
                AS daily_change,


            posted_last_7_days,

            posted_previous_7_days,


            (
                posted_last_7_days
                -
                posted_previous_7_days
            )
                AS weekly_change,


            CASE

                WHEN posted_previous_7_days = 0
                THEN NULL

                ELSE ROUND(

                    (
                        (
                            posted_last_7_days
                            -
                            posted_previous_7_days
                        )::numeric

                        /

                        posted_previous_7_days::numeric
                    )

                    * 100,

                    2
                )

            END
                AS weekly_growth_percent,


            posted_last_15_days,

            active_from_last_15_days,

            removed_from_last_15_days,

            active_30_plus_days,

            active_45_plus_days,

            active_90_plus_days,

            latest_posted_at,

            oldest_active_posted_at,


            CASE

                WHEN tracking_started_at IS NULL
                THEN 0

                ELSE GREATEST(

                    0,

                    (
                        (
                            NOW()
                            AT TIME ZONE 'UTC'
                        )::date

                        -

                        (
                            tracking_started_at
                            AT TIME ZONE 'UTC'
                        )::date
                    )

                )

            END
                AS tracking_days

        FROM aggregated
    ),


    finalized AS (

        SELECT
            *,

            (
                tracking_days
                    >= v_min_tracking_days

                AND

                jobs_with_posted_at > 0

                AND

                posted_at_coverage
                    >= v_min_posted_at_coverage
            )
                AS is_publishable,


            CASE

                WHEN total_jobs_seen = 0
                THEN 'no_jobs_seen'

                WHEN tracking_days
                    < v_min_tracking_days
                THEN 'tracking_under_15_days'

                WHEN jobs_with_posted_at = 0
                THEN 'no_exact_posted_dates'

                WHEN posted_at_coverage
                    < v_min_posted_at_coverage
                THEN 'posted_at_coverage_below_80_percent'

                ELSE NULL

            END
                AS publishable_reason

        FROM calculated
    )


    INSERT INTO company_hiring_stats (

        company_id,

        current_open_jobs,

        total_jobs_seen,

        jobs_with_posted_at,

        jobs_without_posted_at,

        posted_at_coverage,

        posted_today,

        posted_yesterday,

        daily_change,

        posted_last_7_days,

        posted_previous_7_days,

        weekly_change,

        weekly_growth_percent,

        posted_last_15_days,

        active_from_last_15_days,

        removed_from_last_15_days,

        active_30_plus_days,

        active_45_plus_days,

        active_90_plus_days,

        latest_posted_at,

        oldest_active_posted_at,

        tracking_days,

        is_publishable,

        publishable_reason,

        calculated_at
    )


    SELECT

        company_id,

        current_open_jobs,

        total_jobs_seen,

        jobs_with_posted_at,

        jobs_without_posted_at,

        posted_at_coverage,

        posted_today,

        posted_yesterday,

        daily_change,

        posted_last_7_days,

        posted_previous_7_days,

        weekly_change,

        weekly_growth_percent,

        posted_last_15_days,

        active_from_last_15_days,

        removed_from_last_15_days,

        active_30_plus_days,

        active_45_plus_days,

        active_90_plus_days,

        latest_posted_at,

        oldest_active_posted_at,

        tracking_days,

        is_publishable,

        publishable_reason,

        NOW()

    FROM finalized


    ON CONFLICT (
        company_id
    )

    DO UPDATE SET

        current_open_jobs =
            EXCLUDED.current_open_jobs,

        total_jobs_seen =
            EXCLUDED.total_jobs_seen,

        jobs_with_posted_at =
            EXCLUDED.jobs_with_posted_at,

        jobs_without_posted_at =
            EXCLUDED.jobs_without_posted_at,

        posted_at_coverage =
            EXCLUDED.posted_at_coverage,

        posted_today =
            EXCLUDED.posted_today,

        posted_yesterday =
            EXCLUDED.posted_yesterday,

        daily_change =
            EXCLUDED.daily_change,

        posted_last_7_days =
            EXCLUDED.posted_last_7_days,

        posted_previous_7_days =
            EXCLUDED.posted_previous_7_days,

        weekly_change =
            EXCLUDED.weekly_change,

        weekly_growth_percent =
            EXCLUDED.weekly_growth_percent,

        posted_last_15_days =
            EXCLUDED.posted_last_15_days,

        active_from_last_15_days =
            EXCLUDED.active_from_last_15_days,

        removed_from_last_15_days =
            EXCLUDED.removed_from_last_15_days,

        active_30_plus_days =
            EXCLUDED.active_30_plus_days,

        active_45_plus_days =
            EXCLUDED.active_45_plus_days,

        active_90_plus_days =
            EXCLUDED.active_90_plus_days,

        latest_posted_at =
            EXCLUDED.latest_posted_at,

        oldest_active_posted_at =
            EXCLUDED.oldest_active_posted_at,

        tracking_days =
            EXCLUDED.tracking_days,

        is_publishable =
            EXCLUDED.is_publishable,

        publishable_reason =
            EXCLUDED.publishable_reason,

        calculated_at =
            EXCLUDED.calculated_at;


    GET DIAGNOSTICS
        v_rows = ROW_COUNT;


    RETURN v_rows;

END;

$$;


-- ============================================================
-- Initial deterministic backfill
-- ============================================================

SELECT refresh_company_hiring_stats();