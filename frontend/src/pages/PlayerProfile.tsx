import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useState, useMemo } from 'react';
import { ArrowLeft, TrendingUp, Target, Shield, Crosshair, AlertTriangle, BarChart3, User } from 'lucide-react';
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

type TabId = 'overview' | 'gto' | 'leaks' | 'charts';

const tabs: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Overview', icon: User },
  { id: 'gto', label: 'GTO Analysis', icon: Target },
  { id: 'leaks', label: 'Leaks', icon: AlertTriangle },
  { id: 'charts', label: 'Charts', icon: BarChart3 },
];

// Helper to get diff color
const getDiffColor = (diff: number, threshold: number = 5) => {
  const absDiff = Math.abs(diff);
  if (absDiff < threshold) return 'text-green-600';
  if (absDiff < threshold * 2) return 'text-yellow-600';
  return 'text-red-600';
};

// Helper to format diff with sign
const formatDiff = (diff: number) => {
  return diff > 0 ? `+${diff.toFixed(1)}%` : `${diff.toFixed(1)}%`;
};

// Helper function to generate tooltip content for a statistic
const createStatTooltip = (statDefinitions: Record<string, any>) => (statKey: string, value?: number) => {
  const def = statDefinitions[statKey];
  if (!def) return null;

  return (
    <div className="space-y-2 max-w-xs">
      <div>
        <div className="font-semibold text-blue-300">{def.name}</div>
        <div className="text-xs text-gray-300 mt-1">{def.description}</div>
      </div>
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
          </div>
        </div>
      )}
    </div>
  );
};

