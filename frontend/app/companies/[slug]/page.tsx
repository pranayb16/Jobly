import { DetailHeader, EmptyState, Metric, Ranking } from '@/components/IntelligenceUI';
import { CompanySnapshot, CountItem, formatNumber, getIntelligence, topEntries } from '@/lib/intelligence';

export default async function CompanyPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const company = await getIntelligence<CompanySnapshot>(`/api/companies/${encodeURIComponent(slug)}`);
  if (!company) return <div className="shell intel-page"><EmptyState /></div>;
  const roles: CountItem[] = topEntries(company.role_counts).map(([name, count]) => ({ name, count }));
  const skills: CountItem[] = topEntries(company.skill_counts).map(([name, count]) => ({ name, count }));
  return <div className="shell intel-page"><DetailHeader label="COMPANY INTELLIGENCE" title={company.name} value={formatNumber(company.total_open_jobs)} href={company.website_domain ? `https://${company.website_domain}` : undefined} /><div className="metric-grid detail-metrics"><Metric label="Added today" value={company.new_jobs ?? 0} /><Metric label="Removed today" value={company.removed_jobs ?? 0} /><Metric label="Changed today" value={company.changed_jobs ?? 0} /><Metric label="Enrichment coverage" value={`${Math.round((company.enrichment_coverage ?? 0) * 100)}%`} /></div>{company.ai_aggregates_available ? <div className="intel-split"><Ranking title="Current roles" items={roles} basePath="/roles" /><Ranking title="Current skills" items={skills} basePath="/skills" /></div> : <div className="intel-empty"><strong>Semantic aggregates are withheld for now.</strong><p>Coverage is below the publication threshold; deterministic opening and change counts remain valid.</p></div>}</div>;
}
