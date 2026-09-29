import { Check, ChevronDown, Search } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { FilterDefinition, FilterKey } from './types';

function FilterDropdown({ definition, selected, open, onOpen, onToggle, onClear }: {
  definition: FilterDefinition;
  selected: string[];
  open: boolean;
  onOpen: () => void;
  onToggle: (value: string, single?: boolean) => void;
  onClear: () => void;
}) {
  const [search, setSearch] = useState('');
  const root = useRef<HTMLDivElement>(null);
  const options = definition.options.filter((option) => option.label.toLowerCase().includes(search.toLowerCase().trim()));

  useEffect(() => {
    if (!open) setSearch('');
  }, [open]);

  return <div className="filter-menu-wrap-v3" ref={root}>
    <button className={selected.length ? 'filter-trigger-v3 active' : 'filter-trigger-v3'} type="button" aria-expanded={open} onClick={onOpen}>
      <span>{definition.label}</span>{selected.length > 0 && <b>{selected.length}</b>}<ChevronDown size={14} />
    </button>
    {open && <div className="filter-popover-v3" role="dialog" aria-label={`${definition.label} filters`}>
      <div className="filter-popover-head-v3"><strong>{definition.label}</strong>{selected.length > 0 && <button type="button" onClick={onClear}>Clear</button>}</div>
      {definition.searchable && <label className="filter-search-v3"><Search size={14} /><input autoFocus aria-label={`Search ${definition.label.toLowerCase()}`} value={search} onChange={(event) => setSearch(event.target.value)} placeholder={`Search ${definition.label.toLowerCase()}...`} /></label>}
      <div className="filter-options-v3">
        {options.length ? options.map((option) => {
          const checked = selected.includes(option.value);
          return <label className="filter-option-v3" key={option.value}>
            <input type={definition.single ? 'radio' : 'checkbox'} name={definition.single ? definition.key : undefined} checked={checked} onChange={() => onToggle(option.value, definition.single)} />
            <span className="filter-check-v3">{checked && <Check size={12} />}</span>
            <span>{option.label}</span>{option.count !== undefined && <small>{option.count}</small>}
          </label>;
        }) : <p className="filter-no-options-v3">No matching options</p>}
      </div>
      <div className="filter-popover-foot-v3"><button type="button" onClick={onClear} disabled={!selected.length}>Clear</button><button type="button" onClick={onOpen}>Done</button></div>
    </div>}
  </div>;
}

export function JobFilterToolbar({ definitions, filters, savedOnly, onToggle, onClearCategory, onSaved }: {
  definitions: FilterDefinition[];
  filters: Record<FilterKey, string[]>;
  savedOnly: boolean;
  onToggle: (key: FilterKey, value: string, single?: boolean) => void;
  onClearCategory: (key: FilterKey) => void;
  onSaved: (value: boolean) => void;
}) {
  const [openKey, setOpenKey] = useState<FilterKey | 'more' | null>(null);
  const toolbar = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (event: MouseEvent) => { if (!toolbar.current?.contains(event.target as Node)) setOpenKey(null); };
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpenKey(null); };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', escape); };
  }, []);

  return <div className="job-filter-toolbar-v3" ref={toolbar}>
    {definitions.map((definition) => <FilterDropdown key={definition.key} definition={definition} selected={filters[definition.key]} open={openKey === definition.key} onOpen={() => setOpenKey((current) => current === definition.key ? null : definition.key)} onToggle={(value, single) => onToggle(definition.key, value, single)} onClear={() => onClearCategory(definition.key)} />)}
    <div className="filter-menu-wrap-v3 more-filter-v3">
      <button className={savedOnly ? 'filter-trigger-v3 active' : 'filter-trigger-v3'} type="button" aria-expanded={openKey === 'more'} onClick={() => setOpenKey((current) => current === 'more' ? null : 'more')}><span>More filters</span>{savedOnly && <b>1</b>}<ChevronDown size={14} /></button>
      {openKey === 'more' && <div className="filter-popover-v3 compact" role="dialog" aria-label="More filters"><div className="filter-popover-head-v3"><strong>More filters</strong>{savedOnly && <button onClick={() => onSaved(false)}>Clear</button>}</div><div className="filter-options-v3"><label className="filter-option-v3"><input type="checkbox" checked={savedOnly} onChange={() => onSaved(!savedOnly)} /><span className="filter-check-v3">{savedOnly && <Check size={12} />}</span><span>Saved jobs only</span></label></div><div className="filter-popover-foot-v3"><button type="button" onClick={() => onSaved(false)} disabled={!savedOnly}>Clear</button><button type="button" onClick={() => setOpenKey(null)}>Done</button></div></div>}
    </div>
  </div>;
}