// GTO Scenario Table Component
const GTOScenarioTable = ({
  title,
  data,
  columns
}: {
  title: string;
  data: any[];
  columns: { key: string; label: string; isPlayer?: boolean; isGTO?: boolean; isDiff?: boolean }[]
}) => {
  if (!data || data.length === 0) return null;

  return (
    <div className="card mb-6">
      <h3 className="font-semibold text-gray-900 mb-4">{title}</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              {columns.map(col => (
                <th key={col.key} className={`py-2 px-3 font-medium ${
                  col.isGTO ? 'text-blue-600 bg-blue-50' :
                  col.isDiff ? 'text-gray-600' : 'text-gray-600'
                } ${col.key === 'position' ? 'text-left' : 'text-right'}`}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, idx) => (
              <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                {columns.map(col => {
                  const value = row[col.key];
                  const isPosition = col.key === 'position';
                  const isSampleSize = col.key === 'sample_size' || col.key === 'total_hands';

                  if (col.isDiff) {
                    return (
                      <td key={col.key} className={`py-2 px-3 text-right font-medium ${getDiffColor(value)}`}>
                        {formatDiff(value)}
                      </td>
                    );
                  }

                  return (
                    <td key={col.key} className={`py-2 px-3 ${
                      isPosition ? 'font-medium' :
                      isSampleSize ? 'text-right text-gray-500' :
                      col.isGTO ? 'text-right text-blue-600 bg-blue-50/50' :
                      'text-right'
                    }`}>
                      {typeof value === 'number' && !isSampleSize ? `${value.toFixed(1)}%` : value}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const PlayerProfile = () => {
  const { playerName } = useParams<{ playerName: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  const { data: player, isLoading, error } = useQuery({
    queryKey: ['player', playerName],
    queryFn: () => api.getPlayerProfile(playerName!),
    enabled: !!playerName,
  });

  const { data: exploitAnalysis } = useQuery({
    queryKey: ['playerExploits', playerName],
    queryFn: () => api.analyzePlayerExploits(playerName!),
    enabled: !!playerName,
  });

  const { data: leakAnalysis } = useQuery({
    queryKey: ['playerLeaks', playerName],
    queryFn: () => api.getPlayerLeaks(playerName!),
    enabled: !!playerName,
  });

  const { data: gtoAnalysis, isLoading: gtoLoading } = useQuery({
    queryKey: ['playerGTOAnalysis', playerName],
    queryFn: () => api.getPlayerGTOAnalysis(playerName!),
    enabled: !!playerName,
  });

  const { data: gtoRanges } = useQuery({
    queryKey: ['gtoOptimalRanges'],
    queryFn: () => api.getGTOOptimalRanges(),
    staleTime: 1000 * 60 * 60,
  });

  const statDefinitions = useMemo(() => {
    if (!gtoRanges?.overall) return STAT_DEFINITIONS;
    return getStatDefinitionsWithGTO(gtoRanges.overall as unknown as Record<string, GTOOptimalRange>);
  }, [gtoRanges]);

  const getStatTooltipGTO = useMemo(
    () => createStatTooltip(statDefinitions),
    [statDefinitions]
  );

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

      {/* Player header (always visible) */}
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
                player.exploitability_index > 60 ? 'text-red-600' :
                player.exploitability_index > 40 ? 'text-yellow-600' : 'text-green-600'
              }`}>
                {player.exploitability_index > 60 ? 'Highly Exploitable' :
                 player.exploitability_index > 40 ? 'Moderately Exploitable' : 'Difficult to Exploit'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-1" aria-label="Tabs">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-colors ${
                  isActive
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon size={18} />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Preflop Statistics */}
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Preflop Statistics</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  title="VPIP%"
                  value={player.vpip_pct != null ? `${player.vpip_pct.toFixed(1)}%` : 'N/A'}
                  subtitle="Voluntarily Put $ In Pot"
                  color="blue"
                  tooltip={getStatTooltipGTO('vpip_pct', player.vpip_pct ?? undefined)}
                />
                <StatCard
                  title="PFR%"
                  value={player.pfr_pct != null ? `${player.pfr_pct.toFixed(1)}%` : 'N/A'}
                  subtitle="Pre-Flop Raise"
                  color="green"
                  tooltip={getStatTooltipGTO('pfr_pct', player.pfr_pct ?? undefined)}
                />
                <StatCard
                  title="3-Bet%"
                  value={player.three_bet_pct != null ? `${player.three_bet_pct.toFixed(1)}%` : 'N/A'}
                  subtitle="3-Bet Percentage"
                  color="yellow"
                  tooltip={getStatTooltipGTO('three_bet_pct', player.three_bet_pct ?? undefined)}
                />
                <StatCard
                  title="Fold to 3-Bet%"
                  value={player.fold_to_three_bet_pct != null ? `${player.fold_to_three_bet_pct.toFixed(1)}%` : 'N/A'}
                  subtitle="Fold to 3-Bet"
                  color="red"
                  tooltip={getStatTooltipGTO('fold_to_three_bet_pct', player.fold_to_three_bet_pct ?? undefined)}
                />
                <StatCard
                  title="4-Bet%"
                  value={player.four_bet_pct != null ? `${player.four_bet_pct.toFixed(1)}%` : 'N/A'}
                  subtitle="4-Bet Percentage"
                  color="blue"
                  tooltip={getStatTooltipGTO('four_bet_pct', player.four_bet_pct ?? undefined)}
                />
                <StatCard
                  title="Cold Call%"
                  value={player.cold_call_pct != null ? `${player.cold_call_pct.toFixed(1)}%` : 'N/A'}
                  subtitle="Cold Call Percentage"
                  color="green"
                  tooltip={getStatTooltipGTO('cold_call_pct', player.cold_call_pct ?? undefined)}
                />
                <StatCard
                  title="Limp%"
                  value={player.limp_pct != null ? `${player.limp_pct.toFixed(1)}%` : 'N/A'}
                  subtitle="Limp Percentage"
                  color="yellow"
                  tooltip={getStatTooltipGTO('limp_pct', player.limp_pct ?? undefined)}
                />
                <StatCard
                  title="BB/100"
                  value={player.bb_per_100 != null ? `${player.bb_per_100.toFixed(1)}` : 'N/A'}
                  subtitle="Big Blinds per 100 Hands"
                  color={player.bb_per_100 != null && player.bb_per_100 > 0 ? 'green' : player.bb_per_100 != null && player.bb_per_100 < 0 ? 'red' : 'gray'}
                  tooltip={getStatTooltipGTO('bb_per_100', player.bb_per_100 ?? undefined)}
                />
              </div>
            </div>

            {/* Composite Metrics */}
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Composite Metrics</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard
                  title="Positional Awareness"
                  value={player.positional_awareness_index != null ? player.positional_awareness_index.toFixed(1) : 'N/A'}
                  subtitle="Position-specific play quality"
                  icon={<Target size={24} />}
                  color="yellow"
                  tooltip={getStatTooltipGTO('positional_awareness_index', player.positional_awareness_index ?? undefined)}
                />
                <StatCard
                  title="Blind Defense"
                  value={player.blind_defense_efficiency != null ? player.blind_defense_efficiency.toFixed(1) : 'N/A'}
                  subtitle="Quality of blind defense"
                  icon={<Shield size={24} />}
                  color="blue"
                  tooltip={getStatTooltipGTO('blind_defense_efficiency', player.blind_defense_efficiency ?? undefined)}
                />
                <StatCard
                  title="Skill Rating"
                  value={player.optimal_stake_skill_rating != null ? player.optimal_stake_skill_rating.toFixed(1) : 'N/A'}
                  subtitle="Skill level assessment"
                  icon={<TrendingUp size={24} />}
                  color="green"
                  tooltip={getStatTooltipGTO('optimal_stake_skill_rating', player.optimal_stake_skill_rating ?? undefined)}
                />
              </div>
            </div>

            {/* Ask Claude */}
            <div className="card bg-gradient-to-br from-purple-50 to-indigo-50 border border-purple-200">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Get AI Analysis</h3>
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
        )}

        {/* GTO ANALYSIS TAB */}
        {activeTab === 'gto' && (
          <div className="space-y-6">
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
            ) : gtoAnalysis ? (
              <>
                {/* GTO Adherence Summary */}
                <div className="card bg-gradient-to-r from-blue-50 to-cyan-50 border border-blue-200">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="font-semibold text-gray-900">GTO Adherence Score</h3>
                      <p className="text-sm text-gray-600">How closely this player follows GTO strategy</p>
                    </div>
                    <span className={`text-4xl font-bold ${
                      gtoAnalysis.adherence.gto_adherence_score >= 80 ? 'text-green-600' :
                      gtoAnalysis.adherence.gto_adherence_score >= 60 ? 'text-yellow-600' :
                      'text-red-600'
                    }`}>
                      {gtoAnalysis.adherence.gto_adherence_score.toFixed(0)}%
                    </span>
                  </div>
                  <div className="grid grid-cols-4 gap-4 text-center">
                    <div className="bg-white/50 rounded-lg p-3">
                      <div className="text-2xl font-bold text-gray-900">
                        {gtoAnalysis.adherence.avg_deviation.toFixed(1)}%
                      </div>
                      <div className="text-xs text-gray-600">Avg Deviation</div>
                    </div>
                    <div className="bg-white/50 rounded-lg p-3">
                      <div className="text-2xl font-bold text-red-600">
                        {gtoAnalysis.adherence.major_leaks_count}
                      </div>
                      <div className="text-xs text-gray-600">Major Leaks</div>
                    </div>
                    <div className="bg-white/50 rounded-lg p-3">
                      <div className="text-2xl font-bold text-yellow-600">
                        {gtoAnalysis.adherence.moderate_leaks_count}
                      </div>
                      <div className="text-xs text-gray-600">Moderate Leaks</div>
                    </div>
                    <div className="bg-white/50 rounded-lg p-3">
                      <div className="text-2xl font-bold text-gray-900">
                        {gtoAnalysis.adherence.total_hands.toLocaleString()}
                      </div>
                      <div className="text-xs text-gray-600">Hands Analyzed</div>
                    </div>
                  </div>
                </div>

                {/* Opening Ranges */}
                <GTOScenarioTable
                  title="Opening Ranges (RFI)"
                  data={gtoAnalysis.opening_ranges}
                  columns={[
                    { key: 'position', label: 'Position' },
                    { key: 'total_hands', label: 'Hands' },
                    { key: 'player_frequency', label: 'Player', isPlayer: true },
                    { key: 'gto_frequency', label: 'GTO', isGTO: true },
                    { key: 'frequency_diff', label: 'Diff', isDiff: true },
                  ]}
                />

                {/* Defense vs Opens */}
                <GTOScenarioTable
                  title="Defense vs Opens (Fold/Call/3-Bet)"
                  data={gtoAnalysis.defense_vs_open}
                  columns={[
                    { key: 'position', label: 'Position' },
                    { key: 'sample_size', label: 'Hands' },
                    { key: 'player_fold', label: 'Fold', isPlayer: true },
                    { key: 'gto_fold', label: 'GTO Fold', isGTO: true },
                    { key: 'fold_diff', label: 'Diff', isDiff: true },
                    { key: 'player_call', label: 'Call', isPlayer: true },
                    { key: 'gto_call', label: 'GTO Call', isGTO: true },
                    { key: 'call_diff', label: 'Diff', isDiff: true },
                    { key: 'player_3bet', label: '3-Bet', isPlayer: true },
                    { key: 'gto_3bet', label: 'GTO 3-Bet', isGTO: true },
                    { key: '3bet_diff', label: 'Diff', isDiff: true },
                  ]}
                />

                {/* Facing 3-Bet */}
                <GTOScenarioTable
                  title="Facing 3-Bet (After Opening)"
                  data={gtoAnalysis.facing_3bet}
                  columns={[
                    { key: 'position', label: 'Position' },
                    { key: 'sample_size', label: 'Hands' },
                    { key: 'player_fold', label: 'Fold', isPlayer: true },
                    { key: 'gto_fold', label: 'GTO Fold', isGTO: true },
                    { key: 'fold_diff', label: 'Diff', isDiff: true },
                    { key: 'player_call', label: 'Call', isPlayer: true },
                    { key: 'gto_call', label: 'GTO Call', isGTO: true },
                    { key: 'call_diff', label: 'Diff', isDiff: true },
                    { key: 'player_4bet', label: '4-Bet', isPlayer: true },
                    { key: 'gto_4bet', label: 'GTO 4-Bet', isGTO: true },
                    { key: '4bet_diff', label: 'Diff', isDiff: true },
                  ]}
                />

                {/* Blind Defense */}
                <GTOScenarioTable
                  title="Blind Defense vs Steals"
                  data={gtoAnalysis.blind_defense}
                  columns={[
                    { key: 'position', label: 'Position' },
                    { key: 'sample_size', label: 'Hands' },
                    { key: 'player_fold', label: 'Fold', isPlayer: true },
                    { key: 'gto_fold', label: 'GTO Fold', isGTO: true },
                    { key: 'fold_diff', label: 'Diff', isDiff: true },
                    { key: 'player_call', label: 'Call', isPlayer: true },
                    { key: 'gto_call', label: 'GTO Call', isGTO: true },
                    { key: 'call_diff', label: 'Diff', isDiff: true },
                    { key: 'player_3bet', label: '3-Bet', isPlayer: true },
                    { key: 'gto_3bet', label: 'GTO 3-Bet', isGTO: true },
                    { key: '3bet_diff', label: 'Diff', isDiff: true },
                  ]}
                />

                {/* Steal Attempts */}
                <GTOScenarioTable
                  title="Steal Attempts (Late Position)"
                  data={gtoAnalysis.steal_attempts}
                  columns={[
                    { key: 'position', label: 'Position' },
                    { key: 'sample_size', label: 'Opportunities' },
                    { key: 'player_frequency', label: 'Player', isPlayer: true },
                    { key: 'gto_frequency', label: 'GTO', isGTO: true },
                    { key: 'frequency_diff', label: 'Diff', isDiff: true },
                  ]}
                />

                {/* Position-Specific Defense Matchups with Player Data */}
                {gtoAnalysis.position_matchups && gtoAnalysis.position_matchups.length > 0 && (
                  <div className="card mb-6">
                    <h3 className="font-semibold text-gray-900 mb-2">Defense by Position Matchup</h3>
                    <p className="text-sm text-gray-500 mb-4">How you defend vs opens from specific positions compared to GTO</p>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-200">
                            <th className="text-left py-2 px-3 font-medium text-gray-600">Your Pos</th>
                            <th className="text-left py-2 px-3 font-medium text-gray-600">vs</th>
                            <th className="text-right py-2 px-3 font-medium text-gray-600">n</th>
                            <th className="text-right py-2 px-3 font-medium text-gray-900">Fold</th>
                            <th className="text-right py-2 px-3 font-medium text-blue-600 bg-blue-50">GTO</th>
                            <th className="text-right py-2 px-3 font-medium text-gray-600">Diff</th>
                            <th className="text-right py-2 px-3 font-medium text-gray-900">Call</th>
                            <th className="text-right py-2 px-3 font-medium text-blue-600 bg-blue-50">GTO</th>
                            <th className="text-right py-2 px-3 font-medium text-gray-600">Diff</th>
                            <th className="text-right py-2 px-3 font-medium text-gray-900">3-Bet</th>
                            <th className="text-right py-2 px-3 font-medium text-blue-600 bg-blue-50">GTO</th>
                            <th className="text-right py-2 px-3 font-medium text-gray-600">Diff</th>
                          </tr>
                        </thead>
                        <tbody>
                          {gtoAnalysis.position_matchups.map((row, idx) => (
                            <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                              <td className="py-2 px-3 font-medium">{row.position}</td>
                              <td className="py-2 px-3 text-gray-600">{row.vs_position}</td>
                              <td className="py-2 px-3 text-right text-gray-500">{row.sample_size || '-'}</td>
                              <td className="py-2 px-3 text-right font-medium">{row.player_fold != null ? `${row.player_fold.toFixed(1)}%` : '-'}</td>
                              <td className="py-2 px-3 text-right text-blue-600 bg-blue-50/50">{row.gto_fold.toFixed(1)}%</td>
                              <td className={`py-2 px-3 text-right font-medium ${row.fold_diff != null ? (row.fold_diff > 10 ? 'text-red-600' : row.fold_diff < -10 ? 'text-green-600' : 'text-gray-600') : 'text-gray-400'}`}>
                                {row.fold_diff != null ? `${row.fold_diff > 0 ? '+' : ''}${row.fold_diff.toFixed(1)}` : '-'}
                              </td>
                              <td className="py-2 px-3 text-right font-medium">{row.player_call != null ? `${row.player_call.toFixed(1)}%` : '-'}</td>
                              <td className="py-2 px-3 text-right text-blue-600 bg-blue-50/50">{row.gto_call.toFixed(1)}%</td>
                              <td className={`py-2 px-3 text-right font-medium ${row.call_diff != null ? (Math.abs(row.call_diff) > 10 ? 'text-red-600' : 'text-gray-600') : 'text-gray-400'}`}>
                                {row.call_diff != null ? `${row.call_diff > 0 ? '+' : ''}${row.call_diff.toFixed(1)}` : '-'}
                              </td>
                              <td className="py-2 px-3 text-right font-medium">{row.player_3bet != null ? `${row.player_3bet.toFixed(1)}%` : '-'}</td>
                              <td className="py-2 px-3 text-right text-blue-600 bg-blue-50/50">{row.gto_3bet.toFixed(1)}%</td>
                              <td className={`py-2 px-3 text-right font-medium ${row['3bet_diff'] != null ? (Math.abs(row['3bet_diff']) > 10 ? 'text-red-600' : 'text-gray-600') : 'text-gray-400'}`}>
                                {row['3bet_diff'] != null ? `${row['3bet_diff'] > 0 ? '+' : ''}${row['3bet_diff'].toFixed(1)}` : '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <p className="text-xs text-gray-400 mt-2">Note: Player data requires hands to be re-parsed after upgrading to track raiser positions.</p>
                  </div>
                )}

                {/* Facing 4-Bet Analysis */}
                {gtoAnalysis.facing_4bet_reference && gtoAnalysis.facing_4bet_reference.length > 0 && (
                  <div className="card mb-6">
                    <h3 className="font-semibold text-gray-900 mb-2">Facing 4-Bet</h3>
                    <p className="text-sm text-gray-500 mb-4">How you respond after 3-betting and facing a 4-bet, compared to GTO</p>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-200">
                            <th className="text-left py-2 px-3 font-medium text-gray-600">Your Pos</th>
                            <th className="text-left py-2 px-3 font-medium text-gray-600">vs</th>
                            <th className="text-right py-2 px-3 font-medium text-gray-600">n</th>
                            <th className="text-right py-2 px-3 font-medium text-gray-900">Fold</th>
                            <th className="text-right py-2 px-3 font-medium text-blue-600 bg-blue-50">GTO</th>
                            <th className="text-right py-2 px-3 font-medium text-gray-600">Diff</th>
                            <th className="text-right py-2 px-3 font-medium text-gray-900">Call</th>
                            <th className="text-right py-2 px-3 font-medium text-blue-600 bg-blue-50">GTO</th>
                            <th className="text-right py-2 px-3 font-medium text-gray-600">Diff</th>
                            <th className="text-right py-2 px-3 font-medium text-gray-900">5-Bet</th>
                            <th className="text-right py-2 px-3 font-medium text-blue-600 bg-blue-50">GTO</th>
                            <th className="text-right py-2 px-3 font-medium text-gray-600">Diff</th>
                          </tr>
                        </thead>
                        <tbody>
                          {gtoAnalysis.facing_4bet_reference.map((row, idx) => (
                            <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                              <td className="py-2 px-3 font-medium">{row.position}</td>
                              <td className="py-2 px-3 text-gray-600">{row.vs_position}</td>
                              <td className="py-2 px-3 text-right text-gray-500">{row.sample_size || '-'}</td>
                              <td className="py-2 px-3 text-right font-medium">{row.player_fold != null ? `${row.player_fold.toFixed(1)}%` : '-'}</td>
                              <td className="py-2 px-3 text-right text-blue-600 bg-blue-50/50">{row.gto_fold.toFixed(1)}%</td>
                              <td className={`py-2 px-3 text-right font-medium ${row.fold_diff != null ? (row.fold_diff > 10 ? 'text-red-600' : row.fold_diff < -10 ? 'text-green-600' : 'text-gray-600') : 'text-gray-400'}`}>
                                {row.fold_diff != null ? `${row.fold_diff > 0 ? '+' : ''}${row.fold_diff.toFixed(1)}` : '-'}
                              </td>
                              <td className="py-2 px-3 text-right font-medium">{row.player_call != null ? `${row.player_call.toFixed(1)}%` : '-'}</td>
                              <td className="py-2 px-3 text-right text-blue-600 bg-blue-50/50">{row.gto_call.toFixed(1)}%</td>
                              <td className={`py-2 px-3 text-right font-medium ${row.call_diff != null ? (Math.abs(row.call_diff) > 10 ? 'text-red-600' : 'text-gray-600') : 'text-gray-400'}`}>
                                {row.call_diff != null ? `${row.call_diff > 0 ? '+' : ''}${row.call_diff.toFixed(1)}` : '-'}
                              </td>
                              <td className="py-2 px-3 text-right font-medium">{row.player_5bet != null ? `${row.player_5bet.toFixed(1)}%` : '-'}</td>
                              <td className="py-2 px-3 text-right text-blue-600 bg-blue-50/50">{row.gto_5bet.toFixed(1)}%</td>
                              <td className={`py-2 px-3 text-right font-medium ${row['5bet_diff'] != null ? (Math.abs(row['5bet_diff']) > 10 ? 'text-red-600' : 'text-gray-600') : 'text-gray-400'}`}>
                                {row['5bet_diff'] != null ? `${row['5bet_diff'] > 0 ? '+' : ''}${row['5bet_diff'].toFixed(1)}` : '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <p className="text-xs text-gray-400 mt-2">Note: Player data requires hands to be re-parsed after upgrading to track 4-bet scenarios.</p>
                  </div>
                )}
              </>
            ) : (
              <div className="card text-center text-gray-500 py-12">
                No GTO analysis data available. Upload more hands to see GTO comparison.
              </div>
            )}
          </div>
        )}

        {/* LEAKS TAB */}
        {activeTab === 'leaks' && (
          <div className="space-y-6">
            {leakAnalysis ? (
              <>
                {/* Leak Summary */}
                <LeakSummary
                  totalLeaks={leakAnalysis.leak_summary.total_leaks}
                  criticalLeaks={leakAnalysis.leak_summary.critical_leaks}
                  majorLeaks={leakAnalysis.leak_summary.major_leaks}
                  totalEvOpportunity={leakAnalysis.leak_summary.total_ev_opportunity}
                  reliability={leakAnalysis.leak_summary.reliability}
                />

                {/* Player Type Exploit Info */}
                {leakAnalysis.player_type && (
                  <div className="card bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200">
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
                          <div>Aggression: <span className="font-medium">{leakAnalysis.player_type.aggression_ratio.toFixed(2)}</span></div>
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

                {/* Detailed Leaks List */}
                <div className="card">
                  <h3 className="font-semibold text-gray-900 mb-4">Identified Leaks</h3>
                  <LeaksList leaks={leakAnalysis.leaks} maxLeaks={15} />
                </div>

                {/* Exploit Analysis */}
                {exploitAnalysis && exploitAnalysis.analyses && exploitAnalysis.analyses.length > 0 && (
                  <>
                    <ExploitDashboard
                      deviations={
                        exploitAnalysis.analyses
                          .filter(a => a.comparison_type === 'baseline' || a.scenario === 'Poker Theory Baselines')
                          .flatMap(a => a.deviations)
                      }
                      playerName={player.player_name}
                    />
                    <DeviationHeatmap
                      deviations={
                        exploitAnalysis.analyses
                          .filter(a => a.comparison_type === 'baseline' || a.scenario === 'Poker Theory Baselines')
                          .flatMap(a => a.deviations)
                      }
                      playerName={player.player_name}
                    />
                    <BaselineComparison
                      deviations={
                        exploitAnalysis.analyses
                          .filter(a => a.comparison_type === 'baseline' || a.scenario === 'Poker Theory Baselines')
                          .flatMap(a => a.deviations)
                      }
                      playerName={player.player_name}
                    />
                  </>
                )}
              </>
            ) : (
              <div className="card text-center text-gray-500 py-12">
                No leak analysis data available. Upload more hands to see leak analysis.
              </div>
            )}
          </div>
        )}

        {/* CHARTS TAB */}
        {activeTab === 'charts' && (
          <div className="space-y-6">
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

            {/* Composite metrics radar chart */}
            <MetricChart
              data={compositeMetrics}
              title="Composite Metrics Overview"
            />

            {/* Core Metrics Summary from Leak Analysis */}
            {leakAnalysis?.core_metrics && (
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
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PlayerProfile;
