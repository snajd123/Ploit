import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Target,
  TrendingDown,
  AlertCircle,
  Award,
  BarChart3,
  ChevronRight,
  Shield,
  Zap,
  Info
} from 'lucide-react';
import SinglePlayerAutocomplete from '../components/SinglePlayerAutocomplete';
import { Tooltip } from '../components/Tooltip';

interface GTODashboardData {
  player: string;
  adherence: {
    gto_adherence_score: number;
    avg_ev_loss_per_hand: number;
    total_ev_loss_bb: number;
    major_leaks_count: number;
    scenarios_analyzed: number;
    total_hands: number;
  };
  opening_ranges: Array<{
    position: string;
    total_hands: number;
    player_frequency: number;
    gto_frequency: number;
    frequency_diff: number;
    leak_severity: string;
    ev_loss_bb: number;
  }>;
  defense_stats: Array<{
    scenario_name: string;
    total_hands: number;
    player_frequency: number;
    gto_frequency: number;
    frequency_diff: number;
    leak_type: string;
    leak_severity: string;
  }>;
  threebet_stats: Array<{
    scenario_name: string;
    position: string;
    vs_position: string;
    total_hands: number;
    player_frequency: number;
    gto_frequency: number;
    frequency_diff: number;
    leak_type: string;
    leak_severity: string;
  }>;
  top_leaks: Array<{
    scenario_name: string;
    category: string;
    total_hands: number;
    player_frequency: number;
    gto_frequency: number;
    frequency_diff: number;
    total_ev_loss_bb: number;
    leak_type: string;
    leak_severity: string;
  }>;
}

