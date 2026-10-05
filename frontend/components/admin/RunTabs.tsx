import Link from 'next/link';

export type RunView = 'overview' | 'crawl' | 'enrichment' | 'stats' | 'issues' | 'logs';

const tabs: Array<{ view: RunView; label: string }> = [
  { view: 'overview', label: 'Overview' },
  { view: 'crawl', label: 'Crawl' },
  { view: 'enrichment', label: 'Enrichment' },
  { view: 'stats', label: 'Statistics' },
  { view: 'issues', label: 'Issues' },
  { view: 'logs', label: 'Raw Logs' },
];

export function RunTabs({ runId, active }: { runId: number; active: RunView }) {
  return <nav className="admin-tabs" aria-label="Pipeline run sections">
    {tabs.map((tab) => <Link aria-current={active === tab.view ? 'page' : undefined} className={active === tab.view ? 'active' : ''} href={`/admin/runs/${runId}?view=${tab.view}`} key={tab.view}>{tab.label}</Link>)}
  </nav>;
}
