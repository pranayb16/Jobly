'use client';

import { ArrowLeft, ArrowRight, Clock3, Menu, Moon, Sun, X } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

export function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [dark, setDark] = useState(false);
  const pathname = usePathname();
  const onJobs = pathname === '/jobs';

  useEffect(() => { setDark(document.documentElement.dataset.theme === 'dark'); }, []);
  const toggleTheme = () => { const next = !dark; setDark(next); document.documentElement.dataset.theme = next ? 'dark' : 'light'; localStorage.setItem('jobly:theme', next ? 'dark' : 'light'); };

  return (
    <header className={onJobs ? 'site-header jobs-header' : 'site-header'}>
      <div className="shell header-inner">
        <Link className="brand" href="/" aria-label="Jobly home" onClick={() => setMenuOpen(false)}>
          <span className="brand-mark"><i /><i /></span>
          <span>jobly</span>
          <small>beta</small>
        </Link>

        <button className="menu-button" type="button" aria-label={menuOpen ? 'Close menu' : 'Open menu'} aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>

        <nav className={menuOpen ? 'header-nav is-open' : 'header-nav'} aria-label="Main navigation">
          {onJobs ? <><div className="jobs-nav-context"><Clock3 size={14} /><span>Live job index</span><b>48h only</b></div><Link className="nav-link back-home" href="/" onClick={() => setMenuOpen(false)}><ArrowLeft size={14} /> Home</Link></> : <><Link className="nav-link" href="/jobs" onClick={() => setMenuOpen(false)}>Browse jobs</Link><Link className="nav-link" href="/#how-it-works" onClick={() => setMenuOpen(false)}>How it works</Link><Link className="nav-cta" href="/jobs" onClick={() => setMenuOpen(false)}>Search the index <ArrowRight size={15} /></Link></>}
          <button className="theme-toggle" type="button" onClick={toggleTheme} aria-label={dark ? 'Use light mode' : 'Use dark mode'}>{dark ? <Sun size={16} /> : <Moon size={16} />}<span>{dark ? 'Light' : 'Dark'}</span></button>
        </nav>
      </div>
    </header>
  );
}
