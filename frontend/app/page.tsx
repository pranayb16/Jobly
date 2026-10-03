import Link from 'next/link';
import { ArrowRight, Building2, DatabaseZap, LineChart, Sparkles } from 'lucide-react';
import { Metric, Ranking } from '@/components/IntelligenceUI';
import { CompanySnapshot, Trends, formatNumber, getIntelligence } from '@/lib/intelligence';

type CompaniesPayload = { companies: CompanySnapshot[] };

export default async function HomePage() {
  const [trends, companiesPayload] = await Promise.all([
    getIntelligence<Trends>('/api/trends'),
    getIntelligence<CompaniesPayload>('/api/companies?limit=5'),
  ]);
  const companies = companiesPayload?.companies ?? [];
  const hasData = Boolean(trends?.snapshot_date);

  return <div className="intelligence-home">
    <section className="intel-hero"><div className="shell intel-hero-grid"><div><span className="intel-kicker"><i /> Daily employer intelligence</span><h1>See how companies are <em>actually hiring.</em></h1><p>Jobly tracks employer career sites over time, preserves every meaningful change, and turns job data into comparable hiring signals.</p><div className="intel-actions"><Link href="/companies">Explore companies <ArrowRight size={16} /></Link><Link href="/trends">View market trends</Link></div></div><div className="pipeline-card"><div><DatabaseZap size={19} /><strong>Daily intelligence pipeline</strong><span>{hasData ? 'Current' : 'Awaiting first run'}</span></div>{['Career sites crawled', 'Changes preserved', 'Jobs enriched', 'Snapshots generated'].map((item, index) => <p key={item}><b>{index + 1}</b>{item}<i /></p>)}<small>{trends?.snapshot_date ? `Latest snapshot · ${trends.snapshot_date}` : 'Run the pipeline to establish the first baseline'}</small></div></div></section>

    <section className="shell intel-overview"><div className="section-title"><div><span>MARKET OVERVIEW</span><h2>Today&apos;s hiring surface</h2></div><Link href="/trends">Full trends <ArrowRight size={14} /></Link></div><div className="metric-grid"><Metric label="Companies tracked" value={trends?.companies_tracked ?? 0} note="canonical employers" /><Metric label="Active openings" value={trends?.total_open_jobs ?? 0} note="current career-site listings" /><Metric label="Added today" value={trends?.new_jobs ?? 0} note="newly observed roles" /><Metric label="Removed today" value={trends?.removed_jobs ?? 0} note="closed or delisted roles" /><Metric label="Enrichment coverage" value={`${Math.round((trends?.enrichment_coverage ?? 0) * 100)}%`} note="AI aggregates disclose coverage" /></div></section>

    <section className="shell intel-split">{trends?.top_roles ? <Ranking title="Top roles" items={trends.top_roles} basePath="/roles" /> : <div className="coverage-card"><Sparkles size={20} /><h2>Role intelligence is building</h2><p>AI-derived rankings appear once enrichment coverage reaches the publication threshold.</p></div>}{trends?.top_skills ? <Ranking title="Top skills" items={trends.top_skills} basePath="/skills" /> : <div className="coverage-card"><LineChart size={20} /><h2>Skill intelligence is building</h2><p>Deterministic totals remain available while semantic coverage catches up.</p></div>}</section>

    <section className="shell company-preview"><div className="section-title"><div><span>COMPANY PULSE</span><h2>Largest active hiring footprints</h2></div><Link href="/companies">All companies <ArrowRight size={14} /></Link></div><div className="company-grid">{companies.map((company) => <Link href={`/companies/${company.slug}`} key={company.id}><Building2 size={18} /><strong>{company.name}</strong><span>{formatNumber(company.total_open_jobs)} openings</span><small>+{company.new_jobs ?? 0} / −{company.removed_jobs ?? 0} today</small></Link>)}{companies.length === 0 && <p className="inline-empty">No company snapshots yet.</p>}</div></section>
  </div>;
}
