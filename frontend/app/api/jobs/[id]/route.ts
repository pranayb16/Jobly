import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type Row = Record<string, unknown>;

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
    });
  } catch {
    return NextResponse.json({ message: 'Job details are unavailable.' }, { status: 502 });
  }
}
