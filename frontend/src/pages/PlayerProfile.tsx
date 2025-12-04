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
// Note: ExploitDashboard, BaselineComparison, DeviationHeatmap disabled - require player_scenario_stats table
import LeakAnalysisView from '../components/LeakAnalysisView';
import { GTOCategorySummaryCard, GTOCategoryDetailView } from '../components/gto';
import ScenarioHandsModal, { type ScenarioSelection } from '../components/ScenarioHandsModal';
import { STAT_DEFINITIONS, getStatDefinitionsWithGTO, GTOOptimalRange } from '../config/statDefinitions';
import type { GTOAnalysisResponse } from '../types';

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

// Enhanced category stats with detailed info
interface CategoryStats {
  avgDeviation: number;
  totalHands: number;
  leakCount: number;
  worstLeak: { position: string; deviation: number } | null;
  tendency: string;
  positionStats: { position: string; deviation: number; status: 'good' | 'warning' | 'bad' }[];
  actionBreakdown: { playerFold: number; gtoFold: number; playerRaise: number; gtoRaise: number } | null;
}

// Calculate aggregate stats for a category
const calculateCategoryStats = (category: GTOCategoryKey, data: GTOAnalysisResponse): CategoryStats => {
  let totalHands = 0;
  let weightedDeviation = 0;
  let leakCount = 0;
  let worstLeak: { position: string; deviation: number } | null = null;
  const positionStats: { position: string; deviation: number; status: 'good' | 'warning' | 'bad' }[] = [];
  let actionBreakdown: CategoryStats['actionBreakdown'] = null;

  // Track tendency (positive = too aggressive/loose, negative = too passive/tight)
  let tendencySum = 0;
  let tendencyCount = 0;

  const processRow = (row: any, diffKey: string, handsKey: string, isRaiseDiff: boolean = false) => {
    const hands = row[handsKey] || 0;
    const diff = row[diffKey] ?? 0;
    const absDiff = Math.abs(diff);

    totalHands += hands;
    weightedDeviation += absDiff * hands;
    if (absDiff > 10) leakCount++;

    // Track worst leak
    if (!worstLeak || absDiff > Math.abs(worstLeak.deviation)) {
      worstLeak = { position: row.position + (row.vs_position ? ` vs ${row.vs_position}` : ''), deviation: diff };
    }

    // Track tendency (raise diffs: positive = too aggressive, fold diffs: positive = too passive)
    if (isRaiseDiff) {
      tendencySum += diff; // positive = raises more than GTO
    } else {
      tendencySum -= diff; // positive fold diff means folding more = passive
    }
    tendencyCount++;
  };

  const addPositionStat = (position: string, deviation: number) => {
    const absDev = Math.abs(deviation);
    const status = absDev < 5 ? 'good' : absDev < 10 ? 'warning' : 'bad';
    positionStats.push({ position, deviation, status });
  };

  switch (category) {
    case 'opening':
      data.opening_ranges?.forEach(row => {
        processRow(row, 'open_diff', 'opportunities', true);
        addPositionStat(row.position, row.open_diff);
      });
      // Calculate tendency for opening
      if (data.opening_ranges?.length) {
        const avgDiff = data.opening_ranges.reduce((sum, r) => sum + (r.open_diff || 0), 0) / data.opening_ranges.length;
        tendencySum = avgDiff;
      }
      break;

    case 'defense':
      let totalPlayerFold = 0, totalGtoFold = 0, totalPlayer3bet = 0, totalGto3bet = 0, defenseCount = 0;
      data.defense_vs_open?.forEach(row => {
        const maxDiff = Math.max(Math.abs(row.fold_diff || 0), Math.abs(row.call_diff || 0), Math.abs(row.raise_diff || 0));
        processRow({ ...row, maxDiff }, 'fold_diff', 'total_opportunities', false);
        addPositionStat(row.position, row.fold_diff || 0);
        totalPlayerFold += row.player_fold || 0;
        totalGtoFold += row.gto_fold || 0;
        totalPlayer3bet += row.player_3bet || 0;
        totalGto3bet += row.gto_3bet || 0;
        defenseCount++;
        tendencySum += (row.fold_diff || 0); // positive fold = too passive
      });
      if (defenseCount > 0) {
        actionBreakdown = {
          playerFold: totalPlayerFold / defenseCount,
          gtoFold: totalGtoFold / defenseCount,
          playerRaise: totalPlayer3bet / defenseCount,
          gtoRaise: totalGto3bet / defenseCount,
        };
      }
      break;

    case 'facing_3bet':
      let f3PlayerFold = 0, f3GtoFold = 0, f3Player4bet = 0, f3Gto4bet = 0, f3Count = 0;
      data.facing_3bet?.forEach(row => {
        processRow(row, 'fold_diff', 'times_opened', false);
        addPositionStat(row.position, row.fold_diff || 0);
        f3PlayerFold += row.player_fold || 0;
        f3GtoFold += row.gto_fold || 0;
        f3Player4bet += row.player_4bet || 0;
        f3Gto4bet += row.gto_4bet || 0;
        f3Count++;
        tendencySum += (row.fold_diff || 0);
      });
      if (f3Count > 0) {
        actionBreakdown = {
          playerFold: f3PlayerFold / f3Count,
          gtoFold: f3GtoFold / f3Count,
          playerRaise: f3Player4bet / f3Count,
          gtoRaise: f3Gto4bet / f3Count,
        };
      }
      break;

    case 'facing_4bet':
      let f4PlayerFold = 0, f4GtoFold = 0, f4Player5bet = 0, f4Gto5bet = 0, f4Count = 0;
      data.facing_4bet_reference?.forEach(row => {
        processRow(row, 'fold_diff', 'sample_size', false);
        addPositionStat(row.position + (row.vs_position ? ` vs ${row.vs_position}` : ''), row.fold_diff || 0);
        f4PlayerFold += row.player_fold || 0;
        f4GtoFold += row.gto_fold || 0;
        f4Player5bet += row.player_5bet || 0;
        f4Gto5bet += row.gto_5bet || 0;
        f4Count++;
        tendencySum += (row.fold_diff || 0);
      });
      if (f4Count > 0) {
        actionBreakdown = {
          playerFold: f4PlayerFold / f4Count,
          gtoFold: f4GtoFold / f4Count,
          playerRaise: f4Player5bet / f4Count,
          gtoRaise: f4Gto5bet / f4Count,
        };
      }
      break;
  }

  const avgDeviation = totalHands > 0 ? weightedDeviation / totalHands : 0;

  // Determine tendency label
  let tendency = 'Balanced';
  if (category === 'opening') {
    if (tendencySum > 5) tendency = 'Too Loose';
    else if (tendencySum < -5) tendency = 'Too Tight';
  } else {
    if (tendencySum > 5) tendency = 'Too Passive';
    else if (tendencySum < -5) tendency = 'Too Aggressive';
  }

  return { avgDeviation, totalHands, leakCount, worstLeak, tendency, positionStats, actionBreakdown };
};

