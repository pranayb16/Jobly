import Link from 'next/link';
import type { ReactNode } from 'react';
import { CollapsibleSection } from '@/components/admin/CollapsibleSection';
import { CrawlTable } from '@/components/admin/CrawlTable';
import { LogViewer } from '@/components/admin/LogViewer';
import { KeyValueRows, MetricStrip, StatusBadge } from '@/components/admin/AdminPrimitives';
import { AdminDetailFrame, AdminViewTransition } from '@/components/admin/AdminMotion';
import { RunTabs, type RunView } from '@/components/admin/RunTabs';
import {
  formatAdminDate,
  formatDuration,
  getAdmin,
  type LogsPayload,
  type PipelineEvent,
  type PipelineStage,
  type RunDetailPayload,
} from '@/lib/admin';
import { formatNumber } from '@/lib/intelligence';

const allowedViews = new Set<RunView>(['overview', 'crawl', 'enrichment', 'stats', 'issues', 'logs']);
const firstValue = (value: string | string[] | undefined) => Array.isArray(value) ? value[0] : value;
const objectMetric = (value: unknown): Record<string, unknown> => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
const metricNumber = (metrics: Record<string, unknown>, key: string) => {
  const value = metrics[key];
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && Number.isFinite(Number(value))) return Number(value);
  return null;
};
const label = (key: string) => key.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase());
const display = (value: unknown) => typeof value === 'number' ? formatNumber(value) : typeof value === 'string' || typeof value === 'boolean' ? String(value) : '—';
const issueEvent = (event: PipelineEvent) => ['critical', 'error', 'warning'].includes(event.severity);

function PanelHeading({ eyebrow, title, copy, trailing }: { eyebrow: string; title: string; copy?: string; trailing?: ReactNode }) {
  return <div className="admin-panel-heading"><div><span>{eyebrow}</span><h2>{title}</h2>{copy && <p>{copy}</p>}</div>{trailing}</div>;
}

function ModelAndTokenPanels({ enrichment }: { enrichment: PipelineStage | undefined }) {
  const metrics = objectMetric(enrichment?.metrics);
  const models = objectMetric(metrics.models);
  const nestedTokens = objectMetric(metrics.tokens);
  const tokens = [
    ['Input', metricNumber(metrics, 'input_tokens') ?? metricNumber(nestedTokens, 'input')],
    ['Output', metricNumber(metrics, 'output_tokens') ?? metricNumber(nestedTokens, 'output')],
    ['Reasoning', metricNumber(metrics, 'thought_tokens') ?? metricNumber(metrics, 'reasoning_tokens') ?? metricNumber(nestedTokens, 'thought') ?? metricNumber(nestedTokens, 'reasoning')],
    ['Cached', metricNumber(metrics, 'cached_tokens') ?? metricNumber(nestedTokens, 'cached')],
    ['Total', metricNumber(metrics, 'total_tokens') ?? metricNumber(nestedTokens, 'total')],
  ];

  return <div className="admin-two-column">
    <section className="admin-subpanel"><h3>AI models</h3>{Object.keys(models).length ? <KeyValueRows items={Object.entries(models).map(([model, count]) => ({ label: model, value: display(count) }))} /> : <p className="admin-muted">No model usage recorded.</p>}</section>
    <section className="admin-subpanel"><h3>Token usage</h3><KeyValueRows items={tokens.map(([tokenLabel, count]) => ({ label: String(tokenLabel), value: count === null ? '—' : formatNumber(Number(count)) }))} /></section>
  </div>;
}

function EventList({ events }: { events: PipelineEvent[] }) {
  if (!events.length) return <div className="admin-ok">No structured issues recorded for this run.</div>;
  return <div className="admin-event-list">{events.map((event) => {
    const details = objectMetric(event.details);
    return <details className={`admin-event severity-${event.severity}`} key={event.id}>
      <summary><StatusBadge status={event.severity} /><span><strong>{event.stage ?? 'pipeline'} · {label(event.event_type)}</strong><small>{event.message}</small></span><time>{formatAdminDate(event.created_at)}</time><i aria-hidden="true">›</i></summary>
      <div className="admin-event-body">
        <p>{event.message}</p>
        <KeyValueRows items={[
          { label: 'Provider', value: event.provider ?? '—' },
          { label: 'Model', value: event.model ?? '—' },
          { label: 'Job ID', value: event.job_id ?? '—' },
          { label: 'Queue ID', value: event.queue_id ?? '—' },
          { label: 'Source ID', value: event.source_id ?? '—' },
          { label: 'Timestamp', value: formatAdminDate(event.created_at) },
          ...Object.entries(details).filter(([, value]) => typeof value !== 'object').map(([key, value]) => ({ label: label(key), value: display(value) })),
        ]} />
        {Object.keys(details).length > 0 && <details className="admin-raw-json"><summary>View raw JSON</summary><pre>{JSON.stringify(details, null, 2)}</pre></details>}
      </div>
    </details>;
  })}</div>;
}

