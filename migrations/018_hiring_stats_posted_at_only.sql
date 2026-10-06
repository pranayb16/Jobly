-- ============================================================
-- Jobly hiring statistics: posted_at-only product metrics
--
-- Phase 1 statistics are based ONLY on the job data Jobly
-- currently possesses:
--
--     jobs.posted_at
--     jobs.active
--
-- No tracking-age requirement.
-- No snapshots.
-- No enrichment.
-- No first_seen_at fallback.
-- No observed-new fallback.
--
-- If exact posted_at values exist, statistics are immediately
-- usable for those known jobs.
-- ============================================================


-- ============================================================
-- tracking_days was part of the original publication model.
-- It must not participate in Phase 1 hiring statistics.
-- ============================================================

ALTER TABLE company_hiring_stats
DROP COLUMN IF EXISTS tracking_days;


-- ============================================================
-- Keep the oldest exact posting date as a useful diagnostic.
-- ============================================================

ALTER TABLE company_hiring_stats
ADD COLUMN IF NOT EXISTS oldest_posted_at TIMESTAMPTZ;


-- ============================================================
-- Replace the statistics refresh function.
-- ============================================================

CREATE OR REPLACE FUNCTION refresh_company_hiring_stats(
    p_company_id BIGINT DEFAULT NULL
)

RETURNS INTEGER

LANGUAGE plpgsql

AS $$

DECLARE
    v_rows INTEGER := 0;

BEGIN

    -- --------------------------------------------------------
    -- Prevent overlapping refresh operations.
    -- --------------------------------------------------------

    PERFORM pg_advisory_xact_lock(
        170018001
    );


    WITH aggregated AS (

        SELECT
            c.id AS company_id,


            -- ------------------------------------------------
            -- Total/current inventory
            -- ------------------------------------------------

            COUNT(j.id)
                AS total_jobs_seen,


            COUNT(j.id) FILTER (
                WHERE j.active = TRUE
            )
                AS current_open_jobs,


            -- ------------------------------------------------
            -- Exact posted_at availability
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
            -- Calendar dates are normalized to UTC so server
            -- timezone does not alter the result.
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE j.posted_at IS NOT NULL

                  AND (
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

                WHERE j.posted_at IS NOT NULL

                  AND (
                        j.posted_at
                        AT TIME ZONE 'UTC'
                      )::date

                      =

                      (
                        NOW()
                        AT TIME ZONE 'UTC'
                      )::date - 1
            )
                AS posted_yesterday,


            -- ------------------------------------------------
            -- Rolling last 7 days
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE j.posted_at IS NOT NULL

                  AND j.posted_at
                      >= NOW() - INTERVAL '7 days'

                  AND j.posted_at <= NOW()
            )
                AS posted_last_7_days,


            -- ------------------------------------------------
            -- Previous rolling 7 days
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE j.posted_at IS NOT NULL

                  AND j.posted_at
                      >= NOW() - INTERVAL '14 days'

                  AND j.posted_at
                      < NOW() - INTERVAL '7 days'
            )
                AS posted_previous_7_days,


            -- ------------------------------------------------
            -- Rolling last 15 days
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE j.posted_at IS NOT NULL

                  AND j.posted_at
                      >= NOW() - INTERVAL '15 days'

                  AND j.posted_at <= NOW()
            )
                AS posted_last_15_days,


            -- ------------------------------------------------
            -- Last-15-day postings still active
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE j.posted_at IS NOT NULL

                  AND j.posted_at
                      >= NOW() - INTERVAL '15 days'

                  AND j.posted_at <= NOW()

                  AND j.active = TRUE
            )
                AS active_from_last_15_days,


            -- ------------------------------------------------
            -- Last-15-day postings currently removed
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE j.posted_at IS NOT NULL

                  AND j.posted_at
                      >= NOW() - INTERVAL '15 days'

                  AND j.posted_at <= NOW()

                  AND j.active = FALSE
            )
                AS removed_from_last_15_days,


            -- ------------------------------------------------
            -- Long-running currently active postings
            -- ------------------------------------------------

            COUNT(j.id) FILTER (

                WHERE j.active = TRUE

                  AND j.posted_at IS NOT NULL

                  AND j.posted_at
                      <= NOW() - INTERVAL '30 days'
            )
                AS active_30_plus_days,


            COUNT(j.id) FILTER (

                WHERE j.active = TRUE

                  AND j.posted_at IS NOT NULL

                  AND j.posted_at
                      <= NOW() - INTERVAL '45 days'
            )
                AS active_45_plus_days,


            COUNT(j.id) FILTER (

                WHERE j.active = TRUE

                  AND j.posted_at IS NOT NULL

                  AND j.posted_at
                      <= NOW() - INTERVAL '90 days'
            )
                AS active_90_plus_days,


            -- ------------------------------------------------
            -- Posting-date boundaries
            -- ------------------------------------------------

            MAX(j.posted_at)
                AS latest_posted_at,


            MIN(j.posted_at)
                AS oldest_posted_at,


            MIN(j.posted_at) FILTER (
                WHERE j.active = TRUE
            )
                AS oldest_active_posted_at


        FROM companies AS c


        LEFT JOIN jobs AS j
            ON j.company_id = c.id
           AND j.is_us_job IS TRUE


        WHERE
            p_company_id IS NULL

            OR

            c.id = p_company_id


        GROUP BY
            c.id
    ),


    calculated AS (

        SELECT
            company_id,

            current_open_jobs,

            total_jobs_seen,

            jobs_with_posted_at,

            jobs_without_posted_at,


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

            oldest_posted_at,

            oldest_active_posted_at,


            -- ------------------------------------------------
            -- Phase 1 publication rule
            --
            -- If Jobly possesses at least one exact posting
            -- date, there is date-based information to show.
            --
            -- Coverage is exposed separately instead of
            -- suppressing the company.
            -- ------------------------------------------------

            (
                jobs_with_posted_at > 0
            )
                AS is_publishable,


            CASE

                WHEN total_jobs_seen = 0
                THEN 'no_jobs_seen'

                WHEN jobs_with_posted_at = 0
                THEN 'no_exact_posted_dates'

                ELSE NULL

            END
                AS publishable_reason


        FROM aggregated
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

        oldest_posted_at,

        oldest_active_posted_at,

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

        oldest_posted_at,

        oldest_active_posted_at,

        is_publishable,

        publishable_reason,

        NOW()

    FROM calculated


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

        oldest_posted_at =
            EXCLUDED.oldest_posted_at,

        oldest_active_posted_at =
            EXCLUDED.oldest_active_posted_at,

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
-- Immediately recalculate existing data using the corrected
-- posted_at-only rules.
-- ============================================================

SELECT refresh_company_hiring_stats();
