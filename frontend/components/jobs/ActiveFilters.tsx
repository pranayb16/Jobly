import { X } from 'lucide-react';
import type { ActiveFilterGroup, FilterKey } from './types';

export function ActiveFilters({ groups, onRemove, onClearAll }: {
  groups: ActiveFilterGroup[];
  onRemove: (key: FilterKey | 'saved', value: string) => void;
  onClearAll: () => void;
}) {
  if (!groups.length) return null;
  return <section className="active-filter-area-v3" aria-label="Active filters">
    <div className="active-filter-groups-v3">{groups.map((group) => <div className="active-filter-group-v3" key={group.key}><strong>{group.label}</strong><div>{group.values.map((option) => <button type="button" key={option.value} onClick={() => onRemove(group.key, option.value)}>{option.label}<X size={12} /><span className="sr-only">Remove</span></button>)}</div></div>)}</div>
    <button className="clear-all-v3" type="button" onClick={onClearAll}>Clear all</button>
  </section>;
}
