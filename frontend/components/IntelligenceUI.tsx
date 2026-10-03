import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { CountItem, formatNumber } from '@/lib/intelligence';

export function PageIntro({ eyebrow, title, copy }: { eyebrow: string; title: string; copy: string }) {
  return <div className="intel-intro"><span>{eyebrow}</span><h1>{title}</h1><p>{copy}</p></div>;
}

export function EmptyState() {
  return <div className="intel-empty"><strong>Intelligence data is not available yet.</strong><p>Run the daily pipeline and snapshot command to populate this view.</p></div>;
}

export function Metric({ label, value, note }: { label: string; value: number | string; note?: string }) {
  return <article className="metric-card"><span>{label}</span><strong>{typeof value === 'number' ? formatNumber(value) : value}</strong>{note && <small>{note}</small>}</article>;
}

export function Ranking({ title, items, basePath }: { title: string; items: CountItem[]; basePath: string }) {
  return <section className="ranking-card"><div className="section-title"><h2>{title}</h2><span>{items.length} shown</span></div><ol>{items.map((item, index) => <li key={item.name}><b>{String(index + 1).padStart(2, '0')}</b><Link href={`${basePath}/${encodeURIComponent(item.name)}`}>{item.name}</Link><strong>{formatNumber(item.count)}</strong></li>)}</ol></section>;
}

export function DetailHeader({ label, title, value, href }: { label: string; title: string; value: string; href?: string }) {
  return <section className="detail-hero"><div><span>{label}</span><h1>{title}</h1></div><div><strong>{value}</strong><small>current openings</small>{href && <Link href={href}>View source <ArrowRight size={14} /></Link>}</div></section>;
}
