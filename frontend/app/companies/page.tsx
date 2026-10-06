import { CompanyIntelligenceDashboard } from '@/components/companies/CompanyIntelligenceDashboard';
import { EmptyState } from '@/components/IntelligenceUI';
import { CompanyHiringStats, getIntelligence } from '@/lib/intelligence';

type Payload = { companies: CompanyHiringStats[]; count: number };

export default async function CompaniesPage() {
  const companies: CompanyHiringStats[] = [];
  let offset = 0;
  let total = Number.POSITIVE_INFINITY;
  while (offset < total) {
    const page = await getIntelligence<Payload>(`/api/companies?limit=200&offset=${offset}`);
    if (!page) break;
    companies.push(...page.companies);
    total = page.count;
    if (page.companies.length === 0) break;
    offset += page.companies.length;
  }
  return <div className="company-intelligence-shell">
    <div className="intelligence-ambient" aria-hidden="true"><i /><i /><i /></div>
    <div className="shell intel-page">
      {!companies.length ? <EmptyState message="No publishable company hiring statistics are available yet." /> : <CompanyIntelligenceDashboard companies={companies} total={Number.isFinite(total) ? total : companies.length} />}
    </div>
  </div>;
}
