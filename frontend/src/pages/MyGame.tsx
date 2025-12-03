import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { User, TrendingUp, TrendingDown, Calendar, Clock, Target, ChevronRight, Settings, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import type { MyGameOverview, HeroSessionResponse } from '../types';

const MyGame = () => {
  const [overview, setOverview] = useState<MyGameOverview | null>(null);
  const [sessions, setSessions] = useState<HeroSessionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewData, sessionsData] = await Promise.all([
        api.getMyGameOverview(),
        api.getMyGameSessions(20)
      ]);
      setOverview(overviewData);
      setSessions(sessionsData);
    } catch (err) {
      setError('Failed to load data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatProfit = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(1)} BB`;
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto flex items-center justify-center py-20">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  // No hero nicknames configured
  if (overview && overview.hero_nicknames.length === 0) {
    return (
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">My Game</h1>
        <div className="card text-center py-12">
          <User className="mx-auto text-gray-400 mb-4" size={48} />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No Nicknames Configured</h2>
          <p className="text-gray-600 mb-6">
            Add your poker screen names in Settings to start tracking your game.
          </p>
          <Link
            to="/settings"
            className="inline-flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <Settings size={18} />
            <span>Go to Settings</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">My Game</h1>
          <p className="mt-1 text-gray-600">
            Your performance with hole card analysis
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {overview?.hero_nicknames.map(nickname => (
            <span key={nickname} className="px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full text-sm font-medium">
              {nickname}
            </span>
          ))}
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg flex items-center space-x-2">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Stats overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Calendar className="text-blue-600" size={20} />
            </div>
            <div>
              <p className="text-sm text-gray-500">Sessions</p>
              <p className="text-xl font-bold text-gray-900">{overview?.total_sessions || 0}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Target className="text-purple-600" size={20} />
            </div>
            <div>
              <p className="text-sm text-gray-500">Hands</p>
              <p className="text-xl font-bold text-gray-900">
                {(overview?.total_hands || 0).toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${(overview?.total_profit_bb || 0) >= 0 ? 'bg-green-100' : 'bg-red-100'}`}>
              {(overview?.total_profit_bb || 0) >= 0 ? (
                <TrendingUp className="text-green-600" size={20} />
              ) : (
                <TrendingDown className="text-red-600" size={20} />
              )}
            </div>
            <div>
              <p className="text-sm text-gray-500">Total P/L</p>
              <p className={`text-xl font-bold ${(overview?.total_profit_bb || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatProfit(overview?.total_profit_bb || 0)}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${(overview?.avg_bb_100 || 0) >= 0 ? 'bg-green-100' : 'bg-red-100'}`}>
              <Clock className={`${(overview?.avg_bb_100 || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`} size={20} />
            </div>
            <div>
              <p className="text-sm text-gray-500">Win Rate</p>
              <p className={`text-xl font-bold ${(overview?.avg_bb_100 || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {(overview?.avg_bb_100 || 0).toFixed(1)} bb/100
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link to="/sessions" className="card hover:border-indigo-300 transition-colors group">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900">Sessions</h3>
              <p className="text-sm text-gray-500">View all your sessions</p>
            </div>
            <ChevronRight className="text-gray-400 group-hover:text-indigo-500 transition-colors" size={20} />
          </div>
        </Link>

        {overview && overview.stats_by_nickname.length > 0 && (
          <Link
            to={`/players/${encodeURIComponent(overview.stats_by_nickname[0].player_name)}`}
            className="card hover:border-indigo-300 transition-colors group"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-gray-900">Leak Analysis</h3>
                <p className="text-sm text-gray-500">Find your GTO leaks</p>
              </div>
              <ChevronRight className="text-gray-400 group-hover:text-indigo-500 transition-colors" size={20} />
            </div>
          </Link>
        )}

        <Link to="/gto-browser" className="card hover:border-indigo-300 transition-colors group">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900">GTO Ranges</h3>
              <p className="text-sm text-gray-500">Study optimal ranges</p>
            </div>
            <ChevronRight className="text-gray-400 group-hover:text-indigo-500 transition-colors" size={20} />
          </div>
        </Link>
      </div>

      {/* Recent sessions */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Recent Sessions</h2>
          <Link to="/sessions" className="text-sm text-indigo-600 hover:text-indigo-800">
            View all
          </Link>
        </div>

        {sessions.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Calendar className="mx-auto mb-2" size={32} />
            <p>No sessions yet</p>
            <p className="text-sm">Upload hand histories to see your sessions</p>
          </div>
        ) : (
          <div className="space-y-2">
            {sessions.slice(0, 10).map(session => (
              <Link
                key={session.session_id}
                to={`/sessions/${session.session_id}`}
                className="block p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div>
                      <p className="font-medium text-gray-900">
                        {session.table_stakes}
                        {session.table_name && (
                          <span className="text-gray-500 ml-2">{session.table_name}</span>
                        )}
                      </p>
                      <p className="text-sm text-gray-500">
                        {formatDate(session.start_time)} · {session.total_hands} hands · {session.duration_minutes}min
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`font-bold ${session.profit_loss_bb >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatProfit(session.profit_loss_bb)}
                    </p>
                    <p className={`text-sm ${session.bb_100 >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {session.bb_100.toFixed(1)} bb/100
                    </p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Stats by nickname (if multiple) */}
      {overview && overview.stats_by_nickname.length > 1 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Stats by Nickname</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-gray-500 border-b">
                  <th className="pb-2 font-medium">Nickname</th>
                  <th className="pb-2 font-medium text-right">Hands</th>
                  <th className="pb-2 font-medium text-right">Sessions</th>
                  <th className="pb-2 font-medium text-right">P/L (BB)</th>
                  <th className="pb-2 font-medium text-right">bb/100</th>
                  <th className="pb-2 font-medium text-right">VPIP</th>
                  <th className="pb-2 font-medium text-right">PFR</th>
                </tr>
              </thead>
              <tbody>
                {overview.stats_by_nickname.map(stats => (
                  <tr key={stats.player_name} className="border-b last:border-0">
                    <td className="py-3 font-medium">{stats.player_name}</td>
                    <td className="py-3 text-right">{stats.total_hands.toLocaleString()}</td>
                    <td className="py-3 text-right">{stats.sessions_count}</td>
                    <td className={`py-3 text-right font-medium ${stats.total_profit_bb >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatProfit(stats.total_profit_bb)}
                    </td>
                    <td className={`py-3 text-right ${stats.avg_bb_100 >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {stats.avg_bb_100.toFixed(1)}
                    </td>
                    <td className="py-3 text-right">{stats.vpip_pct.toFixed(1)}%</td>
                    <td className="py-3 text-right">{stats.pfr_pct.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default MyGame;
