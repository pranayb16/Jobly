import { CompanyIntelligenceDashboard } from '@/components/companies/CompanyIntelligenceDashboard';
import { EmptyState } from '@/components/IntelligenceUI';
import { CompanyHiringStats, getIntelligence } from '@/lib/intelligence';

type Payload = { companies: CompanyHiringStats[]; count: number };

export default async function CompaniesPage() {
  const data = await getIntelligence<Payload>('/api/companies?limit=200');
  return <div className="company-intelligence-shell">
    <div className="intelligence-ambient" aria-hidden="true"><i /><i /><i /></div>
    <div className="shell intel-page">
      {!data?.companies.length ? <EmptyState message="No publishable company hiring statistics are available yet." /> : <CompanyIntelligenceDashboard companies={data.companies} total={data.count} />}
    </div>
  </div>;
}
