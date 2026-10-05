import type { Metadata } from 'next';
import Link from 'next/link';
import { Header } from '@/components/Header';
import '../src/styles.css';

export const metadata: Metadata = {
  title: {
    default: 'Jobly — Hiring intelligence from employer career sites',
    template: '%s | Jobly',
  },
  description: 'Track company hiring activity, role demand, skills, and job changes over time.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <div className="app-shell">
          <div className="site-ambient" aria-hidden="true"><i /><i /><i /><i /></div>
          <Header />
          <main className="site-main">{children}</main>
          <footer className="site-footer">
            <div className="shell footer-inner">
              <Link className="brand footer-brand" href="/">
                <span className="brand-mark"><i /><i /></span>
                <span>jobly</span>
              </Link>
              <p>Career-site history turned into hiring intelligence.</p>
              <span>© {new Date().getFullYear()} Jobly</span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
