import { Check, Search, X } from 'lucide-react';
import { useState } from 'react';
import type { FilterDefinition, FilterKey } from './types';

function MobileFilterSection({ definition, selected, onToggle, onClear }: { definition: FilterDefinition; selected: string[]; onToggle: (value: string, single?: boolean) => void; onClear: () => void }) {
  const [search, setSearch] = useState('');
  const options = definition.options.filter((option) => option.label.toLowerCase().includes(search.toLowerCase().trim()));
  return <details className="mobile-filter-section-v3" open={['workplace', 'experience', 'employment'].includes(definition.key)}><summary><span>{definition.label}{selected.length > 0 && <b>{selected.length}</b>}</span><span>+</span></summary><div>{definition.searchable && <label className="filter-search-v3"><Search size={14} /><input aria-label={`Search ${definition.label.toLowerCase()}`} value={search} onChange={(event) => setSearch(event.target.value)} placeholder={`Search ${definition.label.toLowerCase()}...`} /></label>}<div className="filter-options-v3">{options.map((option) => { const checked = selected.includes(option.value); return <label className="filter-option-v3" key={option.value}><input type={definition.single ? 'radio' : 'checkbox'} name={definition.single ? `mobile-${definition.key}` : undefined} checked={checked} onChange={() => onToggle(option.value, definition.single)} /><span className="filter-check-v3">{checked && <Check size={12} />}</span><span>{option.label}</span>{option.count !== undefined && <small>{option.count}</small>}</label>; })}</div>{selected.length > 0 && <button className="mobile-clear-category-v3" type="button" onClick={onClear}>Clear {definition.label.toLowerCase()}</button>}</div></details>;
}

export function MobileFilterDrawer({ definitions, filters, savedOnly, count, onToggle, onClearCategory, onSaved, onClearAll, onClose }: {
  definitions: FilterDefinition[];
  filters: Record<FilterKey, string[]>;
  savedOnly: boolean;
  count: number;
  onToggle: (key: FilterKey, value: string, single?: boolean) => void;
  onClearCategory: (key: FilterKey) => void;
  onSaved: (value: boolean) => void;
  onClearAll: () => void;
  onClose: () => void;
}) {
  return <div className="mobile-filters-v3"><button className="mobile-filter-backdrop-v3" type="button" onClick={onClose} aria-label="Close filters" /><aside><header><div><strong>Filters</strong>{count > 0 && <b>{count}</b>}</div><button type="button" onClick={onClose} aria-label="Close filters"><X size={19} /></button></header><div className="mobile-filter-scroll-v3"><label className="mobile-saved-filter-v3"><input type="checkbox" checked={savedOnly} onChange={() => onSaved(!savedOnly)} /><span className="filter-check-v3">{savedOnly && <Check size={12} />}</span><span>Saved jobs only</span></label>{definitions.map((definition) => <MobileFilterSection key={definition.key} definition={definition} selected={filters[definition.key]} onToggle={(value, single) => onToggle(definition.key, value, single)} onClear={() => onClearCategory(definition.key)} />)}</div><footer><button type="button" onClick={onClearAll} disabled={!count}>Clear all</button><button type="button" onClick={onClose}>Show jobs</button></footer></aside></div>;
}
