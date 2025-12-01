import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useState, useMemo } from 'react';
import { ArrowLeft, TrendingUp, Target, Shield, Crosshair, AlertTriangle, BarChart3, User, X, CheckCircle, XCircle, Grid3X3 } from 'lucide-react';
import { api } from '../services/api';
import PlayerBadge from '../components/PlayerBadge';
import StatCard from '../components/StatCard';
import { Tooltip } from '../components/Tooltip';
import MetricChart from '../components/MetricChart';
import PositionalVPIPChart from '../components/PositionalVPIPChart';
import PreflopAggressionChart from '../components/PreflopAggressionChart';
import RangeGrid from '../components/RangeGrid';
import type { HandActions } from '../components/RangeGrid';
// Note: ExploitDashboard, BaselineComparison, DeviationHeatmap disabled - require player_scenario_stats table
import { LeakSummary, LeaksList } from '../components/LeakCard';
import { GTOCategorySummaryCard, GTOCategoryDetailView } from '../components/gto';
import { STAT_DEFINITIONS, getStatDefinitionsWithGTO, GTOOptimalRange } from '../config/statDefinitions';
import type { ScenarioHandsResponse, GTOAnalysisResponse } from '../types';

// Scenario drill-down selection
interface ScenarioSelection {
  scenario: 'opening' | 'defense' | 'facing_3bet' | 'facing_4bet';
  position: string;
  vsPosition?: string;
}

// GTO navigation state
type GTOCategoryKey = 'opening' | 'defense' | 'facing_3bet' | 'facing_4bet';
type GTOView =
  | { level: 'summary' }
  | { level: 'detail'; category: GTOCategoryKey };

// Category configuration
const GTO_CATEGORY_CONFIG: Record<GTOCategoryKey, {
  title: string;
  subtitle: string;
  icon: React.ElementType;
  dataKeys: string[];
}> = {
  opening: {
    title: 'Opening Ranges',
    subtitle: 'RFI and Steal Attempts',
    icon: TrendingUp,
    dataKeys: ['opening_ranges', 'steal_attempts'],
  },
  defense: {
    title: 'Defense vs Opens',
    subtitle: 'How you respond to opens',
    icon: Shield,
    dataKeys: ['defense_vs_open', 'blind_defense', 'position_matchups'],
  },
  facing_3bet: {
    title: 'Facing 3-Bet',
    subtitle: 'After opening',
    icon: Target,
    dataKeys: ['facing_3bet', 'facing_3bet_matchups'],
  },
  facing_4bet: {
    title: 'Facing 4-Bet',
    subtitle: 'After 3-betting',
    icon: AlertTriangle,
    dataKeys: ['facing_4bet_reference'],
  },
};

// Calculate aggregate stats for a category
const calculateCategoryStats = (category: GTOCategoryKey, data: GTOAnalysisResponse) => {
  let totalHands = 0;
  let weightedDeviation = 0;
  let leakCount = 0;

  const addStats = (rows: any[] | undefined, diffKeys: string[], handsKey: string) => {
    if (!rows) return;
    rows.forEach(row => {
      const hands = row[handsKey] || 0;
      totalHands += hands;
      diffKeys.forEach(key => {
        const diff = Math.abs(row[key] ?? 0);
        weightedDeviation += diff * hands;
        if (diff > 10) leakCount++;
      });
    });
  };

  switch (category) {
    case 'opening':
      addStats(data.opening_ranges, ['frequency_diff'], 'total_hands');
      addStats(data.steal_attempts, ['frequency_diff'], 'sample_size');
      break;
    case 'defense':
      addStats(data.defense_vs_open, ['fold_diff', 'call_diff', '3bet_diff'], 'sample_size');
      addStats(data.blind_defense, ['fold_diff', 'call_diff', '3bet_diff'], 'sample_size');
      break;
    case 'facing_3bet':
      addStats(data.facing_3bet, ['fold_diff', 'call_diff', '4bet_diff'], 'sample_size');
      break;
    case 'facing_4bet':
      addStats(data.facing_4bet_reference, ['fold_diff', 'call_diff', '5bet_diff'], 'sample_size');
      break;
  }

  const avgDeviation = totalHands > 0 ? weightedDeviation / totalHands : 0;
  return { avgDeviation, totalHands, leakCount };
};

type TabId = 'overview' | 'gto' | 'leaks' | 'charts';

const tabs: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Overview', icon: User },
  { id: 'gto', label: 'GTO Analysis', icon: Target },
  { id: 'leaks', label: 'Leaks', icon: AlertTriangle },
  { id: 'charts', label: 'Charts', icon: BarChart3 },
];

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

