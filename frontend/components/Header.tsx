'use client';

import { ArrowUpRight, Menu, X } from 'lucide-react';
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
          <span className="brand-mark">J</span>
          <span>jobly</span>
        </Link>

        <button className="menu-button" type="button" aria-label={menuOpen ? 'Close menu' : 'Open menu'} aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>

        <nav className={menuOpen ? 'header-nav is-open' : 'header-nav'} aria-label="Main navigation">
          <Link className={pathname === '/' ? 'nav-link active' : 'nav-link'} href="/" onClick={() => setMenuOpen(false)}>Home</Link>
          <Link className={pathname === '/jobs' ? 'nav-link active' : 'nav-link'} href="/jobs" onClick={() => setMenuOpen(false)}>All jobs</Link>
          <span className="nav-divider" />
          <Link className="nav-cta" href="/jobs" onClick={() => setMenuOpen(false)}>Open job index <ArrowUpRight size={15} /></Link>
        </nav>
      </div>
    </header>
  );
}
