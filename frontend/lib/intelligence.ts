export type CountItem = { name: string; count: number };

export type CompanySnapshot = {
  id: number;
  name: string;
  slug: string;
  website_domain?: string | null;
  snapshot_date?: string | null;
  total_open_jobs?: number | null;
  new_jobs?: number | null;
  removed_jobs?: number | null;
  changed_jobs?: number | null;
  enriched_jobs?: number | null;
  enrichment_coverage?: number | null;
  ai_aggregates_available?: boolean;
  role_counts?: Record<string, number> | null;
  skill_counts?: Record<string, number> | null;
  seniority_counts?: Record<string, number> | null;
  location_counts?: Record<string, number> | null;
  workplace_counts?: Record<string, number> | null;
  domain_counts?: Record<string, number> | null;
};

export type CompanyHiringStats = {
  id: number;
  name: string;
  slug: string;
  website_domain: string | null;
  current_open_jobs: number;
  total_jobs_seen: number;
  jobs_with_posted_at: number;
  jobs_without_posted_at: number;
  posted_at_coverage: number;
  posted_today: number;
  posted_yesterday: number;
  daily_change: number;
  posted_last_7_days: number;
  posted_previous_7_days: number;
  weekly_change: number;
  weekly_growth_percent: number | null;
  posted_last_15_days: number;
  active_from_last_15_days: number;
  removed_from_last_15_days: number;
  active_30_plus_days: number;
  active_45_plus_days: number;
  active_90_plus_days: number;
  latest_posted_at: string | null;
  oldest_posted_at: string | null;
  oldest_active_posted_at: string | null;
  is_publishable: boolean;
  publishable_reason: string | null;
  calculated_at: string;
};

export type Trends = {
  snapshot_date?: string | null;
  companies_tracked: number;
  total_open_jobs: number;
  new_jobs: number;
  removed_jobs: number;
  changed_jobs: number;
  enriched_jobs: number;
  enrichment_coverage: number;
  ai_aggregates_available: boolean;
  change_7d?: { absolute: number; percent: number | null } | null;
  change_30d?: { absolute: number; percent: number | null } | null;
  top_roles?: CountItem[] | null;
  top_skills?: CountItem[] | null;
};

const apiBase = (process.env.JOBS_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

export async function getIntelligence<T>(path: string): Promise<T | null> {
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

export function formatNumber(value?: number | null) {
  return new Intl.NumberFormat('en-US').format(value ?? 0);
}

export function formatSigned(value: number) {
  if (value > 0) return `+${formatNumber(value)}`;
  return formatNumber(value);
}

export function formatGrowth(value: number | null) {
  if (value === null) return '—';
  return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
}

export function changeClass(value: number | null) {
  if (value === null || value === 0) return 'neutral';
  return value > 0 ? 'positive' : 'negative';
}

export function formatDateTime(value: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

export function topEntries(values?: Record<string, number> | null, limit = 8) {
  return Object.entries(values ?? {}).sort((a, b) => b[1] - a[1]).slice(0, limit);
}
