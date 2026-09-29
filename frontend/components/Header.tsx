'use client';

import { ArrowRight, Menu, X } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

export function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const pathname = usePathname();

  return (
    <header className="site-header">
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
          <Link className={pathname === '/jobs' ? 'nav-link active' : 'nav-link'} href="/jobs" onClick={() => setMenuOpen(false)}>Browse jobs</Link>
          <Link className="nav-link" href="/#how-it-works" onClick={() => setMenuOpen(false)}>How it works</Link>
          <Link className="nav-cta" href="/jobs" onClick={() => setMenuOpen(false)}>Search the index <ArrowRight size={15} /></Link>
        </nav>
      </div>
    </header>
  );
}
