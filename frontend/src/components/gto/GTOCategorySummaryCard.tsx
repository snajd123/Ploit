import React from 'react';
import { ChevronRight } from 'lucide-react';

interface PositionStat {
  position: string;
  deviation: number;
  status: 'good' | 'warning' | 'bad';
}

interface ActionBreakdown {
  playerFold: number;
  gtoFold: number;
  playerRaise: number;
  gtoRaise: number;
}

interface GTOCategorySummaryCardProps {
  title: string;
  subtitle: string;
  icon: React.ElementType;
  avgDeviation: number;
  totalHands: number;
  leakCount: number;
  worstLeak: { position: string; deviation: number } | null;
  tendency: string;
  positionStats: PositionStat[];
  actionBreakdown: ActionBreakdown | null;
  onClick: () => void;
}

const getDeviationColor = (deviation: number) => {
  const absDeviation = Math.abs(deviation);
  if (absDeviation < 5) return 'bg-green-100 text-green-700';
  if (absDeviation < 10) return 'bg-yellow-100 text-yellow-700';
  return 'bg-red-100 text-red-700';
};

const getTendencyColor = (tendency: string) => {
  if (tendency === 'Balanced') return 'text-green-600';
  return 'text-amber-600';
};

const getStatusColor = (status: 'good' | 'warning' | 'bad') => {
  switch (status) {
    case 'good': return 'bg-green-500';
    case 'warning': return 'bg-yellow-500';
    case 'bad': return 'bg-red-500';
  }
};

// Mini bar component for action comparison
const MiniActionBar = ({
  label,
  playerValue,
  gtoValue
}: {
  label: string;
  playerValue: number;
  gtoValue: number;
}) => {
  const diff = playerValue - gtoValue;
  const diffColor = Math.abs(diff) < 5 ? 'text-green-600' : Math.abs(diff) < 10 ? 'text-yellow-600' : 'text-red-600';

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-10 text-gray-500">{label}</span>
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden relative">
        {/* GTO reference line */}
        <div
          className="absolute h-full w-0.5 bg-blue-600 z-10"
          style={{ left: `${Math.min(gtoValue, 100)}%` }}
        />
        {/* Player bar */}
        <div
          className={`h-full rounded-full ${playerValue > gtoValue ? 'bg-amber-400' : 'bg-green-400'}`}
          style={{ width: `${Math.min(playerValue, 100)}%` }}
        />
      </div>
      <span className={`w-12 text-right font-medium ${diffColor}`}>
        {diff > 0 ? '+' : ''}{diff.toFixed(0)}%
      </span>
    </div>
  );
};

const GTOCategorySummaryCard: React.FC<GTOCategorySummaryCardProps> = ({
  title,
  subtitle,
  icon: Icon,
  avgDeviation,
  totalHands,
  leakCount,
  worstLeak,
  tendency,
  positionStats,
  actionBreakdown,
  onClick,
}) => {
  return (
    <button
      onClick={onClick}
      className="card w-full text-left hover:shadow-md transition-shadow cursor-pointer group"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{title}</h3>
            <p className="text-xs text-gray-500">{subtitle}</p>
          </div>
        </div>
        <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
      </div>

      {/* Stats Row */}
      <div className="mt-3 flex items-center gap-3 flex-wrap">
        <div className={`px-2 py-1 rounded-full text-xs font-medium ${getDeviationColor(avgDeviation)}`}>
          {avgDeviation >= 0 ? '+' : ''}{avgDeviation.toFixed(1)}% avg
        </div>
        <span className="text-xs text-gray-500">
          {totalHands.toLocaleString()} hands
        </span>
        {leakCount > 0 && (
          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
            {leakCount} leak{leakCount !== 1 ? 's' : ''}
          </span>
        )}
        <span className={`text-xs font-medium ${getTendencyColor(tendency)}`}>
          {tendency}
        </span>
      </div>

      {/* Worst Leak */}
      {worstLeak && Math.abs(worstLeak.deviation) > 5 && (
        <div className="mt-2 text-xs text-gray-600">
          <span className="text-gray-400">Worst:</span>{' '}
          <span className="font-medium">{worstLeak.position}</span>{' '}
          <span className={Math.abs(worstLeak.deviation) > 10 ? 'text-red-600 font-medium' : 'text-yellow-600'}>
            ({worstLeak.deviation > 0 ? '+' : ''}{worstLeak.deviation.toFixed(1)}%)
          </span>
        </div>
      )}

      {/* Action Breakdown Mini Chart */}
      {actionBreakdown && (
        <div className="mt-3 space-y-1">
          <MiniActionBar label="Fold" playerValue={actionBreakdown.playerFold} gtoValue={actionBreakdown.gtoFold} />
          <MiniActionBar label="Raise" playerValue={actionBreakdown.playerRaise} gtoValue={actionBreakdown.gtoRaise} />
        </div>
      )}

      {/* Position Status Dots */}
      {positionStats.length > 0 && (
        <div className="mt-3 flex items-center gap-1">
          <span className="text-xs text-gray-400 mr-1">Positions:</span>
          {positionStats.slice(0, 6).map((ps, i) => (
            <div
              key={i}
              className={`w-2.5 h-2.5 rounded-full ${getStatusColor(ps.status)}`}
              title={`${ps.position}: ${ps.deviation > 0 ? '+' : ''}${ps.deviation.toFixed(1)}%`}
            />
          ))}
          {positionStats.length > 6 && (
            <span className="text-xs text-gray-400 ml-1">+{positionStats.length - 6}</span>
          )}
        </div>
      )}
    </button>
  );
};

export default GTOCategorySummaryCard;