// Interface for GTO positional leaks
interface GTOPositionalLeak {
  category: string;
  position: string;
  vsPosition?: string;
  action: string;
  playerValue: number;
  gtoValue: number;
  deviation: number;
  severity: 'moderate' | 'major';
  sampleSize: number;
  confidence: 'low' | 'moderate' | 'high';
}

// Sample size thresholds for statistical significance (based on poker statistics research)
// Key insight: Never show deviations with < minimum opportunities - that's just noise
const SAMPLE_THRESHOLDS = {
  // RFI by position: need 20+ opps to show, 50 for moderate, 100 for high confidence
  rfi: { min: 20, moderate: 50, high: 100 },
  // Defense vs opens (aggregate by position): 25+ min, 60 moderate, 120 high
  defense: { min: 25, moderate: 60, high: 120 },
  // Defense position matchups (e.g., BB vs CO): need more samples due to specificity
  defense_matchup: { min: 50, moderate: 120, high: 240 },
  // Facing 3-bet (aggregate): 20+ for fold stats, 30+ for 4-bet stats
  facing_3bet: { min: 20, moderate: 50, high: 100 },
  // Facing 3-bet matchups: need more samples
  facing_3bet_matchup: { min: 40, moderate: 100, high: 200 },
  // Facing 4-bet: rare scenario, need decent sample
  facing_4bet: { min: 25, moderate: 60, high: 120 },
};

