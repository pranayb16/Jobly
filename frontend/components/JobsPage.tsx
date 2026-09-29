'use client';

import {
  ArrowRight,
  ArrowUpRight,
  BriefcaseBusiness,
  Building2,
  Check,
  ChevronDown,
  Clock3,
  Database,
  MapPin,
  Search,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import type { Job } from '@/src/types';

async function getJobs(signal?: AbortSignal): Promise<{ jobs: Job[]; count: number }> {
  const response = await fetch('/api/jobs', { signal });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { message?: string } | null;
    throw new Error(payload?.message ?? 'We could not load the jobs right now.');
  }
  return response.json() as Promise<{ jobs: Job[]; count: number }>;
}

const formatLabel = (value: string) => value
  .replace(/([a-z])([A-Z])/g, '$1 $2')
  .replace(/[_-]/g, ' ')
  .replace(/\b\w/g, (letter) => letter.toUpperCase());

function ageInHours(value: string | null) {
  if (!value) return Number.POSITIVE_INFINITY;
  const time = new Date(value).getTime();
  return Number.isNaN(time) ? Number.POSITIVE_INFINITY : Math.max(0, (Date.now() - time) / 3_600_000);
}

function timeAgo(value: string | null) {
  if (!value) return 'Recently';
  const minutes = Math.floor(ageInHours(value) * 60);
  if (!Number.isFinite(minutes)) return 'Recently';
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

function exactPostTime(value: string | null) {
  if (!value) return undefined;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return undefined;
  return date.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' });
}

function salary(job: Job) {
  if (job.salaryMin === null && job.salaryMax === null) return null;
  const currency = job.salaryCurrency || 'USD';
  const formatter = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });
  if (job.salaryMin !== null && job.salaryMax !== null) return `${currency} ${formatter.format(job.salaryMin)}–${formatter.format(job.salaryMax)}`;
  return `${currency} ${formatter.format((job.salaryMin ?? job.salaryMax) as number)}+`;
}

function JobRow({ job, index }: { job: Job; index: number }) {
  const destination = job.applyUrl || job.jobUrl;
  const initial = job.company.charAt(0).toUpperCase() || 'J';
  const pay = salary(job);
  return (
    <article className="aggregator-job" style={{ '--delay': `${Math.min(index * 30, 240)}ms` } as CSSProperties}>
      <div className="aggregator-logo">{initial}</div>
      <div className="aggregator-job-main">
        <div className="aggregator-title-row">
          <div>
            <h3>{job.title}</h3>
            <p><strong>{job.company}</strong>{job.provider && <><span>·</span> via {formatLabel(job.provider)}</>}</p>
          </div>
          <time dateTime={job.createdAt ?? undefined} title={exactPostTime(job.createdAt)}><i /> {timeAgo(job.createdAt)}</time>
        </div>
        <div className="aggregator-meta">
          <span><MapPin size={14} /> {job.location || 'Location flexible'}</span>
          <span><BriefcaseBusiness size={14} /> {formatLabel(job.employmentType || 'Full time')}</span>
          {job.workplaceType && <span>{formatLabel(job.workplaceType)}</span>}
          {pay && <span className="salary-chip">{pay}</span>}
        </div>
        <p className="aggregator-description">{job.description || 'Open the source listing to see the complete role description and requirements.'}</p>
        <div className="aggregator-row-footer">
          <span className="source-label"><Database size={12} /> Aggregated from {job.provider ? formatLabel(job.provider) : 'company careers'}</span>
          {destination ? <a href={destination} target="_blank" rel="noreferrer">View original listing <ArrowUpRight size={15} /></a> : <span>Source link unavailable</span>}
        </div>
      </div>
    </article>
  );
}

function JobSkeleton() { return <div className="aggregator-job aggregator-skeleton"><div /><span /><span /><span /></div>; }

type Filters = { location: string; company: string; source: string; employment: string; workplace: string; hours: number };
type FilterPanelProps = {
  jobs: Job[];
  filters: Filters;
  update: <K extends keyof Filters>(key: K, value: Filters[K]) => void;
  clear: () => void;
};

function countBy(jobs: Job[], key: keyof Job, value: string) { return jobs.filter((job) => job[key] === value).length; }

