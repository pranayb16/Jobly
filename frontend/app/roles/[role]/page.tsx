import Link from 'next/link';
import { DetailHeader, EmptyState } from '@/components/IntelligenceUI';
import { formatNumber, getIntelligence } from '@/lib/intelligence';

type Detail = { role: string; count: number; companies: { company: string; slug: string; count: number; enrichment_coverage: number }[] };

export default async function RolePage({ params }: { params: Promise<{ role: string }> }) {
  const { role } = await params;
  const data = await getIntelligence<Detail>(`/api/roles/${encodeURIComponent(role)}`);
  if (!data) return <div className="shell intel-page"><EmptyState /></div>;
  return <div className="shell intel-page"><DetailHeader label="ROLE INTELLIGENCE" title={data.role} value={formatNumber(data.count)} /><div className="entity-list">{data.companies.map((row) => <Link href={`/companies/${row.slug}`} key={row.slug}><strong>{row.company}</strong><span>{formatNumber(row.count)} openings</span><small>{Math.round(row.enrichment_coverage * 100)}% coverage</small></Link>)}</div></div>;
}
