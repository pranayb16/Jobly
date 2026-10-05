'use client';

import { Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import type { PipelineLog } from '@/lib/admin';

const logTime = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(date);
};

export function LogViewer({ logs }: { logs: PipelineLog[] }) {
  const stages = [...new Set(logs.map((log) => log.stage ?? 'pipeline'))].sort();
  const levels = [...new Set(logs.map((log) => log.level))].sort();
  const [stage, setStage] = useState('');
  const [level, setLevel] = useState('');
  const [query, setQuery] = useState('');
  const visible = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return logs.filter((log) => (!stage || (log.stage ?? 'pipeline') === stage) && (!level || log.level === level) && (!needle || `${log.logger} ${log.message} ${log.exception ?? ''}`.toLocaleLowerCase().includes(needle)));
  }, [logs, stage, level, query]);

  return <div className="admin-contained-table log-browser">
    <div className="admin-table-toolbar log-toolbar">
      <label><span className="sr-only">Stage</span><select value={stage} onChange={(event) => setStage(event.target.value)}><option value="">All stages</option>{stages.map((item) => <option value={item} key={item}>{item}</option>)}</select></label>
      <label><span className="sr-only">Level</span><select value={level} onChange={(event) => setLevel(event.target.value)}><option value="">All levels</option>{levels.map((item) => <option value={item} key={item}>{item}</option>)}</select></label>
      <label className="admin-search"><Search size={14} /><span className="sr-only">Search logs</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search logs…" /></label>
      <span className="admin-result-count">{visible.length} shown</span>
    </div>
    <div className="log-columns" aria-hidden="true"><span>Time</span><span>Level</span><span>Stage</span><span>Logger</span><span>Message</span></div>
    <div className="admin-scroll-region log-scroll-region">
      {visible.length === 0 ? <div className="admin-inline-empty">No logs match these filters.</div> : visible.map((log) => <article className={`log-entry log-${log.level.toLocaleLowerCase()}`} key={log.id}>
        <time dateTime={log.created_at}>{logTime(log.created_at)}</time>
        <strong>{log.level}</strong>
        <span>{log.stage ?? 'pipeline'}</span>
        <code>{log.logger}</code>
        <div><p>{log.message}</p>{log.exception && <details><summary>View stack trace</summary><pre>{log.exception}</pre></details>}</div>
      </article>)}
    </div>
  </div>;
}
