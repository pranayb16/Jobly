import { EmptyState, Metric, PageIntro, Ranking } from '@/components/IntelligenceUI';
import { Trends, getIntelligence } from '@/lib/intelligence';

function changeLabel(change?: { absolute: number; percent: number | null } | null) {
  if (!change) return 'Unavailable';
  const sign = change.absolute > 0 ? '+' : '';
  return `${sign}${change.absolute}${change.percent === null ? '' : ` (${sign}${change.percent}%)`}`;
}

export default async function TrendsPage() {
  const data = await getIntelligence<Trends>('/api/trends');
  return <div className="shell intel-page"><PageIntro eyebrow="MARKET TRENDS" title="Daily hiring movement" copy="Deterministic changes derived from job events and company snapshots—no generated predictions." />{!data?.snapshot_date ? <EmptyState /> : <><div className="metric-grid"><Metric label="Active openings" value={data.total_open_jobs} /><Metric label="7-day change" value={changeLabel(data.change_7d)} /><Metric label="30-day change" value={changeLabel(data.change_30d)} /><Metric label="Coverage" value={`${Math.round(data.enrichment_coverage * 100)}%`} /></div>{data.ai_aggregates_available && data.top_roles && data.top_skills ? <div className="intel-split"><Ranking title="Top roles" items={data.top_roles} basePath="/roles" /><Ranking title="Top skills" items={data.top_skills} basePath="/skills" /></div> : <div className="intel-empty"><strong>Semantic rankings are not published yet.</strong><p>Historical totals are valid, but enrichment coverage is below the safe threshold.</p></div>}</>}</div>;
}
