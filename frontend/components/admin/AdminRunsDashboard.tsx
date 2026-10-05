'use client';

import Link from 'next/link';
import {
  Activity,
  Bot,
  Braces,
  ChevronDown,
  CircleAlert,
  Clock3,
  DatabaseZap,
  ExternalLink,
  Search,
  ServerCog,
  Sparkles,
} from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useMemo, useState, type ReactNode } from 'react';
import { formatAdminDate, formatDuration, type PipelineRun } from '@/lib/admin';
import { formatNumber } from '@/lib/intelligence';
import { StatusBadge } from './AdminPrimitives';

function RunMetric({ label, value, icon }: { label: string; value: ReactNode; icon?: ReactNode }) {
  return <div className="run-expanded-metric">{icon}<span>{label}</span><strong>{value}</strong></div>;
}

function RunCard({ run, open, onToggle, index }: { run: PipelineRun; open: boolean; onToggle: () => void; index: number }) {
  const reduceMotion = useReducedMotion();
  const problemCount = (run.sources_failed ?? 0) + (run.enrichments_failed ?? 0);
  return <motion.article
    layout={!reduceMotion}
    className={`run-card ${open ? 'is-open' : ''} run-${run.status}`}
    initial={reduceMotion ? false : { opacity: 0, y: 12 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: .3, delay: reduceMotion ? 0 : Math.min(index * .04, .28) }}
  >
    <button className="run-card-summary" type="button" onClick={onToggle} aria-expanded={open} aria-controls={`run-details-${run.id}`}>
      <span className="run-id"><i aria-hidden="true">#{run.id}</i><span><strong>Pipeline run</strong><small>{formatAdminDate(run.started_at)}</small></span></span>
      <span className="run-summary-stat"><small>Duration</small><strong>{formatDuration(run.duration_seconds)}</strong></span>
      <span className="run-summary-stat"><small>Sources</small><strong>{formatNumber(run.sources_attempted)}</strong></span>
      <span className="run-summary-stat"><small>Jobs seen</small><strong>{formatNumber(run.jobs_seen)}</strong></span>
      <span className="run-summary-stat"><small>AI complete</small><strong>{formatNumber(run.enrichments_completed)}</strong></span>
      <span className="run-summary-stat"><small>Failed</small><strong className={problemCount ? 'negative' : ''}>{formatNumber(problemCount)}</strong></span>
      <StatusBadge status={run.status} />
      <ChevronDown className="run-card-chevron" size={17} aria-hidden="true" />
    </button>
    <AnimatePresence initial={false}>
      {open && <motion.div
        id={`run-details-${run.id}`}
        className="run-card-details"
        initial={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
        animate={reduceMotion ? { opacity: 1 } : { height: 'auto', opacity: 1 }}
        exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
        transition={{ duration: .28, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="run-card-details-inner">
          <section><header><ServerCog size={15} /><span>Crawl summary</span></header><div className="run-expanded-grid">
            <RunMetric label="Successful" value={formatNumber(run.sources_successful)} />
            <RunMetric label="Failed" value={formatNumber(run.sources_failed)} />
            <RunMetric label="Jobs new" value={formatNumber(run.jobs_new)} />
            <RunMetric label="Changed" value={formatNumber(run.jobs_changed)} />
            <RunMetric label="Removed" value={formatNumber(run.jobs_removed)} />
          </div></section>
          <section><header><Bot size={15} /><span>Enrichment</span></header><div className="run-expanded-grid">
            <RunMetric label="Processed" value={formatNumber(run.enrichments_processed)} />
            <RunMetric label="Completed" value={formatNumber(run.enrichments_completed)} />
            <RunMetric label="Failed" value={formatNumber(run.enrichments_failed)} />
            <RunMetric label="Backlog" value={formatNumber(run.enrichment_backlog)} />
          </div></section>
          <section><header><DatabaseZap size={15} /><span>Hiring statistics</span></header><div className="run-expanded-grid">
            <RunMetric label="Refreshed" value={formatNumber(run.company_stats_refreshed)} />
            <RunMetric label="Publishable" value={formatNumber(run.company_stats_publishable)} />
            <RunMetric label="Unpublishable" value={formatNumber(run.company_stats_unpublishable)} />
          </div></section>
          {run.error && <div className="run-card-error"><CircleAlert size={15} /><span>{run.error}</span></div>}
          <div className="run-card-actions">
            <Link href={`/admin/runs/${run.id}?view=overview`}>Open run dashboard <ExternalLink size={13} /></Link>
            <Link href={`/admin/runs/${run.id}?view=logs`}><Braces size={13} /> Raw logs</Link>
          </div>
        </div>
      </motion.div>}
    </AnimatePresence>
  </motion.article>;
}

export function AdminRunsDashboard({ runs, count }: { runs: PipelineRun[]; count: number }) {
  const reduceMotion = useReducedMotion();
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const [expanded, setExpanded] = useState<number | null>(runs[0]?.id ?? null);
  const completed = runs.filter((run) => run.status !== 'running');
  const successful = completed.filter((run) => run.status === 'success').length;
  const durations = completed.flatMap((run) => run.duration_seconds === null ? [] : [run.duration_seconds]);
  const averageDuration = durations.length ? durations.reduce((total, duration) => total + duration, 0) / durations.length : null;
  const failures = runs.filter((run) => run.status === 'failed').length;
  const visible = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return runs.filter((run) => (status === 'all' || run.status === status) && (!needle || `#${run.id} ${run.status} ${run.error ?? ''}`.toLocaleLowerCase().includes(needle)));
  }, [query, runs, status]);

  const summaries = [
    { icon: <Activity size={18} />, label: 'Runs captured', value: formatNumber(count), note: 'newest executions first' },
    { icon: <Sparkles size={18} />, label: 'Success rate', value: completed.length ? `${Math.round((successful / completed.length) * 100)}%` : '—', note: `${successful} successful runs` },
    { icon: <Clock3 size={18} />, label: 'Average duration', value: formatDuration(averageDuration), note: 'completed pipelines' },
    { icon: <CircleAlert size={18} />, label: 'Failed runs', value: formatNumber(failures), note: failures ? 'review recommended' : 'no active failures' },
  ];

  return <div className="admin-runs-dashboard">
    <motion.header className="admin-cosmic-hero" initial={reduceMotion ? false : { opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .55, ease: [0.22, 1, 0.36, 1] }}>
      <span><ServerCog size={13} /> INTERNAL OPERATIONS</span>
      <h1>Pipeline <em>Control Room</em></h1>
      <p>A compact, structured view of every crawl, enrichment pass, and statistics refresh—raw output stays out of the way until you need it.</p>
      <div><i /> Observability stream available</div>
    </motion.header>

    <section className="admin-cosmic-metrics" aria-label="Pipeline summary">
      {summaries.map((item, index) => <motion.article initial={reduceMotion ? false : { opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: reduceMotion ? 0 : .08 + index * .06 }} whileHover={reduceMotion ? undefined : { y: -3 }} key={item.label}>
        <span>{item.icon}</span><div><small>{item.label}</small><strong>{item.value}</strong><p>{item.note}</p></div>
      </motion.article>)}
    </section>

    <motion.section className="admin-runs-explorer glass-surface" initial={reduceMotion ? false : { opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: reduceMotion ? 0 : .24 }}>
      <div className="admin-runs-heading"><div><span>RUN HISTORY</span><h2>Latest executions</h2></div><small>{visible.length} of {runs.length}</small></div>
      <div className="admin-runs-toolbar">
        <label><Search size={15} /><span className="sr-only">Search pipeline runs</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search run ID, status, or error…" /></label>
        <div className="admin-cosmic-segments" aria-label="Filter runs by status">{['all', 'success', 'partial_success', 'failed', 'running'].map((value) => <button className={status === value ? 'active' : ''} type="button" onClick={() => setStatus(value)} key={value}>{value.replaceAll('_', ' ')}</button>)}</div>
      </div>
      <div className="admin-run-cards">
        {visible.length ? visible.map((run, index) => <RunCard run={run} open={expanded === run.id} onToggle={() => setExpanded((current) => current === run.id ? null : run.id)} index={index} key={run.id} />) : <div className="admin-empty"><strong>No matching pipeline runs.</strong><p>Try a different status or search term.</p></div>}
      </div>
    </motion.section>
  </div>;
}
