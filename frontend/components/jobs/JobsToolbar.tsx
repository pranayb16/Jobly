import { LayoutGrid, List, SlidersHorizontal } from 'lucide-react';
import type { Sort } from './types';

export function JobsToolbar({ jobs, companies, sort, filterCount, onSort, onFilters }: { jobs: number; companies: number; sort: Sort; filterCount: number; onSort: (sort: Sort) => void; onFilters: () => void }) {
  return <div className="jobs-toolbar-v2"><div><h1>{jobs.toLocaleString()} {jobs === 1 ? 'job' : 'jobs'}</h1><p>from {companies.toLocaleString()} {companies === 1 ? 'company' : 'companies'} · verified within 48 hours</p></div><div><button className="mobile-filter-v2" onClick={onFilters}><SlidersHorizontal size={16} /> Filters{filterCount > 0 && <b>{filterCount}</b>}</button><label>Sort by<select value={sort} onChange={(event) => onSort(event.target.value as Sort)}><option value="newest">Newest</option><option value="oldest">Oldest</option><option value="company">Company A–Z</option></select></label><div className="view-toggle-v2" aria-label="Grid view selected"><button className="active"><LayoutGrid size={15} /></button><button disabled><List size={15} /></button></div></div></div>;
}
