import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type Row = Record<string, unknown>;
const strings = (value: unknown) => Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
const numberOrNull = (value: unknown) => value === null || value === undefined || !Number.isFinite(Number(value)) ? null : Number(value);
const locations = (value: unknown) => Array.isArray(value) ? value.filter((item): item is Row => typeof item === 'object' && item !== null).map((item) => ({ city: item.city ? String(item.city) : null, state: item.state ? String(item.state) : null, stateCode: item.state_code ? String(item.state_code) : null, country: item.country ? String(item.country) : null, countryCode: item.country_code ? String(item.country_code) : null, remote: Boolean(item.remote) })) : [];

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await context.params;
    const apiBaseUrl = (process.env.JOBS_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');
    const response = await fetch(`${apiBaseUrl}/api/jobs/${encodeURIComponent(id)}`, {
      cache: 'no-store', headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(10_000),
    });
    if (!response.ok) return NextResponse.json({ message: 'Job details are unavailable.' }, { status: response.status });
    const row = await response.json() as Row;
    return NextResponse.json({
      id: row.id, title: String(row.title ?? 'Untitled role'), company: String(row.company ?? 'Company'),
      location: String(row.location ?? 'Location flexible'), description: String(row.description_text ?? row.description_excerpt ?? ''),
      employmentType: String(row.employment_type ?? ''), workplaceType: String(row.workplace_type ?? ''),
      salaryMin: null, salaryMax: null, salaryCurrency: 'USD', createdAt: row.posted_at ?? null,
      provider: String(row.provider ?? ''), jobUrl: String(row.job_url ?? ''), applyUrl: String(row.apply_url ?? ''),
      jobFamily: String(row.job_family ?? ''), jobSubfamily: String(row.job_subfamily ?? ''),
      relatedRoles: strings(row.related_roles), skills: strings(row.skills), seniority: String(row.seniority ?? ''),
      yearsExperienceMin: numberOrNull(row.years_experience_min), yearsExperienceMax: numberOrNull(row.years_experience_max),
      aiLocations: locations(row.ai_locations), classificationConfidence: numberOrNull(row.classification_confidence),
    });
  } catch {
    return NextResponse.json({ message: 'Job details are unavailable.' }, { status: 502 });
  }
}
