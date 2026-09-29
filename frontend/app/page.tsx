import { ArrowRight, BriefcaseBusiness, Check, Clock3, Database, MapPin, Search, SlidersHorizontal, Sparkles } from 'lucide-react';
import Link from 'next/link';

const jobs = [
  { company: 'Linear', role: 'Product Engineer', place: 'Remote · Americas', age: '38m', color: '#5b5bd6' },
  { company: 'Vercel', role: 'Staff Product Designer', place: 'New York · Hybrid', age: '2h', color: '#171717' },
  { company: 'Ramp', role: 'Growth Marketing Lead', place: 'San Francisco', age: '5h', color: '#237a57' },
];

export default function HomePage() {
  return <>
    <section className="landing-hero">
      <div className="landing-glow" />
      <div className="shell landing-grid">
        <div className="landing-copy">
          <div className="landing-label"><span /> Updated continuously · nothing older than 48 hours</div>
          <h1>Stop checking<br /><em>every careers page.</em></h1>
          <p>Jobly pulls new openings from company career sites and ATS platforms into one focused, searchable job index.</p>
          <div className="landing-search">
            <Search size={19} />
            <span>Job title, skill, company, or location</span>
            <Link href="/jobs">Search jobs <ArrowRight size={16} /></Link>
          </div>
          <div className="landing-proof"><span><Check size={13} /> Direct company links</span><span><Check size={13} /> Multi-source search</span><span><Check size={13} /> Freshness verified</span></div>
        </div>

        <div className="index-preview">
          <div className="preview-top"><div><Database size={14} /><strong>Live job index</strong></div><span><i /> 1,248 new today</span></div>
          <div className="preview-query"><Search size={15} /> Product design <kbd>⌘ K</kbd></div>
          <div className="preview-layout">
            <aside><strong><SlidersHorizontal size={13} /> Filters</strong><span className="active">Past 24 hours <b>412</b></span><span>Remote <b>286</b></span><span>Full-time <b>942</b></span><span>Entry level <b>174</b></span></aside>
            <div className="preview-results">
              <small>412 MATCHING ROLES</small>
              {jobs.map((job) => <article key={job.company}><div style={{ background: job.color }}>{job.company[0]}</div><section><span>{job.company}<time><i />{job.age} ago</time></span><h3>{job.role}</h3><p><MapPin size={11} />{job.place}</p></section></article>)}
            </div>
          </div>
          <div className="preview-status"><Sparkles size={13} /> Normalized across Greenhouse, Lever, Ashby, and company sites</div>
        </div>
      </div>
    </section>

    <section className="source-strip"><div className="shell"><span>ONE SEARCH ACROSS</span><strong>Greenhouse</strong><strong>Lever</strong><strong>Ashby</strong><strong>Company sites</strong><strong>+ more sources</strong></div></section>

    <section className="product-story" id="how-it-works"><div className="shell"><div className="story-heading"><span>THE AGGREGATOR DIFFERENCE</span><h2>More signal.<br />Less tab chaos.</h2><p>A job search should feel like a workspace—not a pile of career pages.</p></div><div className="story-grid">
      <article><Clock3 size={20} /><b>01</b><h3>Actually fresh</h3><p>Every result is posted within 48 hours, so you apply while teams are actively looking.</p></article>
      <article><SlidersHorizontal size={20} /><b>02</b><h3>Filter the whole market</h3><p>Refine roles across companies and sources without relearning a different career site each time.</p></article>
      <article><BriefcaseBusiness size={20} /><b>03</b><h3>Apply at the source</h3><p>Review normalized details here, then continue directly to the original company listing.</p></article>
    </div></div></section>

    <section className="landing-cta"><div className="shell"><div><span>YOUR NEXT ROLE MAY HAVE POSTED AN HOUR AGO</span><h2>See what just opened.</h2></div><Link href="/jobs">Open the live index <ArrowRight size={18} /></Link></div></section>
  </>;
}
