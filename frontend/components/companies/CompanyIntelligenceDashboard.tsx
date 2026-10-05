'use client';

import Link from 'next/link';
import {
  Activity,
  BriefcaseBusiness,
  CalendarPlus,
  ChevronDown,
  ExternalLink,
  Filter,
  Gauge,
  Search,
  ShieldCheck,
  Sparkles,
  TimerReset,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useMemo, useState, type CSSProperties, type ReactNode } from 'react';
import {
  changeClass,
  type CompanyHiringStats,
  formatGrowth,
  formatNumber,
  formatSigned,
} from '@/lib/intelligence';

type SortKey = 'activity' | 'open' | 'today' | 'growth' | 'aging' | 'name';
type Momentum = 'all' | 'growing' | 'stable' | 'cooling';

const sortLabels: Record<SortKey, string> = {
  activity: 'Last 7 days',
  open: 'Open jobs',
  today: 'Posted today',
  growth: '7d growth',
  aging: '30+ day jobs',
  name: 'Company name',
};

function trendFor(company: CompanyHiringStats) {
  const growth = company.weekly_growth_percent;
  if (growth === null && company.posted_last_7_days > 0 && company.posted_previous_7_days === 0) {
    return { key: 'growing' as const, label: 'New momentum', explanation: 'Activity appeared after a quiet previous period.' };
  }
  if ((growth ?? 0) >= 10 || company.weekly_change >= 3) {
    return { key: 'growing' as const, label: 'Growing', explanation: 'Posting volume is moving above the previous seven-day period.' };
  }
  if ((growth ?? 0) <= -10 || company.weekly_change <= -3) {
    return { key: 'cooling' as const, label: 'Cooling', explanation: 'Posting volume is below the previous seven-day period.' };
  }
  return { key: 'stable' as const, label: 'Stable', explanation: 'Posting activity is broadly consistent with the prior period.' };
}

function SummaryCard({ icon, label, value, note, index }: { icon: ReactNode; label: string; value: number; note: string; index: number }) {
  const reduceMotion = useReducedMotion();
  return <motion.article
    className="company-summary-card"
    initial={reduceMotion ? false : { opacity: 0, y: 18 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: .42, delay: reduceMotion ? 0 : .08 + index * .055, ease: [0.22, 1, 0.36, 1] }}
    whileHover={reduceMotion ? undefined : { y: -3 }}
  >
    <div className="company-summary-icon">{icon}</div>
    <span>{label}</span>
    <strong>{formatNumber(value)}</strong>
    <small>{note}</small>
    <i aria-hidden="true" />
  </motion.article>;
}

function Metric({ label, value, tone }: { label: string; value: ReactNode; tone?: string }) {
  return <div className="company-expanded-metric"><span>{label}</span><strong className={tone}>{value}</strong></div>;
}

function CoverageRing({ value }: { value: number }) {
  const percent = Math.max(0, Math.min(100, Math.round(value * 100)));
  return <div className="coverage-ring" style={{ '--coverage': `${percent * 3.6}deg` } as CSSProperties} aria-label={`${percent}% posting-date coverage`}>
    <span>{percent}%</span>
  </div>;
}

