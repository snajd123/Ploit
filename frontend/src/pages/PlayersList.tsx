import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import { Search, Filter, X, Crosshair } from 'lucide-react';
import { api } from '../services/api';
import PlayerBadge from '../components/PlayerBadge';
import type { PlayerType } from '../types';

const PlayersList = () => {
  const navigate = useNavigate();
  const [minHands, setMinHands] = useState(0);
  const [sortBy, setSortBy] = useState('total_hands');

  // New filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPlayerType, setSelectedPlayerType] = useState<PlayerType | 'ALL'>('ALL');
  const [vpipMin, setVpipMin] = useState(0);
  const [vpipMax, setVpipMax] = useState(100);
  const [eiMin, setEiMin] = useState(0);
  const [eiMax, setEiMax] = useState(100);
  const [showFilters, setShowFilters] = useState(false);

  const { data: allPlayers, isLoading, error } = useQuery({
    queryKey: ['players', minHands, sortBy],
    queryFn: () => api.getPlayers({ min_hands: minHands, sort_by: sortBy, limit: 1000 }),
  });

  // Apply client-side filters
  const players = useMemo(() => {
    if (!allPlayers) return [];

    return allPlayers.filter(player => {
      // Search filter
      if (searchQuery && !player.player_name.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false;
      }

      // Player type filter
      if (selectedPlayerType !== 'ALL' && player.player_type !== selectedPlayerType) {
        return false;
      }

      // VPIP filter
      if (player.vpip_pct !== null && player.vpip_pct !== undefined) {
        if (player.vpip_pct < vpipMin || player.vpip_pct > vpipMax) {
          return false;
        }
      }

      // Exploitability filter
      if (player.exploitability_index !== null && player.exploitability_index !== undefined) {
        if (player.exploitability_index < eiMin || player.exploitability_index > eiMax) {
          return false;
        }
      }

      return true;
    });
  }, [allPlayers, searchQuery, selectedPlayerType, vpipMin, vpipMax, eiMin, eiMax]);

  const handlePlayerClick = (playerName: string) => {
    navigate(`/players/${encodeURIComponent(playerName)}`);
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedPlayerType('ALL');
    setVpipMin(0);
    setVpipMax(100);
    setEiMin(0);
    setEiMax(100);
  };

  const hasActiveFilters = searchQuery || selectedPlayerType !== 'ALL' ||
    vpipMin > 0 || vpipMax < 100 || eiMin > 0 || eiMax < 100;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Players</h1>
        <p className="mt-2 text-gray-600">
          Browse and analyze player statistics
        </p>
      </div>

      {/* Search and Quick Filters */}
      <div className="card">
        <div className="flex items-center space-x-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
              <input
                type="text"
                placeholder="Search players..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-field pl-10"
              />
            </div>
          </div>

          {/* Filter Toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`btn-primary flex items-center space-x-2 ${hasActiveFilters ? 'bg-blue-600' : ''}`}
          >
            <Filter size={18} />
            <span>Filters</span>
            {hasActiveFilters && (
              <span className="bg-white text-blue-600 rounded-full px-2 py-0.5 text-xs font-bold">
                {[searchQuery, selectedPlayerType !== 'ALL', vpipMin > 0 || vpipMax < 100, eiMin > 0 || eiMax < 100].filter(Boolean).length}
              </span>
            )}
          </button>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-gray-600 hover:text-gray-900 flex items-center space-x-1"
              title="Clear all filters"
            >
              <X size={18} />
              <span className="text-sm">Clear</span>
            </button>
          )}
        </div>

        {/* Advanced Filters Panel */}
        {showFilters && (
          <div className="mt-6 pt-6 border-t border-gray-200">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Advanced Filters</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Minimum Hands */}
              <div>
                <label htmlFor="minHands" className="block text-sm font-medium text-gray-700 mb-2">
                  Minimum Hands
                </label>
                <input
                  id="minHands"
                  type="number"
                  min="0"
                  value={minHands}
                  onChange={(e) => setMinHands(Number(e.target.value))}
                  className="input-field"
                />
              </div>

              {/* Sort By */}
              <div>
                <label htmlFor="sortBy" className="block text-sm font-medium text-gray-700 mb-2">
                  Sort By
                </label>
                <select
                  id="sortBy"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="input-field"
                >
                  <option value="total_hands">Total Hands</option>
                  <option value="exploitability_index">Exploitability</option>
                  <option value="vpip_pct">VPIP%</option>
                  <option value="pfr_pct">PFR%</option>
                </select>
              </div>

              {/* Player Type */}
              <div>
                <label htmlFor="playerType" className="block text-sm font-medium text-gray-700 mb-2">
                  Player Type
                </label>
                <select
                  id="playerType"
                  value={selectedPlayerType || 'ALL'}
                  onChange={(e) => setSelectedPlayerType(e.target.value === 'ALL' ? 'ALL' : e.target.value as PlayerType)}
                  className="input-field"
                >
                  <option value="ALL">All Types</option>
                  <option value="TAG">TAG (Tight/Aggressive)</option>
                  <option value="LAG">LAG (Loose/Aggressive)</option>
                  <option value="NIT">NIT (Tight/Passive)</option>
                  <option value="CALLING_STATION">Calling Station</option>
                  <option value="MANIAC">Maniac</option>
                  <option value="FISH">Fish</option>
                  <option value="LOOSE_PASSIVE">Loose/Passive</option>
                  <option value="TIGHT">Tight</option>
                  <option value="UNKNOWN">Unknown</option>
                </select>
              </div>

              {/* VPIP Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  VPIP% Range
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={vpipMin}
                    onChange={(e) => setVpipMin(Number(e.target.value))}
                    className="input-field w-20"
                    placeholder="Min"
                  />
                  <span className="text-gray-500">-</span>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={vpipMax}
                    onChange={(e) => setVpipMax(Number(e.target.value))}
                    className="input-field w-20"
                    placeholder="Max"
                  />
                </div>
              </div>

              {/* Exploitability Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Exploitability Range
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={eiMin}
                    onChange={(e) => setEiMin(Number(e.target.value))}
                    className="input-field w-20"
                    placeholder="Min"
                  />
                  <span className="text-gray-500">-</span>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={eiMax}
                    onChange={(e) => setEiMax(Number(e.target.value))}
                    className="input-field w-20"
                    placeholder="Max"
                  />
                </div>
              </div>
            </div>

            {/* Quick Filter Presets */}
            <div className="mt-4 pt-4 border-t border-gray-200">
              <p className="text-xs font-medium text-gray-700 mb-2">Quick Filters:</p>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => { setSelectedPlayerType('CALLING_STATION'); setEiMin(40); }}
                  className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-md text-xs hover:bg-yellow-200"
                >
                  Calling Stations
                </button>
                <button
                  onClick={() => { setEiMin(60); }}
                  className="px-3 py-1 bg-red-100 text-red-800 rounded-md text-xs hover:bg-red-200"
                >
                  Highly Exploitable (EI &gt; 60)
                </button>
                <button
                  onClick={() => { setVpipMin(40); }}
                  className="px-3 py-1 bg-orange-100 text-orange-800 rounded-md text-xs hover:bg-orange-200"
                >
                  Loose Players (VPIP &gt; 40%)
                </button>
                <button
                  onClick={() => { setVpipMax(20); }}
                  className="px-3 py-1 bg-gray-100 text-gray-800 rounded-md text-xs hover:bg-gray-200"
                >
                  Tight Players (VPIP &lt; 20%)
                </button>
                <button
                  onClick={() => { setSelectedPlayerType('LAG'); }}
                  className="px-3 py-1 bg-blue-100 text-blue-800 rounded-md text-xs hover:bg-blue-200"
                >
                  LAG Players
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Players table */}
      {isLoading && (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading players...</p>
          </div>
        </div>
      )}

      {error && (
        <div className="card bg-red-50 border border-red-200">
          <p className="text-red-800">Error loading players: {(error as Error).message}</p>
        </div>
      )}

      {players && players.length === 0 && (
        <div className="card text-center py-12">
          <Search className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No players found</h3>
          <p className="mt-2 text-sm text-gray-500">
            Try adjusting your filters or upload more hand histories.
          </p>
        </div>
      )}

      {players && players.length > 0 && (
        <div className="card overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Player Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Hands
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    VPIP%
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    PFR%
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    EI
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {players.map((player) => (
                  <tr
                    key={player.player_name}
                    onClick={() => handlePlayerClick(player.player_name)}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {player.player_name}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <PlayerBadge playerType={player.player_type || null} size="sm" />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {player.total_hands.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {player.vpip_pct !== null && player.vpip_pct !== undefined
                        ? `${player.vpip_pct.toFixed(1)}%`
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {player.pfr_pct !== null && player.pfr_pct !== undefined
                        ? `${player.pfr_pct.toFixed(1)}%`
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {player.exploitability_index !== null && player.exploitability_index !== undefined ? (
                        <div className="flex items-center">
                          <span className="text-sm text-gray-900 mr-2">
                            {player.exploitability_index.toFixed(1)}
                          </span>
                          <div className="w-16 bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                player.exploitability_index > 60
                                  ? 'bg-red-500'
                                  : player.exploitability_index > 40
                                  ? 'bg-yellow-500'
                                  : 'bg-green-500'
                              }`}
                              style={{ width: `${player.exploitability_index}%` }}
                            />
                          </div>
                        </div>
                      ) : (
                        <span className="text-sm text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        to={`/strategy?opponent=${encodeURIComponent(player.player_name)}`}
                        onClick={(e) => e.stopPropagation()}
                        className="inline-flex items-center space-x-1 px-3 py-1.5 text-xs font-medium text-purple-700 bg-purple-100 rounded-md hover:bg-purple-200 transition-colors"
                        title="Generate strategy against this player"
                      >
                        <Crosshair size={14} />
                        <span>Strategy</span>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {players && players.length > 0 && (
        <div className="text-sm text-gray-500 text-center">
          Showing {players.length} of {allPlayers?.length || 0} players
          {hasActiveFilters && <span className="text-blue-600 font-medium"> (filtered)</span>}
        </div>
      )}
    </div>
  );
};

export default PlayersList;
