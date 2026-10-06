import { connection, NextResponse } from 'next/server';
import { mockJobs } from '@/lib/mockJobs';

export const runtime = 'nodejs';
export const revalidate = 60;

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

function stringArray(value: unknown) {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function locations(value: unknown) {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is JobRow => typeof item === 'object' && item !== null).map((item) => ({
    city: item.city ? String(item.city) : null,
    state: item.state ? String(item.state) : null,
    stateCode: item.state_code ? String(item.state_code) : null,
    country: item.country ? String(item.country) : null,
    countryCode: item.country_code ? String(item.country_code) : null,
    remote: Boolean(item.remote),
  }));
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
  const postedAt = first(row, ['posted_at', 'date_posted'], null) as string | null;
  const observedAt = first(row, ['first_seen_at'], null) as string | null;
  return {
    id: first(row, ['id', 'job_id'], index + 1) as string | number,
    title: String(first(row, ['title', 'job_title', 'position'], 'Untitled role')),
    company: decodeDisplayValue(first(row, ['company', 'company_name', 'organization'], ''), ''),
    location: String(first(row, ['location', 'job_location', 'city'], '')),
    description: String(first(row, ['description_excerpt', 'description'], '')),
    employmentType: String(first(row, ['employment_type', 'job_type', 'type'], '')),
    workplaceType: String(first(row, ['workplace_type', 'work_mode', 'remote_type'], '')),
    salaryMin: numberOrNull(first(row, ['salary_min', 'min_salary'], null)),
    salaryMax: numberOrNull(first(row, ['salary_max', 'max_salary'], null)),
    salaryCurrency: String(first(row, ['salary_currency', 'currency'], '')),
    salaryPeriod: String(first(row, ['salary_period'], '')),
    createdAt: postedAt ?? observedAt,
    dateSource: postedAt ? 'posted' as const : observedAt ? 'observed' as const : null,
    provider: String(first(row, ['provider', 'source'], '')),
    jobUrl: String(first(row, ['job_url', 'url'], '')),
    applyUrl: String(first(row, ['apply_url', 'application_url'], '')),
    jobFamily: String(first(row, ['job_family'], '')),
    jobSubfamily: String(first(row, ['job_subfamily'], '')),
    relatedRoles: stringArray(first(row, ['related_roles'], [])),
    skills: stringArray(first(row, ['skills'], [])),
    seniority: String(first(row, ['seniority'], '')),
    yearsExperienceMin: numberOrNull(first(row, ['years_experience_min'], null)),
    yearsExperienceMax: numberOrNull(first(row, ['years_experience_max'], null)),
    aiLocations: locations(first(row, ['ai_locations'], [])),
    classificationConfidence: numberOrNull(first(row, ['classification_confidence'], null)),
  };
}

function isWithinLast48Hours(row: JobRow) {
  const value = first(row, ['posted_at', 'date_posted'], null);
  if (!value) return false;

  const postedAt = new Date(String(value)).getTime();
  if (Number.isNaN(postedAt)) return false;

  const age = Date.now() - postedAt;
  return age >= 0 && age <= 48 * 60 * 60 * 1000;
}

async function fetchRecentJobs(apiBaseUrl: string) {
  const postedSince = new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString();
  const response = await fetch(`${apiBaseUrl}/api/jobs?limit=5000&posted_since=${encodeURIComponent(postedSince)}`, {
    next: { revalidate: 60 },
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(10_000),
  });

  if (!response.ok) {
    throw new Error(`Jobs API returned ${response.status}`);
  }

  return response.json() as Promise<JobsApiPayload>;
}


export async function GET() {
  await connection();
  try {
    let rows: JobRow[];

    if (process.env.USE_MOCK_DATA === 'true') {
      rows = mockJobs.filter(isWithinLast48Hours);
    } else {
      const apiBaseUrl = (process.env.JOBS_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');
      const page = await fetchRecentJobs(apiBaseUrl);
      rows = Array.isArray(page.jobs) ? page.jobs.filter(isWithinLast48Hours) : [];
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