function CompanyRow({ company, open, onToggle, index }: { company: CompanyHiringStats; open: boolean; onToggle: () => void; index: number }) {
  const reduceMotion = useReducedMotion();
  const trend = trendFor(company);
  const staleShare = company.current_open_jobs ? company.active_45_plus_days / company.current_open_jobs : 0;
  const heavyStale = company.active_45_plus_days >= 5 && staleShare >= .25;

  return <motion.article
    layout={!reduceMotion}
    className={`company-activity-row ${open ? 'is-open' : ''}`}
    initial={reduceMotion ? false : { opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: .28, delay: reduceMotion ? 0 : Math.min(index * .018, .22) }}
  >
    <button className="company-row-toggle" type="button" aria-expanded={open} aria-controls={`company-details-${company.id}`} onClick={onToggle}>
      <span className="company-row-identity">
        <span className="company-monogram" aria-hidden="true">{company.name.slice(0, 1).toUpperCase()}</span>
        <span><strong>{company.name}</strong><small>{company.website_domain ?? 'Career site tracked'}</small></span>
      </span>
      <span className="company-stat-cell"><small>Open</small><strong>{formatNumber(company.current_open_jobs)}</strong></span>
      <span className="company-stat-cell"><small>Today</small><strong>{formatNumber(company.posted_today)}</strong></span>
      <span className="company-stat-cell company-stat-secondary"><small>Yesterday</small><strong>{formatNumber(company.posted_yesterday)}</strong></span>
      <span className="company-stat-cell"><small>Last 7d</small><strong>{formatNumber(company.posted_last_7_days)}</strong></span>
      <span className="company-stat-cell company-stat-secondary"><small>Previous</small><strong>{formatNumber(company.posted_previous_7_days)}</strong></span>
      <span className="company-stat-cell"><small>Growth</small><strong className={changeClass(company.weekly_growth_percent)}>{formatGrowth(company.weekly_growth_percent)}</strong></span>
      <span className="company-stat-cell company-stat-secondary"><small>30d+</small><strong>{formatNumber(company.active_30_plus_days)}</strong></span>
      <span className={`trend-pill trend-${trend.key}`}>{trend.key === 'growing' ? <TrendingUp size={12} /> : trend.key === 'cooling' ? <TrendingDown size={12} /> : <Activity size={12} />}{trend.label}</span>
      <ChevronDown className="company-row-chevron" size={17} aria-hidden="true" />
    </button>

    <AnimatePresence initial={false}>
      {open && <motion.div
        id={`company-details-${company.id}`}
        className="company-expanded"
        initial={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
        animate={reduceMotion ? { opacity: 1 } : { height: 'auto', opacity: 1 }}
        exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
        transition={{ duration: .28, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="company-expanded-inner">
          <section className="company-expanded-story">
            <span className={`trend-orbit trend-${trend.key}`} aria-hidden="true"><Activity size={18} /></span>
            <div><small>MOMENTUM SIGNAL</small><h3>{trend.label}</h3><p>{trend.explanation}</p></div>
            {heavyStale && <span className="inventory-alert"><TimerReset size={13} /> Heavy long-running inventory</span>}
          </section>
          <section className="company-expanded-grid" aria-label={`${company.name} hiring metrics`}>
            <Metric label="Open jobs" value={formatNumber(company.current_open_jobs)} />
            <Metric label="Posted today" value={formatNumber(company.posted_today)} />
            <Metric label="Posted yesterday" value={formatNumber(company.posted_yesterday)} />
            <Metric label="Daily change" value={formatSigned(company.daily_change)} tone={changeClass(company.daily_change)} />
            <Metric label="Last 7 days" value={formatNumber(company.posted_last_7_days)} />
            <Metric label="Previous 7 days" value={formatNumber(company.posted_previous_7_days)} />
            <Metric label="Weekly change" value={formatSigned(company.weekly_change)} tone={changeClass(company.weekly_change)} />
            <Metric label="Last 15 days" value={formatNumber(company.posted_last_15_days)} />
            <Metric label="Open 30+ days" value={formatNumber(company.active_30_plus_days)} />
            <Metric label="Open 45+ days" value={formatNumber(company.active_45_plus_days)} />
            <Metric label="Open 90+ days" value={formatNumber(company.active_90_plus_days)} />
            <Metric label="Removed, last 15d" value={formatNumber(company.removed_from_last_15_days)} />
          </section>
          <aside className="company-expanded-quality">
            <CoverageRing value={company.posted_at_coverage} />
            <div><small>DATE COVERAGE</small><strong>{formatNumber(company.jobs_with_posted_at)} dated</strong><span>{formatNumber(company.jobs_without_posted_at)} without posted date</span></div>
            <Link href={`/companies/${company.slug}`}>Open intelligence profile <ExternalLink size={13} /></Link>
          </aside>
        </div>
      </motion.div>}
    </AnimatePresence>
  </motion.article>;
}

export function CompanyIntelligenceDashboard({ companies, total }: { companies: CompanyHiringStats[]; total: number }) {
  const reduceMotion = useReducedMotion();
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortKey>('activity');
  const [publishableOnly, setPublishableOnly] = useState(true);
  const [momentum, setMomentum] = useState<Momentum>('all');
  const [minimumCoverage, setMinimumCoverage] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [methodOpen, setMethodOpen] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);

  const totals = useMemo(() => companies.reduce((result, company) => ({
    open: result.open + company.current_open_jobs,
    today: result.today + company.posted_today,
    week: result.week + company.posted_last_7_days,
    aging: result.aging + company.active_30_plus_days,
    publishable: result.publishable + Number(company.is_publishable),
  }), { open: 0, today: 0, week: 0, aging: 0, publishable: 0 }), [companies]);

  const visible = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return companies.filter((company) => {
      const matchesQuery = !needle || `${company.name} ${company.website_domain ?? ''}`.toLocaleLowerCase().includes(needle);
      const matchesPublishable = !publishableOnly || company.is_publishable;
      const matchesMomentum = momentum === 'all' || trendFor(company).key === momentum;
      return matchesQuery && matchesPublishable && matchesMomentum && company.posted_at_coverage >= minimumCoverage;
    }).sort((a, b) => {
      if (sort === 'name') return a.name.localeCompare(b.name);
      const key: keyof CompanyHiringStats = sort === 'open' ? 'current_open_jobs' : sort === 'today' ? 'posted_today' : sort === 'growth' ? 'weekly_growth_percent' : sort === 'aging' ? 'active_30_plus_days' : 'posted_last_7_days';
      return Number(b[key] ?? Number.NEGATIVE_INFINITY) - Number(a[key] ?? Number.NEGATIVE_INFINITY) || a.name.localeCompare(b.name);
    });
  }, [companies, minimumCoverage, momentum, publishableOnly, query, sort]);

  const cards = [
    { icon: <BriefcaseBusiness size={18} />, label: 'Companies tracked', value: total, note: 'publishable employer profiles' },
    { icon: <Gauge size={18} />, label: 'Open jobs', value: totals.open, note: 'current career-site inventory' },
    { icon: <CalendarPlus size={18} />, label: 'Posted today', value: totals.today, note: 'new dated opportunities' },
    { icon: <TrendingUp size={18} />, label: 'Posted last 7d', value: totals.week, note: 'recent hiring activity' },
    { icon: <TimerReset size={18} />, label: 'Open 30+ days', value: totals.aging, note: 'long-running postings' },
    { icon: <ShieldCheck size={18} />, label: 'Publishable', value: totals.publishable, note: 'quality gate passed' },
  ];

  return <div className="company-intelligence-dashboard">
    <motion.header className="company-hero" initial={reduceMotion ? false : { opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .55, ease: [0.22, 1, 0.36, 1] }}>
      <div className="company-hero-kicker"><Sparkles size={13} /> LIVE EMPLOYER SIGNALS</div>
      <h1>Hiring <span>Intelligence</span></h1>
      <p>Hiring activity calculated from exact posting dates and current career-site inventory—built to reveal momentum without the noise.</p>
      <div className="company-hero-status"><i /> Deterministic statistics · refreshed by the Jobly pipeline</div>
    </motion.header>

    <section className="company-summary-grid" aria-label="Hiring activity summary">
      {cards.map((card, index) => <SummaryCard {...card} index={index} key={card.label} />)}
    </section>

    <motion.section className="company-explorer glass-surface" initial={reduceMotion ? false : { opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .5, delay: reduceMotion ? 0 : .25 }}>
      <div className="company-explorer-heading">
        <div><span>EMPLOYER INDEX</span><h2>Hiring activity by employer</h2></div>
        <strong>{formatNumber(visible.length)} <small>results</small></strong>
      </div>

      <div className="company-toolbar">
        <label className="company-search"><Search size={16} /><span className="sr-only">Search companies</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search company or domain…" /></label>
        <label className="company-sort"><span>Sort</span><select value={sort} onChange={(event) => setSort(event.target.value as SortKey)}>{Object.entries(sortLabels).map(([value, sortLabel]) => <option value={value} key={value}>{sortLabel}</option>)}</select></label>
        <button className={filtersOpen ? 'active' : ''} type="button" aria-expanded={filtersOpen} onClick={() => setFiltersOpen((value) => !value)}><Filter size={15} /> Filters <span>{Number(momentum !== 'all') + Number(minimumCoverage > 0)}</span></button>
      </div>

      <AnimatePresence initial={false}>
        {filtersOpen && <motion.div className="company-filter-panel" initial={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }} animate={reduceMotion ? { opacity: 1 } : { height: 'auto', opacity: 1 }} exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }} transition={{ duration: .25 }}>
          <div className="company-filter-inner">
            <label className="company-switch"><input type="checkbox" checked={publishableOnly} onChange={(event) => setPublishableOnly(event.target.checked)} /><span aria-hidden="true" /><strong>Publishable only</strong></label>
            <fieldset><legend>Momentum</legend><div className="company-chip-group">{(['all', 'growing', 'stable', 'cooling'] as Momentum[]).map((value) => <button type="button" className={momentum === value ? 'active' : ''} onClick={() => setMomentum(value)} key={value}>{value}</button>)}</div></fieldset>
            <label className="company-coverage-filter"><span>Minimum date coverage</span><select value={minimumCoverage} onChange={(event) => setMinimumCoverage(Number(event.target.value))}><option value={0}>Any coverage</option><option value={.5}>50%+</option><option value={.75}>75%+</option><option value={.9}>90%+</option></select></label>
          </div>
        </motion.div>}
      </AnimatePresence>

      <div className="company-list-head" aria-hidden="true"><span>Company</span><span>Open</span><span>Today</span><span>Yesterday</span><span>Last 7d</span><span>Previous</span><span>Growth</span><span>30d+</span><span>Signal</span><span /></div>
      <div className="company-activity-list">
        {visible.length ? visible.map((company, index) => <CompanyRow company={company} index={index} open={expanded === company.id} onToggle={() => setExpanded((current) => current === company.id ? null : company.id)} key={company.id} />) : <div className="company-no-results"><Search size={23} /><strong>No companies match this view</strong><span>Try a broader search or reset the filters.</span></div>}
      </div>
    </motion.section>

    <section className={`company-method ${methodOpen ? 'open' : ''}`}>
      <button type="button" aria-expanded={methodOpen} onClick={() => setMethodOpen((value) => !value)}><span><ShieldCheck size={16} /> Data quality & methodology</span><span>Deterministic, posting-date based metrics</span><ChevronDown size={16} /></button>
      <AnimatePresence initial={false}>{methodOpen && <motion.div initial={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }} animate={reduceMotion ? { opacity: 1 } : { height: 'auto', opacity: 1 }} exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}><p>Jobly calculates these signals from job posting dates and current active inventory. Date coverage shows how much of an employer’s observed job history contains a usable posting date. Growth is left blank when the previous comparison period is zero.</p></motion.div>}</AnimatePresence>
    </section>
  </div>;
}
