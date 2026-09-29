import { NextResponse } from 'next/server';
import { mockJobs } from '@/lib/mockJobs';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type JobRow = Record<string, unknown>;
type JobsApiPayload = { count?: number; jobs?: JobRow[] };

function first(row: JobRow, keys: string[], fallback: unknown = '') {
  for (const key of keys) {
    if (row[key] !== undefined && row[key] !== null) return row[key];
  }
  return fallback;
}

function numberOrNull(value: unknown) {
  if (value === '' || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function decodeDisplayValue(value: unknown, fallback: string) {
  const text = String(value ?? fallback);
  try {
    return decodeURIComponent(text);
  } catch {
    return text;
  }
}

function normalizeJob(row: JobRow, index: number) {
  return {
    id: first(row, ['id', 'job_id'], index + 1) as string | number,
    title: String(first(row, ['title', 'job_title', 'position'], 'Untitled role')),
    company: decodeDisplayValue(first(row, ['company', 'company_name', 'organization'], 'Company'), 'Company'),
    location: String(first(row, ['location', 'job_location', 'city'], 'Location flexible')),
    description: String(first(row, ['description_excerpt', 'description'], '')),
    employmentType: String(first(row, ['employment_type', 'job_type', 'type'], 'full_time')),
    workplaceType: String(first(row, ['workplace_type', 'work_mode', 'remote_type'], '')),
    salaryMin: numberOrNull(first(row, ['salary_min', 'min_salary'], null)),
    salaryMax: numberOrNull(first(row, ['salary_max', 'max_salary'], null)),
    salaryCurrency: String(first(row, ['salary_currency', 'currency'], 'USD')),
    createdAt: first(row, ['posted_at', 'created_at', 'date_posted', 'first_seen_at'], null) as string | null,
    provider: String(first(row, ['provider', 'source'], '')),
    jobUrl: String(first(row, ['job_url', 'url'], '')),
    applyUrl: String(first(row, ['apply_url', 'application_url'], '')),
  };
}

function isWithinLast48Hours(row: JobRow) {
  const value = first(row, ['posted_at', 'created_at', 'date_posted', 'first_seen_at'], null);
  if (!value) return false;

  const postedAt = new Date(String(value)).getTime();
  if (Number.isNaN(postedAt)) return false;

  const age = Date.now() - postedAt;
  return age >= 0 && age <= 48 * 60 * 60 * 1000;
}

async function fetchJobsPage(apiBaseUrl: string, offset: number) {
  const response = await fetch(`${apiBaseUrl}/api/jobs?limit=100&offset=${offset}`, {
    cache: 'no-store',
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(10_000),
  });

  if (!response.ok) {
    throw new Error(`Jobs API returned ${response.status}`);
  }

  return response.json() as Promise<JobsApiPayload>;
}


export async function GET() {
  try {
    let rows: JobRow[];

    if (process.env.USE_MOCK_DATA === 'true') {
      rows = mockJobs.filter(isWithinLast48Hours);
    } else {
      const apiBaseUrl = (process.env.JOBS_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');
      rows = [];
      let offset = 0;
      let totalActiveJobs = Number.POSITIVE_INFINITY;
      let reachedOlderJobs = false;

      while (offset < totalActiveJobs && !reachedOlderJobs) {
        const page = await fetchJobsPage(apiBaseUrl, offset);
        const pageRows = Array.isArray(page.jobs) ? page.jobs : [];
        totalActiveJobs = typeof page.count === 'number' ? page.count : offset + pageRows.length;
        rows.push(...pageRows.filter(isWithinLast48Hours));
        reachedOlderJobs = pageRows.some((row) => !isWithinLast48Hours(row));
        offset += 100;
        if (pageRows.length === 0) break;
      }

    }

    const jobs = rows.map(normalizeJob).sort((a, b) => {
      if (!a.createdAt || !b.createdAt) return 0;
      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    });

    return NextResponse.json({ jobs, count: jobs.length });
  } catch (error) {
    console.error('Failed to load jobs from FastAPI:', error);
    return NextResponse.json(
      { message: 'The jobs API is unavailable. Check that FastAPI is running and JOBS_API_URL is correct.' },
      { status: 502 },
    );
  }
}
