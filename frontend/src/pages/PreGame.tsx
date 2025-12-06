import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Target, ChevronRight, AlertCircle, Mail, MailCheck, Trash2,
  Users, TrendingUp, Clock, ArrowLeft
} from 'lucide-react';
import { api } from '../services/api';

const PreGame = () => {
  const [selectedId, setSelectedId] = useState<number | null>(null);
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

  const getClassificationColor = (classification: string) => {
    switch (classification) {
      case 'VERY_SOFT': return 'bg-green-100 text-green-800';
      case 'SOFT': return 'bg-emerald-100 text-emerald-800';
      case 'MIXED': return 'bg-yellow-100 text-yellow-800';
      case 'TOUGH': return 'bg-orange-100 text-orange-800';
      case 'VERY_TOUGH': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'VERY_HIGH': return 'text-green-600';
      case 'HIGH': return 'text-emerald-600';
      case 'MEDIUM': return 'text-yellow-600';
      case 'LOW': return 'text-orange-600';
      case 'VERY_LOW': return 'text-red-600';
      default: return 'text-gray-500';
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto flex items-center justify-center py-20">
        <div className="text-gray-500">Loading pre-game strategies...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="p-4 bg-red-50 text-red-700 rounded-lg flex items-center space-x-2">
          <AlertCircle size={18} />
          <span>Failed to load pre-game strategies</span>
        </div>
      </div>
    );
  }

  // Strategy detail view
  if (selectedId && strategyDetail) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Back button */}
        <button
          onClick={() => setSelectedId(null)}
          className="flex items-center space-x-2 text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft size={18} />
          <span>Back to list</span>
        </button>

        {/* Header */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {strategyDetail.stake_level} Table Strategy
              </h1>
              <p className="text-sm text-gray-500">
                Created {formatDate(strategyDetail.created_at)}
                {strategyDetail.hand_number && ` • Hand #${strategyDetail.hand_number}`}
              </p>
            </div>
            <div className="flex items-center space-x-3">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getClassificationColor(strategyDetail.table_classification)}`}>
                {strategyDetail.table_classification.replace('_', ' ')}
              </span>
              <span className="text-2xl font-bold text-indigo-600">
                {strategyDetail.softness_score}/5.0
              </span>
            </div>
          </div>

          {strategyDetail.email_sent && (
            <div className="flex items-center space-x-2 text-green-600 text-sm">
              <MailCheck size={16} />
              <span>Strategy emailed {strategyDetail.email_sent_at ? formatDate(strategyDetail.email_sent_at) : ''}</span>
            </div>
          )}
        </div>

        {/* General Strategy */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">General Strategy</h2>

          <div className="bg-indigo-50 p-4 rounded-lg mb-4">
            <p className="text-gray-800">{strategyDetail.strategy.general_strategy.overview}</p>
          </div>

          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-3 mb-4">
            <p className="font-medium text-yellow-800">
              Key Principle: {strategyDetail.strategy.general_strategy.key_principle}
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <h3 className="font-medium text-gray-700 mb-2">Opening Adjustments</h3>
              <ul className="space-y-1">
                {strategyDetail.strategy.general_strategy.opening_adjustments.map((adj, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-start">
                    <span className="text-indigo-500 mr-2">•</span>
                    {adj}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="font-medium text-gray-700 mb-2">3-Bet Adjustments</h3>
              <ul className="space-y-1">
                {strategyDetail.strategy.general_strategy.three_bet_adjustments.map((adj, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-start">
                    <span className="text-indigo-500 mr-2">•</span>
                    {adj}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="font-medium text-gray-700 mb-2">Defense Adjustments</h3>
              <ul className="space-y-1">
                {strategyDetail.strategy.general_strategy.defense_adjustments.map((adj, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-start">
                    <span className="text-indigo-500 mr-2">•</span>
                    {adj}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Priority Actions */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Priority Actions</h2>
          <ol className="space-y-2">
            {strategyDetail.strategy.priority_actions.map((action, i) => (
              <li key={i} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                <span className="flex-shrink-0 w-6 h-6 bg-indigo-600 text-white rounded-full flex items-center justify-center text-sm font-medium">
                  {i + 1}
                </span>
                <span className="text-gray-800">{action}</span>
              </li>
            ))}
          </ol>
        </div>

        {/* Opponents */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Opponent Analysis ({strategyDetail.opponents.length} players)
          </h2>

          <div className="space-y-4">
            {strategyDetail.opponents.map((opp) => {
              const exploit = strategyDetail.strategy.opponent_exploits.find(e => e.name === opp.name);

              return (
                <div key={opp.name} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-3">
                      <span className="text-lg font-medium text-gray-900">
                        {opp.seat}. {opp.name}
                      </span>
                      <span className="text-sm text-gray-500">({opp.position})</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        opp.classification === 'UNKNOWN' ? 'bg-gray-100 text-gray-600' :
                        opp.classification === 'CALLING_STATION' ? 'bg-red-100 text-red-700' :
                        opp.classification === 'LOOSE_PASSIVE' ? 'bg-orange-100 text-orange-700' :
                        opp.classification === 'NIT' ? 'bg-blue-100 text-blue-700' :
                        opp.classification === 'TAG' ? 'bg-green-100 text-green-700' :
                        opp.classification === 'LAG' ? 'bg-purple-100 text-purple-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {opp.classification.replace('_', ' ')}
                      </span>
                    </div>
                    <span className={`text-sm ${getConfidenceColor(opp.confidence)}`}>
                      {opp.sample_size > 0 ? `${opp.sample_size} hands` : 'No data'}
                    </span>
                  </div>

                  <div className="grid grid-cols-4 gap-4 text-sm mb-3">
                    <div>
                      <span className="text-gray-500">VPIP</span>
                      <span className="ml-2 font-medium">{opp.stats.vpip?.toFixed(1) ?? 'N/A'}%</span>
                    </div>
                    <div>
                      <span className="text-gray-500">PFR</span>
                      <span className="ml-2 font-medium">{opp.stats.pfr?.toFixed(1) ?? 'N/A'}%</span>
                    </div>
                    <div>
                      <span className="text-gray-500">3-Bet</span>
                      <span className="ml-2 font-medium">{opp.stats.three_bet?.toFixed(1) ?? 'N/A'}%</span>
                    </div>
                    <div>
                      <span className="text-gray-500">F3B</span>
                      <span className="ml-2 font-medium">{opp.stats.fold_to_3bet?.toFixed(1) ?? 'N/A'}%</span>
                    </div>
                  </div>

                  {exploit && (
                    <div className="bg-indigo-50 p-3 rounded-lg">
                      <span className="text-indigo-800">{exploit.exploit}</span>
                    </div>
                  )}

                  {opp.population_tendencies && (
                    <div className="mt-2 text-sm text-gray-500">
                      <span className="font-medium">Population tendencies:</span>
                      <ul className="mt-1 space-y-0.5">
                        {opp.population_tendencies.map((t, i) => (
                          <li key={i}>• {t}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Delete button */}
        <div className="flex justify-end">
          <button
            onClick={() => {
              if (confirm('Delete this strategy?')) {
                deleteMutation.mutate(selectedId);
              }
            }}
            className="flex items-center space-x-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg"
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
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Pre-Game</h1>
        <p className="mt-1 text-gray-600">
          Table exploitation strategies generated from emailed hands
        </p>
      </div>

      {!strategies || strategies.length === 0 ? (
        <div className="card text-center py-12">
          <Target className="mx-auto text-gray-400 mb-4" size={48} />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No Pre-Game Strategies Yet</h2>
          <p className="text-gray-600 mb-4 max-w-md mx-auto">
            Email a single hand history to generate an AI-powered exploitation strategy for your table.
          </p>
          <div className="bg-gray-50 p-4 rounded-lg max-w-md mx-auto text-left">
            <p className="text-sm text-gray-700 mb-2">
              <strong>How it works:</strong>
            </p>
            <ol className="text-sm text-gray-600 space-y-1 list-decimal list-inside">
              <li>Copy a single hand from your poker client</li>
              <li>Email it to your import address</li>
              <li>Receive AI strategy for that table</li>
            </ol>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {strategies.map((strategy) => (
            <button
              key={strategy.id}
              onClick={() => setSelectedId(strategy.id)}
              className="w-full text-left card hover:border-indigo-300 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="flex-shrink-0">
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${getClassificationColor(strategy.table_classification)}`}>
                      <span className="text-lg font-bold">{strategy.softness_score}</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-gray-900">{strategy.stake_level}</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${getClassificationColor(strategy.table_classification)}`}>
                        {strategy.table_classification.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="flex items-center space-x-4 text-sm text-gray-500 mt-1">
                      <span className="flex items-center space-x-1">
                        <Clock size={14} />
                        <span>{formatDate(strategy.created_at)}</span>
                      </span>
                      <span className="flex items-center space-x-1">
                        <Users size={14} />
                        <span>{strategy.opponent_count} opponents</span>
                      </span>
                      <span className="flex items-center space-x-1">
                        <TrendingUp size={14} />
                        <span>{strategy.known_opponents} known</span>
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  {strategy.email_sent ? (
                    <MailCheck size={18} className="text-green-500" />
                  ) : (
                    <Mail size={18} className="text-gray-400" />
                  )}
                  <ChevronRight size={20} className="text-gray-400" />
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default PreGame;
