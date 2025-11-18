import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, TrendingUp, Target, Shield } from 'lucide-react';
import { api } from '../services/api';
import PlayerBadge from '../components/PlayerBadge';
import StatCard from '../components/StatCard';
import MetricChart from '../components/MetricChart';
import PositionalVPIPChart from '../components/PositionalVPIPChart';
import PreflopAggressionChart from '../components/PreflopAggressionChart';
import CBetStreetsChart from '../components/CBetStreetsChart';
import ShowdownChart from '../components/ShowdownChart';
import ExploitDashboard from '../components/ExploitDashboard';
import BaselineComparison from '../components/BaselineComparison';
import DeviationHeatmap from '../components/DeviationHeatmap';

const PlayerProfile = () => {
  const { playerName } = useParams<{ playerName: string }>();
  const navigate = useNavigate();

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
              <p className="text-sm text-gray-600">Exploitability Index</p>
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
          />
          <StatCard
            title="PFR%"
            value={player.pfr_pct !== null && player.pfr_pct !== undefined ? `${player.pfr_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Pre-Flop Raise"
            color="green"
          />
          <StatCard
            title="3-Bet%"
            value={player.three_bet_pct !== null && player.three_bet_pct !== undefined ? `${player.three_bet_pct.toFixed(1)}%` : 'N/A'}
            subtitle="3-Bet Percentage"
            color="yellow"
          />
          <StatCard
            title="Fold to 3-Bet%"
            value={player.fold_to_three_bet_pct !== null && player.fold_to_three_bet_pct !== undefined ? `${player.fold_to_three_bet_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Fold to 3-Bet"
            color="red"
          />
          <StatCard
            title="C-Bet Flop%"
            value={player.cbet_flop_pct !== null && player.cbet_flop_pct !== undefined ? `${player.cbet_flop_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Continuation Bet"
            color="blue"
          />
          <StatCard
            title="Fold to C-Bet%"
            value={player.fold_to_cbet_flop_pct !== null && player.fold_to_cbet_flop_pct !== undefined ? `${player.fold_to_cbet_flop_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Fold to C-Bet"
            color="green"
          />
          <StatCard
            title="WTSD%"
            value={player.wtsd_pct !== null && player.wtsd_pct !== undefined ? `${player.wtsd_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Went To Showdown"
            color="yellow"
          />
          <StatCard
            title="W$SD%"
            value={player.wsd_pct !== null && player.wsd_pct !== undefined ? `${player.wsd_pct.toFixed(1)}%` : 'N/A'}
            subtitle="Won $ at Showdown"
            color="gray"
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
              deviations={exploitAnalysis.analyses.flatMap(a => a.deviations)}
              playerName={player.player_name}
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
          <BaselineComparison
            deviations={
              exploitAnalysis.analyses
                .filter(a => a.comparison_type === 'baseline' || a.scenario === 'Poker Theory Baselines')
                .flatMap(a => a.deviations)
            }
            playerName={player.player_name}
          />
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
          />
          <StatCard
            title="Aggression Consistency Ratio"
            value={player.aggression_consistency_ratio !== null && player.aggression_consistency_ratio !== undefined ? player.aggression_consistency_ratio.toFixed(1) : 'N/A'}
            subtitle="Give-up tendency across streets"
            icon={<TrendingUp size={24} />}
            color="green"
          />
          <StatCard
            title="Positional Awareness Index"
            value={player.positional_awareness_index !== null && player.positional_awareness_index !== undefined ? player.positional_awareness_index.toFixed(1) : 'N/A'}
            subtitle="Position-specific play quality"
            icon={<Target size={24} />}
            color="yellow"
          />
          <StatCard
            title="Blind Defense Efficiency"
            value={player.blind_defense_efficiency !== null && player.blind_defense_efficiency !== undefined ? player.blind_defense_efficiency.toFixed(1) : 'N/A'}
            subtitle="Quality of blind defense"
            color="red"
          />
          <StatCard
            title="Multi-Street Persistence"
            value={player.multi_street_persistence_score !== null && player.multi_street_persistence_score !== undefined ? player.multi_street_persistence_score.toFixed(1) : 'N/A'}
            subtitle="Commitment across streets"
            color="blue"
          />
          <StatCard
            title="Delayed Aggression Coefficient"
            value={player.delayed_aggression_coefficient !== null && player.delayed_aggression_coefficient !== undefined ? player.delayed_aggression_coefficient.toFixed(1) : 'N/A'}
            subtitle="Check-raise and trap frequency"
            color="green"
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
