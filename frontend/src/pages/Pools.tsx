import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Users, ChevronRight, AlertCircle, Search, Filter, TrendingUp, Target, Shield, Zap } from 'lucide-react';
import { api } from '../services/api';
import type { PoolSummary, PoolDetail } from '../types';

const Pools = () => {
  const [pools, setPools] = useState<PoolSummary[]>([]);
  const [selectedPool, setSelectedPool] = useState<string | null>(null);
  const [poolDetail, setPoolDetail] = useState<PoolDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<string>('total_hands');

  useEffect(() => {
    loadPools();
  }, []);

  useEffect(() => {
    if (selectedPool) {
      loadPoolDetail(selectedPool);
    }
  }, [selectedPool, sortBy]);

  const loadPools = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getPools();
      setPools(data);
      // Auto-select first pool if available
      if (data.length > 0 && !selectedPool) {
        setSelectedPool(data[0].stake_level);
      }
    } catch (err) {
      setError('Failed to load pools');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadPoolDetail = async (stakeLevel: string) => {
    setDetailLoading(true);
    try {
      const data = await api.getPoolDetail(stakeLevel, 100, sortBy);
      setPoolDetail(data);
    } catch (err) {
      console.error('Failed to load pool detail:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const getPlayerTypeColor = (type: string | null) => {
    switch (type) {
      case 'NIT': return 'bg-blue-100 text-blue-800';
      case 'TAG': return 'bg-green-100 text-green-800';
      case 'LAG': return 'bg-orange-100 text-orange-800';
      case 'FISH': return 'bg-red-100 text-red-800';
      case 'CALLING_STATION': return 'bg-yellow-100 text-yellow-800';
      case 'MANIAC': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const filteredPlayers = poolDetail?.players.filter(player =>
    player.player_name.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto flex items-center justify-center py-20">
        <div className="text-gray-500">Loading pools...</div>
      </div>
    );
  }

  if (pools.length === 0) {
    return (
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Pools</h1>
        <div className="card text-center py-12">
          <Users className="mx-auto text-gray-400 mb-4" size={48} />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No Opponent Data</h2>
          <p className="text-gray-600 mb-6">
            Upload hand histories to see opponent pools grouped by stakes.
          </p>
          <Link
            to="/upload"
            className="inline-flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <span>Upload Hands</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Pools</h1>
        <p className="mt-1 text-gray-600">
          Opponent analysis grouped by site and stakes (aggregate stats, no hole cards)
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg flex items-center space-x-2">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="flex gap-6">
        {/* Pool list sidebar */}
        <div className="w-64 flex-shrink-0">
          <div className="card sticky top-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Stakes</h2>
            <div className="space-y-1">
              {pools.map(pool => (
                <button
                  key={pool.pool_id}
                  onClick={() => setSelectedPool(pool.stake_level)}
                  className={`w-full text-left p-3 rounded-lg transition-colors ${
                    selectedPool === pool.stake_level
                      ? 'bg-indigo-100 text-indigo-800 border border-indigo-200'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{pool.display_name}</span>
                    <ChevronRight size={16} className={selectedPool === pool.stake_level ? 'text-indigo-600' : 'text-gray-400'} />
                  </div>
                  <div className="mt-1 text-sm text-gray-500">
                    {pool.player_count} players · {pool.total_hands.toLocaleString()} hands
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Pool detail */}
        <div className="flex-1">
          {poolDetail && (
            <>
              {/* Pool stats - Primary */}
              <div className="grid grid-cols-4 gap-3 mb-4">
                <div className="card bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
                  <div className="flex items-center gap-2 mb-1">
                    <TrendingUp size={14} className="text-blue-600" />
                    <p className="text-xs text-blue-600 font-medium">VPIP</p>
                  </div>
                  <p className="text-xl font-bold text-blue-900">
                    {poolDetail.avg_stats.vpip?.toFixed(1) || 'N/A'}%
                  </p>
                </div>
                <div className="card bg-gradient-to-br from-green-50 to-green-100 border-green-200">
                  <div className="flex items-center gap-2 mb-1">
                    <Target size={14} className="text-green-600" />
                    <p className="text-xs text-green-600 font-medium">PFR</p>
                  </div>
                  <p className="text-xl font-bold text-green-900">
                    {poolDetail.avg_stats.pfr?.toFixed(1) || 'N/A'}%
                  </p>
                </div>
                <div className="card bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
                  <div className="flex items-center gap-2 mb-1">
                    <Zap size={14} className="text-purple-600" />
                    <p className="text-xs text-purple-600 font-medium">3-Bet</p>
                  </div>
                  <p className="text-xl font-bold text-purple-900">
                    {poolDetail.avg_stats['3bet']?.toFixed(1) || 'N/A'}%
                  </p>
                </div>
                <div className="card bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200">
                  <div className="flex items-center gap-2 mb-1">
                    <Shield size={14} className="text-orange-600" />
                    <p className="text-xs text-orange-600 font-medium">Fold to 3B</p>
                  </div>
                  <p className="text-xl font-bold text-orange-900">
                    {poolDetail.avg_stats.fold_to_3bet?.toFixed(1) || 'N/A'}%
                  </p>
                </div>
              </div>

              {/* Pool stats - Secondary */}
              <div className="grid grid-cols-6 gap-2 mb-4">
                <div className="card py-2 px-3">
                  <p className="text-xs text-gray-500">4-Bet</p>
                  <p className="text-sm font-semibold text-gray-800">{poolDetail.avg_stats['4bet']?.toFixed(1) || 'N/A'}%</p>
                </div>
                <div className="card py-2 px-3">
                  <p className="text-xs text-gray-500">Cold Call</p>
                  <p className="text-sm font-semibold text-gray-800">{poolDetail.avg_stats.cold_call?.toFixed(1) || 'N/A'}%</p>
                </div>
                <div className="card py-2 px-3">
                  <p className="text-xs text-gray-500">Squeeze</p>
                  <p className="text-sm font-semibold text-gray-800">{poolDetail.avg_stats.squeeze?.toFixed(1) || 'N/A'}%</p>
                </div>
                <div className="card py-2 px-3">
                  <p className="text-xs text-gray-500">Limp</p>
                  <p className="text-sm font-semibold text-gray-800">{poolDetail.avg_stats.limp?.toFixed(1) || 'N/A'}%</p>
                </div>
                <div className="card py-2 px-3">
                  <p className="text-xs text-gray-500">Steal</p>
                  <p className="text-sm font-semibold text-gray-800">{poolDetail.avg_stats.steal_attempt?.toFixed(1) || 'N/A'}%</p>
                </div>
                <div className="card py-2 px-3">
                  <p className="text-xs text-gray-500">Fold to Steal</p>
                  <p className="text-sm font-semibold text-gray-800">{poolDetail.avg_stats.fold_to_steal?.toFixed(1) || 'N/A'}%</p>
                </div>
              </div>

              {/* Player Type Distribution & Exploitability */}
              {pools.find(p => p.stake_level === selectedPool) && (
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="card">
                    <h4 className="text-sm font-medium text-gray-700 mb-3">Player Type Distribution</h4>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(pools.find(p => p.stake_level === selectedPool)?.player_type_distribution || {}).map(([type, count]) => (
                        <span
                          key={type}
                          className={`px-2 py-1 rounded text-xs font-medium ${getPlayerTypeColor(type)}`}
                        >
                          {type}: {count}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="card">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Pool Exploitability</h4>
                    <div className="flex items-center gap-3">
                      <div className="text-2xl font-bold text-indigo-600">
                        {pools.find(p => p.stake_level === selectedPool)?.avg_exploitability?.toFixed(1) || 'N/A'}
                      </div>
                      <div className="flex-1">
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500"
                            style={{ width: `${Math.min(pools.find(p => p.stake_level === selectedPool)?.avg_exploitability || 0, 100)}%` }}
                          />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          {(pools.find(p => p.stake_level === selectedPool)?.avg_exploitability || 0) > 60 ? 'Soft pool - high profit potential' :
                           (pools.find(p => p.stake_level === selectedPool)?.avg_exploitability || 0) > 40 ? 'Average pool - selective exploitation' :
                           'Tough pool - focus on GTO'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Controls */}
              <div className="flex items-center justify-between mb-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                  <input
                    type="text"
                    placeholder="Search players..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>
                <div className="flex items-center space-x-2">
                  <Filter size={16} className="text-gray-400" />
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="total_hands">Most Hands</option>
                    <option value="vpip_pct">Highest VPIP</option>
                    <option value="pfr_pct">Highest PFR</option>
                    <option value="three_bet_pct">Highest 3-Bet</option>
                    <option value="player_name">Name A-Z</option>
                  </select>
                </div>
              </div>

              {/* Players table */}
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Players ({filteredPlayers.length})
                </h3>

                {detailLoading ? (
                  <div className="text-center py-8 text-gray-500">Loading players...</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="text-left text-sm text-gray-500 border-b">
                          <th className="pb-3 font-medium">Player</th>
                          <th className="pb-3 font-medium text-right">Hands</th>
                          <th className="pb-3 font-medium text-right">VPIP</th>
                          <th className="pb-3 font-medium text-right">PFR</th>
                          <th className="pb-3 font-medium text-right">3-Bet</th>
                          <th className="pb-3 font-medium text-right">Fold to 3B</th>
                          <th className="pb-3 font-medium text-center">Type</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredPlayers.map(player => (
                          <tr key={player.player_name} className="border-b last:border-0 hover:bg-gray-50">
                            <td className="py-3">
                              <Link
                                to={`/players/${encodeURIComponent(player.player_name)}`}
                                className="font-medium text-indigo-600 hover:text-indigo-800"
                              >
                                {player.player_name}
                              </Link>
                            </td>
                            <td className="py-3 text-right text-gray-600">
                              {player.total_hands.toLocaleString()}
                            </td>
                            <td className="py-3 text-right">
                              <span className={player.vpip_pct > 30 ? 'text-orange-600 font-medium' : ''}>
                                {player.vpip_pct.toFixed(1)}%
                              </span>
                            </td>
                            <td className="py-3 text-right">
                              {player.pfr_pct.toFixed(1)}%
                            </td>
                            <td className="py-3 text-right">
                              {player.three_bet_pct.toFixed(1)}%
                            </td>
                            <td className="py-3 text-right">
                              {player.fold_to_three_bet_pct !== null
                                ? `${player.fold_to_three_bet_pct.toFixed(1)}%`
                                : 'N/A'}
                            </td>
                            <td className="py-3 text-center">
                              {player.player_type && (
                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${getPlayerTypeColor(player.player_type)}`}>
                                  {player.player_type}
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Pools;
