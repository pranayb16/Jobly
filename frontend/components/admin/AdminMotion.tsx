'use client';

import { motion, useReducedMotion } from 'motion/react';
import type { ReactNode } from 'react';

const easing = [0.22, 1, 0.36, 1] as const;

export function AdminDetailFrame({ children }: { children: ReactNode }) {
  const reduceMotion = useReducedMotion();

  return <motion.div
    className="shell admin-page admin-run-detail"
    initial={reduceMotion ? false : { opacity: 0, y: 24 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.55, ease: easing }}
  >
    {children}
  </motion.div>;
}

export function AdminViewTransition({ view, children }: { view: string; children: ReactNode }) {
  const reduceMotion = useReducedMotion();

  return <motion.main
    className="admin-tab-panel"
    key={view}
    initial={reduceMotion ? false : { opacity: 0, y: 16, filter: 'blur(5px)' }}
    animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
    transition={{ duration: 0.38, ease: easing }}
  >
    {children}
  </motion.main>;
}