function FilterPanel({ jobs, filters, update, clear }: FilterPanelProps) {
  const locations = useMemo(() => Array.from(new Set(jobs.map((job) => job.location).filter(Boolean))).sort(), [jobs]);
  const companies = useMemo(() => Array.from(new Set(jobs.map((job) => job.company).filter(Boolean))).sort(), [jobs]);
  const sources = useMemo(() => Array.from(new Set(jobs.map((job) => job.provider).filter(Boolean))).sort(), [jobs]);
  const employment = useMemo(() => Array.from(new Set(jobs.map((job) => job.employmentType).filter(Boolean))).sort(), [jobs]);
  const workplaces = useMemo(() => Array.from(new Set(jobs.map((job) => job.workplaceType).filter(Boolean))).sort(), [jobs]);
  const activeCount = [filters.location, filters.company, filters.source, filters.employment, filters.workplace].filter(Boolean).length + (filters.hours < 48 ? 1 : 0);

  return <div className="aggregator-filters-inner">
    <div className="filters-title"><div><SlidersHorizontal size={17} /><strong>All filters</strong>{activeCount > 0 && <b>{activeCount}</b>}</div>{activeCount > 0 && <button type="button" onClick={clear}>Reset</button>}</div>
    <div className="filter-group">
      <span className="filter-label">Date posted</span>
      <div className="filter-options">
        {[6, 12, 24, 48].map((hours) => <button className={filters.hours === hours ? 'selected' : ''} key={hours} type="button" onClick={() => update('hours', hours)}><span>{filters.hours === hours && <Check size={11} />}</span>{hours === 48 ? 'Any time (48h)' : `Last ${hours} hours`}<em>{jobs.filter((job) => ageInHours(job.createdAt) <= hours).length}</em></button>)}
      </div>
    </div>
    <div className="filter-group">
      <label htmlFor="company-filter">Company</label>
      <div className="select-wrap"><Building2 size={15} /><select id="company-filter" value={filters.company} onChange={(event) => update('company', event.target.value)}><option value="">All companies</option>{companies.map((item) => <option key={item}>{item}</option>)}</select><ChevronDown size={13} /></div>
    </div>
    <div className="filter-group">
      <label htmlFor="location-filter">Location</label>
      <div className="select-wrap"><MapPin size={15} /><select id="location-filter" value={filters.location} onChange={(event) => update('location', event.target.value)}><option value="">All locations</option>{locations.map((item) => <option key={item}>{item}</option>)}</select><ChevronDown size={13} /></div>
    </div>
    {employment.length > 0 && <div className="filter-group"><span className="filter-label">Employment type</span><div className="filter-options"><button className={!filters.employment ? 'selected' : ''} type="button" onClick={() => update('employment', '')}><span>{!filters.employment && <Check size={11} />}</span>All types<em>{jobs.length}</em></button>{employment.map((item) => <button className={filters.employment === item ? 'selected' : ''} key={item} type="button" onClick={() => update('employment', item)}><span>{filters.employment === item && <Check size={11} />}</span>{formatLabel(item)}<em>{countBy(jobs, 'employmentType', item)}</em></button>)}</div></div>}
    {workplaces.length > 0 && <div className="filter-group"><span className="filter-label">Work style</span><div className="filter-options"><button className={!filters.workplace ? 'selected' : ''} type="button" onClick={() => update('workplace', '')}><span>{!filters.workplace && <Check size={11} />}</span>All styles<em>{jobs.length}</em></button>{workplaces.map((item) => <button className={filters.workplace === item ? 'selected' : ''} key={item} type="button" onClick={() => update('workplace', item)}><span>{filters.workplace === item && <Check size={11} />}</span>{formatLabel(item)}<em>{countBy(jobs, 'workplaceType', item)}</em></button>)}</div></div>}
    {sources.length > 0 && <div className="filter-group"><label htmlFor="source-filter">Job source</label><div className="select-wrap"><Database size={15} /><select id="source-filter" value={filters.source} onChange={(event) => update('source', event.target.value)}><option value="">All sources</option>{sources.map((item) => <option key={item} value={item}>{formatLabel(item)} ({countBy(jobs, 'provider', item)})</option>)}</select><ChevronDown size={13} /></div></div>}
  </div>;
}

