import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  User, TrendingUp, TrendingDown, Calendar, Clock, Target, ChevronRight,
  Settings, AlertCircle, BarChart2, Shield, AlertTriangle
} from 'lucide-react';
import { api } from '../services/api';
import { GTOCategoryDetailView, GTOCategorySummaryCard } from '../components/gto';
import LeakAnalysisView from '../components/LeakAnalysisView';
import ScenarioHandsModal, { type ScenarioSelection } from '../components/ScenarioHandsModal';
import { mapPriorityLeaksToGTOLeaks } from '../utils/gtoUtils';
import type { MyGameOverview, HeroSessionResponse, GTOAnalysisResponse, LeakAnalysisResponse } from '../types';

// Tab configuration
type TabId = 'overview' | 'gto' | 'sessions';

const TABS: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Overview', icon: User },
  { id: 'gto', label: 'GTO Analysis', icon: Target },
  { id: 'sessions', label: 'Sessions', icon: BarChart2 },
];

// GTO category configuration
type GTOCategoryKey = 'opening' | 'defense' | 'facing_3bet' | 'facing_4bet';

const GTO_CATEGORY_CONFIG: Record<GTOCategoryKey, {
  title: string;
  subtitle: string;
  icon: React.ElementType;
}> = {
  opening: {
    title: 'Opening Ranges',
    subtitle: 'RFI and Steal Attempts',
    icon: TrendingUp,
  },
  defense: {
    title: 'Defense vs Opens',
    subtitle: 'How you respond to opens',
    icon: Shield,
  },
  facing_3bet: {
    title: 'Facing 3-Bet',
    subtitle: 'After opening',
    icon: Target,
  },
  facing_4bet: {
    title: 'Facing 4-Bet',
    subtitle: 'After 3-betting',
    icon: AlertTriangle,
  },
};

