import { EmptyState, PageIntro, Ranking } from '@/components/IntelligenceUI';
import { CountItem, getIntelligence } from '@/lib/intelligence';

export default async function RolesPage() {
  const data = await getIntelligence<{ roles: CountItem[] }>('/api/roles?limit=100');
  return <div className="shell intel-page"><PageIntro eyebrow="ROLE TAXONOMY" title="Roles companies need now" copy="Normalized role demand across the latest company snapshots." />{data?.roles.length ? <Ranking title="Current role counts" items={data.roles} basePath="/roles" /> : <EmptyState />}</div>;
}
