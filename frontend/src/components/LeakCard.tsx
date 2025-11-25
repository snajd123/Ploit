import React from 'react';
import { AlertTriangle, TrendingUp, TrendingDown, Target, Zap } from 'lucide-react';

interface Leak {
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

interface LeakCardProps {
  leak: Leak;
  showDetails?: boolean;
}

const severityConfig = {
  minor: {
    color: 'border-yellow-200 bg-yellow-50',
    badge: 'bg-yellow-100 text-yellow-800',
    label: 'Minor'
  },
  moderate: {
    color: 'border-orange-200 bg-orange-50',
    badge: 'bg-orange-100 text-orange-800',
    label: 'Moderate'
  },
  major: {
    color: 'border-red-200 bg-red-50',
    badge: 'bg-red-100 text-red-800',
    label: 'Major'
  },
  critical: {
    color: 'border-red-300 bg-red-100',
    badge: 'bg-red-200 text-red-900',
    label: 'Critical'
  }
};

const statLabels: Record<string, string> = {
  vpip: 'VPIP',
  pfr: 'PFR',
  three_bet: '3-Bet%',
  fold_to_three_bet: 'Fold to 3-Bet',
  cbet_flop: 'C-Bet Flop',
  fold_to_cbet_flop: 'Fold to C-Bet',
  wtsd: 'WTSD',
  wsd: 'W$SD'
};

const LeakCard: React.FC<LeakCardProps> = ({ leak, showDetails = true }) => {
  const config = severityConfig[leak.severity];
  const TrendIcon = leak.direction === 'high' ? TrendingUp : TrendingDown;

  return (
    <div className={`rounded-lg border p-4 ${config.color}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <AlertTriangle size={18} className="text-gray-600" />
          <span className="font-semibold text-gray-900">
            {statLabels[leak.stat] || leak.stat}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${config.badge}`}>
            {config.label}
          </span>
        </div>
        <div className="flex items-center gap-1 text-sm">
          <TrendIcon size={14} className={leak.direction === 'high' ? 'text-red-500' : 'text-blue-500'} />
          <span className="font-medium">
            {leak.deviation > 0 ? '+' : ''}{leak.deviation.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Values comparison */}
      <div className="flex items-center gap-4 text-sm mb-3">
        <div>
          <span className="text-gray-500">Player:</span>
          <span className="font-semibold text-gray-900 ml-1">{leak.player_value.toFixed(1)}%</span>
        </div>
        <div>
          <span className="text-gray-500">GTO:</span>
          <span className="font-semibold text-gray-600 ml-1">{leak.gto_baseline.toFixed(1)}%</span>
        </div>
        <div className="flex items-center gap-1">
          <Zap size={14} className="text-green-600" />
          <span className="text-green-700 font-medium">+{leak.ev_impact_bb_100.toFixed(1)} BB/100</span>
        </div>
      </div>

      {showDetails && (
        <>
          {/* Tendency */}
          <p className="text-sm text-gray-700 mb-2">
            <span className="font-medium">Tendency:</span> {leak.tendency}
          </p>

          {/* Exploit recommendation */}
          <div className="flex items-start gap-2 p-2 bg-white/50 rounded border border-gray-200">
            <Target size={16} className="text-purple-600 mt-0.5 flex-shrink-0" />
            <div>
              <span className="text-xs font-semibold text-purple-700 uppercase">How to Exploit</span>
              <p className="text-sm text-gray-800">{leak.exploit}</p>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default LeakCard;

// Leak summary component
interface LeakSummaryProps {
  totalLeaks: number;
  criticalLeaks: number;
  majorLeaks: number;
  totalEvOpportunity: number;
  reliability: string;
}

export const LeakSummary: React.FC<LeakSummaryProps> = ({
  totalLeaks,
  criticalLeaks,
  majorLeaks,
  totalEvOpportunity,
  reliability
}) => {
  const getReliabilityColor = () => {
    switch (reliability) {
      case 'high':
      case 'good':
        return 'text-green-600';
      case 'moderate':
        return 'text-yellow-600';
      default:
        return 'text-gray-500';
    }
  };

  return (
    <div className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg p-4 border border-purple-200">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">Leak Analysis Summary</h3>
        <span className={`text-sm ${getReliabilityColor()}`}>
          {reliability} confidence
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">{totalLeaks}</div>
          <div className="text-xs text-gray-600">Total Leaks</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-red-600">{criticalLeaks}</div>
          <div className="text-xs text-gray-600">Critical</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-orange-600">{majorLeaks}</div>
          <div className="text-xs text-gray-600">Major</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">+{totalEvOpportunity.toFixed(1)}</div>
          <div className="text-xs text-gray-600">BB/100 Potential</div>
        </div>
      </div>
    </div>
  );
};

// Leaks list component
interface LeaksListProps {
  leaks: Leak[];
  maxLeaks?: number;
}

export const LeaksList: React.FC<LeaksListProps> = ({ leaks, maxLeaks = 5 }) => {
  const displayLeaks = leaks.slice(0, maxLeaks);

  if (leaks.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Target size={32} className="mx-auto mb-2 text-gray-400" />
        <p>No significant leaks detected</p>
        <p className="text-sm">This player appears to play close to GTO</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {displayLeaks.map((leak, index) => (
        <LeakCard key={`${leak.stat}-${index}`} leak={leak} />
      ))}

      {leaks.length > maxLeaks && (
        <p className="text-sm text-gray-500 text-center">
          +{leaks.length - maxLeaks} more leaks identified
        </p>
      )}
    </div>
  );
};
