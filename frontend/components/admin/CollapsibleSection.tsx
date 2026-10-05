'use client';

import { ChevronDown, ChevronRight } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useState, type ReactNode } from 'react';

export function CollapsibleSection({ title, summary, defaultOpen = false, status, children }: { title: string; summary: string; defaultOpen?: boolean; status?: ReactNode; children: ReactNode }) {
  const [open, setOpen] = useState(defaultOpen);
  const reduceMotion = useReducedMotion();

  return <section className={`admin-accordion ${open ? 'open' : ''}`}>
    <button type="button" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
      {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      <span><strong>{title}</strong><small>{summary}</small></span>
      {status}
    </button>
    <AnimatePresence initial={false}>{open && <motion.div
      initial={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
      animate={reduceMotion ? { opacity: 1 } : { height: 'auto', opacity: 1 }}
      exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
      transition={{ duration: .25, ease: [0.22, 1, 0.36, 1] }}
    ><div className="admin-accordion-body">{children}</div></motion.div>}</AnimatePresence>
  </section>;
}
