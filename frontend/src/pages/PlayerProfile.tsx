import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useRef, useMemo } from 'react';
import { ArrowLeft, TrendingUp, Target, Shield, Crosshair, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import PlayerBadge from '../components/PlayerBadge';
import StatCard from '../components/StatCard';
import { Tooltip } from '../components/Tooltip';
import MetricChart from '../components/MetricChart';
import PositionalVPIPChart from '../components/PositionalVPIPChart';
import PreflopAggressionChart from '../components/PreflopAggressionChart';
import ExploitDashboard from '../components/ExploitDashboard';
import BaselineComparison from '../components/BaselineComparison';
import DeviationHeatmap from '../components/DeviationHeatmap';
import { LeakSummary, LeaksList } from '../components/LeakCard';
import { STAT_DEFINITIONS, getStatDefinitionsWithGTO, GTOOptimalRange } from '../config/statDefinitions';

// Helper function to generate tooltip content for a statistic
// Now accepts statDefinitions as parameter for GTO-enhanced definitions
const createStatTooltip = (statDefinitions: Record<string, any>) => (statKey: string, value?: number) => {
  const def = statDefinitions[statKey];
  if (!def) return null;

  return (
    <div className="space-y-2 max-w-xs">
      <div>
        <div className="font-semibold text-blue-300">{def.name}</div>
        <div className="text-xs text-gray-300 mt-1">{def.description}</div>
      </div>

      {def.formula && (
        <div className="text-xs border-t border-gray-700 pt-2">
          <div className="text-gray-400">Formula:</div>
          <code className="text-gray-200 font-mono text-xs">{def.formula}</code>
        </div>
      )}

      {def.optimalRange && (
        <div className="text-xs border-t border-gray-700 pt-2">
          <div className="text-gray-400">Optimal Range (GTO):</div>
          <div className="text-green-300 font-medium">
            {def.optimalRange[0]}{def.unit} - {def.optimalRange[1]}{def.unit}
          </div>
        </div>
      )}

      {value !== undefined && def.optimalRange && (
        <div className="text-xs border-t border-gray-700 pt-2">
          <div className="text-gray-400">Current Value:</div>
          <div className={`font-medium ${
            value < def.optimalRange[0] ? 'text-yellow-300' :
            value > def.optimalRange[1] ? 'text-yellow-300' :
            'text-green-300'
          }`}>
            {value.toFixed(1)}{def.unit}
            {value < def.optimalRange[0] && ' (below optimal)'}
            {value > def.optimalRange[1] && ' (above optimal)'}
            {value >= def.optimalRange[0] && value <= def.optimalRange[1] && ' (optimal)'}
          </div>
        </div>
      )}
    </div>
  );
};

const PlayerProfile = () => {
  const { playerName } = useParams<{ playerName: string }>();
  const navigate = useNavigate();
  const baselineTableRef = useRef<HTMLDivElement>(null);

  const { data: player, isLoading, error } = useQuery({
    queryKey: ['player', playerName],
    queryFn: () => api.getPlayerProfile(playerName!),
    enabled: !!playerName,
  });

  // Fetch baseline/exploit analysis
  const { data: exploitAnalysis } = useQuery({
    queryKey: ['playerExploits', playerName],
    queryFn: () => api.analyzePlayerExploits(playerName!),
    enabled: !!playerName,
  });

  // Fetch leak analysis with confidence intervals
  const { data: leakAnalysis } = useQuery({
    queryKey: ['playerLeaks', playerName],
    queryFn: () => api.getPlayerLeaks(playerName!),
    enabled: !!playerName,
  });

  // Fetch GTO analysis (on-the-fly calculation)
  const { data: gtoAnalysis, isLoading: gtoLoading } = useQuery({
    queryKey: ['playerGTOAnalysis', playerName],
    queryFn: () => api.getPlayerGTOAnalysis(playerName!),
    enabled: !!playerName,
  });

  // Fetch GTO optimal ranges from database
  const { data: gtoRanges } = useQuery({
    queryKey: ['gtoOptimalRanges'],
    queryFn: () => api.getGTOOptimalRanges(),
    staleTime: 1000 * 60 * 60, // Cache for 1 hour - GTO data rarely changes
  });

  // Merge GTO ranges with default stat definitions
  const statDefinitions = useMemo(() => {
    if (!gtoRanges?.overall) return STAT_DEFINITIONS;
    return getStatDefinitionsWithGTO(gtoRanges.overall as unknown as Record<string, GTOOptimalRange>);
  }, [gtoRanges]);

  // Create tooltip function using merged definitions
  const getStatTooltipGTO = useMemo(
    () => createStatTooltip(statDefinitions),
    [statDefinitions]
  );

  // Scroll to baseline comparison table
  const scrollToBaselineTable = () => {
    baselineTableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading player profile...</p>
        </div>
      </div>
    );
  }

  if (error || !player) {
    return (
      <div className="card bg-red-50 border border-red-200">
        <p className="text-red-800">Error loading player profile</p>
      </div>
    );
  }

  // Prepare composite metrics for radar chart (preflop-focused)
  const compositeMetrics = [
    { metric: 'EI', value: player.exploitability_index ?? 0, fullMark: 100 },
    { metric: 'PAI', value: player.positional_awareness_index ?? 0, fullMark: 100 },
    { metric: 'BDE', value: player.blind_defense_efficiency ?? 0, fullMark: 100 },
    { metric: 'OSSR', value: player.optimal_stake_skill_rating ?? 0, fullMark: 100 },
  ];

  return (
    <div className="space-y-6">
      {/* Back button */}
      <button
        onClick={() => navigate('/players')}
        className="flex items-center space-x-2 text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft size={20} />
        <span>Back to players</span>
      </button>

      {/* Player header */}
      <div className="card">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{player.player_name}</h1>
            <div className="flex items-center space-x-4 mt-3">
              <PlayerBadge playerType={player.player_type || null} size="lg" />
              <span className="text-sm text-gray-500">
                {player.total_hands.toLocaleString()} hands
              </span>
            </div>
            {/* Generate Strategy Button */}
            <Link
              to={`/strategy?opponent=${encodeURIComponent(player.player_name)}`}
              className="inline-flex items-center space-x-2 mt-4 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg hover:from-purple-700 hover:to-indigo-700 transition-all shadow-md hover:shadow-lg"
            >
              <Crosshair size={18} />
              <span>Generate Strategy</span>
            </Link>
          </div>
          {player.exploitability_index !== null && player.exploitability_index !== undefined && (
            <div className="text-right">
              <div className="flex items-center justify-end gap-1">
                <p className="text-sm text-gray-600">Exploitability Index</p>
                <Tooltip content={getStatTooltipGTO('exploitability_index', player.exploitability_index)} position="bottom" iconSize={14} />
              </div>
              <p className="text-4xl font-bold text-gray-900 mt-1">
                {player.exploitability_index.toFixed(1)}
              </p>
              <p className={`text-sm font-medium mt-1 ${
                player.exploitability_index > 60
                  ? 'text-red-600'
                  : player.exploitability_index > 40
                  ? 'text-yellow-600'
                  : 'text-green-600'
              }`}>
                {player.exploitability_index > 60
                  ? 'Highly Exploitable'
                  : player.exploitability_index > 40
                  ? 'Moderately Exploitable'
                  : 'Difficult to Exploit'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Preflop Statistics */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Preflop Statistics</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            title="VPIP%"
            value={player.vpip_pct !== null && player.vpip_pct !== undefined ? `${player.vpip_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Voluntarily Put $ In Pot"
            color="blue"
            tooltip={getStatTooltipGTO('vpip_pct', player.vpip_pct ?? undefined)}
          />
          <StatCard
            title="PFR%"
            value={player.pfr_pct !== null && player.pfr_pct !== undefined ? `${player.pfr_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Pre-Flop Raise"
            color="green"
            tooltip={getStatTooltipGTO('pfr_pct', player.pfr_pct ?? undefined)}
          />
          <StatCard
            title="3-Bet%"
            value={player.three_bet_pct !== null && player.three_bet_pct !== undefined ? `${player.three_bet_pct.toFixed(1)}%` : 'N/A'}
            subtitle="3-Bet Percentage"
            color="yellow"
            tooltip={getStatTooltipGTO('three_bet_pct', player.three_bet_pct ?? undefined)}
          />
          <StatCard
            title="Fold to 3-Bet%"
            value={player.fold_to_three_bet_pct !== null && player.fold_to_three_bet_pct !== undefined ? `${player.fold_to_three_bet_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Fold to 3-Bet"
            color="red"
            tooltip={getStatTooltipGTO('fold_to_three_bet_pct', player.fold_to_three_bet_pct ?? undefined)}
          />
          <StatCard
            title="4-Bet%"
            value={player.four_bet_pct !== null && player.four_bet_pct !== undefined ? `${player.four_bet_pct.toFixed(1)}%` : 'N/A'}
            subtitle="4-Bet Percentage"
            color="blue"
            tooltip={getStatTooltipGTO('four_bet_pct', player.four_bet_pct ?? undefined)}
          />
          <StatCard
            title="Cold Call%"
            value={player.cold_call_pct !== null && player.cold_call_pct !== undefined ? `${player.cold_call_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Cold Call Percentage"
            color="green"
            tooltip={getStatTooltipGTO('cold_call_pct', player.cold_call_pct ?? undefined)}
          />
          <StatCard
            title="Limp%"
            value={player.limp_pct !== null && player.limp_pct !== undefined ? `${player.limp_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Limp Percentage"
            color="yellow"
            tooltip={getStatTooltipGTO('limp_pct', player.limp_pct ?? undefined)}
          />
          <StatCard
            title="BB/100"
            value={player.bb_per_100 !== null && player.bb_per_100 !== undefined ? `${player.bb_per_100.toFixed(1)}` : 'N/A'}
            subtitle="Big Blinds per 100 Hands"
            color={player.bb_per_100 !== null && player.bb_per_100 !== undefined && player.bb_per_100 > 0 ? 'green' : player.bb_per_100 !== null && player.bb_per_100 !== undefined && player.bb_per_100 < 0 ? 'red' : 'gray'}
            tooltip={getStatTooltipGTO('bb_per_100', player.bb_per_100 ?? undefined)}
          />
        </div>
      </div>

      {/* Leak Analysis Section */}
      {leakAnalysis && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="text-orange-500" size={24} />
            <h2 className="text-xl font-semibold text-gray-900">Leak Analysis</h2>
          </div>

          {/* Leak Summary */}
          <div className="mb-6">
            <LeakSummary
              totalLeaks={leakAnalysis.leak_summary.total_leaks}
              criticalLeaks={leakAnalysis.leak_summary.critical_leaks}
              majorLeaks={leakAnalysis.leak_summary.major_leaks}
              totalEvOpportunity={leakAnalysis.leak_summary.total_ev_opportunity}
              reliability={leakAnalysis.leak_summary.reliability}
            />
          </div>

          {/* Player Type Exploit Info */}
          {leakAnalysis.player_type && (
            <div className="card bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 mb-6">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-gray-900">
                  Player Profile: {leakAnalysis.player_type.type}
                </h3>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  leakAnalysis.player_type.confidence === 'high' ? 'bg-green-100 text-green-700' :
                  leakAnalysis.player_type.confidence === 'good' ? 'bg-green-100 text-green-700' :
                  leakAnalysis.player_type.confidence === 'moderate' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  {leakAnalysis.player_type.confidence} confidence ({leakAnalysis.player_type.sample_size} hands)
                </span>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <h4 className="text-xs font-semibold text-gray-600 uppercase mb-1">Stats</h4>
                  <div className="text-sm text-gray-700 space-y-1">
                    <div>VPIP: <span className="font-medium">{leakAnalysis.player_type.vpip?.toFixed(1) ?? 'N/A'}%</span></div>
                    <div>PFR: <span className="font-medium">{leakAnalysis.player_type.pfr?.toFixed(1) ?? 'N/A'}%</span></div>
                    <div>Aggression Ratio: <span className="font-medium">{leakAnalysis.player_type.aggression_ratio.toFixed(2)}</span></div>
                  </div>
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-gray-600 uppercase mb-1">How to Exploit</h4>
                  <ul className="text-sm text-gray-700 space-y-1">
                    {leakAnalysis.player_type.exploits.map((exploit, i) => (
                      <li key={i} className="flex items-start gap-1">
                        <span className="text-purple-500 mt-1">•</span>
                        <span>{exploit}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Core Metrics Summary */}
          {leakAnalysis.core_metrics && (
            <div className="mb-6">
              <div className="card">
                <h3 className="font-semibold text-gray-900 mb-4">Core Profile Summary</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {leakAnalysis.core_metrics.exploitability_score && (
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-2xl font-bold text-gray-900">
                        {leakAnalysis.core_metrics.exploitability_score.value?.toFixed(0) ?? 'N/A'}
                      </div>
                      <div className="text-xs text-gray-600 mt-1">Exploitability</div>
                      <div className={`text-xs mt-1 ${
                        leakAnalysis.core_metrics.exploitability_score.interpretation === 'very_exploitable' ? 'text-red-600' :
                        leakAnalysis.core_metrics.exploitability_score.interpretation === 'exploitable' ? 'text-orange-600' :
                        leakAnalysis.core_metrics.exploitability_score.interpretation === 'solid' ? 'text-yellow-600' :
                        'text-green-600'
                      }`}>
                        {leakAnalysis.core_metrics.exploitability_score.interpretation}
                      </div>
                    </div>
                  )}
                  {leakAnalysis.core_metrics.positional_awareness && (
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-lg font-bold text-gray-900 capitalize">
                        {leakAnalysis.core_metrics.positional_awareness.interpretation}
                      </div>
                      <div className="text-xs text-gray-600 mt-1">Position Awareness</div>
                    </div>
                  )}
                  {leakAnalysis.core_metrics.blind_defense && (
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-lg font-bold text-gray-900 capitalize">
                        {leakAnalysis.core_metrics.blind_defense.interpretation}
                      </div>
                      <div className="text-xs text-gray-600 mt-1">Blind Defense</div>
                    </div>
                  )}
                  {leakAnalysis.core_metrics.preflop_aggression && (
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-lg font-bold text-gray-900 capitalize">
                        {leakAnalysis.core_metrics.preflop_aggression.interpretation}
                      </div>
                      <div className="text-xs text-gray-600 mt-1">Preflop Aggression</div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Detailed Leaks List */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">Identified Leaks</h3>
            <LeaksList leaks={leakAnalysis.leaks} maxLeaks={10} />
          </div>
        </div>
      )}

      {/* GTO Analysis Section */}
      {(gtoAnalysis || gtoLoading) && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Target className="text-blue-500" size={24} />
            <h2 className="text-xl font-semibold text-gray-900">GTO Analysis</h2>
          </div>

          {gtoLoading ? (
            <div className="card">
              <div className="animate-pulse flex space-x-4">
                <div className="flex-1 space-y-4 py-1">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-200 rounded"></div>
                  <div className="h-4 bg-gray-200 rounded w-5/6"></div>
                </div>
              </div>
            </div>
          ) : gtoAnalysis && (
            <>
              {/* GTO Adherence Summary */}
              <div className="card bg-gradient-to-r from-blue-50 to-cyan-50 border border-blue-200 mb-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-900">GTO Adherence Score</h3>
                  <span className={`text-3xl font-bold ${
                    gtoAnalysis.adherence.gto_adherence_score >= 80 ? 'text-green-600' :
                    gtoAnalysis.adherence.gto_adherence_score >= 60 ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {gtoAnalysis.adherence.gto_adherence_score.toFixed(0)}%
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="bg-white/50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {gtoAnalysis.adherence.avg_deviation.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-600">Avg Deviation</div>
                  </div>
                  <div className="bg-white/50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {gtoAnalysis.adherence.major_leaks_count}
                    </div>
                    <div className="text-xs text-gray-600">Major Leaks</div>
                  </div>
                  <div className="bg-white/50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {gtoAnalysis.adherence.total_hands.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-600">Hands Analyzed</div>
                  </div>
                </div>
              </div>

              {/* Opening Ranges vs GTO */}
              {gtoAnalysis.opening_ranges && gtoAnalysis.opening_ranges.length > 0 && (
                <div className="card mb-6">
                  <h3 className="font-semibold text-gray-900 mb-4">Opening Ranges vs GTO</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left py-2 px-3 font-medium text-gray-600">Position</th>
                          <th className="text-right py-2 px-3 font-medium text-gray-600">Hands</th>
                          <th className="text-right py-2 px-3 font-medium text-gray-600">Player</th>
                          <th className="text-right py-2 px-3 font-medium text-gray-600">GTO</th>
                          <th className="text-right py-2 px-3 font-medium text-gray-600">Diff</th>
                          <th className="text-center py-2 px-3 font-medium text-gray-600">Leak</th>
                        </tr>
                      </thead>
                      <tbody>
                        {gtoAnalysis.opening_ranges.map((row: typeof gtoAnalysis.opening_ranges[number]) => (
                          <tr key={row.position} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="py-2 px-3 font-medium">{row.position}</td>
                            <td className="py-2 px-3 text-right text-gray-600">{row.total_hands}</td>
                            <td className="py-2 px-3 text-right">{row.player_frequency.toFixed(1)}%</td>
                            <td className="py-2 px-3 text-right text-blue-600">{row.gto_frequency.toFixed(1)}%</td>
                            <td className={`py-2 px-3 text-right font-medium ${
                              Math.abs(row.frequency_diff) < 5 ? 'text-green-600' :
                              Math.abs(row.frequency_diff) < 10 ? 'text-yellow-600' :
                              'text-red-600'
                            }`}>
                              {row.frequency_diff > 0 ? '+' : ''}{row.frequency_diff.toFixed(1)}%
                            </td>
                            <td className="py-2 px-3 text-center">
                              {row.leak_type ? (
                                <span className={`text-xs px-2 py-0.5 rounded-full ${
                                  row.leak_severity === 'major' ? 'bg-red-100 text-red-700' :
                                  row.leak_severity === 'moderate' ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-gray-100 text-gray-600'
                                }`}>
                                  {row.leak_type}
                                </span>
                              ) : (
                                <span className="text-xs text-green-600">✓ Optimal</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* 3-Bet Stats vs GTO */}
              {gtoAnalysis.threebet_stats && gtoAnalysis.threebet_stats.length > 0 && (
                <div className="card mb-6">
                  <h3 className="font-semibold text-gray-900 mb-4">3-Bet Frequency vs GTO</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left py-2 px-3 font-medium text-gray-600">Position</th>
                          <th className="text-right py-2 px-3 font-medium text-gray-600">Opportunities</th>
                          <th className="text-right py-2 px-3 font-medium text-gray-600">3-Bets</th>
                          <th className="text-right py-2 px-3 font-medium text-gray-600">Player</th>
                          <th className="text-right py-2 px-3 font-medium text-gray-600">GTO</th>
                          <th className="text-right py-2 px-3 font-medium text-gray-600">Diff</th>
                          <th className="text-center py-2 px-3 font-medium text-gray-600">Leak</th>
                        </tr>
                      </thead>
                      <tbody>
                        {gtoAnalysis.threebet_stats.map((row: typeof gtoAnalysis.threebet_stats[number]) => (
                          <tr key={row.position} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="py-2 px-3 font-medium">{row.position}</td>
                            <td className="py-2 px-3 text-right text-gray-600">{row.opportunities}</td>
                            <td className="py-2 px-3 text-right text-gray-600">{row.three_bets}</td>
                            <td className="py-2 px-3 text-right">{row.player_frequency.toFixed(1)}%</td>
                            <td className="py-2 px-3 text-right text-blue-600">{row.gto_frequency.toFixed(1)}%</td>
                            <td className={`py-2 px-3 text-right font-medium ${
                              Math.abs(row.frequency_diff) < 3 ? 'text-green-600' :
                              Math.abs(row.frequency_diff) < 6 ? 'text-yellow-600' :
                              'text-red-600'
                            }`}>
                              {row.frequency_diff > 0 ? '+' : ''}{row.frequency_diff.toFixed(1)}%
                            </td>
                            <td className="py-2 px-3 text-center">
                              {row.leak_type ? (
                                <span className={`text-xs px-2 py-0.5 rounded-full ${
                                  row.leak_severity === 'major' ? 'bg-red-100 text-red-700' :
                                  row.leak_severity === 'moderate' ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-gray-100 text-gray-600'
                                }`}>
                                  {row.leak_type}
                                </span>
                              ) : (
                                <span className="text-xs text-green-600">✓ Optimal</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Fold to 3-Bet Summary */}
              {gtoAnalysis.fold_to_3bet && gtoAnalysis.fold_to_3bet.faced_3bet > 0 && (
                <div className="card">
                  <h3 className="font-semibold text-gray-900 mb-4">Fold to 3-Bet Analysis</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-2xl font-bold text-gray-900">
                        {gtoAnalysis.fold_to_3bet.faced_3bet}
                      </div>
                      <div className="text-xs text-gray-600">Faced 3-Bet</div>
                    </div>
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-2xl font-bold text-gray-900">
                        {gtoAnalysis.fold_to_3bet.folded}
                      </div>
                      <div className="text-xs text-gray-600">Folded</div>
                    </div>
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className={`text-2xl font-bold ${
                        Math.abs(gtoAnalysis.fold_to_3bet.frequency_diff) < 5 ? 'text-green-600' :
                        Math.abs(gtoAnalysis.fold_to_3bet.frequency_diff) < 10 ? 'text-yellow-600' :
                        'text-red-600'
                      }`}>
                        {gtoAnalysis.fold_to_3bet.player_frequency.toFixed(1)}%
                      </div>
                      <div className="text-xs text-gray-600">Player Fold %</div>
                    </div>
                    <div className="text-center p-3 bg-blue-50 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {gtoAnalysis.fold_to_3bet.gto_frequency.toFixed(1)}%
                      </div>
                      <div className="text-xs text-gray-600">GTO Fold %</div>
                    </div>
                  </div>
                  {Math.abs(gtoAnalysis.fold_to_3bet.frequency_diff) > 5 && (
                    <div className={`mt-4 p-3 rounded-lg ${
                      gtoAnalysis.fold_to_3bet.frequency_diff > 0 ? 'bg-red-50 text-red-700' : 'bg-yellow-50 text-yellow-700'
                    }`}>
                      <strong>Leak:</strong> {gtoAnalysis.fold_to_3bet.frequency_diff > 0
                        ? `Folds ${gtoAnalysis.fold_to_3bet.frequency_diff.toFixed(1)}% too often. Exploit: 3-bet wider for folds.`
                        : `Folds ${Math.abs(gtoAnalysis.fold_to_3bet.frequency_diff).toFixed(1)}% too rarely. Play value-heavy vs their 3-bet defense.`
                      }
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Visual Analytics Section */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Preflop Analytics</h2>

        {/* Preflop and Positional Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PreflopAggressionChart
            vpip_pct={player.vpip_pct}
            pfr_pct={player.pfr_pct}
            three_bet_pct={player.three_bet_pct}
            limp_pct={player.limp_pct}
          />
          <PositionalVPIPChart
            vpip_utg={player.vpip_utg}
            vpip_hj={player.vpip_hj}
            vpip_mp={player.vpip_mp}
            vpip_co={player.vpip_co}
            vpip_btn={player.vpip_btn}
            vpip_sb={player.vpip_sb}
            vpip_bb={player.vpip_bb}
          />
        </div>
      </div>

      {/* Exploit Analysis Section */}
      {exploitAnalysis && exploitAnalysis.analyses && exploitAnalysis.analyses.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Exploit Analysis</h2>

          {/* Exploit Dashboard Summary */}
          <div className="mb-6">
            <ExploitDashboard
              deviations={
                exploitAnalysis.analyses
                  .filter(a => a.comparison_type === 'baseline' || a.scenario === 'Poker Theory Baselines')
                  .flatMap(a => a.deviations)
              }
              playerName={player.player_name}
              onViewDetails={scrollToBaselineTable}
            />
          </div>

          {/* Deviation Heatmap */}
          <div className="mb-6">
            <DeviationHeatmap
              deviations={
                exploitAnalysis.analyses
                  .filter(a => a.comparison_type === 'baseline' || a.scenario === 'Poker Theory Baselines')
                  .flatMap(a => a.deviations)
              }
              playerName={player.player_name}
            />
          </div>

          {/* Baseline Comparison Table */}
          <div ref={baselineTableRef}>
            <BaselineComparison
              deviations={
                exploitAnalysis.analyses
                  .filter(a => a.comparison_type === 'baseline' || a.scenario === 'Poker Theory Baselines')
                  .flatMap(a => a.deviations)
              }
              playerName={player.player_name}
            />
          </div>
        </div>
      )}

      {/* Composite metrics chart */}
      <MetricChart
        data={compositeMetrics}
        title="Composite Metrics Overview"
      />

      {/* Preflop Composite Metrics */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Preflop Composite Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StatCard
            title="Positional Awareness Index"
            value={player.positional_awareness_index !== null && player.positional_awareness_index !== undefined ? player.positional_awareness_index.toFixed(1) : 'N/A'}
            subtitle="Position-specific play quality"
            icon={<Target size={24} />}
            color="yellow"
            tooltip={getStatTooltipGTO('positional_awareness_index', player.positional_awareness_index ?? undefined)}
          />
          <StatCard
            title="Blind Defense Efficiency"
            value={player.blind_defense_efficiency !== null && player.blind_defense_efficiency !== undefined ? player.blind_defense_efficiency.toFixed(1) : 'N/A'}
            subtitle="Quality of blind defense"
            icon={<Shield size={24} />}
            color="blue"
            tooltip={getStatTooltipGTO('blind_defense_efficiency', player.blind_defense_efficiency ?? undefined)}
          />
          <StatCard
            title="Optimal Stake Rating"
            value={player.optimal_stake_skill_rating !== null && player.optimal_stake_skill_rating !== undefined ? player.optimal_stake_skill_rating.toFixed(1) : 'N/A'}
            subtitle="Skill level assessment"
            icon={<TrendingUp size={24} />}
            color="green"
            tooltip={getStatTooltipGTO('optimal_stake_skill_rating', player.optimal_stake_skill_rating ?? undefined)}
          />
        </div>
      </div>

      {/* Ask Claude button */}
      <div className="card bg-gradient-to-br from-purple-50 to-indigo-50 border border-purple-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              Get AI Analysis
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              Ask Claude AI for strategic recommendations on how to exploit {player.player_name}
            </p>
          </div>
          <button
            onClick={() => navigate(`/claude?player=${encodeURIComponent(player.player_name)}`)}
            className="btn-primary"
          >
            Ask Claude
          </button>
        </div>
      </div>
    </div>
  );
};

export default PlayerProfile;