const defaultFilters: Filters = { location: '', company: '', source: '', employment: '', workplace: '', hours: 48 };

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [sort, setSort] = useState<'newest' | 'oldest' | 'company'>('newest');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    getJobs(controller.signal).then((data) => { setJobs(data.jobs); setStatus('ready'); }).catch((reason: unknown) => {
      if (reason instanceof DOMException && reason.name === 'AbortError') return;
      setError(reason instanceof Error ? reason.message : 'We could not load the jobs right now.'); setStatus('error');
    });
    return () => controller.abort();
  }, []);

  const updateFilter = <K extends keyof Filters>(key: K, value: Filters[K]) => setFilters((current) => ({ ...current, [key]: value }));
  const clearFilters = () => { setQuery(''); setFilters(defaultFilters); };
  const visibleJobs = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const filtered = jobs.filter((job) => (!needle || [job.title, job.company, job.description, job.location].some((field) => field.toLowerCase().includes(needle)))
      && (!filters.location || job.location === filters.location)
      && (!filters.company || job.company === filters.company)
      && (!filters.source || job.provider === filters.source)
      && (!filters.employment || job.employmentType === filters.employment)
      && (!filters.workplace || job.workplaceType === filters.workplace)
      && ageInHours(job.createdAt) <= filters.hours);
    return [...filtered].sort((a, b) => sort === 'company' ? a.company.localeCompare(b.company) : (new Date(a.createdAt ?? 0).getTime() - new Date(b.createdAt ?? 0).getTime()) * (sort === 'newest' ? -1 : 1));
  }, [jobs, query, filters, sort]);

  const companiesCount = new Set(jobs.map((job) => job.company)).size;
  const sourcesCount = new Set(jobs.map((job) => job.provider).filter(Boolean)).size;
  const filterProps = { jobs, filters, update: updateFilter, clear: clearFilters };

  return <section className="aggregator-page">
    <div className="aggregator-search-shell">
      <div className="shell aggregator-search-inner">
        <div><span className="aggregator-kicker"><Database size={13} /> Multi-source job index</span><h1>Search every fresh job<br />from one place.</h1></div>
        <div className="aggregator-stats"><span><strong>{status === 'ready' ? jobs.length : '—'}</strong> live jobs</span><span><strong>{status === 'ready' ? companiesCount : '—'}</strong> companies</span><span><strong>{status === 'ready' ? sourcesCount : '—'}</strong> sources</span></div>
        <div className="aggregator-search"><Search size={20} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search job titles, companies, skills, or keywords" aria-label="Search all jobs" /><button type="button" onClick={() => document.querySelector('.aggregator-results')?.scrollIntoView({ behavior: 'smooth' })}>Search jobs <ArrowRight size={16} /></button></div>
      </div>
    </div>
    <div className="shell aggregator-layout">
      <aside className="aggregator-sidebar"><FilterPanel {...filterProps} /></aside>
      <main className="aggregator-results">
        <div className="aggregator-results-bar">
          <div><span>All aggregated jobs</span><h2>{status === 'ready' ? `${visibleJobs.length} results` : 'Loading jobs…'}</h2></div>
          <div><button className="mobile-filter-button" type="button" onClick={() => setFiltersOpen(true)}><SlidersHorizontal size={15} /> Filters</button><label>Sort by<select value={sort} onChange={(event) => setSort(event.target.value as typeof sort)}><option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="company">Company A–Z</option></select></label></div>
        </div>
        <div className="aggregator-notice"><Clock3 size={15} /><span><strong>Freshness guaranteed.</strong> This index only includes jobs published in the last 48 hours.</span></div>
        {status === 'loading' && <div className="aggregator-list"><JobSkeleton /><JobSkeleton /><JobSkeleton /></div>}
        {status === 'error' && <div className="state-card"><div className="state-icon"><BriefcaseBusiness size={24} /></div><h2>We couldn’t open the job index</h2><p>{error}</p><button className="state-button" type="button" onClick={() => window.location.reload()}>Try again</button></div>}
        {status === 'ready' && visibleJobs.length > 0 && <div className="aggregator-list">{visibleJobs.map((job, index) => <JobRow key={job.id} job={job} index={index} />)}</div>}
        {status === 'ready' && visibleJobs.length === 0 && <div className="state-card"><div className="state-icon"><Search size={24} /></div><h2>No jobs match these filters</h2><p>Broaden your search or reset the filters to return to the full index.</p><button className="state-button" type="button" onClick={clearFilters}>Reset all filters</button></div>}
      </main>
    </div>
    {filtersOpen && <div className="mobile-filter-sheet"><button className="filter-backdrop" type="button" aria-label="Close filters" onClick={() => setFiltersOpen(false)} /><div className="filter-drawer"><button className="drawer-close" type="button" onClick={() => setFiltersOpen(false)}><X size={19} /> Close</button><FilterPanel {...filterProps} /><button className="show-results-button" type="button" onClick={() => setFiltersOpen(false)}>Show {visibleJobs.length} jobs</button></div></div>}
  </section>;
}
