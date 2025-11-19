import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useRef } from 'react';
import { ArrowLeft, TrendingUp, Target, Shield } from 'lucide-react';
import { api } from '../services/api';
import PlayerBadge from '../components/PlayerBadge';
import StatCard from '../components/StatCard';
import { Tooltip } from '../components/Tooltip';
import MetricChart from '../components/MetricChart';
import PositionalVPIPChart from '../components/PositionalVPIPChart';
import PreflopAggressionChart from '../components/PreflopAggressionChart';
import CBetStreetsChart from '../components/CBetStreetsChart';
import ShowdownChart from '../components/ShowdownChart';
import ExploitDashboard from '../components/ExploitDashboard';
import BaselineComparison from '../components/BaselineComparison';
import DeviationHeatmap from '../components/DeviationHeatmap';
import { STAT_DEFINITIONS } from '../config/statDefinitions';

// Helper function to generate tooltip content for a statistic
const getStatTooltip = (statKey: string, value?: number) => {
  const def = STAT_DEFINITIONS[statKey];
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
          <div className="text-gray-400">Optimal Range:</div>
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

  // Prepare composite metrics for radar chart
  const compositeMetrics = [
    { metric: 'EI', value: player.exploitability_index ?? 0, fullMark: 100 },
    { metric: 'PVS', value: player.pressure_vulnerability_score ?? 0, fullMark: 100 },
    { metric: 'ACR', value: player.aggression_consistency_ratio ?? 0, fullMark: 100 },
    { metric: 'PAI', value: player.positional_awareness_index ?? 0, fullMark: 100 },
    { metric: 'BDE', value: player.blind_defense_efficiency ?? 0, fullMark: 100 },
    { metric: 'MPS', value: player.multi_street_persistence_score ?? 0, fullMark: 100 },
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
          </div>
          {player.exploitability_index !== null && player.exploitability_index !== undefined && (
            <div className="text-right">
              <div className="flex items-center justify-end gap-1">
                <p className="text-sm text-gray-600">Exploitability Index</p>
                <Tooltip content={getStatTooltip('exploitability_index', player.exploitability_index)} position="bottom" iconSize={14} />
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

      {/* Traditional stats */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Traditional Statistics</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            title="VPIP%"
            value={player.vpip_pct !== null && player.vpip_pct !== undefined ? `${player.vpip_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Voluntarily Put $ In Pot"
            color="blue"
            tooltip={getStatTooltip('vpip_pct', player.vpip_pct ?? undefined)}
          />
          <StatCard
            title="PFR%"
            value={player.pfr_pct !== null && player.pfr_pct !== undefined ? `${player.pfr_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Pre-Flop Raise"
            color="green"
            tooltip={getStatTooltip('pfr_pct', player.pfr_pct ?? undefined)}
          />
          <StatCard
            title="3-Bet%"
            value={player.three_bet_pct !== null && player.three_bet_pct !== undefined ? `${player.three_bet_pct.toFixed(1)}%` : 'N/A'}
            subtitle="3-Bet Percentage"
            color="yellow"
            tooltip={getStatTooltip('three_bet_pct', player.three_bet_pct ?? undefined)}
          />
          <StatCard
            title="Fold to 3-Bet%"
            value={player.fold_to_three_bet_pct !== null && player.fold_to_three_bet_pct !== undefined ? `${player.fold_to_three_bet_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Fold to 3-Bet"
            color="red"
            tooltip={getStatTooltip('fold_to_three_bet_pct', player.fold_to_three_bet_pct ?? undefined)}
          />
          <StatCard
            title="C-Bet Flop%"
            value={player.cbet_flop_pct !== null && player.cbet_flop_pct !== undefined ? `${player.cbet_flop_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Continuation Bet"
            color="blue"
            tooltip={getStatTooltip('cbet_flop_pct', player.cbet_flop_pct ?? undefined)}
          />
          <StatCard
            title="Fold to C-Bet%"
            value={player.fold_to_cbet_flop_pct !== null && player.fold_to_cbet_flop_pct !== undefined ? `${player.fold_to_cbet_flop_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Fold to C-Bet"
            color="green"
            tooltip={getStatTooltip('fold_to_cbet_flop_pct', player.fold_to_cbet_flop_pct ?? undefined)}
          />
          <StatCard
            title="WTSD%"
            value={player.wtsd_pct !== null && player.wtsd_pct !== undefined ? `${player.wtsd_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Went To Showdown"
            color="yellow"
            tooltip={getStatTooltip('wtsd_pct', player.wtsd_pct ?? undefined)}
          />
          <StatCard
            title="W$SD%"
            value={player.wsd_pct !== null && player.wsd_pct !== undefined ? `${player.wsd_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Won $ at Showdown"
            color="gray"
            tooltip={getStatTooltip('wsd_pct', player.wsd_pct ?? undefined)}
          />
          <StatCard
            title="AF"
            value={player.af !== null && player.af !== undefined ? player.af.toFixed(2) : 'N/A'}
            subtitle="Aggression Factor"
            color="blue"
            tooltip={getStatTooltip('af', player.af ?? undefined)}
          />
          <StatCard
            title="AFQ%"
            value={player.afq !== null && player.afq !== undefined ? `${player.afq.toFixed(1)}%` : 'N/A'}
            subtitle="Aggression Frequency"
            color="green"
            tooltip={getStatTooltip('afq', player.afq ?? undefined)}
          />
          <StatCard
            title="BB/100"
            value={player.bb_per_100 !== null && player.bb_per_100 !== undefined ? `${player.bb_per_100.toFixed(1)}` : 'N/A'}
            subtitle="Big Blinds per 100 Hands"
            color={player.bb_per_100 !== null && player.bb_per_100 !== undefined && player.bb_per_100 > 0 ? 'green' : player.bb_per_100 !== null && player.bb_per_100 !== undefined && player.bb_per_100 < 0 ? 'red' : 'gray'}
            tooltip={getStatTooltip('bb_per_100', player.bb_per_100 ?? undefined)}
          />
        </div>
      </div>

      {/* Visual Analytics Section */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Visual Analytics</h2>

        {/* Row 1: Preflop and Positional */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
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

        {/* Row 2: C-Bet and Showdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CBetStreetsChart
            cbet_flop_pct={player.cbet_flop_pct}
            cbet_turn_pct={player.cbet_turn_pct}
            cbet_river_pct={player.cbet_river_pct}
          />
          <ShowdownChart
            wtsd_pct={player.wtsd_pct}
            wsd_pct={player.wsd_pct}
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

      {/* Advanced metrics */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Advanced Composite Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StatCard
            title="Pressure Vulnerability Score"
            value={player.pressure_vulnerability_score !== null && player.pressure_vulnerability_score !== undefined ? player.pressure_vulnerability_score.toFixed(1) : 'N/A'}
            subtitle="Fold frequency under pressure"
            icon={<Shield size={24} />}
            color="blue"
            tooltip={getStatTooltip('pressure_vulnerability_score', player.pressure_vulnerability_score ?? undefined)}
          />
          <StatCard
            title="Aggression Consistency Ratio"
            value={player.aggression_consistency_ratio !== null && player.aggression_consistency_ratio !== undefined ? player.aggression_consistency_ratio.toFixed(1) : 'N/A'}
            subtitle="Give-up tendency across streets"
            icon={<TrendingUp size={24} />}
            color="green"
            tooltip={getStatTooltip('aggression_consistency_ratio', player.aggression_consistency_ratio ?? undefined)}
          />
          <StatCard
            title="Positional Awareness Index"
            value={player.positional_awareness_index !== null && player.positional_awareness_index !== undefined ? player.positional_awareness_index.toFixed(1) : 'N/A'}
            subtitle="Position-specific play quality"
            icon={<Target size={24} />}
            color="yellow"
            tooltip={getStatTooltip('positional_awareness_index', player.positional_awareness_index ?? undefined)}
          />
          <StatCard
            title="Blind Defense Efficiency"
            value={player.blind_defense_efficiency !== null && player.blind_defense_efficiency !== undefined ? player.blind_defense_efficiency.toFixed(1) : 'N/A'}
            subtitle="Quality of blind defense"
            color="red"
            tooltip={getStatTooltip('blind_defense_efficiency', player.blind_defense_efficiency ?? undefined)}
          />
          <StatCard
            title="Multi-Street Persistence"
            value={player.multi_street_persistence_score !== null && player.multi_street_persistence_score !== undefined ? player.multi_street_persistence_score.toFixed(1) : 'N/A'}
            subtitle="Commitment across streets"
            color="blue"
            tooltip={getStatTooltip('multi_street_persistence_score', player.multi_street_persistence_score ?? undefined)}
          />
          <StatCard
            title="Delayed Aggression Coefficient"
            value={player.delayed_aggression_coefficient !== null && player.delayed_aggression_coefficient !== undefined ? player.delayed_aggression_coefficient.toFixed(1) : 'N/A'}
            subtitle="Check-raise and trap frequency"
            color="green"
            tooltip={getStatTooltip('delayed_aggression_coefficient', player.delayed_aggression_coefficient ?? undefined)}
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
