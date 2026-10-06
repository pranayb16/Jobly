import { ArrowUpRight, Bookmark, Check, Clock3, MapPin, X } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import type { Job } from '@/src/types';
import { ago, companyMark, exact, jobLocations, label } from './helpers';

export function JobDetail({ job, saved, applied, onSave, onApplied, onClose }: { job: Job; saved: boolean; applied: boolean; onSave: () => void; onApplied: () => void; onClose: () => void }) {
  const reduceMotion = useReducedMotion();
  const destination = job.applyUrl || job.jobUrl;
  const experience = job.yearsExperienceMin === null && job.yearsExperienceMax === null
    ? 'Not specified'
    : job.yearsExperienceMin === null
      ? `Up to ${job.yearsExperienceMax} years`
      : job.yearsExperienceMax === null
        ? `${job.yearsExperienceMin}+ years`
        : `${job.yearsExperienceMin}–${job.yearsExperienceMax} years`;
  return <motion.div className="detail-backdrop-v2" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: reduceMotion ? 0 : .2 }}><button aria-label="Close job details" onClick={onClose} /><motion.aside className="job-detail-v2" initial={reduceMotion ? false : { x: '100%' }} animate={{ x: 0 }} exit={reduceMotion ? undefined : { x: '100%' }} transition={{ duration: reduceMotion ? 0 : .3, ease: [0.22, 1, 0.36, 1] }}><button className="detail-close-v2" onClick={onClose}><X size={18} /></button><div className="detail-company-v2"><div className="company-avatar-v2 large" style={companyMark(job.company)}>{job.company.slice(0,1)}</div><span>{job.company}</span><h2>{job.title}</h2><p><MapPin size={14} />{jobLocations(job).join(' · ') || 'Location flexible'}<Clock3 size={14} />{job.dateSource === 'observed' ? 'First observed' : 'Posted'} {ago(job.createdAt)}</p></div><div className="detail-actions-v2">{destination ? <a href={destination} target="_blank" rel="noreferrer" onClick={onApplied}>Apply on company site <ArrowUpRight size={16} /></a> : <button disabled>Apply unavailable</button>}<button className={saved ? 'saved' : ''} onClick={onSave}><Bookmark size={16} fill={saved ? 'currentColor' : 'none'} />{saved ? 'Saved' : 'Save'}</button></div>{applied && <div className="applied-v2"><Check size={14} /> Marked as applied</div>}<div className="detail-facts-v2">{[['Job family',label(job.jobFamily || 'Not specified')],['Specialization',label(job.jobSubfamily || 'Not specified')],['Seniority',label(job.seniority || 'Not specified')],['Experience',experience],['Commitment',label(job.employmentType || 'Not specified')],[job.dateSource === 'observed' ? 'First observed' : 'Published',exact(job.createdAt) || 'Not provided']].map(([key,value]) => <div key={key}><small>{key}</small><strong>{value}</strong></div>)}</div>{job.skills.length > 0 && <section className="detail-skills-v2"><h3>Skills</h3><div>{job.skills.map((skill) => <span key={skill}>{skill}</span>)}</div></section>}<section className="detail-copy-v2"><h3>About this role</h3>{job.description ? job.description.split(/\n+/).filter(Boolean).map((paragraph,index) => <p key={index}>{paragraph}</p>) : <p>The source did not provide a description preview.</p>}</section></motion.aside></motion.div>;
}
