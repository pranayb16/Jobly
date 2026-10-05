import { DetailHeader, EmptyState, Metric } from '@/components/IntelligenceUI';
import {
  changeClass,
  CompanyHiringStats,
  formatDateTime,
  formatGrowth,
  formatNumber,
  formatSigned,
  getIntelligence,
} from '@/lib/intelligence';

export default async function CompanyPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const company = await getIntelligence<CompanyHiringStats>(`/api/companies/${encodeURIComponent(slug)}`);
  if (!company) return <div className="company-intelligence-shell"><div className="intelligence-ambient" aria-hidden="true"><i /><i /><i /></div><div className="shell intel-page"><EmptyState message="This company is unavailable or does not yet have publishable hiring statistics." /></div></div>;

  return <div className="company-intelligence-shell"><div className="intelligence-ambient" aria-hidden="true"><i /><i /><i /></div><div className="shell intel-page company-detail-page">
    <DetailHeader label="COMPANY HIRING INTELLIGENCE" title={company.name} value={formatNumber(company.current_open_jobs)} href={company.website_domain ? `https://${company.website_domain}` : undefined} />

    <section className="company-detail-section">
      <div className="section-title"><div><span>RECENT ACTIVITY</span><h2>Posting momentum</h2></div></div>
      <div className="metric-grid company-primary-metrics">
        <Metric label="Posted today" value={company.posted_today} />
        <Metric label="Posted yesterday" value={company.posted_yesterday} />
        <Metric label="Daily change" value={formatSigned(company.daily_change)} tone={changeClass(company.daily_change)} />
        <Metric label="Last 7 days" value={company.posted_last_7_days} />
        <Metric label="Previous 7 days" value={company.posted_previous_7_days} />
        <Metric label="Weekly change" value={formatSigned(company.weekly_change)} tone={changeClass(company.weekly_change)} />
        <Metric label="Weekly growth" value={formatGrowth(company.weekly_growth_percent)} tone={changeClass(company.weekly_growth_percent)} />
        <Metric label="Last 15 days" value={company.posted_last_15_days} />
      </div>
    </section>

    <section className="company-detail-section">
      <div className="section-title"><div><span>INVENTORY</span><h2>Posting lifecycle</h2></div></div>
      <div className="metric-grid company-secondary-metrics">
        <Metric label="Active from last 15 days" value={company.active_from_last_15_days} />
        <Metric label="Removed from last 15 days" value={company.removed_from_last_15_days} />
        <Metric label="Open 30+ days" value={company.active_30_plus_days} note="long-running postings" />
        <Metric label="Open 45+ days" value={company.active_45_plus_days} note="long-running postings" />
        <Metric label="Open 90+ days" value={company.active_90_plus_days} note="long-running postings" />
      </div>
    </section>

    <div className="company-detail-split">
      <section className="company-info-card">
        <span>DATA QUALITY</span><h2>Posting-date coverage</h2>
        <strong>{Math.round(company.posted_at_coverage * 100)}%</strong>
        <dl><div><dt>Jobs with posted_at</dt><dd>{formatNumber(company.jobs_with_posted_at)}</dd></div><div><dt>Jobs without posted_at</dt><dd>{formatNumber(company.jobs_without_posted_at)}</dd></div><div><dt>Total jobs seen</dt><dd>{formatNumber(company.total_jobs_seen)}</dd></div></dl>
      </section>
      <section className="company-info-card">
        <span>TIMELINE</span><h2>Statistics boundaries</h2>
        <dl><div><dt>Latest posted date</dt><dd>{formatDateTime(company.latest_posted_at)}</dd></div><div><dt>Oldest posting date</dt><dd>{formatDateTime(company.oldest_posted_at)}</dd></div><div><dt>Oldest active posting date</dt><dd>{formatDateTime(company.oldest_active_posted_at)}</dd></div><div><dt>Statistics calculated</dt><dd>{formatDateTime(company.calculated_at)}</dd></div></dl>
      </section>
    </div>
  </div></div>;
}
