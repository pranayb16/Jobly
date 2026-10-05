import type { ReactNode } from 'react';

export function StatusBadge({ status }: { status: string }) {
  return <span className={`admin-status admin-status-${status}`}>{status.replaceAll('_', ' ')}</span>;
}

export function MetricStrip({ items }: { items: Array<{ label: string; value: ReactNode; tone?: string }> }) {
  return <div className="admin-metric-strip">
    {items.map((item) => <div className={item.tone ? `tone-${item.tone}` : undefined} key={item.label}><span>{item.label}</span><strong>{item.value}</strong></div>)}
  </div>;
}

export function KeyValueRows({ items }: { items: Array<{ label: string; value: ReactNode }> }) {
  return <dl className="admin-key-values">
    {items.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}
  </dl>;
}
