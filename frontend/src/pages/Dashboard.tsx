import { useQuery } from '@tanstack/react-query';
import { Database, Users, TrendingUp, Activity } from 'lucide-react';
import { api } from '../services/api';
import StatCard from '../components/StatCard';

const Dashboard = () => {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['database-stats'],
    queryFn: () => api.getDatabaseStats(),
  });

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card bg-red-50 border border-red-200">
        <p className="text-red-800">Error loading dashboard: {(error as Error).message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Overview of your poker analysis database
        </p>
      </div>

      {/* Database health */}
      {health && (
        <div className="card bg-white border-l-4 border-l-green-500">
          <div className="flex items-center space-x-3">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            <div>
              <p className="font-semibold text-gray-900">System Status: {health.status}</p>
              <p className="text-sm text-gray-600">Database: {health.database}</p>
            </div>
          </div>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Hands"
          value={stats?.total_hands.toLocaleString() || '0'}
          subtitle="Parsed and stored"
          icon={<Database size={24} />}
          color="blue"
        />
        <StatCard
          title="Total Players"
          value={stats?.total_players.toLocaleString() || '0'}
          subtitle="Unique players tracked"
          icon={<Users size={24} />}
          color="green"
        />
        <StatCard
          title="Date Range"
          value={
            stats?.first_hand_date
              ? new Date(stats.first_hand_date).toLocaleDateString()
              : 'N/A'
          }
          subtitle={
            stats?.last_hand_date
              ? `to ${new Date(stats.last_hand_date).toLocaleDateString()}`
              : 'No data'
          }
          icon={<TrendingUp size={24} />}
          color="yellow"
        />
        <StatCard
          title="Status"
          value="Active"
          subtitle="Ready for analysis"
          icon={<Activity size={24} />}
          color="gray"
        />
      </div>

      {/* Quick actions */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a
            href="/upload"
            className="block p-6 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg border border-blue-200 hover:shadow-md transition-shadow"
          >
            <Database size={32} className="text-blue-600 mb-3" />
            <h3 className="font-semibold text-gray-900 mb-1">Upload Hands</h3>
            <p className="text-sm text-gray-600">Import new hand history files</p>
          </a>

          <a
            href="/players"
            className="block p-6 bg-gradient-to-br from-green-50 to-green-100 rounded-lg border border-green-200 hover:shadow-md transition-shadow"
          >
            <Users size={32} className="text-green-600 mb-3" />
            <h3 className="font-semibold text-gray-900 mb-1">Browse Players</h3>
            <p className="text-sm text-gray-600">View player statistics and metrics</p>
          </a>

          <a
            href="/claude"
            className="block p-6 bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg border border-purple-200 hover:shadow-md transition-shadow"
          >
            <Activity size={32} className="text-purple-600 mb-3" />
            <h3 className="font-semibold text-gray-900 mb-1">Ask Claude</h3>
            <p className="text-sm text-gray-600">Get AI-powered strategic insights</p>
          </a>
        </div>
      </div>

      {/* Info card */}
      <div className="card bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">About This Platform</h2>
        <p className="text-gray-700 mb-4">
          This poker analysis platform parses PokerStars hand histories and calculates
          12 advanced composite statistical models for exploitative strategy. You can:
        </p>
        <ul className="space-y-2 text-gray-700">
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">•</span>
            <span>Upload hand history files and track player tendencies</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">•</span>
            <span>View traditional stats (VPIP, PFR, 3-bet, etc.) and advanced metrics</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">•</span>
            <span>Get player classifications (NIT, TAG, LAG, FISH, etc.)</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">•</span>
            <span>Ask Claude AI natural language questions about your data</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">•</span>
            <span>Receive strategic exploit recommendations</span>
          </li>
        </ul>
      </div>
    </div>
  );
};

export default Dashboard;
