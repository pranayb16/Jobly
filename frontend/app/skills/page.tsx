import { EmptyState, PageIntro, Ranking } from '@/components/IntelligenceUI';
import { CountItem, getIntelligence } from '@/lib/intelligence';

export default async function SkillsPage() {
  const data = await getIntelligence<{ skills: CountItem[] }>('/api/skills?limit=100');
  return <div className="shell intel-page"><PageIntro eyebrow="SKILL TAXONOMY" title="Skills appearing in demand" copy="Required and preferred skills found in currently open jobs, shown with explicit enrichment coverage." />{data?.skills.length ? <Ranking title="Current skill counts" items={data.skills} basePath="/skills" /> : <EmptyState />}</div>;
}
