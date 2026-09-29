import type { Metadata } from 'next';
import JobsPage from '@/components/JobsPage';

export const metadata: Metadata = {
  title: 'Open jobs',
  description: 'Browse fresh opportunities posted within the last 48 hours, with clear company, location, work-style, and role details.',
};

export default function Page() {
  return <JobsPage />;
}
