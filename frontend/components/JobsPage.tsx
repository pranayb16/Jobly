'use client';

import { Database, Search } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import type { Job } from '@/src/types';
import { ActiveFilters } from './jobs/ActiveFilters';
import { JobCard } from './jobs/JobCard';
import { JobDetail } from './jobs/JobDetail';
import { JobFilterToolbar } from './jobs/JobFilterToolbar';
import { JobSearchBar } from './jobs/JobSearchBar';
import { JobsToolbar } from './jobs/JobsToolbar';
import { MobileFilterDrawer } from './jobs/MobileFilterDrawer';
import { allLocations, arrayValues, hoursOld, jobLocations, label, values } from './jobs/helpers';
import { FILTER_GROUP_ORDER } from './jobs/types';
import type { ActiveFilterGroup, FilterDefinition, FilterKey, Filters, Sort } from './jobs/types';

const defaults = (): Filters => ({ datePosted: [], location: [], workplace: [], role: [], experience: [], employment: [], skill: [], company: [], source: [] });
const filterLabels: Record<FilterKey, string> = { datePosted: 'Date posted', location: 'Location', workplace: 'Workplace', role: 'Role', experience: 'Experience', employment: 'Job type', skill: 'Skills', company: 'Company', source: 'Source' };
const JOBS_POLL_INTERVAL_MS = 60_000;
const storageKey = (kind: string) => `jobly:${kind}`;
const readIds = (kind: string) => { try { return new Set<string>(JSON.parse(localStorage.getItem(storageKey(kind)) || '[]')); } catch { return new Set<string>(); } };
const readInitialFilters = (params: URLSearchParams): Filters => {
  const role = [...params.getAll('role'), ...params.getAll('family').map((value) => `family:${value}`), ...params.getAll('subfamily').map((value) => `subfamily:${value}`)];
  const experience = [...params.getAll('experience').map((value) => value.includes(':') ? value : `years:${value}`), ...params.getAll('seniority').map((value) => `seniority:${value}`)];
  return {
    datePosted: params.getAll('datePosted'),
    location: params.getAll('location'),
    workplace: params.getAll('workplace'),
    role,
    experience,
    employment: params.getAll('employment'),
    skill: params.getAll('skill').map((value) => value.toLocaleLowerCase()),
    company: params.getAll('company'),
    source: params.getAll('source'),
  };
};

