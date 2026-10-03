import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { EmptyState, PageIntro } from '@/components/IntelligenceUI';
import { CompanySnapshot, formatNumber, getIntelligence } from '@/lib/intelligence';

type Payload = { companies: CompanySnapshot[]; count: number };

export default async function CompaniesPage() {
  const data = await getIntelligence<Payload>('/api/companies?limit=200');
  return <div className="shell intel-page"><PageIntro eyebrow="COMPANY INDEX" title="Hiring activity by employer" copy="Current openings, daily changes, and semantic coverage for every canonical company Jobly tracks." />{!data?.companies.length ? <EmptyState /> : <div className="data-table company-table"><div className="data-row data-head"><span>Company</span><span>Open roles</span><span>Added</span><span>Removed</span><span>Coverage</span></div>{data.companies.map((company) => <Link className="data-row" href={`/companies/${company.slug}`} key={company.id}><strong>{company.name}<small>{company.website_domain ?? 'Career site tracked'}</small></strong><b>{formatNumber(company.total_open_jobs)}</b><span className="positive">+{company.new_jobs ?? 0}</span><span className="negative">−{company.removed_jobs ?? 0}</span><span>{Math.round((company.enrichment_coverage ?? 0) * 100)}% <ArrowRight size={13} /></span></Link>)}</div>}</div>;
}
