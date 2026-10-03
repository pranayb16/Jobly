'use client';

import { Menu, Moon, Sun, X } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

const links = [
  ['/', 'Overview'],
  ['/companies', 'Companies'],
  ['/roles', 'Roles'],
  ['/skills', 'Skills'],
  ['/trends', 'Trends'],
  ['/jobs', 'Jobs'],
];

export function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [dark, setDark] = useState(false);
  const pathname = usePathname();
  const onJobs = pathname.startsWith('/jobs');

  useEffect(() => {
    const stored = localStorage.getItem('jobly:theme');
    const next = stored ? stored === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
    setDark(next);
    document.documentElement.dataset.theme = next ? 'dark' : 'light';
  }, []);

  const toggleTheme = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.dataset.theme = next ? 'dark' : 'light';
    localStorage.setItem('jobly:theme', next ? 'dark' : 'light');
  };

  return <header className={onJobs ? 'site-header jobs-header' : 'site-header'}>
    <div className="shell header-inner">
      <Link className="brand" href="/" aria-label="Jobly home" onClick={() => setMenuOpen(false)}><span className="brand-mark"><i /><i /></span><span>jobly</span><small>intel</small></Link>
      <button className="menu-button" type="button" aria-label={menuOpen ? 'Close menu' : 'Open menu'} aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>{menuOpen ? <X size={22} /> : <Menu size={22} />}</button>
      <nav className={menuOpen ? 'header-nav is-open' : 'header-nav'} aria-label="Main navigation">
        {links.map(([href, label]) => {
          const active = pathname === href || (href !== '/' && pathname.startsWith(`${href}/`));
          return <Link key={href} className={`nav-link ${active ? 'active' : ''}`} href={href} onClick={() => setMenuOpen(false)}>{label}</Link>;
        })}
        <button className="theme-toggle" type="button" onClick={toggleTheme} aria-label={dark ? 'Use light mode' : 'Use dark mode'}>{dark ? <Sun size={16} /> : <Moon size={16} />}<span>{dark ? 'Light' : 'Dark'}</span></button>
      </nav>
    </div>
  </header>;
}