const GTOAnalysis = () => {
  const [selectedPlayer, setSelectedPlayer] = useState<string>('');
  const [searchValue, setSearchValue] = useState<string>('');

  // Auto-load hero name from localStorage on mount
  useEffect(() => {
    const savedHeroName = localStorage.getItem('poker-hero-name');
    if (savedHeroName && !selectedPlayer) {
      setSelectedPlayer(savedHeroName);
      setSearchValue(savedHeroName);
    }
  }, []);

  const formatScenarioName = (scenarioName: string): string => {
    // Convert "SB_vs_BTN_fold" to "SB vs BTN - Fold"
    // Convert "UTG_open" to "UTG Open"
    return scenarioName
      .replace(/_/g, ' ')
      .split(' ')
      .map((word, idx, arr) => {
        if (word === 'vs') return 'vs';
        if (idx === arr.length - 1 && ['fold', 'call', 'raise', '3bet', 'open'].includes(word)) {
          return '- ' + word.charAt(0).toUpperCase() + word.slice(1);
        }
        return word.toUpperCase();
      })
      .join(' ');
  };

  const getScenarioExplanation = (scenarioName: string, category: string): string => {
    const explanations: Record<string, string> = {
      'open': 'How often you raise first in (RFI) from this position',
      'defense': 'How you respond when facing a raise',
      'multiway': 'How you play when there are already callers or raises',
      'facing_3bet': 'How you respond to a 3-bet',
    };

    const actions: Record<string, string> = {
      'fold': 'Folding frequency in this spot',
      'call': 'Calling frequency in this spot',
      '3bet': '3-betting frequency in this spot',
      'open': 'Opening raise frequency from this position',
    };

    const parts = scenarioName.split('_');
    const action = parts[parts.length - 1];

    const categoryExplanation = explanations[category] || 'Poker scenario';
    const actionExplanation = actions[action] || '';

    return actionExplanation || categoryExplanation;
  };

  const { data, isLoading, error } = useQuery<GTODashboardData>({
    queryKey: ['gtoDashboard', selectedPlayer],
    queryFn: async () => {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      const response = await fetch(`${apiUrl}/api/gto/dashboard/${selectedPlayer}`);
      if (!response.ok) throw new Error('Failed to fetch GTO data');
      return response.json();
    },
    enabled: !!selectedPlayer,
  });

  const getScoreGradient = (score: number) => {
    if (score >= 80) return 'from-green-500 to-emerald-600';
    if (score >= 60) return 'from-blue-500 to-cyan-600';
    if (score >= 40) return 'from-yellow-500 to-amber-600';
    if (score >= 20) return 'from-orange-500 to-red-500';
    return 'from-red-500 to-rose-600';
  };

  const getScoreRating = (score: number) => {
    if (score >= 80) return '⭐⭐⭐⭐⭐ Excellent';
    if (score >= 60) return '⭐⭐⭐⭐ Good';
    if (score >= 40) return '⭐⭐⭐ Average';
    if (score >= 20) return '⭐⭐ Below Average';
    return '⭐ Needs Improvement';
  };

  const getSeverityBadge = (severity: string) => {
    const badges = {
      major: <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-900/50 text-red-300 border border-red-700">🔴 Major</span>,
      moderate: <span className="px-2 py-1 text-xs font-semibold rounded-full bg-yellow-900/50 text-yellow-300 border border-yellow-700">🟡 Moderate</span>,
      minor: <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-900/50 text-green-300 border border-green-700">🟢 Minor</span>,
    };
    return badges[severity as keyof typeof badges] || badges.minor;
  };

  if (!selectedPlayer) {
    return (
      <div className="p-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-purple-500 to-pink-600 mb-4">
              <Target className="w-10 h-10 text-white" />
            </div>
            <h1 className="text-4xl font-bold text-white mb-2">GTO Analysis</h1>
            <p className="text-gray-400 text-lg">
              Compare your play to Game Theory Optimal strategy
            </p>
          </div>

          <div className="bg-gray-800/50 backdrop-blur rounded-xl p-8 border border-gray-700">
            <label className="block text-sm font-medium text-gray-300 mb-3">
              Select Player to Analyze
            </label>
            <SinglePlayerAutocomplete
              value={searchValue}
              onChange={setSearchValue}
              onSelect={setSelectedPlayer}
              placeholder="Search for a player..."
              className="w-full"
            />

            <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="flex items-start space-x-3 p-4 bg-blue-900/20 rounded-lg border border-blue-800/30">
                <Shield className="w-6 h-6 text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-white mb-1">Overall Adherence</h3>
                  <p className="text-sm text-gray-400">See how closely you follow GTO strategy</p>
                </div>
              </div>

              <div className="flex items-start space-x-3 p-4 bg-purple-900/20 rounded-lg border border-purple-800/30">
                <Target className="w-6 h-6 text-purple-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-white mb-1">Identify Leaks</h3>
                  <p className="text-sm text-gray-400">Discover your biggest strategic mistakes</p>
                </div>
              </div>

              <div className="flex items-start space-x-3 p-4 bg-green-900/20 rounded-lg border border-green-800/30">
                <BarChart3 className="w-6 h-6 text-green-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-white mb-1">Track Progress</h3>
                  <p className="text-sm text-gray-400">Monitor improvements over time</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-purple-500 mx-auto"></div>
          <p className="mt-4 text-gray-400 font-medium">Analyzing GTO data...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <div className="max-w-2xl mx-auto">
          <div className="bg-red-900/20 border border-red-700 rounded-lg p-6">
            <div className="flex items-center space-x-3 mb-3">
              <AlertCircle className="w-6 h-6 text-red-400" />
              <h3 className="text-lg font-semibold text-white">No GTO Data Available</h3>
            </div>
            <p className="text-gray-300 mb-4">
              No GTO analysis data found for {selectedPlayer}. Make sure the player has enough hands analyzed.
            </p>
            <button
              onClick={() => setSelectedPlayer('')}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              Select Different Player
            </button>
          </div>
        </div>
      </div>
    );
  }

  const { adherence, opening_ranges, defense_stats, threebet_stats, top_leaks } = data;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => setSelectedPlayer('')}
            className="text-gray-400 hover:text-white transition-colors mb-2 flex items-center space-x-1 text-sm"
          >
            <ChevronRight className="w-4 h-4 rotate-180" />
            <span>Change Player</span>
          </button>
          <h1 className="text-3xl font-bold text-white">GTO Analysis: {selectedPlayer}</h1>
          <p className="text-gray-400 mt-1">{adherence.total_hands} hands analyzed across {adherence.scenarios_analyzed} scenarios</p>
        </div>
      </div>

      {/* Overall Score Card */}
      <div className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${getScoreGradient(adherence.gto_adherence_score)} p-8 text-white shadow-2xl border-2 border-white/20`}>
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/20 rounded-full -translate-y-32 translate-x-32"></div>
        <div className="relative z-10">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-3 mb-2">
                <Award className="w-8 h-8" />
                <h2 className="text-2xl font-bold">GTO Adherence Score</h2>
              </div>
              <div className="text-6xl font-bold mb-2">
                {adherence.gto_adherence_score.toFixed(1)}
                <span className="text-3xl ml-2">/ 100</span>
              </div>
              <div className="text-xl opacity-90">{getScoreRating(adherence.gto_adherence_score)}</div>
            </div>
            <div className="text-right space-y-3">
              <div>
                <div className="text-sm opacity-75">Total EV Loss</div>
                <div className="text-2xl font-bold">
                  {adherence.total_ev_loss_bb.toFixed(2)} BB
                </div>
              </div>
              <div>
                <div className="text-sm opacity-75">Avg Loss per Hand</div>
                <div className="text-2xl font-bold">
                  {adherence.avg_ev_loss_per_hand.toFixed(3)} BB
                </div>
              </div>
              {adherence.major_leaks_count > 0 && (
                <div className="inline-flex items-center space-x-2 px-4 py-2 bg-white/20 rounded-full">
                  <AlertCircle className="w-5 h-5" />
                  <span className="font-semibold">{adherence.major_leaks_count} Major Leaks</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Opening Ranges */}
      <div className="bg-slate-900 rounded-xl border border-blue-500/30 overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <BarChart3 className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-bold text-white">Opening Ranges (RFI)</h2>
          </div>
          <Tooltip content="Raise First In - How often you open from each position">
            <Info className="w-5 h-5 text-gray-400 hover:text-gray-300 cursor-help" />
          </Tooltip>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
            {opening_ranges.map((range) => (
              <div
                key={range.position}
                className="bg-slate-800 rounded-lg p-4 border border-slate-600 hover:border-blue-400 transition-all shadow-lg"
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-bold text-white">{range.position}</h3>
                  {getSeverityBadge(range.leak_severity)}
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-300">Your %:</span>
                    <span className="font-semibold text-white">{range.player_frequency.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">GTO %:</span>
                    <span className="font-semibold text-blue-300">{range.gto_frequency.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Diff:</span>
                    <span className={`font-semibold ${range.frequency_diff > 0 ? 'text-red-400' : range.frequency_diff < 0 ? 'text-yellow-400' : 'text-green-400'}`}>
                      {range.frequency_diff > 0 ? '+' : ''}{range.frequency_diff.toFixed(1)}%
                    </span>
                  </div>
                  <div className="pt-2 border-t border-slate-600">
                    <div className="flex justify-between">
                      <span className="text-gray-300">Hands:</span>
                      <span className="text-gray-200">{range.total_hands}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">EV Loss:</span>
                      <span className="text-red-400 font-medium">{range.ev_loss_bb.toFixed(2)} BB</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 3-Bet Stats */}
      {threebet_stats.length > 0 && (
        <div className="bg-slate-900 rounded-xl border border-purple-500/30 overflow-hidden shadow-xl">
          <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Zap className="w-6 h-6 text-purple-400" />
              <h2 className="text-xl font-bold text-white">3-Bet Frequencies</h2>
            </div>
            <Tooltip content="How often you 3-bet when facing a raise">
              <Info className="w-5 h-5 text-gray-400 hover:text-gray-300 cursor-help" />
            </Tooltip>
          </div>
          <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {threebet_stats.slice(0, 9).map((stat, idx) => (
              <div key={idx} className="bg-slate-800 rounded-lg p-4 border border-slate-600 hover:border-purple-400 transition-all shadow-lg">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex-1">
                    <h3 className="text-sm font-bold text-white">{stat.position} vs {stat.vs_position}</h3>
                    <p className="text-xs text-gray-400 mt-0.5">3-betting vs {stat.vs_position} open</p>
                  </div>
                  {getSeverityBadge(stat.leak_severity)}
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-300">Your %:</span>
                    <span className="font-semibold text-white">{stat.player_frequency.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">GTO %:</span>
                    <span className="font-semibold text-purple-300">{stat.gto_frequency.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Diff:</span>
                    <span className={`font-semibold ${stat.frequency_diff > 0 ? 'text-red-400' : stat.frequency_diff < 0 ? 'text-yellow-400' : 'text-green-400'}`}>
                      {stat.frequency_diff > 0 ? '+' : ''}{stat.frequency_diff.toFixed(1)}%
                    </span>
                  </div>
                  <div className="pt-2 border-t border-slate-600">
                    <div className="flex justify-between">
                      <span className="text-gray-300">Hands:</span>
                      <span className="text-gray-200">{stat.total_hands}</span>
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {stat.leak_type === 'over3bet' && '⚠️ 3-betting too often'}
                      {stat.leak_type === 'under3bet' && '⚠️ 3-betting too rarely'}
                      {!stat.leak_type && 'No significant leak'}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Leaks */}
      <div className="bg-slate-900 rounded-xl border border-red-500/30 overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <TrendingDown className="w-6 h-6 text-red-400" />
            <h2 className="text-xl font-bold text-white">Top Leaks (by EV Loss)</h2>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-800/80">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">#</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Scenario</th>
                <th className="px-6 py-3 text-center text-xs font-semibold text-gray-300 uppercase tracking-wider">Severity</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-300 uppercase tracking-wider">Hands</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-300 uppercase tracking-wider">Your %</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-300 uppercase tracking-wider">GTO %</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-300 uppercase tracking-wider">Diff</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-300 uppercase tracking-wider">EV Loss</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {top_leaks.map((leak, idx) => (
                <tr key={idx} className="hover:bg-slate-800/50 transition-colors">
                  <td className="px-6 py-4 text-gray-200 font-medium">{idx + 1}</td>
                  <td className="px-6 py-4">
                    <div className="text-white font-medium">{formatScenarioName(leak.scenario_name)}</div>
                    <div className="text-xs text-gray-300">{getScenarioExplanation(leak.scenario_name, leak.category)}</div>
                  </td>
                  <td className="px-6 py-4 text-center">
                    {getSeverityBadge(leak.leak_severity)}
                  </td>
                  <td className="px-6 py-4 text-right text-gray-200">{leak.total_hands}</td>
                  <td className="px-6 py-4 text-right text-white font-medium">{leak.player_frequency.toFixed(1)}%</td>
                  <td className="px-6 py-4 text-right text-blue-300 font-medium">{leak.gto_frequency.toFixed(1)}%</td>
                  <td className={`px-6 py-4 text-right font-semibold ${leak.frequency_diff > 0 ? 'text-red-400' : 'text-yellow-400'}`}>
                    {leak.frequency_diff > 0 ? '+' : ''}{leak.frequency_diff.toFixed(1)}%
                  </td>
                  <td className="px-6 py-4 text-right text-red-400 font-bold">
                    {leak.total_ev_loss_bb.toFixed(2)} BB
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Defense Stats */}
      {defense_stats.length > 0 && (
        <div className="bg-slate-900 rounded-xl border border-green-500/30 overflow-hidden shadow-xl">
          <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Shield className="w-6 h-6 text-green-400" />
              <h2 className="text-xl font-bold text-white">Defense Scenarios</h2>
            </div>
            <span className="text-sm text-gray-300">{defense_stats.length} scenarios</span>
          </div>
          <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            {defense_stats.slice(0, 6).map((stat, idx) => (
              <div key={idx} className="bg-slate-800 rounded-lg p-4 border border-slate-600 hover:border-green-400 transition-all shadow-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex-1">
                    <h3 className="text-sm font-semibold text-white">{formatScenarioName(stat.scenario_name)}</h3>
                    <p className="text-xs text-gray-400 mt-0.5">{getScenarioExplanation(stat.scenario_name, 'defense')}</p>
                  </div>
                  {getSeverityBadge(stat.leak_severity)}
                </div>
                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div>
                    <div className="text-gray-300 mb-1">Your %</div>
                    <div className="font-semibold text-white">{stat.player_frequency.toFixed(1)}%</div>
                  </div>
                  <div>
                    <div className="text-gray-300 mb-1">GTO %</div>
                    <div className="font-semibold text-green-300">{stat.gto_frequency.toFixed(1)}%</div>
                  </div>
                  <div>
                    <div className="text-gray-300 mb-1">Diff</div>
                    <div className={`font-semibold ${stat.frequency_diff > 0 ? 'text-red-400' : 'text-yellow-400'}`}>
                      {stat.frequency_diff > 0 ? '+' : ''}{stat.frequency_diff.toFixed(1)}%
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 rounded-xl border border-blue-700/50 p-6">
        <div className="flex items-start space-x-4">
          <div className="flex-shrink-0">
            <Zap className="w-8 h-8 text-yellow-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-bold text-white mb-3">Key Recommendations</h3>
            <ul className="space-y-2 text-gray-300">
              {adherence.major_leaks_count > 0 && (
                <li className="flex items-start space-x-2">
                  <ChevronRight className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                  <span>Focus on fixing your {adherence.major_leaks_count} major leaks first - they're costing you the most EV</span>
                </li>
              )}
              {opening_ranges.some(r => Math.abs(r.frequency_diff) > 15) && (
                <li className="flex items-start space-x-2">
                  <ChevronRight className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                  <span>Review your opening ranges - some positions show significant deviations from GTO</span>
                </li>
              )}
              <li className="flex items-start space-x-2">
                <ChevronRight className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                <span>Track your progress by running this analysis again after 100+ hands</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GTOAnalysis;
