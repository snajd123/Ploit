import React, { useState, useMemo } from 'react';
import { TrendingDown, TrendingUp, Phone, AlertTriangle, CheckCircle, ChevronRight, Target, Zap, Lightbulb, Sparkles } from 'lucide-react';
import ImprovementAdviceModal from './ImprovementAdviceModal';
import AILeakAnalysisModal from './AILeakAnalysisModal';

// Advice modal state
interface AdviceModalState {
  isOpen: boolean;
  leakCategory: string;
  leakDirection: string;
  position: string;
  vsPosition?: string | null;
  playerValue: number;
  gtoValue: number;
  sampleSize: number;
}

// Types
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

interface StatBasedLeak {
  stat: string;
  player_value: number;
  gto_baseline: number;
  deviation: number;
  direction: 'high' | 'low';
  severity: 'minor' | 'moderate' | 'major' | 'critical';
  tendency: string;
  exploit: string;
  ev_impact_bb_100: number;
}

// Tendency types
type TendencyType = 'fold_too_much' | 'call_too_much' | 'not_aggressive' | 'too_aggressive';

interface TendencyBucket {
  type: TendencyType;
  title: string;
  subtitle: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  leaks: (GTOPositionalLeak | StatBasedLeak & { isStatBased: true })[];
  totalEvImpact: number;
}

// Scenario selection for drill-down
interface ScenarioSelection {
  scenario: 'opening' | 'defense' | 'facing_3bet' | 'facing_4bet';
  position: string;
  vsPosition?: string;
}

// Insufficient sample info
interface InsufficientSampleInfo {
  category: string;
  count: number;
  minRequired: number;
}

interface LeakAnalysisViewProps {
  gtoLeaks: GTOPositionalLeak[];
  statLeaks: StatBasedLeak[];
  totalHands: number;
  playerName?: string;  // For fetching player-specific hand data
  onLeakClick?: (selection: ScenarioSelection) => void;
  insufficientSamples?: InsufficientSampleInfo[];
}

// Map leak category to scenario type
const mapCategoryToScenario = (category: string): ScenarioSelection['scenario'] | null => {
  switch (category) {
    case 'Opening': return 'opening';
    case 'Defense': return 'defense';
    case 'Facing 3-Bet': return 'facing_3bet';
    case 'Facing 4-Bet': return 'facing_4bet';
    default: return null;
  }
};

// Categorize a leak into a tendency bucket
const categorizeLeak = (leak: GTOPositionalLeak): TendencyType | null => {
  const { action, deviation } = leak;

  // Positive deviation = player does MORE than GTO
  // Negative deviation = player does LESS than GTO

  if (action === 'Fold') {
    // Over-folding = folding too much = too tight
    // Under-folding = not folding enough = defending too much = too loose
    return deviation > 0 ? 'fold_too_much' : 'call_too_much';
  }
  if (action === 'Call') {
    // Over-calling = calling too much
    // Under-calling = not calling enough = might be folding or raising instead
    return deviation > 0 ? 'call_too_much' : 'fold_too_much';
  }
  if (action === 'RFI' || action === '3-Bet' || action === '4-Bet' || action === '5-Bet') {
    if (deviation > 0) return 'too_aggressive'; // Over-raising
    if (deviation < 0) return 'not_aggressive'; // Under-raising
  }

  return null;
};

// Categorize stat-based leak
const categorizeStatLeak = (leak: StatBasedLeak): TendencyType | null => {
  const { stat, direction } = leak;

  // VPIP/PFR high = loose/aggressive, low = tight/passive
  if (stat === 'vpip' || stat === 'pfr') {
    return direction === 'high' ? 'too_aggressive' : 'not_aggressive';
  }
  // 3-bet high = aggressive, low = passive
  if (stat === 'three_bet' || stat === 'four_bet') {
    return direction === 'high' ? 'too_aggressive' : 'not_aggressive';
  }
  // Fold to 3-bet high = folding too much
  if (stat === 'fold_to_three_bet') {
    return direction === 'high' ? 'fold_too_much' : 'call_too_much';
  }
  // Cold call high = calling too much
  if (stat === 'cold_call') {
    return direction === 'high' ? 'call_too_much' : null;
  }

  return null;
};

