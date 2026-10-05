import { AdminRunsDashboard } from '@/components/admin/AdminRunsDashboard';
import { getAdmin, type RunsPayload } from '@/lib/admin';

// Internal operations route: protect /admin/runs before exposing a public deployment.
export default async function AdminRunsPage() {
  const data = await getAdmin<RunsPayload>('/api/admin/runs?limit=100');
  const runs = data?.runs ?? [];

  return <div className="admin-cosmic-shell">
    <div className="intelligence-ambient" aria-hidden="true"><i /><i /><i /></div>
    <div className="shell admin-page admin-runs-page">
      {!runs.length ? <div className="admin-empty"><strong>No pipeline runs are available.</strong><p>The operations API could not be reached, or no pipeline has run yet.</p></div> : <AdminRunsDashboard runs={runs} count={data?.count ?? runs.length} />}
    </div>
  </div>;
}