// Get confidence tier based on sample size
const getConfidenceTier = (sampleSize: number, thresholds: { min: number; moderate: number; high: number }): 'low' | 'moderate' | 'high' | null => {
  if (sampleSize < thresholds.min) return null; // Don't show at all
  if (sampleSize < thresholds.moderate) return 'low';
  if (sampleSize < thresholds.high) return 'moderate';
  return 'high';
};

// Result type for leak extraction
interface LeakExtractionResult {
  leaks: GTOPositionalLeak[];
  insufficientSamples: {
    category: string;
    count: number;
    minRequired: number;
  }[];
}

// Extract positional leaks from GTO analysis data (with statistical significance filtering)
const extractGTOPositionalLeaks = (data: GTOAnalysisResponse): LeakExtractionResult => {
  const leaks: GTOPositionalLeak[] = [];
  const insufficientSamples: LeakExtractionResult['insufficientSamples'] = [];
  const MAJOR_THRESHOLD = 15;
  const MODERATE_THRESHOLD = 8;

  // Track insufficient samples by category
  const insufficientByCategory: Record<string, number> = {};

  // Opening ranges (RFI)
  data.opening_ranges?.forEach(row => {
    const diff = row.open_diff ?? 0;
    const absDiff = Math.abs(diff);
    const sampleSize = row.opportunities ?? 0;
    const confidence = getConfidenceTier(sampleSize, SAMPLE_THRESHOLDS.rfi);

    if (absDiff > MODERATE_THRESHOLD && confidence) {
      leaks.push({
        category: 'Opening',
        position: row.position,
        action: 'RFI',
        playerValue: row.player_frequency ?? 0,
        gtoValue: row.gto_frequency ?? 0,
        deviation: diff,
        severity: absDiff > MAJOR_THRESHOLD ? 'major' : 'moderate',
        sampleSize,
        confidence,
      });
    }
  });

  // Defense vs open (aggregate by position)
  data.defense_vs_open?.forEach(row => {
    const sampleSize = row.total_opportunities ?? 0;
    const confidence = getConfidenceTier(sampleSize, SAMPLE_THRESHOLDS.defense);
    if (!confidence) return; // Skip if insufficient sample

    const diffs = [
      { action: 'Fold', diff: row.fold_diff, player: row.player_fold, gto: row.gto_fold },
      { action: 'Call', diff: row.call_diff, player: row.player_call, gto: row.gto_call },
      { action: '3-Bet', diff: row.raise_diff, player: row.player_3bet, gto: row.gto_3bet },
    ];
    diffs.forEach(({ action, diff, player, gto }) => {
      if (diff != null && Math.abs(diff) > MODERATE_THRESHOLD) {
        leaks.push({
          category: 'Defense',
          position: row.position,
          action,
          playerValue: player ?? 0,
          gtoValue: gto ?? 0,
          deviation: diff,
          severity: Math.abs(diff) > MAJOR_THRESHOLD ? 'major' : 'moderate',
          sampleSize,
          confidence,
        });
      }
    });
  });

  // Position matchups (defense) - requires higher sample sizes
  data.position_matchups?.forEach(row => {
    const sampleSize = row.sample_size ?? 0;
    const confidence = getConfidenceTier(sampleSize, SAMPLE_THRESHOLDS.defense_matchup);
    if (!confidence) return; // Skip if insufficient sample

    const diffs = [
      { action: 'Fold', diff: row.fold_diff, player: row.player_fold, gto: row.gto_fold },
      { action: 'Call', diff: row.call_diff, player: row.player_call, gto: row.gto_call },
      { action: '3-Bet', diff: row['3bet_diff'], player: row.player_3bet, gto: row.gto_3bet },
    ];
    diffs.forEach(({ action, diff, player, gto }) => {
      if (diff != null && Math.abs(diff) > MODERATE_THRESHOLD) {
        leaks.push({
          category: 'Defense',
          position: row.position,
          vsPosition: row.vs_position,
          action,
          playerValue: player ?? 0,
          gtoValue: gto ?? 0,
          deviation: diff,
          severity: Math.abs(diff) > MAJOR_THRESHOLD ? 'major' : 'moderate',
          sampleSize,
          confidence,
        });
      }
    });
  });

  // Facing 3-bet (aggregate)
  data.facing_3bet?.forEach(row => {
    const sampleSize = row.times_opened ?? 0;
    const confidence = getConfidenceTier(sampleSize, SAMPLE_THRESHOLDS.facing_3bet);
    if (!confidence) {
      // Track insufficient samples for this category
      insufficientByCategory['Facing 3-Bet'] = (insufficientByCategory['Facing 3-Bet'] || 0) + 1;
      return;
    }

    const diffs = [
      { action: 'Fold', diff: row.fold_diff, player: row.player_fold, gto: row.gto_fold },
      { action: 'Call', diff: row.call_diff, player: row.player_call, gto: row.gto_call },
      { action: '4-Bet', diff: row['4bet_diff'], player: row.player_4bet, gto: row.gto_4bet },
    ];
    diffs.forEach(({ action, diff, player, gto }) => {
      if (diff != null && Math.abs(diff) > MODERATE_THRESHOLD) {
        leaks.push({
          category: 'Facing 3-Bet',
          position: row.position,
          action,
          playerValue: player ?? 0,
          gtoValue: gto ?? 0,
          deviation: diff,
          severity: Math.abs(diff) > MAJOR_THRESHOLD ? 'major' : 'moderate',
          sampleSize,
          confidence,
        });
      }
    });
  });

  // Facing 3-bet matchups - requires higher sample sizes
  data.facing_3bet_matchups?.forEach(row => {
    const sampleSize = row.sample_size ?? 0;
    const confidence = getConfidenceTier(sampleSize, SAMPLE_THRESHOLDS.facing_3bet_matchup);
    if (!confidence) return;

    const diffs = [
      { action: 'Fold', diff: row.fold_diff, player: row.player_fold, gto: row.gto_fold },
      { action: 'Call', diff: row.call_diff, player: row.player_call, gto: row.gto_call },
      { action: '4-Bet', diff: row['4bet_diff'], player: row.player_4bet, gto: row.gto_4bet },
    ];
    diffs.forEach(({ action, diff, player, gto }) => {
      if (diff != null && Math.abs(diff) > MODERATE_THRESHOLD) {
        leaks.push({
          category: 'Facing 3-Bet',
          position: row.position,
          vsPosition: row.vs_position,
          action,
          playerValue: player ?? 0,
          gtoValue: gto ?? 0,
          deviation: diff,
          severity: Math.abs(diff) > MAJOR_THRESHOLD ? 'major' : 'moderate',
          sampleSize,
          confidence,
        });
      }
    });
  });

  // Facing 4-bet
  data.facing_4bet_reference?.forEach(row => {
    const sampleSize = row.sample_size ?? 0;
    const confidence = getConfidenceTier(sampleSize, SAMPLE_THRESHOLDS.facing_4bet);
    if (!confidence) return;

    const diffs = [
      { action: 'Fold', diff: row.fold_diff, player: row.player_fold, gto: row.gto_fold },
      { action: 'Call', diff: row.call_diff, player: row.player_call, gto: row.gto_call },
      { action: '5-Bet', diff: row['5bet_diff'], player: row.player_5bet, gto: row.gto_5bet },
    ];
    diffs.forEach(({ action, diff, player, gto }) => {
      if (diff != null && Math.abs(diff) > MODERATE_THRESHOLD) {
        leaks.push({
          category: 'Facing 4-Bet',
          position: row.position,
          vsPosition: row.vs_position,
          action,
          playerValue: player ?? 0,
          gtoValue: gto ?? 0,
          deviation: diff,
          severity: Math.abs(diff) > MAJOR_THRESHOLD ? 'major' : 'moderate',
          sampleSize,
          confidence,
        });
      }
    });
  });

  // EV weights by position (same as session analysis)
  const EV_WEIGHTS: Record<string, number> = {
    // Opening - BTN most frequent
    'Opening_BTN': 1.5, 'Opening_CO': 1.3, 'Opening_SB': 1.4, 'Opening_MP': 1.1, 'Opening_UTG': 1.0,
    // Defense - BB highest frequency
    'Defense_BB': 1.6, 'Defense_SB': 1.2, 'Defense_BTN': 1.0, 'Defense_CO': 0.9, 'Defense_MP': 0.8,
    // Facing 3-bet
    'Facing 3-Bet_BTN': 1.4, 'Facing 3-Bet_CO': 1.3, 'Facing 3-Bet_SB': 1.2, 'Facing 3-Bet_MP': 1.0, 'Facing 3-Bet_UTG': 0.9,
    // Facing 4-bet
    'Facing 4-Bet_BTN': 1.3, 'Facing 4-Bet_CO': 1.2, 'Facing 4-Bet_SB': 1.1, 'Facing 4-Bet_MP': 1.0, 'Facing 4-Bet_UTG': 0.9,
  };

  // Calculate priority score (same formula as session analysis)
  const calculatePriorityScore = (leak: GTOPositionalLeak): number => {
    const severityScores = { minor: 1, moderate: 2, major: 3 };
    const confidenceScores = { low: 0.6, moderate: 0.85, high: 1.0 };

    const severityScore = severityScores[leak.severity] || 1;
    const evWeight = EV_WEIGHTS[`${leak.category}_${leak.position}`] || 1.0;
    const deviation = Math.abs(leak.deviation);
    const confidence = confidenceScores[leak.confidence] || 0.5;

    return (severityScore * 10 + deviation * 0.5) * evWeight * confidence;
  };

  // Sort by priority score (higher = more important to fix)
  leaks.sort((a, b) => calculatePriorityScore(b) - calculatePriorityScore(a));

  // Build insufficient samples array
  const categoryThresholds: Record<string, number> = {
    'Opening': SAMPLE_THRESHOLDS.rfi.min,
    'Defense': SAMPLE_THRESHOLDS.defense.min,
    'Facing 3-Bet': SAMPLE_THRESHOLDS.facing_3bet.min,
    'Facing 4-Bet': SAMPLE_THRESHOLDS.facing_4bet.min,
  };

  Object.entries(insufficientByCategory).forEach(([category, count]) => {
    if (count > 0) {
      insufficientSamples.push({
        category,
        count,
        minRequired: categoryThresholds[category] || 20,
      });
    }
  });

  return { leaks, insufficientSamples };
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

  // Compute filtered GTO positional leaks (with statistical significance)
  const filteredGTOLeaks = useMemo(() => {
    if (!gtoAnalysis) return { all: [], major: [], moderate: [], insufficientSamples: [] };
    const { leaks: all, insufficientSamples } = extractGTOPositionalLeaks(gtoAnalysis);
    const major = all.filter(l => l.severity === 'major');
    const moderate = all.filter(l => l.severity === 'moderate');
    return { all, major, moderate, insufficientSamples };
  }, [gtoAnalysis]);

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
                        {filteredGTOLeaks.major.length}
                      </div>
                      <div className="text-xs text-gray-600">Major Leaks</div>
                    </div>
                    <div className="bg-white/50 rounded-lg p-3">
                      <div className="text-2xl font-bold text-yellow-600">
                        {filteredGTOLeaks.moderate.length}
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
                  <p className="text-xs text-gray-500 mt-3 text-center">
                    Only counting leaks with statistically significant sample sizes
                  </p>
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
                          worstLeak={stats.worstLeak}
                          tendency={stats.tendency}
                          positionStats={stats.positionStats}
                          actionBreakdown={stats.actionBreakdown}
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
          <LeakAnalysisView
            gtoLeaks={filteredGTOLeaks.all}
            statLeaks={leakAnalysis?.leaks || []}
            totalHands={gtoAnalysis?.adherence?.total_hands || player.total_hands || 0}
            playerName={playerName}
            onLeakClick={setSelectedScenario}
            insufficientSamples={filteredGTOLeaks.insufficientSamples}
            priorityLeaks={gtoAnalysis?.priority_leaks}
          />
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
