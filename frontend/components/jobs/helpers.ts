import type { Job } from '@/src/types';

export const label = (value: string) => value.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/[_-]/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
export const hoursOld = (value: string | null) => value ? Math.max(0, (Date.now() - new Date(value).getTime()) / 3_600_000) : Infinity;
export const ago = (value: string | null) => { const minutes = Math.floor(hoursOld(value) * 60); return !Number.isFinite(minutes) ? 'Recently' : minutes < 1 ? 'Just now' : minutes < 60 ? `${minutes}m ago` : `${Math.floor(minutes / 60)}h ago`; };
export const exact = (value: string | null) => value ? new Date(value).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) : '';
export const values = (jobs: Job[], key: keyof Job) => Array.from(new Set(jobs.map((job) => String(job[key] || '')).filter(Boolean))).sort();
export const arrayValues = (jobs: Job[], key: 'skills' | 'relatedRoles') => Array.from(new Set(jobs.flatMap((job) => job[key]))).sort();
const locationLabel = (location: Job['aiLocations'][number]) => location.remote ? 'Remote' : [location.city, location.stateCode || location.state, location.countryCode].filter(Boolean).join(', ');
export const jobLocations = (job: Job) => Array.from(new Set([job.location, ...job.aiLocations.map(locationLabel)].filter(Boolean)));
export const allLocations = (jobs: Job[]) => Array.from(new Set(jobs.flatMap(jobLocations))).sort();
export function companyMark(company: string) { const colors = ['#356ae6', '#667085', '#087e8b', '#7f56d9', '#b54708']; return { background: colors[[...company].reduce((sum, character) => sum + character.charCodeAt(0), 0) % colors.length] }; }
