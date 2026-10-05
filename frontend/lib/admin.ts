export type PipelineRun = {
  id: number;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  source_target: number | null;
  sources_attempted: number | null;
  sources_successful: number | null;
  sources_failed: number | null;
  jobs_seen: number | null;
  jobs_new: number | null;
  jobs_changed: number | null;
  jobs_removed: number | null;
  enrichments_processed: number | null;
  enrichments_completed: number | null;
  enrichments_failed: number | null;
  enrichment_backlog: number | null;
  snapshots_created: number | null;
  company_stats_refreshed: number | null;
  company_stats_publishable: number | null;
  company_stats_unpublishable: number | null;
  error: string | null;
};

export type PipelineStage = {
  stage: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  metrics: Record<string, unknown> | null;
  error: string | null;
};

export type PipelineEvent = {
  id: number;
  stage: string | null;
  severity: string;
  event_type: string;
  source_id: number | null;
  job_id: number | null;
  queue_id: number | null;
  provider: string | null;
  model: string | null;
  message: string;
  details: Record<string, unknown> | null;
  created_at: string;
};

export type CrawlRun = {
  crawl_run_id: number;
  source_id: number;
  provider: string | null;
  canonical_url: string | null;
  company_id: number | null;
  company_name: string | null;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  job_count: number | null;
  deactivation_skipped: boolean;
  warning: string | null;
  error: string | null;
};

export type PipelineLog = {
  id: number;
  stage: string | null;
  created_at: string;
  level: string;
  logger: string;
  message: string;
  exception: string | null;
};

export type RunsPayload = { count: number; limit: number; offset: number; runs: PipelineRun[] };
export type RunDetailPayload = { run: PipelineRun; stages: PipelineStage[]; events: PipelineEvent[]; crawl_runs: CrawlRun[] };
export type LogsPayload = { count: number; limit: number; offset: number; logs: PipelineLog[] };

const apiBase = (process.env.JOBS_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

export async function getAdmin<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${apiBase}${path}`, {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(8_000),
    });
    if (!response.ok) return null;
    return await response.json() as T;
  } catch {
    return null;
  }
}

export function formatAdminDate(value: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'medium' }).format(date);
}

export function formatDuration(value: number | null) {
  if (value === null || !Number.isFinite(value)) return '—';
  if (value < 60) return `${value.toFixed(value < 10 ? 1 : 0)}s`;
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes}m ${seconds}s`;
}
