'use client';

import { Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import type { CrawlRun } from '@/lib/admin';
import { formatDuration } from '@/lib/admin';
import { formatNumber } from '@/lib/intelligence';
import { StatusBadge } from './AdminPrimitives';

type CrawlFilter = 'all' | 'success' | 'warning' | 'failed';

const classification = (crawl: CrawlRun): Exclude<CrawlFilter, 'all'> => crawl.status === 'failed' || crawl.error ? 'failed' : crawl.warning || crawl.deactivation_skipped ? 'warning' : 'success';

export function CrawlTable({ crawls }: { crawls: CrawlRun[] }) {
  const [filter, setFilter] = useState<CrawlFilter>('all');
  const [query, setQuery] = useState('');
  const visible = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return crawls.filter((crawl) => {
      const matchesFilter = filter === 'all' || classification(crawl) === filter;
      const haystack = [crawl.company_name, crawl.provider, crawl.canonical_url, crawl.source_id].join(' ').toLocaleLowerCase();
      return matchesFilter && (!needle || haystack.includes(needle));
    });
  }, [crawls, filter, query]);

  return <div className="admin-contained-table crawl-browser">
    <div className="admin-table-toolbar">
      <div className="admin-segmented" aria-label="Filter crawl results">
        {(['all', 'success', 'warning', 'failed'] as CrawlFilter[]).map((item) => <button className={filter === item ? 'active' : ''} onClick={() => setFilter(item)} type="button" key={item}>{item}</button>)}
      </div>
      <label className="admin-search"><Search size={14} /><span className="sr-only">Search company or source</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search company/source…" /></label>
      <span className="admin-result-count">{visible.length} of {crawls.length}</span>
    </div>
    <div className="crawl-columns" aria-hidden="true"><span>Company</span><span>Provider</span><span>Jobs</span><span>Status</span><span>Duration</span><span>Warning / error</span><span /></div>
    <div className="admin-scroll-region crawl-scroll-region">
      {visible.length === 0 ? <div className="admin-inline-empty">No crawl rows match this view.</div> : visible.map((crawl) => {
        const kind = classification(crawl);
        return <details className={`crawl-entry crawl-${kind}`} key={crawl.crawl_run_id}>
          <summary>
            <strong>{crawl.company_name ?? `Source #${crawl.source_id}`}</strong>
            <span>{crawl.provider ?? '—'}</span>
            <span>{formatNumber(crawl.job_count)}</span>
            <span><StatusBadge status={kind === 'warning' ? 'warning' : crawl.status} /></span>
            <span>{formatDuration(crawl.duration_seconds)}</span>
            <span>{crawl.error ?? crawl.warning ?? (crawl.deactivation_skipped ? 'Deactivation skipped' : '—')}</span>
            <i aria-hidden="true">›</i>
          </summary>
          <dl>
            <div><dt>Source URL</dt><dd>{crawl.canonical_url ?? '—'}</dd></div>
            <div><dt>Source ID</dt><dd>{crawl.source_id}</dd></div>
            <div><dt>Crawl run ID</dt><dd>{crawl.crawl_run_id}</dd></div>
            <div><dt>Started</dt><dd>{crawl.started_at}</dd></div>
            <div><dt>Finished</dt><dd>{crawl.finished_at ?? 'Still running'}</dd></div>
            <div><dt>Duration</dt><dd>{formatDuration(crawl.duration_seconds)}</dd></div>
            <div><dt>Deactivation skipped</dt><dd>{crawl.deactivation_skipped ? 'Yes' : 'No'}</dd></div>
            {crawl.warning && <div><dt>Warning</dt><dd>{crawl.warning}</dd></div>}
            {crawl.error && <div><dt>Error</dt><dd>{crawl.error}</dd></div>}
          </dl>
        </details>;
      })}
    </div>
  </div>;
}
