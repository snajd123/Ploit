import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Search, ArrowUpDown } from 'lucide-react';
import { api } from '../services/api';
import PlayerBadge from '../components/PlayerBadge';

const PlayersList = () => {
  const navigate = useNavigate();
  const [minHands, setMinHands] = useState(100);
  const [sortBy, setSortBy] = useState('total_hands');

  const { data: players, isLoading, error } = useQuery({
    queryKey: ['players', minHands, sortBy],
    queryFn: () => api.getPlayers({ min_hands: minHands, sort_by: sortBy, limit: 100 }),
  });

  const handlePlayerClick = (playerName: string) => {
    navigate(`/players/${encodeURIComponent(playerName)}`);
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Players</h1>
        <p className="mt-2 text-gray-600">
          Browse and analyze player statistics
        </p>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
        </div>
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
                      <PlayerBadge playerType={player.player_type} size="sm" />
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {players && players.length > 0 && (
        <div className="text-sm text-gray-500 text-center">
          Showing {players.length} players with {minHands}+ hands
        </div>
      )}
    </div>
  );
};

export default PlayersList;
