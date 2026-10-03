import Link from 'next/link';
import { DetailHeader, EmptyState } from '@/components/IntelligenceUI';
import { formatNumber, getIntelligence } from '@/lib/intelligence';

type Detail = { skill: string; count: number; companies: { company: string; slug: string; count: number; enrichment_coverage: number }[] };

export default async function SkillPage({ params }: { params: Promise<{ skill: string }> }) {
  const { skill } = await params;
  const data = await getIntelligence<Detail>(`/api/skills/${encodeURIComponent(skill)}`);
  if (!data) return <div className="shell intel-page"><EmptyState /></div>;
  return <div className="shell intel-page"><DetailHeader label="SKILL INTELLIGENCE" title={data.skill} value={formatNumber(data.count)} /><div className="entity-list">{data.companies.map((row) => <Link href={`/companies/${row.slug}`} key={row.slug}><strong>{row.company}</strong><span>{formatNumber(row.count)} openings</span><small>{Math.round(row.enrichment_coverage * 100)}% coverage</small></Link>)}</div></div>;
}
