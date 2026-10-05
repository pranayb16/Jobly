'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import { CountItem, formatNumber } from '@/lib/intelligence';

export function PageIntro({ eyebrow, title, copy }: { eyebrow: string; title: string; copy: string }) {
  const reduceMotion = useReducedMotion();
  return <motion.div className="intel-intro" initial={reduceMotion ? false : { opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .48, ease: [0.22, 1, 0.36, 1] }}><span>{eyebrow}</span><h1>{title}</h1><p>{copy}</p></motion.div>;
}

export function EmptyState({ message = 'Run the daily pipeline to populate this view.' }: { message?: string }) {
  return <div className="intel-empty"><strong>Intelligence data is not available yet.</strong><p>{message}</p></div>;
}

export function Metric({ label, value, note, tone }: { label: string; value: number | string; note?: string; tone?: 'positive' | 'negative' | 'neutral' }) {
  const reduceMotion = useReducedMotion();
  return <motion.article className={`metric-card ${tone ?? ''}`} initial={reduceMotion ? false : { opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: .25 }} whileHover={reduceMotion ? undefined : { y: -3 }} transition={{ duration: .34 }}><span>{label}</span><strong>{typeof value === 'number' ? formatNumber(value) : value}</strong>{note && <small>{note}</small>}<i aria-hidden="true" /></motion.article>;
}

export function Ranking({ title, items, basePath }: { title: string; items: CountItem[]; basePath: string }) {
  const reduceMotion = useReducedMotion();
  return <motion.section className="ranking-card" initial={reduceMotion ? false : { opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: .05 }} transition={{ duration: .42 }}><div className="section-title"><h2>{title}</h2><span>{items.length} shown</span></div><ol>{items.map((item, index) => <motion.li initial={reduceMotion ? false : { opacity: 0, x: -8 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: reduceMotion ? 0 : Math.min(index * .025, .18) }} key={item.name}><b>{String(index + 1).padStart(2, '0')}</b><Link href={`${basePath}/${encodeURIComponent(item.name)}`}>{item.name}</Link><strong>{formatNumber(item.count)}</strong></motion.li>)}</ol></motion.section>;
}

export function DetailHeader({ label, title, value, href }: { label: string; title: string; value: string; href?: string }) {
  const reduceMotion = useReducedMotion();
  return <motion.section className="detail-hero" initial={reduceMotion ? false : { opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .48, ease: [0.22, 1, 0.36, 1] }}><div><span>{label}</span><h1>{title}</h1></div><div><strong>{value}</strong><small>current openings</small>{href && <Link href={href}>View source <ArrowRight size={14} /></Link>}</div></motion.section>;
}