// Estimate EV impact for a positional leak (simplified)
const estimateEvImpact = (leak: GTOPositionalLeak): number => {
  const { category, deviation, sampleSize } = leak;
  const absDeviation = Math.abs(deviation);

  // Base EV factor varies by scenario (BB/100 per % deviation)
  let evFactor = 0.02; // Default
  if (category === 'Defense') evFactor = 0.03; // Blind defense is high EV
  if (category === 'Facing 3-Bet') evFactor = 0.025;
  if (category === 'Opening') evFactor = 0.015;

  // Frequency factor (how often does this occur per 100 hands)
  const frequencyFactor = Math.min(sampleSize / 100, 1); // Normalize

  return absDeviation * evFactor * frequencyFactor;
};

// Get letter grade from EV loss
const getLeakGrade = (totalEvLoss: number): { grade: string; color: string } => {
  if (totalEvLoss < 1) return { grade: 'A', color: 'text-green-600' };
  if (totalEvLoss < 2) return { grade: 'B+', color: 'text-green-500' };
  if (totalEvLoss < 3) return { grade: 'B', color: 'text-yellow-600' };
  if (totalEvLoss < 4) return { grade: 'C+', color: 'text-yellow-600' };
  if (totalEvLoss < 6) return { grade: 'C', color: 'text-orange-500' };
  if (totalEvLoss < 8) return { grade: 'D', color: 'text-orange-600' };
  return { grade: 'F', color: 'text-red-600' };
};

// Get tendency label from buckets
const getPrimaryTendency = (buckets: TendencyBucket[]): string => {
  const sorted = [...buckets].sort((a, b) => b.totalEvImpact - a.totalEvImpact);
  if (sorted[0].totalEvImpact === 0) return 'Balanced';

  const primary = sorted[0].type;
  if (primary === 'fold_too_much') return 'Tight-Passive';
  if (primary === 'call_too_much') return 'Loose-Passive';
  if (primary === 'not_aggressive') return 'Passive';
  if (primary === 'too_aggressive') return 'Aggressive';
  return 'Mixed';
};

// Tendency card component
const TendencyCard: React.FC<{
  bucket: TendencyBucket;
  onClick: () => void;
  isExpanded: boolean;
}> = ({ bucket, onClick, isExpanded }) => {
  const Icon = bucket.icon;
  const hasLeaks = bucket.leaks.length > 0;

  return (
    <button
      onClick={onClick}
      disabled={!hasLeaks}
      className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
        hasLeaks
          ? `${bucket.bgColor} ${bucket.color} border-current hover:shadow-md cursor-pointer`
          : 'bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed'
      } ${isExpanded ? 'ring-2 ring-offset-2' : ''}`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon size={20} />
          <span className="font-semibold">{bucket.title}</span>
        </div>
        {hasLeaks && <ChevronRight size={18} className={isExpanded ? 'rotate-90' : ''} />}
      </div>
      <p className="text-xs opacity-75 mb-3">{bucket.subtitle}</p>

      <div className="flex items-center justify-between">
        <span className={`text-sm font-medium ${hasLeaks ? '' : 'text-gray-400'}`}>
          {bucket.leaks.length} leak{bucket.leaks.length !== 1 ? 's' : ''}
        </span>
        {hasLeaks && bucket.totalEvImpact > 0 && (
          <span className="text-sm font-bold">
            ~{bucket.totalEvImpact.toFixed(1)} BB/100
          </span>
        )}
      </div>

      {/* Impact bar */}
      <div className="mt-2 h-2 bg-white/50 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${hasLeaks ? 'bg-current opacity-60' : 'bg-gray-300'}`}
          style={{ width: `${Math.min(bucket.totalEvImpact * 15, 100)}%` }}
        />
      </div>
    </button>
  );
};

// Helper function to map category to leak category
const mapCategoryToLeakCategory = (category: string): string => {
  const mapping: Record<string, string> = {
    'Opening': 'opening',
    'Defense': 'defense',
    'Facing 3-Bet': 'facing_3bet',
    'Facing 4-Bet': 'facing_4bet',
  };
  return mapping[category] || 'opening';
};

