import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Target, ChevronRight, AlertCircle, Mail, MailCheck, Trash2,
  Users, Clock, ArrowLeft, Zap, Shield, Eye, TrendingUp,
  ChevronDown, ChevronUp, AlertTriangle
} from 'lucide-react';
import { api } from '../services/api';

const PreGame = () => {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [expandedOpponents, setExpandedOpponents] = useState<Set<string>>(new Set());
  const queryClient = useQueryClient();

  // Fetch list of strategies
  const { data: strategies, isLoading, error } = useQuery({
    queryKey: ['pregame-strategies'],
    queryFn: () => api.getPregameStrategies(50)
  });

  // Fetch selected strategy detail
  const { data: strategyDetail } = useQuery({
    queryKey: ['pregame-strategy', selectedId],
    queryFn: () => selectedId ? api.getPregameStrategy(selectedId) : null,
    enabled: !!selectedId
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deletePregameStrategy(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pregame-strategies'] });
      setSelectedId(null);
    }
  });

  const toggleOpponent = (name: string) => {
    const newExpanded = new Set(expandedOpponents);
    if (newExpanded.has(name)) {
      newExpanded.delete(name);
    } else {
      newExpanded.add(name);
    }
    setExpandedOpponents(newExpanded);
  };

  const getSoftnessGradient = (score: number) => {
    if (score >= 4) return 'from-green-500 to-emerald-600';
    if (score >= 3) return 'from-emerald-500 to-teal-600';
    if (score >= 2.5) return 'from-yellow-500 to-amber-600';
    if (score >= 2) return 'from-orange-500 to-red-500';
    return 'from-red-500 to-red-700';
  };

  const getClassificationStyle = (classification: string) => {
    switch (classification) {
      case 'VERY_SOFT': return { bg: 'bg-green-500', text: 'text-green-700', light: 'bg-green-50' };
      case 'SOFT': return { bg: 'bg-emerald-500', text: 'text-emerald-700', light: 'bg-emerald-50' };
      case 'MIXED': return { bg: 'bg-yellow-500', text: 'text-yellow-700', light: 'bg-yellow-50' };
      case 'TOUGH': return { bg: 'bg-orange-500', text: 'text-orange-700', light: 'bg-orange-50' };
      case 'VERY_TOUGH': return { bg: 'bg-red-500', text: 'text-red-700', light: 'bg-red-50' };
      default: return { bg: 'bg-gray-500', text: 'text-gray-700', light: 'bg-gray-50' };
    }
  };

  const getPlayerTypeStyle = (classification: string) => {
    switch (classification) {
      case 'CALLING_STATION': return 'bg-red-100 text-red-700 border-red-200';
      case 'LOOSE_PASSIVE': return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'NIT': return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'TAG': return 'bg-green-100 text-green-700 border-green-200';
      case 'LAG': return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'MANIAC': return 'bg-pink-100 text-pink-700 border-pink-200';
      default: return 'bg-gray-100 text-gray-600 border-gray-200';
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto flex items-center justify-center py-20">
        <div className="animate-pulse flex items-center space-x-3">
          <Target className="w-6 h-6 text-blue-500" />
          <span className="text-gray-500">Loading strategies...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto">
        <div className="p-4 bg-red-50 text-red-700 rounded-xl flex items-center space-x-3 border border-red-100">
          <AlertCircle size={20} />
          <span>Failed to load pre-game strategies</span>
        </div>
      </div>
    );
  }

  // Strategy detail view
  if (selectedId && strategyDetail) {
    const knownOpponents = strategyDetail.opponents.filter(o => o.sample_size >= 30);
    const unknownOpponents = strategyDetail.opponents.filter(o => o.sample_size < 30);

    return (
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Back button */}
        <button
          onClick={() => setSelectedId(null)}
          className="flex items-center space-x-2 text-gray-500 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft size={18} />
          <span className="text-sm font-medium">Back to strategies</span>
        </button>

        {/* Hero Header */}
        <div className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${getSoftnessGradient(strategyDetail.softness_score)} p-6 text-white`}>
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-32 translate-x-32" />
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-black/10 rounded-full translate-y-24 -translate-x-24" />

          <div className="relative flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-3 mb-2">
                <span className="px-3 py-1 bg-white/20 backdrop-blur rounded-full text-sm font-medium">
                  {strategyDetail.stake_level}
                </span>
                <span className="px-3 py-1 bg-white/20 backdrop-blur rounded-full text-sm font-medium">
                  {strategyDetail.table_classification.replace('_', ' ')}
                </span>
              </div>
              <h1 className="text-2xl font-bold mb-1">Table Strategy</h1>
              <p className="text-white/80 text-sm">
                {formatDate(strategyDetail.created_at)}
                {strategyDetail.hand_number && ` · Hand #${strategyDetail.hand_number}`}
              </p>
            </div>

            <div className="text-right">
              <div className="text-5xl font-bold">{strategyDetail.softness_score}</div>
              <div className="text-white/80 text-sm">Softness Score</div>
            </div>
          </div>

          {strategyDetail.email_sent && (
            <div className="relative mt-4 flex items-center space-x-2 text-white/90 text-sm bg-white/10 backdrop-blur w-fit px-3 py-1.5 rounded-full">
              <MailCheck size={14} />
              <span>Strategy emailed</span>
            </div>
          )}
        </div>

        {/* Key Principle Banner */}
        <div className="bg-gradient-to-r from-amber-50 to-yellow-50 border border-amber-200 rounded-xl p-4">
          <div className="flex items-start space-x-3">
            <div className="p-2 bg-amber-100 rounded-lg">
              <Zap className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <div className="text-xs font-semibold text-amber-600 uppercase tracking-wide mb-1">Key Principle</div>
              <p className="text-gray-800 font-medium">{strategyDetail.strategy.general_strategy.key_principle}</p>
            </div>
          </div>
        </div>

        {/* Overview */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <p className="text-gray-700 leading-relaxed">{strategyDetail.strategy.general_strategy.overview}</p>
        </div>

        {/* Priority Actions */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 bg-gray-50">
            <h2 className="font-semibold text-gray-900 flex items-center space-x-2">
              <Target className="w-5 h-5 text-blue-500" />
              <span>Priority Actions</span>
            </h2>
          </div>
          <div className="p-5">
            <div className="space-y-3">
              {strategyDetail.strategy.priority_actions.map((action, i) => (
                <div key={i} className="flex items-start space-x-3">
                  <span className="flex-shrink-0 w-7 h-7 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                    {i + 1}
                  </span>
                  <span className="text-gray-700 pt-0.5">{action}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Strategy Adjustments */}
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-indigo-50">
              <h3 className="font-semibold text-gray-900 text-sm flex items-center space-x-2">
                <TrendingUp className="w-4 h-4 text-blue-500" />
                <span>Opening</span>
              </h3>
            </div>
            <ul className="p-4 space-y-2">
              {strategyDetail.strategy.general_strategy.opening_adjustments.map((adj, i) => (
                <li key={i} className="text-sm text-gray-600 flex items-start">
                  <span className="text-blue-500 mr-2 mt-1">•</span>
                  <span>{adj}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 bg-gradient-to-r from-purple-50 to-pink-50">
              <h3 className="font-semibold text-gray-900 text-sm flex items-center space-x-2">
                <Zap className="w-4 h-4 text-purple-500" />
                <span>3-Betting</span>
              </h3>
            </div>
            <ul className="p-4 space-y-2">
              {strategyDetail.strategy.general_strategy.three_bet_adjustments.map((adj, i) => (
                <li key={i} className="text-sm text-gray-600 flex items-start">
                  <span className="text-purple-500 mr-2 mt-1">•</span>
                  <span>{adj}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 bg-gradient-to-r from-green-50 to-emerald-50">
              <h3 className="font-semibold text-gray-900 text-sm flex items-center space-x-2">
                <Shield className="w-4 h-4 text-green-500" />
                <span>Defense</span>
              </h3>
            </div>
            <ul className="p-4 space-y-2">
              {strategyDetail.strategy.general_strategy.defense_adjustments.map((adj, i) => (
                <li key={i} className="text-sm text-gray-600 flex items-start">
                  <span className="text-green-500 mr-2 mt-1">•</span>
                  <span>{adj}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Known Opponents with Exploits */}
        {knownOpponents.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 bg-gray-50">
              <h2 className="font-semibold text-gray-900 flex items-center space-x-2">
                <Users className="w-5 h-5 text-indigo-500" />
                <span>Opponent Exploits</span>
                <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">
                  {knownOpponents.length} with data
                </span>
              </h2>
            </div>
            <div className="divide-y divide-gray-100">
              {knownOpponents.map((opp) => {
                const exploit = strategyDetail.strategy.opponent_exploits.find(e => e.name === opp.name);
                const isExpanded = expandedOpponents.has(opp.name);

                return (
                  <div key={opp.name} className="p-4">
                    <button
                      onClick={() => toggleOpponent(opp.name)}
                      className="w-full text-left"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-sm font-bold text-gray-600">
                            {opp.seat}
                          </div>
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="font-medium text-gray-900">{opp.name}</span>
                              <span className="text-xs text-gray-400">({opp.position})</span>
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getPlayerTypeStyle(opp.classification)}`}>
                                {opp.classification.replace('_', ' ')}
                              </span>
                            </div>
                            <div className="text-xs text-gray-500 mt-0.5">
                              {opp.sample_size} hands · {opp.confidence} confidence
                            </div>
                          </div>
                        </div>
                        {isExpanded ? <ChevronUp size={18} className="text-gray-400" /> : <ChevronDown size={18} className="text-gray-400" />}
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="mt-3 ml-11 space-y-3">
                        <div className="grid grid-cols-4 gap-3 text-sm">
                          <div className="bg-gray-50 rounded-lg p-2 text-center">
                            <div className="text-xs text-gray-500">VPIP</div>
                            <div className="font-semibold text-gray-900">{opp.stats.vpip?.toFixed(1) ?? 'N/A'}%</div>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-2 text-center">
                            <div className="text-xs text-gray-500">PFR</div>
                            <div className="font-semibold text-gray-900">{opp.stats.pfr?.toFixed(1) ?? 'N/A'}%</div>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-2 text-center">
                            <div className="text-xs text-gray-500">3-Bet</div>
                            <div className="font-semibold text-gray-900">{opp.stats.three_bet?.toFixed(1) ?? 'N/A'}%</div>
                          </div>
                          <div className="bg-gray-50 rounded-lg p-2 text-center">
                            <div className="text-xs text-gray-500">F3B</div>
                            <div className="font-semibold text-gray-900">{opp.stats.fold_to_3bet?.toFixed(1) ?? 'N/A'}%</div>
                          </div>
                        </div>

                        {exploit && (
                          <div className="bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-100 rounded-lg p-3">
                            <div className="flex items-start space-x-2">
                              <Target className="w-4 h-4 text-indigo-500 mt-0.5 flex-shrink-0" />
                              <span className="text-sm text-gray-700">{exploit.exploit}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Unknown Opponents */}
        {unknownOpponents.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 bg-gray-50">
              <h2 className="font-semibold text-gray-900 flex items-center space-x-2">
                <Eye className="w-5 h-5 text-gray-400" />
                <span>Unknown Players</span>
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                  {unknownOpponents.length} need more data
                </span>
              </h2>
            </div>
            <div className="p-4">
              <div className="flex items-start space-x-2 text-sm text-gray-500 mb-3">
                <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <span>Players with less than 30 hands - using population defaults</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {unknownOpponents.map((opp) => (
                  <div
                    key={opp.name}
                    className="flex items-center space-x-2 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2"
                  >
                    <span className="w-5 h-5 rounded-full bg-gray-200 flex items-center justify-center text-xs font-medium text-gray-600">
                      {opp.seat}
                    </span>
                    <span className="text-sm text-gray-700">{opp.name}</span>
                    <span className="text-xs text-gray-400">
                      {opp.sample_size > 0 ? `${opp.sample_size}h` : 'new'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Delete button */}
        <div className="flex justify-end pt-4">
          <button
            onClick={() => {
              if (confirm('Delete this strategy?')) {
                deleteMutation.mutate(selectedId);
              }
            }}
            className="flex items-center space-x-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <Trash2 size={18} />
            <span>Delete Strategy</span>
          </button>
        </div>
      </div>
    );
  }

  // List view
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Pre-Game Strategy</h1>
        <p className="mt-1 text-gray-500">
          AI-powered table exploitation strategies
        </p>
      </div>

      {!strategies || strategies.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 text-center py-16 px-6">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <Target className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No Strategies Yet</h2>
          <p className="text-gray-500 mb-6 max-w-sm mx-auto">
            Email a single hand to generate an AI-powered exploitation strategy for your table.
          </p>
          <div className="bg-gray-50 rounded-xl p-5 max-w-md mx-auto text-left">
            <div className="space-y-3">
              <div className="flex items-start space-x-3">
                <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-bold flex-shrink-0">1</div>
                <p className="text-sm text-gray-600">Copy a hand history from your poker client</p>
              </div>
              <div className="flex items-start space-x-3">
                <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-bold flex-shrink-0">2</div>
                <p className="text-sm text-gray-600">Email it to your import address</p>
              </div>
              <div className="flex items-start space-x-3">
                <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-bold flex-shrink-0">3</div>
                <p className="text-sm text-gray-600">Receive instant exploitation strategy</p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {strategies.map((strategy) => {
            const style = getClassificationStyle(strategy.table_classification);

            return (
              <button
                key={strategy.id}
                onClick={() => setSelectedId(strategy.id)}
                className="w-full text-left bg-white rounded-xl border border-gray-200 p-4 hover:border-blue-300 hover:shadow-md transition-all group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${getSoftnessGradient(strategy.softness_score)} flex items-center justify-center`}>
                      <span className="text-xl font-bold text-white">{strategy.softness_score}</span>
                    </div>

                    <div>
                      <div className="flex items-center space-x-2 mb-1">
                        <span className="font-semibold text-gray-900">{strategy.stake_level}</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${style.light} ${style.text}`}>
                          {strategy.table_classification.replace('_', ' ')}
                        </span>
                      </div>
                      <div className="flex items-center space-x-3 text-sm text-gray-500">
                        <span className="flex items-center space-x-1">
                          <Clock size={14} />
                          <span>{formatDate(strategy.created_at)}</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <Users size={14} />
                          <span>{strategy.opponent_count} players</span>
                        </span>
                        {strategy.known_opponents > 0 && (
                          <span className="text-green-600">
                            {strategy.known_opponents} known
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3">
                    {strategy.email_sent ? (
                      <MailCheck size={18} className="text-green-500" />
                    ) : (
                      <Mail size={18} className="text-gray-300" />
                    )}
                    <ChevronRight size={20} className="text-gray-300 group-hover:text-blue-500 transition-colors" />
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default PreGame;
