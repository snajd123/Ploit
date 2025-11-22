import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  X,
  Search,
  Target,
  AlertCircle,
  ExternalLink,
  TrendingUp,
  Zap,
  Award,
  Brain,
  BarChart3,
  DollarSign
} from 'lucide-react';
import { api } from '../services/api';
import SinglePlayerAutocomplete from './SinglePlayerAutocomplete';

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
  const navigate = useNavigate();
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

  const handleViewProfile = () => {
    if (searchName) {
      navigate(`/players/${encodeURIComponent(searchName)}`);
      onClose();
    }
  };

  const getPlayerTypeColor = (type: string | null) => {
    switch (type) {
      case 'TAG': return 'text-blue-600 bg-blue-100 border-blue-300';
      case 'LAG': return 'text-purple-600 bg-purple-100 border-purple-300';
      case 'NIT': return 'text-gray-600 bg-gray-100 border-gray-300';
      case 'CALLING_STATION': return 'text-green-600 bg-green-100 border-green-300';
      case 'MANIAC': return 'text-red-600 bg-red-100 border-red-300';
      case 'FISH': return 'text-orange-600 bg-orange-100 border-orange-300';
      default: return 'text-gray-500 bg-gray-50 border-gray-200';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-600 text-white';
      case 'major': return 'bg-orange-500 text-white';
      case 'severe': return 'bg-orange-500 text-white';
      case 'moderate': return 'bg-yellow-500 text-white';
      case 'extreme': return 'bg-red-600 text-white';
      default: return 'bg-blue-500 text-white';
    }
  };

  const getSeverityBorderColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'border-l-red-600';
      case 'major': return 'border-l-orange-500';
      case 'severe': return 'border-l-orange-500';
      case 'moderate': return 'border-l-yellow-500';
      case 'extreme': return 'border-l-red-600';
      default: return 'border-l-blue-500';
    }
  };

  // Separate GTO and traditional exploits
  const gtoExploits = playerData?.top_exploits?.filter((e: any) => e.is_gto_based) || [];
  const traditionalExploits = playerData?.top_exploits?.filter((e: any) => !e.is_gto_based) || [];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 flex items-center justify-between rounded-t-2xl">
          <div className="flex items-center gap-3">
            <div className="bg-white bg-opacity-20 p-2 rounded-lg">
              <Target className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-xl font-bold text-white">Quick Opponent Lookup</h2>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-white hover:bg-opacity-20 p-2 rounded-lg transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Search Input */}
        <div className="px-6 py-5 bg-slate-50 border-b border-gray-200">
          <div className="flex gap-3">
            <SinglePlayerAutocomplete
              value={playerName}
              onChange={setPlayerName}
              onSelect={(name) => setSearchName(name)}
              placeholder="Start typing player name..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white shadow-sm"
              autoFocus
            />
            <button
              onClick={handleSearch}
              disabled={!playerName.trim() || isLoading}
              className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium shadow-sm flex items-center gap-2"
            >
              {isLoading ? (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              ) : (
                <>
                  <Search className="w-5 h-5" />
                  Search
                </>
              )}
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-6">
          {error && (
            <div className="p-4 bg-red-50 border-l-4 border-red-500 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-red-900">Player not found</p>
                <p className="text-sm text-red-700 mt-1">
                  No data available for "{searchName}"
                </p>
              </div>
            </div>
          )}

          {isLoading && (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600"></div>
              <p className="mt-4 text-gray-600 font-medium">Loading player data...</p>
            </div>
          )}

          {playerData && !isLoading && (
            <div className="space-y-6">
              {/* Player Header Card */}
              <div className="bg-gradient-to-br from-slate-50 to-blue-50 rounded-xl p-6 border border-gray-200">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <h3 className="text-3xl font-bold text-gray-900">{playerData.player_name}</h3>
                      <button
                        onClick={handleViewProfile}
                        className="text-blue-600 hover:text-blue-700 hover:bg-blue-100 p-2 rounded-lg transition-colors"
                        title="View full profile"
                      >
                        <ExternalLink className="w-5 h-5" />
                      </button>
                    </div>
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold border ${getPlayerTypeColor(playerData.player_type)}`}>
                        <Award className="w-4 h-4" />
                        {playerData.player_type || 'UNKNOWN'}
                      </span>
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-lg text-sm font-medium text-gray-700 border border-gray-300">
                        <BarChart3 className="w-4 h-4" />
                        {playerData.total_hands.toLocaleString()} hands
                      </span>
                      {playerData.gto_exploit_count > 0 && (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-100 text-purple-700 rounded-lg text-sm font-medium border border-purple-300">
                          <Brain className="w-4 h-4" />
                          {playerData.gto_exploit_count} GTO leaks
                        </span>
                      )}
                    </div>
                  </div>
                  {playerData.exploitability_index !== null && (
                    <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200 text-center">
                      <div className="text-4xl font-bold bg-gradient-to-r from-red-600 to-orange-600 bg-clip-text text-transparent">
                        {playerData.exploitability_index.toFixed(0)}
                      </div>
                      <div className="text-xs text-gray-600 font-medium mt-1">Exploit Score</div>
                    </div>
                  )}
                </div>
              </div>

              {/* Strategy Summary */}
              {playerData.strategy_summary && (
                <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl p-5 text-white shadow-lg">
                  <div className="flex items-start gap-3">
                    <div className="bg-white bg-opacity-20 p-2 rounded-lg flex-shrink-0">
                      <Target className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                      <h4 className="font-bold text-lg mb-2">Game Plan</h4>
                      <div className="text-sm leading-relaxed whitespace-pre-line opacity-95">
                        {playerData.strategy_summary}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Key Stats Grid */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <TrendingUp className="w-5 h-5 text-gray-700" />
                  <h4 className="font-bold text-gray-900 text-lg">Key Statistics</h4>
                </div>
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
                  {Object.entries(playerData.key_stats).map(([stat, value]) => (
                    <div key={stat} className="bg-white border border-gray-200 rounded-lg p-3 hover:border-blue-300 transition-colors">
                      <div className="text-xs text-gray-600 font-medium mb-1">{stat}</div>
                      <div className="text-base font-bold text-gray-900">{value as string}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* GTO Exploits Section */}
              {gtoExploits.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Brain className="w-5 h-5 text-purple-600" />
                      <h4 className="font-bold text-gray-900 text-lg">GTO-Based Exploits</h4>
                      <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-semibold rounded-full">
                        Real Data
                      </span>
                    </div>
                    {playerData.total_ev > 0 && (
                      <div className="flex items-center gap-1.5 px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-sm font-semibold border border-green-300">
                        <DollarSign className="w-4 h-4" />
                        +{playerData.total_ev.toFixed(2)} BB Total EV
                      </div>
                    )}
                  </div>
                  <div className="space-y-3">
                    {gtoExploits.map((exploit: any, idx: number) => (
                      <div
                        key={idx}
                        className={`bg-white rounded-xl border-l-4 ${getSeverityBorderColor(exploit.severity)} shadow-sm hover:shadow-md transition-shadow overflow-hidden`}
                      >
                        <div className="p-4">
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2 flex-1">
                              <Zap className="w-4 h-4 text-purple-600 flex-shrink-0 mt-0.5" />
                              <span className="font-semibold text-gray-900">{exploit.stat}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              {exploit.ev_loss && (
                                <span className="px-2 py-1 bg-green-50 text-green-700 text-xs font-bold rounded border border-green-200">
                                  {exploit.ev_loss}
                                </span>
                              )}
                              <span className="px-2 py-1 bg-slate-100 text-slate-700 text-xs font-bold rounded">
                                {exploit.deviation}
                              </span>
                              <span className={`px-2 py-1 text-xs font-bold rounded ${getSeverityColor(exploit.severity)}`}>
                                {exploit.severity.toUpperCase()}
                              </span>
                            </div>
                          </div>
                          <p className="text-sm text-gray-700 leading-relaxed pl-6">{exploit.exploit}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Traditional Stats Exploits Section */}
              {traditionalExploits.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Target className="w-5 h-5 text-blue-600" />
                    <h4 className="font-bold text-gray-900 text-lg">Traditional Stats Exploits</h4>
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-semibold rounded-full">
                      Aggregate Data
                    </span>
                  </div>
                  <div className="space-y-3">
                    {traditionalExploits.map((exploit: any, idx: number) => (
                      <div
                        key={idx}
                        className={`bg-white rounded-xl border-l-4 ${getSeverityBorderColor(exploit.severity)} shadow-sm hover:shadow-md transition-shadow overflow-hidden`}
                      >
                        <div className="p-4">
                          <div className="flex items-start justify-between mb-2">
                            <span className="font-semibold text-gray-900">{exploit.stat}</span>
                            <div className="flex items-center gap-2">
                              <span className="px-2 py-1 bg-slate-100 text-slate-700 text-xs font-bold rounded">
                                {exploit.deviation}
                              </span>
                              <span className={`px-2 py-1 text-xs font-bold rounded ${getSeverityColor(exploit.severity)}`}>
                                {exploit.severity.toUpperCase()}
                              </span>
                            </div>
                          </div>
                          <p className="text-sm text-gray-700 leading-relaxed">{exploit.exploit}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* No Exploits Message */}
              {playerData.top_exploits.length === 0 && (
                <div className="text-center py-8 bg-gray-50 rounded-xl border border-gray-200">
                  <Target className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-600 font-medium">No significant exploits found</p>
                  <p className="text-sm text-gray-500 mt-1">This player appears to play close to GTO</p>
                </div>
              )}
            </div>
          )}

          {!searchName && !isLoading && (
            <div className="text-center py-16">
              <div className="bg-blue-50 w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-4">
                <Search className="w-12 h-12 text-blue-600" />
              </div>
              <p className="text-gray-900 font-semibold text-lg">Search for an opponent</p>
              <p className="text-gray-600 mt-2">Enter a player name to see quick stats and exploits</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default QuickLookupModal;