const MyGame = () => {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [overview, setOverview] = useState<MyGameOverview | null>(null);
  const [sessions, setSessions] = useState<HeroSessionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // GTO analysis state
  const [selectedCategory, setSelectedCategory] = useState<GTOCategoryKey | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<ScenarioSelection | null>(null);

  // Get hero player name for links (first nickname with data)
  const heroPlayerName = overview?.stats_by_nickname?.[0]?.player_name;

  // Fetch aggregated GTO analysis across all hero nicknames
  const { data: gtoData, isLoading: gtoLoading } = useQuery<GTOAnalysisResponse>({
    queryKey: ['my-game-gto-analysis'],
    queryFn: () => api.getMyGameGTOAnalysis(),
    enabled: !!(overview && overview.hero_nicknames.length > 0 && activeTab === 'gto'),
  });

  // Fetch aggregated stat-based leak analysis across all hero nicknames
  const { data: statLeaksData } = useQuery<LeakAnalysisResponse>({
    queryKey: ['my-game-leaks'],
    queryFn: () => api.getMyGameLeaks(),
    enabled: !!(overview && overview.hero_nicknames.length > 0 && activeTab === 'gto'),
  });

  // Fetch scenario hands for drill-down modal (aggregated across all hero nicknames)
  const { data: scenarioHandsData, isLoading: scenarioHandsLoading } = useQuery({
    queryKey: ['myGameScenarioHands', selectedScenario],
    queryFn: () => api.getMyGameScenarioHands(
      selectedScenario!.scenario,
      selectedScenario!.position,
      selectedScenario!.vsPosition,
      selectedScenario!.action
    ),
    enabled: !!selectedScenario,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewData, sessionsData] = await Promise.all([
        api.getMyGameOverview(),
        api.getMyGameSessions(50)
      ]);
      setOverview(overviewData);
      setSessions(sessionsData);
    } catch (err) {
      setError('Failed to load data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatProfit = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(1)} BB`;
  };

  // Enhanced category stats with detailed info for GTOCategorySummaryCard
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
    };

    const addPositionStat = (position: string, deviation: number) => {
      const absDev = Math.abs(deviation);
      const status = absDev < 5 ? 'good' : absDev < 10 ? 'warning' : 'bad';
      positionStats.push({ position, deviation, status });
    };

    switch (category) {
      case 'opening':
        data.opening_ranges?.forEach(row => {
          processRow(row, 'frequency_diff', 'total_hands', true);
          addPositionStat(row.position, row.frequency_diff);
        });
        // Calculate tendency for opening
        if (data.opening_ranges?.length) {
          const avgDiff = data.opening_ranges.reduce((sum, r) => sum + (r.frequency_diff || 0), 0) / data.opening_ranges.length;
          tendencySum = avgDiff;
        }
        break;

      case 'defense':
        let totalPlayerFold = 0, totalGtoFold = 0, totalPlayer3bet = 0, totalGto3bet = 0, defenseCount = 0;
        data.defense_vs_open?.forEach(row => {
          processRow({ ...row }, 'fold_diff', 'sample_size', false);
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
          processRow(row, 'fold_diff', 'sample_size', false);
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

  // Handle scenario click - show hands modal inline
  const handleRowClick = (selection: ScenarioSelection) => {
    setSelectedScenario(selection);
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto flex items-center justify-center py-20">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  // No hero nicknames configured
  if (overview && overview.hero_nicknames.length === 0) {
    return (
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">My Game</h1>
        <div className="card text-center py-12">
          <User className="mx-auto text-gray-400 mb-4" size={48} />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No Nicknames Configured</h2>
          <p className="text-gray-600 mb-6">
            Add your poker screen names in Settings to start tracking your game.
          </p>
          <Link
            to="/settings"
            className="inline-flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <Settings size={18} />
            <span>Go to Settings</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">My Game</h1>
          <p className="mt-1 text-gray-600">
            Your performance with hole card analysis
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {overview?.hero_nicknames.map(nickname => (
            <span key={nickname} className="px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full text-sm font-medium">
              {nickname}
            </span>
          ))}
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg flex items-center space-x-2">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setSelectedCategory(null);
              }}
              className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <tab.icon size={18} />
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Stats overview */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="card">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Calendar className="text-blue-600" size={20} />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Sessions</p>
                  <p className="text-xl font-bold text-gray-900">{overview?.total_sessions || 0}</p>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Target className="text-purple-600" size={20} />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Hands</p>
                  <p className="text-xl font-bold text-gray-900">
                    {(overview?.total_hands || 0).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-lg ${(overview?.total_profit_bb || 0) >= 0 ? 'bg-green-100' : 'bg-red-100'}`}>
                  {(overview?.total_profit_bb || 0) >= 0 ? (
                    <TrendingUp className="text-green-600" size={20} />
                  ) : (
                    <TrendingDown className="text-red-600" size={20} />
                  )}
                </div>
                <div>
                  <p className="text-sm text-gray-500">Total P/L</p>
                  <p className={`text-xl font-bold ${(overview?.total_profit_bb || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatProfit(overview?.total_profit_bb || 0)}
                  </p>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-lg ${(overview?.avg_bb_100 || 0) >= 0 ? 'bg-green-100' : 'bg-red-100'}`}>
                  <Clock className={`${(overview?.avg_bb_100 || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`} size={20} />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Win Rate</p>
                  <p className={`text-xl font-bold ${(overview?.avg_bb_100 || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {(overview?.avg_bb_100 || 0).toFixed(1)} bb/100
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Quick links */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={() => setActiveTab('gto')}
              className="card hover:border-indigo-300 transition-colors group text-left"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">GTO Analysis</h3>
                  <p className="text-sm text-gray-500">Find your leaks</p>
                </div>
                <ChevronRight className="text-gray-400 group-hover:text-indigo-500 transition-colors" size={20} />
              </div>
            </button>

            <button
              onClick={() => setActiveTab('sessions')}
              className="card hover:border-indigo-300 transition-colors group text-left"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">Sessions</h3>
                  <p className="text-sm text-gray-500">View all your sessions</p>
                </div>
                <ChevronRight className="text-gray-400 group-hover:text-indigo-500 transition-colors" size={20} />
              </div>
            </button>

            <Link to="/gto-browser" className="card hover:border-indigo-300 transition-colors group">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">GTO Ranges</h3>
                  <p className="text-sm text-gray-500">Study optimal ranges</p>
                </div>
                <ChevronRight className="text-gray-400 group-hover:text-indigo-500 transition-colors" size={20} />
              </div>
            </Link>
          </div>

          {/* Recent sessions preview */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Recent Sessions</h2>
              <button
                onClick={() => setActiveTab('sessions')}
                className="text-sm text-indigo-600 hover:text-indigo-800"
              >
                View all
              </button>
            </div>

            {sessions.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Calendar className="mx-auto mb-2" size={32} />
                <p>No sessions yet</p>
              </div>
            ) : (
              <div className="space-y-2">
                {sessions.slice(0, 5).map(session => (
                  <Link
                    key={session.session_id}
                    to={`/sessions/${session.session_id}`}
                    className="block p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">{session.table_stakes}</p>
                        <p className="text-sm text-gray-500">
                          {formatDate(session.start_time)} · {session.total_hands} hands
                        </p>
                      </div>
                      <p className={`font-bold ${session.profit_loss_bb >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatProfit(session.profit_loss_bb)}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'gto' && (
        <div className="space-y-6">
          {gtoLoading ? (
            <div className="text-center py-12 text-gray-500">Loading GTO analysis...</div>
          ) : !gtoData ? (
            <div className="text-center py-12 text-gray-500">
              <Target className="mx-auto mb-2" size={32} />
              <p>No GTO data available</p>
              <p className="text-sm mt-1">Upload hand histories to see your GTO analysis</p>
            </div>
          ) : selectedCategory ? (
            /* Category Detail View */
            <GTOCategoryDetailView
              category={selectedCategory}
              data={gtoData}
              onBack={() => setSelectedCategory(null)}
              onRowClick={handleRowClick}
            />
          ) : (
            <>
              {/* Priority Leaks */}
              {gtoData.priority_leaks && gtoData.priority_leaks.length > 0 && (
                <LeakAnalysisView
                  gtoLeaks={mapPriorityLeaksToGTOLeaks(gtoData.priority_leaks)}
                  statLeaks={statLeaksData?.leaks || []}
                  totalHands={gtoData.adherence?.total_hands || overview?.total_hands || 0}
                  playerName="Hero"
                  priorityLeaks={gtoData.priority_leaks}
                  onLeakClick={(selection) => handleRowClick(selection)}
                />
              )}

              {/* Category Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {(Object.keys(GTO_CATEGORY_CONFIG) as GTOCategoryKey[]).map(categoryKey => {
                  const config = GTO_CATEGORY_CONFIG[categoryKey];
                  const stats = calculateCategoryStats(categoryKey, gtoData);

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
                      onClick={() => setSelectedCategory(categoryKey)}
                    />
                  );
                })}
              </div>

              {/* Link to full player profile for more details */}
              {heroPlayerName && (
                <div className="text-center">
                  <Link
                    to={`/players/${encodeURIComponent(heroPlayerName)}`}
                    className="inline-flex items-center space-x-2 text-indigo-600 hover:text-indigo-800"
                  >
                    <span>View full analysis with hand replayer</span>
                    <ChevronRight size={16} />
                  </Link>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {activeTab === 'sessions' && (
        <div className="space-y-4">
          {sessions.length === 0 ? (
            <div className="card text-center py-12 text-gray-500">
              <Calendar className="mx-auto mb-2" size={32} />
              <p>No sessions yet</p>
              <p className="text-sm">Upload hand histories to see your sessions</p>
            </div>
          ) : (
            <div className="space-y-2">
              {sessions.map(session => (
                <Link
                  key={session.session_id}
                  to={`/sessions/${session.session_id}`}
                  className="block card hover:border-indigo-300 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div>
                        <p className="font-medium text-gray-900">
                          {session.table_stakes}
                          {session.table_name && (
                            <span className="text-gray-500 ml-2">{session.table_name}</span>
                          )}
                        </p>
                        <p className="text-sm text-gray-500">
                          {formatDate(session.start_time)} · {session.total_hands} hands · {session.duration_minutes}min
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`font-bold ${session.profit_loss_bb >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatProfit(session.profit_loss_bb)}
                      </p>
                      <p className={`text-sm ${session.bb_100 >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {session.bb_100.toFixed(1)} bb/100
                      </p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Scenario Hands Drill-down Modal */}
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

export default MyGame;
