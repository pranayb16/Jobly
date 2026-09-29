import {
  ArrowRight,
  ArrowUpRight,
  Clock3,
  MapPin,
  Search,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import Link from 'next/link';

const previewJobs = [
  { company: 'Arc Studio', role: 'Product Designer', location: 'New York · Hybrid', age: '2h ago', tone: 'mint', initial: 'A' },
  { company: 'Northstar', role: 'Frontend Engineer', location: 'Remote · US', age: '5h ago', tone: 'lilac', initial: 'N' },
  { company: 'Monument', role: 'Growth Marketing Lead', location: 'Austin · On-site', age: '11h ago', tone: 'peach', initial: 'M' },
];

const principles = [
  { number: '01', title: 'Fresh by default', copy: 'Every role is automatically limited to the last 48 hours.' },
  { number: '02', title: 'Details up front', copy: 'See the company, location, work style, and real description before you click.' },
  { number: '03', title: 'Built for momentum', copy: 'Search less, decide faster, and apply while the opportunity is still new.' },
];

export default function HomePage() {
  return (
    <>
      <section className="home-hero">
        <div className="shell home-hero-grid">
          <div className="home-hero-copy">
            <div className="hero-badge"><span /> Career sites + ATS feeds · one search</div>
            <h1>Every job.<br /><em>One fresh feed.</em></h1>
            <p>
              Jobly aggregates jobs from company career sites and hiring platforms into one searchable index—then removes anything older than 48 hours.
            </p>
            <div className="hero-actions">
              <Link className="hero-primary" href="/jobs">Search the job index <ArrowRight size={18} /></Link>
              <span><Clock3 size={16} /> Nothing older than 48 hours</span>
            </div>
          </div>

          <div className="hero-board" aria-label="Preview of recent job listings">
            <div className="hero-board-toolbar">
              <div className="mini-brand"><span>J</span> Unified job feed</div>
              <span className="live-counter"><i /> Multi-source</span>
            </div>
            <div className="hero-search-preview"><Search size={17} /><span>Search title, skill, or company</span><kbd>⌘ K</kbd></div>
            <div className="preview-list">
              {previewJobs.map((job) => (
                <article className={`mini-job ${job.tone}`} key={job.company}>
                  <div className="mini-job-logo">{job.initial}</div>
                  <div className="mini-job-copy">
                    <span>{job.company}</span>
                    <strong>{job.role}</strong>
                    <small><MapPin size={12} /> {job.location}</small>
                  </div>
                  <div className="mini-job-aside"><time>{job.age}</time><ArrowUpRight size={17} /></div>
                </article>
              ))}
            </div>
            <div className="board-caption"><Sparkles size={15} /> Aggregated, normalized, and sorted by freshness.</div>
          </div>
        </div>
        <div className="hero-marquee" aria-hidden="true">
          <span>PRODUCT</span><i /> <span>ENGINEERING</span><i /> <span>DESIGN</span><i /> <span>MARKETING</span><i /> <span>OPERATIONS</span>
        </div>
      </section>

      <section className="freshness-section">
        <div className="shell freshness-grid">
          <div className="freshness-intro">
            <span className="section-label">Why Jobly</span>
            <h2>The whole market,<br />in one clean index.</h2>
            <p>Instead of checking dozens of company sites and ATS platforms, search their newest roles together with consistent filters and source links.</p>
          </div>
          <div className="principles-list">
            {principles.map((principle) => (
              <article key={principle.number}>
                <span>{principle.number}</span>
                <div><h3>{principle.title}</h3><p>{principle.copy}</p></div>
                <ArrowUpRight size={18} />
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="home-cta-section">
        <div className="shell home-cta">
          <div className="cta-stamp"><ShieldCheck size={24} /><span>48H<small>ONLY</small></span></div>
          <div><span className="section-label section-label-light">Ready when you are</span><h2>Your next application<br />could be the early one.</h2></div>
          <Link className="cta-button" href="/jobs">See all fresh roles <ArrowRight size={18} /></Link>
        </div>
      </section>
    </>
  );
}
