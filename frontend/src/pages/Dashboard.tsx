import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Database, Users, TrendingUp, Activity, Upload, Target, BarChart2, Crosshair, HelpCircle, ArrowRight, Sparkles } from 'lucide-react';
import { api } from '../services/api';
import StatCard from '../components/StatCard';
import OnboardingModal, { resetOnboarding } from '../components/OnboardingModal';

const Dashboard = () => {
  const [showTutorial, setShowTutorial] = useState(false);

  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['database-stats'],
    queryFn: () => api.getDatabaseStats(),
  });

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const handleShowTutorial = () => {
    resetOnboarding();
    setShowTutorial(true);
  };

  // Determine recommended next step based on data state
  const getRecommendedAction = () => {
    if (!stats || stats.total_hands === 0) {
      return {
        type: 'upload',
        title: 'Upload Your First Hand History',
        description: 'Get started by importing your PokerStars hand history files.',
        icon: Upload,
        color: 'blue',
        link: '/upload'
      };
    }
    if (stats.total_hands > 0 && stats.total_players > 0) {
      return {
        type: 'strategy',
        title: 'Generate Strategy for Your Next Session',
        description: `You have ${stats.total_hands.toLocaleString()} hands analyzed. Create a strategy against your opponents.`,
        icon: Target,
        color: 'purple',
        link: '/strategy'
      };
    }
    return null;
  };

  const recommendedAction = getRecommendedAction();

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
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Overview of your poker analysis database
          </p>
        </div>
        <button
          onClick={handleShowTutorial}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 hover:text-gray-900 transition-colors"
        >
          <HelpCircle size={16} />
          Show Tutorial
        </button>
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

      {/* Recommended Next Step */}
      {recommendedAction && (
        <Link
          to={recommendedAction.link}
          className={`block p-6 rounded-xl border-2 transition-all hover:shadow-lg ${
            recommendedAction.color === 'blue'
              ? 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200 hover:border-blue-400'
              : 'bg-gradient-to-r from-purple-50 to-indigo-50 border-purple-200 hover:border-purple-400'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-xl ${
                recommendedAction.color === 'blue' ? 'bg-blue-100' : 'bg-purple-100'
              }`}>
                <recommendedAction.icon
                  size={28}
                  className={recommendedAction.color === 'blue' ? 'text-blue-600' : 'text-purple-600'}
                />
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Sparkles size={14} className="text-yellow-500" />
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Recommended Next Step
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-gray-900">{recommendedAction.title}</h3>
                <p className="text-sm text-gray-600 mt-1">{recommendedAction.description}</p>
              </div>
            </div>
            <ArrowRight size={24} className="text-gray-400" />
          </div>
        </Link>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Hands"
          value={stats?.total_hands ? stats.total_hands.toLocaleString() : '0'}
          subtitle="Parsed and stored"
          icon={<Database size={24} />}
          color="blue"
        />
        <StatCard
          title="Total Players"
          value={stats?.total_players ? stats.total_players.toLocaleString() : '0'}
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            to="/strategy"
            className="block p-5 bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg border border-purple-200 hover:shadow-md hover:border-purple-300 transition-all"
          >
            <Target size={28} className="text-purple-600 mb-3" />
            <h3 className="font-semibold text-gray-900 mb-1">Generate Strategy</h3>
            <p className="text-sm text-gray-600">Pre-game opponent analysis</p>
          </Link>

          <Link
            to="/sessions"
            className="block p-5 bg-gradient-to-br from-green-50 to-green-100 rounded-lg border border-green-200 hover:shadow-md hover:border-green-300 transition-all"
          >
            <BarChart2 size={28} className="text-green-600 mb-3" />
            <h3 className="font-semibold text-gray-900 mb-1">Review Sessions</h3>
            <p className="text-sm text-gray-600">Analyze your play</p>
          </Link>

          <Link
            to="/gto"
            className="block p-5 bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg border border-orange-200 hover:shadow-md hover:border-orange-300 transition-all"
          >
            <Crosshair size={28} className="text-orange-600 mb-3" />
            <h3 className="font-semibold text-gray-900 mb-1">GTO Analysis</h3>
            <p className="text-sm text-gray-600">Compare to optimal play</p>
          </Link>

          <Link
            to="/upload"
            className="block p-5 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg border border-blue-200 hover:shadow-md hover:border-blue-300 transition-all"
          >
            <Upload size={28} className="text-blue-600 mb-3" />
            <h3 className="font-semibold text-gray-900 mb-1">Upload Hands</h3>
            <p className="text-sm text-gray-600">Import hand histories</p>
          </Link>
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

      {/* Onboarding Modal */}
      <OnboardingModal
        isOpen={showTutorial}
        onClose={() => setShowTutorial(false)}
      />
    </div>
  );
};

export default Dashboard;
