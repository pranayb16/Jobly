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

export function topEntries(values?: Record<string, number> | null, limit = 8) {
  return Object.entries(values ?? {}).sort((a, b) => b[1] - a[1]).slice(0, limit);
}