const experienceMatch = (job: Job, value: string) => {
  if (value.startsWith('seniority:')) return job.seniority === value.slice(10);
  const years = job.yearsExperienceMin ?? 0;
  return value === 'years:entry' ? years <= 2 : value === 'years:mid' ? years >= 3 && years <= 5 : years >= 6;
};

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filters, setFilters] = useState<Filters>(defaults);
  const [query, setQuery] = useState('');
  const [locationQuery, setLocationQuery] = useState('');
  const [queryDraft, setQueryDraft] = useState('');
  const [locationDraft, setLocationDraft] = useState('');
  const [sort, setSort] = useState<Sort>('newest');
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState('');
  const [selectedId, setSelectedId] = useState('');
  const [detailJob, setDetailJob] = useState<Job | null>(null);
  const [saved, setSaved] = useState<Set<string>>(new Set());
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [applied, setApplied] = useState<Set<string>>(new Set());
  const [savedOnly, setSavedOnly] = useState(false);
  const [mobileFilters, setMobileFilters] = useState(false);
  const [page, setPage] = useState(1);
  const [urlHydrated, setUrlHydrated] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const initialQuery = params.get('q') || '';
    const initialLocation = params.get('near') || '';
    setQuery(initialQuery); setQueryDraft(initialQuery); setLocationQuery(initialLocation); setLocationDraft(initialLocation);
    setSelectedId(params.get('job') || '');
    setSavedOnly(params.get('saved') === 'true');
    setFilters(readInitialFilters(params));
    setUrlHydrated(true);
    setSaved(readIds('saved')); setHidden(readIds('hidden')); setApplied(readIds('applied'));
  }, []);

  useEffect(() => {
    let disposed = false;
    let hasLoaded = false;
    let activeRequest: AbortController | null = null;

    const refreshJobs = async () => {
      if (activeRequest) return;
      const controller = new AbortController();
      activeRequest = controller;

      try {
        const response = await fetch('/api/jobs', { cache: 'no-store', signal: controller.signal });
        if (!response.ok) throw new Error((await response.json()).message || 'Unable to load jobs');
        const data = await response.json();
        if (disposed) return;
        setJobs(data.jobs);
        setError('');
        setStatus('ready');
        hasLoaded = true;
      } catch (reason) {
        if (disposed || (reason instanceof DOMException && reason.name === 'AbortError')) return;
        if (!hasLoaded) {
          setError(reason instanceof Error ? reason.message : 'Unable to load jobs');
          setStatus('error');
        }
      } finally {
        if (activeRequest === controller) activeRequest = null;
      }
    };

    const refreshWhenVisible = () => { if (document.visibilityState === 'visible') void refreshJobs(); };
    void refreshJobs();
    const poll = window.setInterval(() => void refreshJobs(), JOBS_POLL_INTERVAL_MS);
    document.addEventListener('visibilitychange', refreshWhenVisible);

    return () => {
      disposed = true;
      window.clearInterval(poll);
      document.removeEventListener('visibilitychange', refreshWhenVisible);
      activeRequest?.abort();
    };
  }, []);

  useEffect(() => {
    if (!urlHydrated) return;
    const params = new URLSearchParams();
    if (query) params.set('q', query); if (locationQuery) params.set('near', locationQuery); if (selectedId) params.set('job', selectedId); if (savedOnly) params.set('saved', 'true');
    FILTER_GROUP_ORDER.forEach((key) => filters[key].forEach((value) => params.append(key, value)));
    history.replaceState(null, '', `${window.location.pathname}${params.size ? `?${params}` : ''}`);
  }, [query, locationQuery, selectedId, filters, savedOnly, urlHydrated]);

  useEffect(() => {
    if (!selectedId) { setDetailJob(null); return; }
    const controller = new AbortController();
    fetch(`/api/jobs/${encodeURIComponent(selectedId)}`, { signal: controller.signal }).then((response) => response.ok ? response.json() : Promise.reject()).then(setDetailJob).catch(() => setDetailJob(null));
    return () => controller.abort();
  }, [selectedId]);

  const persist = (kind: string, ids: Set<string>) => { const next = new Set(ids); localStorage.setItem(storageKey(kind), JSON.stringify([...next])); return next; };
  const toggleState = (kind: 'saved' | 'hidden' | 'applied', id: string) => { const current = kind === 'saved' ? saved : kind === 'hidden' ? hidden : applied; const next = new Set(current); next.has(id) ? next.delete(id) : next.add(id); const stored = persist(kind, next); if (kind === 'saved') setSaved(stored); else if (kind === 'hidden') setHidden(stored); else setApplied(stored); };

  const definitions = useMemo<FilterDefinition[]>(() => {
    const tally = (test: (job: Job) => boolean) => jobs.filter(test).length;
    const option = (value: string, text: string, test: (job: Job) => boolean) => ({ value, label: text, count: tally(test) });
    const skillLabels = new Map<string, string>();
    arrayValues(jobs, 'skills').forEach((skill) => { const key = skill.toLocaleLowerCase(); if (!skillLabels.has(key)) skillLabels.set(key, skill); });
    return [
      { key: 'datePosted', label: 'Date posted', single: true, options: [option('24', 'Last 24 hours', (job) => hoursOld(job.createdAt) <= 24), option('48', 'Last 48 hours', (job) => hoursOld(job.createdAt) <= 48)] },
      { key: 'location', label: 'Location', searchable: true, options: allLocations(jobs).map((value) => option(value, value, (job) => jobLocations(job).includes(value))) },
      { key: 'workplace', label: 'Workplace', options: values(jobs, 'workplaceType').map((value) => option(value, label(value), (job) => job.workplaceType === value)) },
      { key: 'role', label: 'Role', searchable: true, options: [...values(jobs, 'jobFamily').map((value) => option(`family:${value}`, value, (job) => job.jobFamily === value)), ...values(jobs, 'jobSubfamily').map((value) => option(`subfamily:${value}`, value, (job) => job.jobSubfamily === value))] },
      { key: 'experience', label: 'Experience', options: [...values(jobs, 'seniority').map((value) => option(`seniority:${value}`, label(value), (job) => job.seniority === value)), option('years:entry', '0–2 years', (job) => experienceMatch(job, 'years:entry')), option('years:mid', '3–5 years', (job) => experienceMatch(job, 'years:mid')), option('years:senior', '6+ years', (job) => experienceMatch(job, 'years:senior'))] },
      { key: 'employment', label: 'Job type', options: values(jobs, 'employmentType').map((value) => option(value, label(value), (job) => job.employmentType === value)) },
      { key: 'skill', label: 'Skills', searchable: true, options: [...skillLabels].map(([value, text]) => option(value, text, (job) => job.skills.some((skill) => skill.toLocaleLowerCase() === value))) },
      { key: 'company', label: 'Company', searchable: true, options: values(jobs, 'company').map((value) => option(value, value, (job) => job.company === value)) },
      { key: 'source', label: 'Source', options: values(jobs, 'provider').map((value) => option(value, label(value), (job) => job.provider === value)) },
    ];
  }, [jobs]);

  const optionMaps = useMemo(() => Object.fromEntries(definitions.map((definition) => [definition.key, new Map(definition.options.map((option) => [option.value, option]))])) as Record<FilterKey, Map<string, { value: string; label: string; count?: number }>>, [definitions]);

  const visible = useMemo(() => jobs.filter((job) => {
    const id = String(job.id); const needle = query.toLowerCase().trim(); const place = locationQuery.toLowerCase().trim();
    const matches = (key: FilterKey, test: (value: string) => boolean) => !filters[key].length || filters[key].some(test);
    return !hidden.has(id) && (!savedOnly || saved.has(id))
      && (!needle || [job.title, job.company, job.description, job.jobFamily, job.jobSubfamily, ...job.skills, ...job.relatedRoles].some((value) => value.toLowerCase().includes(needle)))
      && (!place || jobLocations(job).some((value) => value.toLowerCase().includes(place)))
      && matches('datePosted', (value) => hoursOld(job.createdAt) <= Number(value))
      && matches('location', (value) => jobLocations(job).includes(value))
      && matches('workplace', (value) => job.workplaceType === value)
      && matches('role', (value) => value.startsWith('family:') ? job.jobFamily === value.slice(7) : job.jobSubfamily === value.slice(10))
      && matches('experience', (value) => experienceMatch(job, value))
      && matches('employment', (value) => job.employmentType === value)
      && matches('skill', (value) => job.skills.some((skill) => skill.toLocaleLowerCase() === value))
      && matches('company', (value) => job.company === value)
      && matches('source', (value) => job.provider === value);
  }).sort((a, b) => sort === 'company' ? a.company.localeCompare(b.company) : (new Date(a.createdAt || 0).getTime() - new Date(b.createdAt || 0).getTime()) * (sort === 'newest' ? -1 : 1)), [jobs, filters, query, locationQuery, sort, savedOnly, saved, hidden]);

  const toggleFilter = (key: FilterKey, value: string, single = false) => setFilters((current) => ({ ...current, [key]: current[key].includes(value) ? current[key].filter((item) => item !== value) : single ? [value] : [...current[key], value] }));
  const clearCategory = (key: FilterKey) => setFilters((current) => ({ ...current, [key]: [] }));
  const clearFilters = () => { setFilters(defaults()); setSavedOnly(false); };
  const clearEverything = () => { clearFilters(); setQuery(''); setQueryDraft(''); setLocationQuery(''); setLocationDraft(''); };
  const filterCount = FILTER_GROUP_ORDER.reduce((sum, key) => sum + filters[key].length, Number(savedOnly));
  const activeGroups = useMemo<ActiveFilterGroup[]>(() => {
    const groups: ActiveFilterGroup[] = FILTER_GROUP_ORDER.flatMap((key) => filters[key].length ? [{ key, label: filterLabels[key], values: filters[key].map((value) => optionMaps[key].get(value) || { value, label: label(value.replace(/^(family|subfamily|seniority|years):/, '')) }) }] : []);
    if (savedOnly) groups.push({ key: 'saved', label: 'Saved jobs', values: [{ value: 'saved', label: 'Saved only' }] });
    return groups;
  }, [filters, optionMaps, savedOnly]);

  const pageSize = 12; const pageCount = Math.max(1, Math.ceil(visible.length / pageSize)); const pagedJobs = visible.slice((page - 1) * pageSize, page * pageSize);
  const pageWindowSize = 7;
  const pageWindowStart = Math.min(page, Math.max(1, pageCount - pageWindowSize + 1));
  const visiblePages = Array.from({ length: Math.min(pageWindowSize, pageCount) }, (_, index) => pageWindowStart + index);
  useEffect(() => { setPage(1); }, [query, locationQuery, filters, sort, savedOnly]);
  useEffect(() => { if (page > pageCount) setPage(pageCount); }, [page, pageCount]);
  const goToPage = (nextPage: number) => {
    const boundedPage = Math.min(pageCount, Math.max(1, nextPage));
    if (boundedPage === page) return;
    setPage(boundedPage);
    window.requestAnimationFrame(() => {
      window.scrollTo({ top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    });
  };

  const selected = detailJob || jobs.find((job) => String(job.id) === selectedId) || null;
  const companies = new Set(visible.map((job) => job.company)).size;

  return <section className="jobs-page-v2"><JobSearchBar query={queryDraft} location={locationDraft} onQuery={setQueryDraft} onLocation={setLocationDraft} onSearch={() => { setQuery(queryDraft.trim()); setLocationQuery(locationDraft.trim()); }} />
    <main className="shell jobs-results-shell-v3"><JobsToolbar jobs={visible.length} companies={companies} sort={sort} filterCount={filterCount} onSort={setSort} onFilters={() => setMobileFilters(true)} />
      <JobFilterToolbar definitions={definitions} filters={filters} savedOnly={savedOnly} onToggle={toggleFilter} onClearCategory={clearCategory} onSaved={setSavedOnly} />
      <ActiveFilters groups={activeGroups} onRemove={(key, value) => key === 'saved' ? setSavedOnly(false) : toggleFilter(key, value)} onClearAll={clearFilters} />
      {status === 'loading' && <div className="jobs-grid-v2 skeleton-grid-v2">{Array.from({ length: 6 }, (_, index) => <div key={index} />)}</div>}
      {status === 'error' && <div className="jobs-state-v2"><Database size={26} /><h2>The job index is unavailable</h2><p>{error}</p><button onClick={() => window.location.reload()}>Try again</button></div>}
      {status === 'ready' && visible.length === 0 && <div className="jobs-state-v2"><Search size={26} /><h2>No jobs match these filters</h2><p>Try removing a filter or broadening your search.</p><button onClick={clearEverything}>Clear search and filters</button></div>}
      {status === 'ready' && visible.length > 0 && <div className="jobs-grid-v2">{pagedJobs.map((job) => <JobCard key={job.id} job={job} selected={String(job.id) === selectedId} saved={saved.has(String(job.id))} onSelect={() => setSelectedId(String(job.id))} onSave={() => toggleState('saved', String(job.id))} onHide={() => toggleState('hidden', String(job.id))} />)}</div>}
      {status === 'ready' && visible.length > 0 && pageCount > 1 && <nav className="pagination-v2" aria-label="Job results pages">
        <button className="pagination-boundary-v2" disabled={page === 1} onClick={() => goToPage(1)}>First</button>
        <div className="pagination-pages-v2">
          {visiblePages.map((pageNumber) => <button key={pageNumber} className={pageNumber === page ? 'active' : ''} aria-current={pageNumber === page ? 'page' : undefined} aria-label={`Page ${pageNumber}`} onClick={() => goToPage(pageNumber)}>{pageNumber}</button>)}
        </div>
        <button className="pagination-boundary-v2" disabled={page === pageCount} onClick={() => goToPage(pageCount)}>Last</button>
        <span className="sr-only" aria-live="polite">Page {page} of {pageCount}</span>
      </nav>}
    </main>
    {mobileFilters && <MobileFilterDrawer definitions={definitions} filters={filters} savedOnly={savedOnly} count={filterCount} onToggle={toggleFilter} onClearCategory={clearCategory} onSaved={setSavedOnly} onClearAll={clearFilters} onClose={() => setMobileFilters(false)} />}
    {selected && <JobDetail job={selected} saved={saved.has(String(selected.id))} applied={applied.has(String(selected.id))} onSave={() => toggleState('saved', String(selected.id))} onApplied={() => { if (!applied.has(String(selected.id))) toggleState('applied', String(selected.id)); }} onClose={() => setSelectedId('')} />}
  </section>;
}