// Helper function to determine leak direction
const getLeakDirection = (deviation: number, action: string): string => {
  // For fold actions, positive deviation means folding too much
  if (action === 'Fold') {
    return deviation > 0 ? 'too_tight' : 'too_loose';
  }
  // For aggressive actions (raise, 3bet, etc.), positive deviation means too aggressive
  return deviation > 0 ? 'too_loose' : 'too_tight';
};

// Priority fix item
const PriorityFix: React.FC<{
  rank: number;
  leak: GTOPositionalLeak | (StatBasedLeak & { isStatBased: true });
  evImpact: number;
  onGetAdvice?: (leak: GTOPositionalLeak | (StatBasedLeak & { isStatBased: true })) => void;
  onViewHands?: (leak: GTOPositionalLeak) => void;
}> = ({ rank, leak, evImpact, onGetAdvice, onViewHands }) => {
  const isStatBased = 'isStatBased' in leak;
  const isMajor = isStatBased
    ? (leak as StatBasedLeak).severity === 'major' || (leak as StatBasedLeak).severity === 'critical'
    : leak.severity === 'major';

  const description = isStatBased
    ? `${(leak as StatBasedLeak).tendency}`
    : `${leak.action} in ${leak.position}${leak.vsPosition ? ` vs ${leak.vsPosition}` : ''}: ${leak.playerValue.toFixed(0)}% vs ${leak.gtoValue.toFixed(0)}% GTO`;

  return (
    <div className="flex items-start gap-3 p-3 bg-white rounded-lg border border-gray-200 hover:border-purple-300 transition-colors">
      <span className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white ${
        isMajor ? 'bg-red-500' : 'bg-yellow-500'
      }`}>
        {rank}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-900 font-medium truncate">{description}</p>
        <p className="text-xs text-gray-500">
          {isStatBased
            ? `${(leak as StatBasedLeak).player_value.toFixed(0)}% vs ${(leak as StatBasedLeak).gto_baseline.toFixed(0)}% GTO`
            : `${leak.category} • ${leak.sampleSize} hands`
          }
        </p>
      </div>
      <div className="flex items-center gap-3">
        <div className="text-right">
          <span className="text-sm font-bold text-red-600">~{evImpact.toFixed(1)}</span>
          <span className="text-xs text-gray-500 block">BB/100</span>
        </div>
        {!isStatBased && (
          <div className="flex items-center gap-1">
            {onViewHands && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onViewHands(leak as GTOPositionalLeak);
                }}
                className="flex items-center gap-1 px-2 py-1 bg-blue-100 hover:bg-blue-200 text-blue-700 text-xs font-medium rounded-lg transition-colors"
                title="View hands in replayer"
              >
                <ChevronRight size={12} />
                Hands
              </button>
            )}
            {onGetAdvice && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onGetAdvice(leak);
                }}
                className="flex items-center gap-1 px-2 py-1 bg-purple-100 hover:bg-purple-200 text-purple-700 text-xs font-medium rounded-lg transition-colors"
                title="Get improvement advice"
              >
                <Lightbulb size={12} />
                Fix
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Leak detail row
const LeakDetailRow: React.FC<{
  leak: GTOPositionalLeak;
  onViewHands?: () => void;
  onGetAdvice?: () => void;
}> = ({ leak, onViewHands, onGetAdvice }) => {
  const isMajor = leak.severity === 'major';
  const absDeviation = Math.abs(leak.deviation);

  return (
    <div className="p-3 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            isMajor ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
          }`}>
            {leak.severity}
          </span>
          <span className="font-medium text-gray-900">
            {leak.position}{leak.vsPosition ? ` vs ${leak.vsPosition}` : ''}
          </span>
          <span className="text-gray-500 text-sm">• {leak.action}</span>
        </div>
        <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
          leak.confidence === 'high' ? 'bg-green-100 text-green-700' :
          leak.confidence === 'moderate' ? 'bg-yellow-100 text-yellow-700' :
          'bg-orange-100 text-orange-700'
        }`}>
          {leak.sampleSize} hands
        </span>
      </div>

      {/* Visual bar comparison */}
      <div className="space-y-1">
        <div className="flex items-center gap-2 text-xs">
          <span className="w-12 text-gray-500">You</span>
          <div className="flex-1 h-4 bg-gray-100 rounded relative">
            <div
              className={`h-full rounded ${leak.deviation > 0 ? 'bg-red-400' : 'bg-blue-400'}`}
              style={{ width: `${Math.min(leak.playerValue, 100)}%` }}
            />
            <span className="absolute right-2 top-0 text-xs font-medium leading-4">
              {leak.playerValue.toFixed(0)}%
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="w-12 text-blue-600">GTO</span>
          <div className="flex-1 h-4 bg-blue-50 rounded relative">
            <div
              className="h-full rounded bg-blue-300"
              style={{ width: `${Math.min(leak.gtoValue, 100)}%` }}
            />
            <span className="absolute right-2 top-0 text-xs font-medium leading-4 text-blue-700">
              {leak.gtoValue.toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      <div className="mt-2 flex items-center justify-between text-xs">
        <span className={`font-medium ${absDeviation > 15 ? 'text-red-600' : 'text-yellow-600'}`}>
          Gap: {leak.deviation > 0 ? '+' : ''}{leak.deviation.toFixed(0)}%
        </span>
        <div className="flex items-center gap-2">
          <span className="text-gray-500">{leak.category}</span>
          {onGetAdvice && (
            <button
              onClick={onGetAdvice}
              className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-purple-600 hover:text-purple-800 hover:bg-purple-50 rounded transition-colors"
            >
              <Lightbulb size={12} />
              How to Fix
            </button>
          )}
          {onViewHands && (
            <button
              onClick={onViewHands}
              className="px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors"
            >
              View Hands →
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// Main component
const LeakAnalysisView: React.FC<LeakAnalysisViewProps> = ({
  gtoLeaks,
  statLeaks,
  totalHands,
  playerName,
  onLeakClick,
  insufficientSamples = [],
}) => {
  const [expandedTendency, setExpandedTendency] = useState<TendencyType | null>(null);
  const [showAIAnalysis, setShowAIAnalysis] = useState(false);
  const [adviceModal, setAdviceModal] = useState<AdviceModalState>({
    isOpen: false,
    leakCategory: '',
    leakDirection: '',
    position: '',
    vsPosition: null,
    playerValue: 0,
    gtoValue: 0,
    sampleSize: 0
  });

  // Handle opening the advice modal
  const handleGetAdvice = (leak: GTOPositionalLeak | (StatBasedLeak & { isStatBased: true })) => {
    if ('isStatBased' in leak) {
      // Stat-based leaks not supported yet for advice
      return;
    }

    const gtoLeak = leak as GTOPositionalLeak;
    setAdviceModal({
      isOpen: true,
      leakCategory: mapCategoryToLeakCategory(gtoLeak.category),
      leakDirection: getLeakDirection(gtoLeak.deviation, gtoLeak.action),
      position: gtoLeak.position,
      vsPosition: gtoLeak.vsPosition || null,
      playerValue: gtoLeak.playerValue,
      gtoValue: gtoLeak.gtoValue,
      sampleSize: gtoLeak.sampleSize
    });
  };

  const closeAdviceModal = () => {
    setAdviceModal(prev => ({ ...prev, isOpen: false }));
  };

  // Create tendency buckets
  const tendencyBuckets = useMemo((): TendencyBucket[] => {
    const buckets: Record<TendencyType, TendencyBucket> = {
      fold_too_much: {
        type: 'fold_too_much',
        title: 'Folding Too Much',
        subtitle: 'Over-folding to aggression',
        icon: TrendingDown,
        color: 'text-red-700',
        bgColor: 'bg-red-50',
        leaks: [],
        totalEvImpact: 0,
      },
      call_too_much: {
        type: 'call_too_much',
        title: 'Calling Too Much',
        subtitle: 'Over-calling instead of raising/folding',
        icon: Phone,
        color: 'text-orange-700',
        bgColor: 'bg-orange-50',
        leaks: [],
        totalEvImpact: 0,
      },
      not_aggressive: {
        type: 'not_aggressive',
        title: 'Not Aggressive Enough',
        subtitle: 'Under-raising and missing value',
        icon: TrendingUp,
        color: 'text-yellow-700',
        bgColor: 'bg-yellow-50',
        leaks: [],
        totalEvImpact: 0,
      },
      too_aggressive: {
        type: 'too_aggressive',
        title: 'Too Aggressive',
        subtitle: 'Over-betting and spewing chips',
        icon: Zap,
        color: 'text-purple-700',
        bgColor: 'bg-purple-50',
        leaks: [],
        totalEvImpact: 0,
      },
    };

    // Categorize GTO leaks
    gtoLeaks.forEach(leak => {
      const tendency = categorizeLeak(leak);
      if (tendency) {
        buckets[tendency].leaks.push(leak);
        buckets[tendency].totalEvImpact += estimateEvImpact(leak);
      }
    });

    // Categorize stat-based leaks
    statLeaks.forEach(leak => {
      const tendency = categorizeStatLeak(leak);
      if (tendency) {
        buckets[tendency].leaks.push({ ...leak, isStatBased: true } as any);
        buckets[tendency].totalEvImpact += leak.ev_impact_bb_100;
      }
    });

    return Object.values(buckets);
  }, [gtoLeaks, statLeaks]);

  // Calculate totals
  const totalEvLoss = tendencyBuckets.reduce((sum, b) => sum + b.totalEvImpact, 0);
  const { grade, color: gradeColor } = getLeakGrade(totalEvLoss);
  const primaryTendency = getPrimaryTendency(tendencyBuckets);

  // Get top 3 priority fixes
  const priorityFixes = useMemo(() => {
    const allLeaks: { leak: any; evImpact: number }[] = [];

    gtoLeaks.forEach(leak => {
      allLeaks.push({ leak, evImpact: estimateEvImpact(leak) });
    });

    statLeaks.forEach(leak => {
      allLeaks.push({ leak: { ...leak, isStatBased: true }, evImpact: leak.ev_impact_bb_100 });
    });

    return allLeaks
      .sort((a, b) => b.evImpact - a.evImpact)
      .slice(0, 3);
  }, [gtoLeaks, statLeaks]);

  // Get leaks for expanded tendency
  const expandedLeaks = expandedTendency
    ? tendencyBuckets.find(b => b.type === expandedTendency)?.leaks || []
    : [];

  return (
    <div className="space-y-6">
      {/* Header Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Leak Grade */}
        <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-5 border border-gray-200">
          <div className="text-center">
            <p className="text-sm text-gray-600 mb-1">Leak Grade</p>
            <p className={`text-5xl font-bold ${gradeColor}`}>{grade}</p>
            <p className="text-sm text-gray-500 mt-1">{primaryTendency}</p>
            <div className="mt-3 pt-3 border-t border-gray-200">
              <p className="text-xs text-gray-500">Estimated Cost</p>
              <p className="text-lg font-bold text-red-600">~{totalEvLoss.toFixed(1)} BB/100</p>
            </div>
            {/* AI Analysis Button */}
            {playerName && (
              <button
                onClick={() => setShowAIAnalysis(true)}
                className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-lg hover:from-purple-700 hover:to-purple-800 transition-all shadow-md hover:shadow-lg"
              >
                <Sparkles size={16} />
                <span className="font-medium">AI Analysis</span>
              </button>
            )}
          </div>
        </div>

        {/* Top 3 Priority Fixes */}
        <div className="md:col-span-2 bg-white rounded-xl p-5 border border-gray-200">
          <div className="flex items-center gap-2 mb-3">
            <Target size={18} className="text-purple-600" />
            <h3 className="font-semibold text-gray-900">Priority Fixes</h3>
          </div>

          {priorityFixes.length > 0 ? (
            <div className="space-y-2">
              {priorityFixes.map((fix, idx) => {
                // Create handler for viewing hands (only for GTO leaks, not stat-based)
                const handleViewHands = !('isStatBased' in fix.leak) && onLeakClick
                  ? (leak: GTOPositionalLeak) => {
                      const scenario = mapCategoryToScenario(leak.category);
                      if (scenario) {
                        onLeakClick({
                          scenario,
                          position: leak.position,
                          vsPosition: leak.vsPosition,
                        });
                      }
                    }
                  : undefined;

                return (
                  <PriorityFix
                    key={idx}
                    rank={idx + 1}
                    leak={fix.leak}
                    evImpact={fix.evImpact}
                    onGetAdvice={handleGetAdvice}
                    onViewHands={handleViewHands}
                  />
                );
              })}
            </div>
          ) : (
            <div className="text-center py-6 text-gray-500">
              <CheckCircle size={32} className="mx-auto mb-2 text-green-500" />
              <p>No significant leaks found</p>
              {insufficientSamples.length > 0 && (
                <p className="text-xs text-gray-400 mt-2">
                  Note: {insufficientSamples.map(s => s.category).join(', ')} excluded due to low sample size
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Tendency Breakdown */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <AlertTriangle size={18} className="text-yellow-600" />
          Leak Categories
          <span className="text-sm font-normal text-gray-500">(click to expand)</span>
        </h3>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {tendencyBuckets.map(bucket => (
            <TendencyCard
              key={bucket.type}
              bucket={bucket}
              onClick={() => setExpandedTendency(
                expandedTendency === bucket.type ? null : bucket.type
              )}
              isExpanded={expandedTendency === bucket.type}
            />
          ))}
        </div>
      </div>

      {/* Expanded Tendency Detail */}
      {expandedTendency && expandedLeaks.length > 0 && (
        <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-semibold text-gray-900">
              {tendencyBuckets.find(b => b.type === expandedTendency)?.title} - Details
            </h4>
            <button
              onClick={() => setExpandedTendency(null)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Close
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {expandedLeaks
              .filter((leak): leak is GTOPositionalLeak => !('isStatBased' in leak))
              .sort((a, b) => Math.abs(b.deviation) - Math.abs(a.deviation))
              .map((leak, idx) => {
                const scenario = mapCategoryToScenario(leak.category);
                const handleViewHands = scenario && onLeakClick
                  ? () => onLeakClick({
                      scenario,
                      position: leak.position,
                      vsPosition: leak.vsPosition,
                    })
                  : undefined;

                return (
                  <LeakDetailRow
                    key={idx}
                    leak={leak}
                    onViewHands={handleViewHands}
                    onGetAdvice={() => handleGetAdvice(leak)}
                  />
                );
              })
            }
          </div>

          {/* Stat-based leaks in this category */}
          {expandedLeaks.some(l => 'isStatBased' in l) && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <h5 className="text-sm font-medium text-gray-700 mb-2">Overall Stats</h5>
              <div className="space-y-2">
                {expandedLeaks
                  .filter((leak): leak is StatBasedLeak & { isStatBased: true } => 'isStatBased' in leak)
                  .map((leak, idx) => (
                    <div key={idx} className="p-3 bg-white rounded-lg border border-gray-200">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-gray-900">{leak.stat.replace(/_/g, ' ').toUpperCase()}</span>
                        <span className={`text-sm font-bold ${leak.deviation > 0 ? 'text-red-600' : 'text-blue-600'}`}>
                          {leak.deviation > 0 ? '+' : ''}{leak.deviation.toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{leak.tendency}</p>
                      <div className="mt-2 p-2 bg-purple-50 rounded text-xs text-purple-800">
                        <span className="font-medium">Exploit:</span> {leak.exploit}
                      </div>
                    </div>
                  ))
                }
              </div>
            </div>
          )}
        </div>
      )}

      {/* Confidence note */}
      <p className="text-xs text-gray-400 text-center">
        Based on {totalHands.toLocaleString()} hands analyzed.
        Only showing statistically significant leaks.
        BB/100 estimates are approximate and may vary based on opponent pool.
      </p>

      {/* Improvement Advice Modal */}
      <ImprovementAdviceModal
        isOpen={adviceModal.isOpen}
        onClose={closeAdviceModal}
        leakCategory={adviceModal.leakCategory}
        leakDirection={adviceModal.leakDirection}
        position={adviceModal.position}
        vsPosition={adviceModal.vsPosition}
        playerValue={adviceModal.playerValue}
        gtoValue={adviceModal.gtoValue}
        sampleSize={adviceModal.sampleSize}
        playerName={playerName}
      />

      {/* AI Leak Analysis Modal */}
      {playerName && (
        <AILeakAnalysisModal
          isOpen={showAIAnalysis}
          onClose={() => setShowAIAnalysis(false)}
          playerName={playerName}
        />
      )}
    </div>
  );
};

export default LeakAnalysisView;
