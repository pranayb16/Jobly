import { Bookmark, EyeOff, ExternalLink } from 'lucide-react';
import type { Job } from '@/src/types';
import { ago, companyMark, exact, label } from './helpers';

function cardTone(job: Job) {
  const seed = `${job.company}:${job.id}`;
  const index = [...seed].reduce((sum, character) => sum + character.charCodeAt(0), 0) % 5;
  return `tone-${index + 1}`;
}

function usableApplyUrl(value: string) {
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) ? url.toString() : '';
  } catch {
    return '';
  }
}

function formatSalary(job: Job) {
  if (job.salaryMin === null && job.salaryMax === null) return '';
  const symbol = ({ USD: '$', EUR: '€', GBP: '£', CAD: 'CA$', AUD: 'A$' } as Record<string, string>)[job.salaryCurrency?.toUpperCase()] || `${job.salaryCurrency || ''} `;
  const amount = (value: number) => `${symbol}${new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: value >= 1000 ? 0 : 1 }).format(value)}`;
  if (job.salaryMin !== null && job.salaryMax !== null) return `${amount(job.salaryMin)}–${amount(job.salaryMax)}`;
  if (job.salaryMin !== null) return `From ${amount(job.salaryMin)}`;
  return `Up to ${amount(job.salaryMax as number)}`;
}

export function JobCard({ job, selected, saved, onSelect, onSave, onHide }: { job: Job; selected: boolean; saved: boolean; onSelect: () => void; onSave: () => void; onHide: () => void }) {
  const applyUrl = usableApplyUrl(job.applyUrl);
  const salary = formatSalary(job);
  const metadata = [job.workplaceType, job.employmentType, job.seniority].filter(Boolean).slice(0, 3);
  const visibleSkills = job.skills.slice(0, 2);
  const remainingSkills = Math.max(0, job.skills.length - visibleSkills.length);
  const jobLabel = `${job.title} at ${job.company}`;

  return <article className={`${selected ? 'job-card-v2 selected' : 'job-card-v2'} ${cardTone(job)}`} onClick={onSelect} role="button" aria-label={`View details for ${jobLabel}`} tabIndex={0} onKeyDown={(event) => { if (event.target === event.currentTarget && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); onSelect(); } }}>
    <div className="job-card-main-v3">
      <div className="job-card-top-v3"><time title={exact(job.createdAt)}><i />{ago(job.createdAt)}</time><div className="job-card-utilities-v3"><button type="button" title={saved ? 'Remove from saved jobs' : 'Save job'} aria-label={`${saved ? 'Unsave' : 'Save'} ${jobLabel}`} className={saved ? 'saved' : ''} onClick={(event) => { event.stopPropagation(); onSave(); }}><Bookmark size={15} fill={saved ? 'currentColor' : 'none'} /></button><button type="button" title="Hide job" aria-label={`Hide ${jobLabel}`} onClick={(event) => { event.stopPropagation(); onHide(); }}><EyeOff size={15} /></button></div></div>
      <strong className="job-card-company-v4">{job.company}</strong>
      <div className="job-card-title-row-v4"><h2>{job.title}</h2><div className="company-avatar-v2 compact" style={companyMark(job.company)} aria-hidden="true">{job.company.slice(0, 1).toUpperCase()}</div></div>
      {metadata.length > 0 && <div className="job-meta-v3">{metadata.map((value) => <span key={value}>{label(value)}</span>)}</div>}
      {visibleSkills.length > 0 && <div className="job-skills-v3">{visibleSkills.map((skill) => <span key={skill}>{skill}</span>)}{remainingSkills > 0 && <span>+{remainingSkills}</span>}</div>}
    </div>
    <footer className="job-card-footer-v3">
      <div className="job-card-facts-v3">{salary && <strong>{salary}</strong>}<span>{job.location || 'Location flexible'} <small>· via {label(job.provider || 'Company')}</small></span></div>
      <div className="job-card-cta-v4">{applyUrl ? <a href={applyUrl} target="_blank" rel="noopener noreferrer" aria-label={`Apply to ${jobLabel}`} onClick={(event) => event.stopPropagation()}>Apply <ExternalLink size={13} /></a> : <button type="button" aria-label={`View details for ${jobLabel}`} onClick={(event) => { event.stopPropagation(); onSelect(); }}>View details</button>}</div>
    </footer>
  </article>;
}
