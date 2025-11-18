import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { X, Search, Target, AlertCircle } from 'lucide-react';
import { api } from '../services/api';

interface QuickLookupModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialPlayerName?: string;
}

const QuickLookupModal: React.FC<QuickLookupModalProps> = ({
  isOpen,
  onClose,
  initialPlayerName = ''
}) => {
  const [playerName, setPlayerName] = useState(initialPlayerName);
  const [searchName, setSearchName] = useState('');

  const { data: playerData, isLoading, error } = useQuery({
    queryKey: ['quickLookup', searchName],
    queryFn: () => api.quickLookup(searchName),
    enabled: searchName.length > 0
  });

  const handleSearch = () => {
    if (playerName.trim()) {
      setSearchName(playerName.trim());
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const getPlayerTypeColor = (type: string | null) => {
    switch (type) {
      case 'TAG': return 'text-blue-600 bg-blue-100';
      case 'LAG': return 'text-purple-600 bg-purple-100';
      case 'NIT': return 'text-gray-600 bg-gray-100';
      case 'CALLING_STATION': return 'text-green-600 bg-green-100';
      case 'MANIAC': return 'text-red-600 bg-red-100';
      case 'FISH': return 'text-orange-600 bg-orange-100';
      default: return 'text-gray-500 bg-gray-50';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'extreme': return 'text-red-600 bg-red-100 border-red-200';
      case 'severe': return 'text-orange-600 bg-orange-100 border-orange-200';
      case 'moderate': return 'text-yellow-600 bg-yellow-100 border-yellow-200';
      default: return 'text-blue-600 bg-blue-100 border-blue-200';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Target className="w-6 h-6 text-blue-600" />
            <h2 className="text-xl font-bold text-gray-900">Quick Opponent Lookup</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Search Input */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex gap-2">
            <input
              type="text"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter player name..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              autoFocus
            />
            <button
              onClick={handleSearch}
              disabled={!playerName.trim() || isLoading}
              className="btn-primary"
            >
              {isLoading ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                <>
                  <Search className="w-4 h-4 mr-2" />
                  Search
                </>
              )}
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-4">
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-900">Player not found</p>
                <p className="text-sm text-red-700 mt-1">
                  No data available for "{searchName}"
                </p>
              </div>
            </div>
          )}

          {isLoading && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <p className="mt-4 text-gray-600">Loading player data...</p>
            </div>
          )}

          {playerData && !isLoading && (
            <div className="space-y-4">
              {/* Player Header */}
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-2xl font-bold text-gray-900">{playerData.player_name}</h3>
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`inline-block px-2 py-1 rounded text-sm font-medium ${getPlayerTypeColor(playerData.player_type)}`}>
                      {playerData.player_type || 'UNKNOWN'}
                    </span>
                    <span className="text-sm text-gray-600">
                      {playerData.total_hands.toLocaleString()} hands
                    </span>
                  </div>
                </div>
                {playerData.exploitability_index !== null && (
                  <div className="text-right">
                    <div className="text-3xl font-bold text-gray-900">
                      {playerData.exploitability_index.toFixed(0)}
                    </div>
                    <div className="text-xs text-gray-600">Exploit Score</div>
                  </div>
                )}
              </div>

              {/* Key Stats */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-semibold text-gray-900 mb-3">Key Statistics</h4>
                <div className="grid grid-cols-3 gap-3">
                  {Object.entries(playerData.key_stats).map(([stat, value]) => (
                    <div key={stat} className="text-center p-2 bg-white rounded">
                      <div className="text-xs text-gray-600">{stat}</div>
                      <div className="text-sm font-semibold text-gray-900">{value as string}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top Exploits */}
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">Top Exploits</h4>
                <div className="space-y-2">
                  {playerData.top_exploits.length === 0 ? (
                    <p className="text-sm text-gray-600 italic">No significant exploits found</p>
                  ) : (
                    playerData.top_exploits.map((exploit: any, idx: number) => (
                      <div
                        key={idx}
                        className={`p-3 rounded-lg border ${getSeverityColor(exploit.severity)}`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium">{exploit.stat}</span>
                          <span className="text-sm font-semibold">{exploit.deviation}</span>
                        </div>
                        <div className="text-sm">{exploit.exploit}</div>
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium mt-1 ${getSeverityColor(exploit.severity)}`}>
                          {exploit.severity}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Expected Value */}
              {playerData.total_ev > 0 && (
                <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-green-900">Estimated EV</span>
                    <span className="text-2xl font-bold text-green-600">
                      +{playerData.total_ev.toFixed(2)} BB/100
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {!searchName && !isLoading && (
            <div className="text-center py-12">
              <Search className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-600">Enter a player name to see quick stats and exploits</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default QuickLookupModal;
