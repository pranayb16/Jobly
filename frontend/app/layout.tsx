import type { Metadata } from 'next';
import Link from 'next/link';
import { Header } from '@/components/Header';
import '../src/styles.css';

export const metadata: Metadata = {
  title: {
    default: 'Jobly — Fresh jobs from the last 48 hours',
    template: '%s | Jobly',
  },
  description: 'Find newly posted opportunities while they are still fresh. Jobly only shows jobs from the last 48 hours.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <div className="app-shell">
          <Header />
          <main>{children}</main>
          <footer className="site-footer">
            <div className="shell footer-inner">
              <Link className="brand footer-brand" href="/">
                <span className="brand-mark">J</span>
                <span>jobly</span>
              </Link>
              <p>Every source. One fresh job index.</p>
              <span>© {new Date().getFullYear()} Jobly</span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
