ALTER TABLE companies
ADD COLUMN IF NOT EXISTS tracking_started_at TIMESTAMPTZ;


CREATE OR REPLACE VIEW company_tracking_summary AS

SELECT
    c.id AS company_id,
    c.name,
    c.tracking_started_at,

    MIN(s.snapshot_date) AS first_snapshot_date,
    MAX(s.snapshot_date) AS latest_snapshot_date,

    COUNT(DISTINCT s.snapshot_date) AS snapshot_days

FROM companies c

LEFT JOIN company_daily_snapshots s
    ON s.company_id = c.id

GROUP BY
    c.id,
    c.name,
    c.tracking_started_at;

SELECT *
FROM company_tracking_summary
ORDER BY company_id;