// Scenario Hands Drill-down Modal
const ScenarioHandsModal = ({
  data,
  isLoading,
  onClose,
  selection
}: {
  data: ScenarioHandsResponse | undefined;
  isLoading: boolean;
  onClose: () => void;
  selection: ScenarioSelection;
}) => {
  const [selectedHand, setSelectedHand] = useState<string | null>(null);
  const [showRangeGrid, setShowRangeGrid] = useState(false);

  // Fetch GTO range matrix for this scenario
  const { data: rangeMatrix, isLoading: rangeLoading } = useQuery({
    queryKey: ['rangeMatrix', selection.scenario, selection.position, selection.vsPosition],
    queryFn: () => api.getGTORangeMatrix(
      selection.scenario,
      selection.position,
      selection.vsPosition || undefined
    ),
    enabled: showRangeGrid,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const scenarioLabels: Record<string, string> = {
    opening: 'Opening Range',
    defense: 'Defense vs Open',
    facing_3bet: 'Facing 3-Bet',
    facing_4bet: 'Facing 4-Bet'
  };

  const actionColors: Record<string, string> = {
    fold: 'text-gray-600 bg-gray-100',
    call: 'text-green-700 bg-green-100',
    raise: 'text-blue-700 bg-blue-100',
    '3bet': 'text-orange-700 bg-orange-100',
    '4bet': 'text-red-700 bg-red-100',
    '5bet': 'text-purple-700 bg-purple-100',
    limp: 'text-yellow-700 bg-yellow-100',
  };

  const tierColors: Record<number, string> = {
    1: 'bg-purple-100 text-purple-800',  // Premium
    2: 'bg-blue-100 text-blue-800',      // Strong
    3: 'bg-green-100 text-green-800',    // Playable
    4: 'bg-yellow-100 text-yellow-800',  // Speculative
    5: 'bg-red-100 text-red-800',        // Weak
  };

  const deviationStyles: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    correct: { bg: 'bg-green-50', text: 'text-green-700', icon: <CheckCircle size={14} className="mr-1" /> },
    suboptimal: { bg: 'bg-yellow-50', text: 'text-yellow-700', icon: <AlertTriangle size={14} className="mr-1" /> },
    mistake: { bg: 'bg-red-50', text: 'text-red-700', icon: <XCircle size={14} className="mr-1" /> },
  };

  // Handle clicking a hand row to show it in the range grid
  const handleHandClick = (handCombo: string | null) => {
    if (handCombo) {
      setSelectedHand(handCombo);
      setShowRangeGrid(true);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">
              {scenarioLabels[selection.scenario]} - {selection.position}
              {selection.vsPosition && ` vs ${selection.vsPosition}`}
            </h2>
            {data && (
              <p className="text-blue-100 text-sm mt-1">
                {data.total_hands} hands analyzed
                {data.hands_with_hole_cards > 0 && ` • ${data.hands_with_hole_cards} with hole cards`}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            {/* Range Grid Toggle */}
            <button
              onClick={() => setShowRangeGrid(!showRangeGrid)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors ${
                showRangeGrid
                  ? 'bg-white text-blue-600'
                  : 'bg-blue-500/30 text-white hover:bg-blue-500/50'
              }`}
            >
              <Grid3X3 size={18} />
              <span className="text-sm font-medium">Range Grid</span>
            </button>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white transition-colors"
            >
              <X size={24} />
            </button>
          </div>
        </div>

        {/* Enhanced Summary Bar */}
        {data?.summary && (
          <div className="bg-gradient-to-r from-gray-50 to-blue-50 px-6 py-3 border-b border-gray-200">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <CheckCircle size={16} className="text-green-600" />
                <span className="text-sm">
                  <span className="font-semibold text-green-700">{data.summary.correct}</span>
                  <span className="text-gray-500 ml-1">correct ({data.summary.correct_pct}%)</span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <AlertTriangle size={16} className="text-yellow-600" />
                <span className="text-sm">
                  <span className="font-semibold text-yellow-700">{data.summary.suboptimal}</span>
                  <span className="text-gray-500 ml-1">suboptimal ({data.summary.suboptimal_pct}%)</span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <XCircle size={16} className="text-red-600" />
                <span className="text-sm">
                  <span className="font-semibold text-red-700">{data.summary.mistakes}</span>
                  <span className="text-gray-500 ml-1">mistakes ({data.summary.mistake_pct}%)</span>
                </span>
              </div>
            </div>
          </div>
        )}

        {/* GTO Reference Bar */}
        {data && Object.keys(data.gto_frequencies).length > 0 && (
          <div className="bg-blue-50 px-6 py-3 border-b border-blue-100">
            <div className="text-sm text-blue-800 font-medium mb-2">GTO Frequencies:</div>
            <div className="flex gap-4 flex-wrap">
              {Object.entries(data.gto_frequencies)
                .sort((a, b) => b[1] - a[1])
                .map(([action, freq]) => (
                  <span key={action} className="text-sm">
                    <span className={`px-2 py-0.5 rounded ${actionColors[action] || 'bg-gray-100'}`}>
                      {action}
                    </span>
                    <span className="text-blue-600 ml-1 font-medium">{freq.toFixed(1)}%</span>
                  </span>
                ))}
            </div>
          </div>
        )}

        {/* Content - Split view when range grid is shown */}
        <div className={`overflow-hidden ${showRangeGrid ? 'flex' : ''}`} style={{ maxHeight: '55vh' }}>
          {/* Range Grid Panel */}
          {showRangeGrid && (
            <div className="w-96 flex-shrink-0 border-r border-gray-200 p-4 overflow-y-auto bg-gray-50">
              <div className="sticky top-0 bg-gray-50 pb-2 mb-2">
                <h3 className="text-sm font-semibold text-gray-700 mb-1">
                  GTO Range: {selection.position}
                  {selection.vsPosition && ` vs ${selection.vsPosition}`}
                </h3>
                <p className="text-xs text-gray-500">
                  Click a hand in the table to highlight it
                </p>
              </div>
              {rangeLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin h-6 w-6 border-2 border-blue-600 border-t-transparent rounded-full" />
                </div>
              ) : rangeMatrix && Object.keys(rangeMatrix).length > 0 ? (
                <RangeGrid
                  actionMatrix={rangeMatrix as Record<string, HandActions>}
                  highlightedHand={selectedHand || undefined}
                  showFolds={false}
                  onHandClick={(hand) => setSelectedHand(hand)}
                />
              ) : (
                <div className="text-center text-gray-500 py-8 text-sm">
                  No GTO data available for this scenario
                </div>
              )}
            </div>
          )}

          {/* Hands Table */}
          <div className={`overflow-y-auto p-6 ${showRangeGrid ? 'flex-1' : 'w-full'}`}>
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin h-8 w-8 border-2 border-blue-600 border-t-transparent rounded-full" />
              </div>
            ) : data && data.hands.length > 0 ? (
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-white">
                  <tr className="border-b-2 border-gray-200">
                    <th className="text-left py-3 px-2 font-semibold text-gray-700">Hand</th>
                    <th className="text-left py-3 px-2 font-semibold text-gray-700">Category</th>
                    <th className="text-center py-3 px-2 font-semibold text-gray-700">Stack</th>
                    {selection.vsPosition === undefined && (
                      <th className="text-left py-3 px-2 font-semibold text-gray-700">vs</th>
                    )}
                    <th className="text-left py-3 px-2 font-semibold text-gray-700">Action</th>
                    <th className="text-right py-3 px-2 font-semibold text-gray-700">GTO%</th>
                    <th className="text-left py-3 px-2 font-semibold text-gray-700">Assessment</th>
                  </tr>
                </thead>
                <tbody>
                  {data.hands.map((hand) => {
                    const devStyle = deviationStyles[hand.deviation_type] || deviationStyles.correct;
                    const isSelected = selectedHand === hand.hand_combo;
                    return (
                      <tr
                        key={hand.hand_id}
                        className={`border-b border-gray-100 cursor-pointer transition-colors ${
                          isSelected ? 'bg-yellow-100 ring-2 ring-yellow-400' : `hover:bg-gray-50 ${devStyle.bg}`
                        }`}
                        onClick={() => handleHandClick(hand.hand_combo)}
                      >
                        {/* Hole Cards */}
                        <td className="py-3 px-2">
                          {hand.hole_cards ? (
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-bold text-gray-800">
                                {hand.hand_combo || hand.hole_cards}
                              </span>
                              {hand.hand_tier && (
                                <span className={`px-1.5 py-0.5 rounded text-xs ${tierColors[hand.hand_tier]}`}>
                                  T{hand.hand_tier}
                                </span>
                              )}
                              {showRangeGrid && (
                                <span title="Click to view in range grid">
                                  <Grid3X3 size={14} className="text-blue-400" />
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-gray-400 italic">Unknown</span>
                          )}
                        </td>
                        {/* Hand Category */}
                        <td className="py-3 px-2 text-gray-600 text-xs">
                          {hand.hand_category || '-'}
                        </td>
                        {/* Effective Stack */}
                        <td className="py-3 px-2 text-center">
                          {hand.effective_stack_bb ? (
                            <span className="font-mono text-gray-700">
                              {hand.effective_stack_bb.toFixed(0)}bb
                            </span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        {/* vs Position */}
                        {selection.vsPosition === undefined && (
                          <td className="py-3 px-2 text-gray-600">{hand.vs_position || '-'}</td>
                        )}
                        {/* Player Action */}
                        <td className="py-3 px-2">
                          <span className={`px-2 py-1 rounded font-medium text-xs ${
                            actionColors[hand.player_action] || 'bg-gray-100'
                          }`}>
                            {hand.player_action}
                          </span>
                        </td>
                        {/* GTO Frequency */}
                        <td className="py-3 px-2 text-right">
                          <span className={`font-mono ${
                            hand.action_gto_freq < 15 ? 'text-red-600 font-bold' :
                            hand.action_gto_freq < 40 ? 'text-yellow-600' : 'text-gray-600'
                          }`}>
                            {hand.action_gto_freq.toFixed(0)}%
                          </span>
                        </td>
                        {/* Assessment */}
                        <td className="py-3 px-2">
                          <div className={`inline-flex items-center text-xs font-medium ${devStyle.text}`}>
                            {devStyle.icon}
                            <span className="capitalize">{hand.deviation_type}</span>
                            {hand.deviation_severity && (
                              <span className="ml-1 opacity-75">({hand.deviation_severity})</span>
                            )}
                          </div>
                          {hand.deviation_type !== 'correct' && (
                            <div className="text-xs text-gray-500 mt-0.5">
                              {hand.deviation_description}
                            </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="text-center text-gray-500 py-12">
              No hands found for this scenario
            </div>
          )}
          </div>
        </div>

        {/* Footer Legend */}
        <div className="border-t border-gray-200 px-6 py-4 bg-gray-50">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap gap-4 text-xs text-gray-500">
              <span>Hand Tiers:</span>
              <span className={`px-1.5 py-0.5 rounded ${tierColors[1]}`}>T1 Premium</span>
              <span className={`px-1.5 py-0.5 rounded ${tierColors[2]}`}>T2 Strong</span>
              <span className={`px-1.5 py-0.5 rounded ${tierColors[3]}`}>T3 Playable</span>
              <span className={`px-1.5 py-0.5 rounded ${tierColors[4]}`}>T4 Speculative</span>
              <span className={`px-1.5 py-0.5 rounded ${tierColors[5]}`}>T5 Weak</span>
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const PlayerProfile = () => {
  const { playerName } = useParams<{ playerName: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [selectedScenario, setSelectedScenario] = useState<ScenarioSelection | null>(null);
  const [gtoView, setGtoView] = useState<GTOView>({ level: 'summary' });

  // Query for scenario hands drill-down
  const { data: scenarioHandsData, isLoading: scenarioHandsLoading } = useQuery({
    queryKey: ['scenarioHands', playerName, selectedScenario],
    queryFn: () => api.getScenarioHands(
      playerName!,
      selectedScenario!.scenario,
      selectedScenario!.position,
      selectedScenario!.vsPosition
    ),
    enabled: !!playerName && !!selectedScenario,
  });

  const { data: player, isLoading, error } = useQuery({
    queryKey: ['player', playerName],
    queryFn: () => api.getPlayerProfile(playerName!),
    enabled: !!playerName,
  });

  // Note: exploitAnalysis disabled - requires player_scenario_stats table to be populated
  // const { data: exploitAnalysis } = useQuery({
  //   queryKey: ['playerExploits', playerName],
  //   queryFn: () => api.analyzePlayerExploits(playerName!),
  //   enabled: !!playerName,
  // });

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
                {/* GTO Adherence Summary - always visible */}
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

                {/* Level 1: Category Summary Cards */}
                {gtoView.level === 'summary' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {(Object.keys(GTO_CATEGORY_CONFIG) as GTOCategoryKey[]).map((categoryKey) => {
                      const config = GTO_CATEGORY_CONFIG[categoryKey];
                      const stats = calculateCategoryStats(categoryKey, gtoAnalysis);

                      // Skip categories with no data
                      if (stats.totalHands === 0) return null;

                      return (
                        <GTOCategorySummaryCard
                          key={categoryKey}
                          title={config.title}
                          subtitle={config.subtitle}
                          icon={config.icon}
                          avgDeviation={stats.avgDeviation}
                          totalHands={stats.totalHands}
                          leakCount={stats.leakCount}
                          onClick={() => setGtoView({ level: 'detail', category: categoryKey })}
                        />
                      );
                    })}
                  </div>
                )}

                {/* Level 2: Category Detail View */}
                {gtoView.level === 'detail' && (
                  <GTOCategoryDetailView
                    category={gtoView.category}
                    data={gtoAnalysis}
                    onBack={() => setGtoView({ level: 'summary' })}
                    onRowClick={setSelectedScenario}
                  />
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

                {/* Exploit Analysis - temporarily disabled while player_scenario_stats is being populated */}
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

      {/* Scenario Drill-down Modal */}
      {selectedScenario && (
        <ScenarioHandsModal
          data={scenarioHandsData}
          isLoading={scenarioHandsLoading}
          onClose={() => setSelectedScenario(null)}
          selection={selectedScenario}
        />
      )}
    </div>
  );
};

export default PlayerProfile;