export default async function AdminRunPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { id } = await params;
  const query = await searchParams;
  const requestedView = firstValue(query.view) as RunView | undefined;
  const view: RunView = requestedView && allowedViews.has(requestedView) ? requestedView : 'overview';
  const requestedOffset = Number(firstValue(query.log_offset) ?? 0);
  const logOffset = Number.isInteger(requestedOffset) && requestedOffset >= 0 ? requestedOffset : 0;
  const logLimit = 200;

  const detail = await getAdmin<RunDetailPayload>(`/api/admin/runs/${encodeURIComponent(id)}`);
  const logs = view === 'logs' ? await getAdmin<LogsPayload>(`/api/admin/runs/${encodeURIComponent(id)}/logs?limit=${logLimit}&offset=${logOffset}`) : null;

  if (!detail) return <div className="admin-cosmic-shell"><div className="intelligence-ambient" aria-hidden="true"><i /><i /><i /></div><div className="shell admin-page"><div className="admin-empty"><strong>Pipeline run unavailable.</strong><p>The run does not exist, or the operations API could not be reached.</p></div></div></div>;

  const run = detail.run;
  const crawl = detail.stages.find((stage) => stage.stage === 'crawl');
  const enrichment = detail.stages.find((stage) => stage.stage === 'enrichment');
  const stats = detail.stages.find((stage) => stage.stage === 'hiring_stats');
  const enrichmentMetrics = objectMetric(enrichment?.metrics);
  const statsMetrics = objectMetric(stats?.metrics);
  const modelCounts = objectMetric(enrichmentMetrics.models);
  const aiCalls = metricNumber(enrichmentMetrics, 'ai_calls') ?? 0;
  const skippedNonUs = metricNumber(enrichmentMetrics, 'skipped_non_us') ?? 0;
  const warningCrawls = detail.crawl_runs.filter((item) => item.warning || item.deactivation_skipped).length;
  const failedOperations = (run.sources_failed ?? 0) + (run.enrichments_failed ?? 0);
  const eventCounts = Object.fromEntries(['critical', 'error', 'warning', 'info'].map((severity) => [severity, detail.events.filter((event) => event.severity === severity).length]));
  const enrichmentIssues = detail.events.filter((event) => event.stage === 'enrichment' && issueEvent(event));
  const meaningfulIssues = detail.events.filter(issueEvent);
  const enrichmentSummary = [
    `${formatNumber(aiCalls)} AI calls`,
    ...Object.entries(modelCounts).slice(0, 2).map(([model, count]) => `${display(count)} ${model}`),
    `${formatNumber(run.enrichments_failed)} failed`,
  ].join(' · ');
  const previousOffset = Math.max(0, logOffset - logLimit);
  const nextOffset = logOffset + logLimit;

  return <div className="admin-cosmic-shell"><div className="intelligence-ambient" aria-hidden="true"><i /><i /><i /></div><AdminDetailFrame>
    <Link className="admin-back" href="/admin/runs">← Pipeline runs</Link>
    <header className="admin-run-header">
      <div><span>PIPELINE EXECUTION</span><h1>Pipeline Run #{run.id}</h1><p>{formatAdminDate(run.started_at)}{run.finished_at ? ` · finished ${formatAdminDate(run.finished_at)}` : ' · still running'}</p></div>
      <div><StatusBadge status={run.status} /><strong>{formatDuration(run.duration_seconds)}</strong><small>duration</small></div>
    </header>
    <MetricStrip items={[
      { label: 'Sources', value: formatNumber(run.sources_attempted) },
      { label: 'Jobs seen', value: formatNumber(run.jobs_seen) },
      { label: 'AI completed', value: formatNumber(run.enrichments_completed) },
      { label: 'Errors', value: formatNumber(failedOperations), tone: failedOperations ? 'error' : undefined },
      { label: 'Stats refreshed', value: formatNumber(run.company_stats_refreshed) },
    ]} />
    {run.error && <div className="admin-error-banner"><strong>Run error</strong><p>{run.error}</p></div>}
    <RunTabs runId={run.id} active={view} />

    <AdminViewTransition view={view}>
      {view === 'overview' && <section>
        <PanelHeading eyebrow="AT A GLANCE" title="Run overview" copy="Summary first, with stage details available on demand." />
        <div className="admin-accordion-stack">
          <CollapsibleSection title="Crawl" summary={`${formatNumber(run.sources_attempted)} attempted · ${formatNumber(run.sources_successful)} successful · ${formatNumber(run.sources_failed)} failed`} defaultOpen status={<StatusBadge status={crawl?.status ?? 'unknown'} />}>
            <div className="admin-detail-groups"><section><h3>Sources</h3><KeyValueRows items={[{ label: 'Attempted', value: formatNumber(run.sources_attempted) }, { label: 'Successful', value: formatNumber(run.sources_successful) }, { label: 'Failed', value: formatNumber(run.sources_failed) }, { label: 'Warnings', value: formatNumber(warningCrawls) }]} /></section><section><h3>Jobs</h3><KeyValueRows items={[{ label: 'Seen', value: formatNumber(run.jobs_seen) }, { label: 'New', value: formatNumber(run.jobs_new) }, { label: 'Changed', value: formatNumber(run.jobs_changed) }, { label: 'Removed', value: formatNumber(run.jobs_removed) }]} /></section></div>
          </CollapsibleSection>
          <CollapsibleSection title="Enrichment" summary={enrichmentSummary} status={<StatusBadge status={enrichment?.status ?? 'unknown'} />}>
            <MetricStrip items={[{ label: 'Processed', value: formatNumber(run.enrichments_processed) }, { label: 'AI calls', value: formatNumber(aiCalls) }, { label: 'Completed', value: formatNumber(run.enrichments_completed) }, { label: 'Failed', value: formatNumber(run.enrichments_failed) }, { label: 'Skipped non-US', value: formatNumber(skippedNonUs) }, { label: 'Backlog', value: formatNumber(run.enrichment_backlog) }]} />
            <ModelAndTokenPanels enrichment={enrichment} />
          </CollapsibleSection>
          <CollapsibleSection title="Statistics" summary={`${formatNumber(run.company_stats_refreshed)} refreshed · ${formatNumber(run.company_stats_publishable)} publishable`} status={<StatusBadge status={stats?.status ?? 'unknown'} />}>
            <MetricStrip items={[{ label: 'Refreshed', value: formatNumber(run.company_stats_refreshed) }, { label: 'Publishable', value: formatNumber(run.company_stats_publishable) }, { label: 'Unpublishable', value: formatNumber(run.company_stats_unpublishable) }]} />
          </CollapsibleSection>
          <CollapsibleSection title="Issues" summary={`${formatNumber(eventCounts.warning)} warnings · ${formatNumber(eventCounts.error)} errors · ${formatNumber(eventCounts.critical)} critical`} status={<StatusBadge status={meaningfulIssues.length ? 'warning' : 'success'} />}>
            <EventList events={meaningfulIssues.slice(0, 5)} />
          </CollapsibleSection>
        </div>
      </section>}

      {view === 'crawl' && <section>
        <PanelHeading eyebrow="CRAWL" title="Source crawl details" copy="Filter and expand individual sources without growing the page." trailing={<StatusBadge status={crawl?.status ?? 'unknown'} />} />
        <MetricStrip items={[{ label: 'Attempted', value: formatNumber(run.sources_attempted) }, { label: 'Successful', value: formatNumber(run.sources_successful) }, { label: 'Failed', value: formatNumber(run.sources_failed), tone: run.sources_failed ? 'error' : undefined }, { label: 'Warnings', value: formatNumber(warningCrawls), tone: warningCrawls ? 'warning' : undefined }, { label: 'Jobs seen', value: formatNumber(run.jobs_seen) }, { label: 'New', value: formatNumber(run.jobs_new) }, { label: 'Changed', value: formatNumber(run.jobs_changed) }, { label: 'Removed', value: formatNumber(run.jobs_removed) }]} />
        {detail.crawl_runs.length ? <CrawlTable crawls={detail.crawl_runs} /> : <div className="admin-empty">No source crawls recorded for this run.</div>}
      </section>}

      {view === 'enrichment' && <section>
        <PanelHeading eyebrow="ENRICHMENT" title="AI processing" copy="Completion, model use, and token consumption for this run." trailing={<StatusBadge status={enrichment?.status ?? 'unknown'} />} />
        <MetricStrip items={[{ label: 'Processed', value: formatNumber(run.enrichments_processed) }, { label: 'AI calls', value: formatNumber(aiCalls) }, { label: 'Completed', value: formatNumber(run.enrichments_completed) }, { label: 'Failed', value: formatNumber(run.enrichments_failed), tone: run.enrichments_failed ? 'error' : undefined }, { label: 'Skipped non-US', value: formatNumber(skippedNonUs) }, { label: 'Backlog', value: formatNumber(run.enrichment_backlog) }]} />
        <ModelAndTokenPanels enrichment={enrichment} />
        <section className="admin-panel admin-recent-issues"><PanelHeading eyebrow="STRUCTURED EVENTS" title="Recent enrichment issues" trailing={<small>{enrichmentIssues.length}</small>} />{enrichmentIssues.length ? <EventList events={enrichmentIssues.slice(-8).reverse()} /> : <div className="admin-ok">No enrichment issues recorded.</div>}</section>
      </section>}

      {view === 'stats' && <section>
        <PanelHeading eyebrow="STATISTICS" title="Company hiring statistics" copy="Refresh outcome and publication totals." trailing={<StatusBadge status={stats?.status ?? 'unknown'} />} />
        <MetricStrip items={[{ label: 'Companies refreshed', value: formatNumber(run.company_stats_refreshed) }, { label: 'Publishable', value: formatNumber(run.company_stats_publishable) }, { label: 'Unpublishable', value: formatNumber(run.company_stats_unpublishable) }]} />
        <section className="admin-panel admin-stage-metadata"><h3>Stage execution</h3><KeyValueRows items={[{ label: 'Status', value: <StatusBadge status={stats?.status ?? 'unknown'} /> }, { label: 'Started', value: formatAdminDate(stats?.started_at ?? null) }, { label: 'Finished', value: formatAdminDate(stats?.finished_at ?? null) }, { label: 'Duration', value: formatDuration(stats?.duration_seconds ?? null) }, ...Object.entries(statsMetrics).map(([key, value]) => ({ label: label(key), value: display(value) }))]} />{stats?.error && <div className="admin-error-banner"><strong>Stage error</strong><p>{stats.error}</p></div>}</section>
      </section>}

      {view === 'issues' && <section>
        <PanelHeading eyebrow="STRUCTURED EVENTS" title="Issues and events" copy="Expand an event to inspect identifiers and structured details." />
        <MetricStrip items={[{ label: 'Critical', value: formatNumber(eventCounts.critical), tone: eventCounts.critical ? 'error' : undefined }, { label: 'Errors', value: formatNumber(eventCounts.error), tone: eventCounts.error ? 'error' : undefined }, { label: 'Warnings', value: formatNumber(eventCounts.warning), tone: eventCounts.warning ? 'warning' : undefined }, { label: 'Info', value: formatNumber(eventCounts.info) }]} />
        <EventList events={detail.events} />
      </section>}

      {view === 'logs' && <section>
        <PanelHeading eyebrow="RAW OUTPUT" title="Pipeline logs" copy="Chronological log output; exceptions stay collapsed until requested." trailing={<small>{formatNumber(logs?.count)} total</small>} />
        {!logs ? <div className="admin-empty">Raw logs are unavailable.</div> : logs.logs.length ? <LogViewer logs={logs.logs} /> : <div className="admin-empty">No logs were recorded for this run.</div>}
        {logs && logs.count > logLimit && <nav className="admin-pagination" aria-label="Log pages">{logOffset > 0 ? <Link href={`/admin/runs/${run.id}?view=logs&log_offset=${previousOffset}`}>Newer logs</Link> : <span />}{nextOffset < logs.count ? <Link href={`/admin/runs/${run.id}?view=logs&log_offset=${nextOffset}`}>Older logs</Link> : <span />}</nav>}
      </section>}
    </AdminViewTransition>
  </AdminDetailFrame></div>;
}
