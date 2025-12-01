import React, { useState } from 'react';

// Multi-action frequencies for defense scenarios
export interface HandActions {
  fold?: number;
  call?: number;
  raise?: number;
  '3bet'?: number;
  '4bet'?: number;
  '5bet'?: number;
  limp?: number;
  allin?: number;
}

interface RangeGridProps {
  // Single action mode (simple range display)
  rangeString?: string;
  rangeMatrix?: Record<string, number>;
  // Multi-action mode (for defense scenarios with call/3bet/fold)
  actionMatrix?: Record<string, HandActions>;
  title?: string;
  highlightedHand?: string;  // Hand combo to highlight (e.g., "AKo")
  showFolds?: boolean;
  onHandClick?: (hand: string) => void;
}

const RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];

// Standard solver colors (PioSOLVER convention)
const ACTION_COLORS: Record<string, { r: number; g: number; b: number }> = {
  raise: { r: 229, g: 57, b: 53 },    // Red
  '3bet': { r: 229, g: 57, b: 53 },   // Red
  '4bet': { r: 180, g: 40, b: 40 },   // Darker Red
  '5bet': { r: 140, g: 20, b: 20 },   // Even darker Red
  call: { r: 67, g: 160, b: 71 },     // Green
  fold: { r: 200, g: 200, b: 200 },   // Light gray
  limp: { r: 255, g: 193, b: 7 },     // Yellow
  allin: { r: 142, g: 36, b: 170 },   // Purple
};

// Parse simple range strings like "AA,KK,QQ,AKs,AKo"
const parseRangeString = (rangeString: string): Record<string, number> => {
  if (!rangeString) return {};

  const matrix: Record<string, number> = {};
  const parts = rangeString.split(',').map(s => s.trim());

  for (const part of parts) {
    // Handle pocket pairs with + (e.g., "22+" means 22,33,44,...,AA)
    if (part.includes('+') && part.length === 3 && part[0] === part[1]) {
      const rank = part[0];
      const rankIndex = RANKS.indexOf(rank);
      for (let i = 0; i <= rankIndex; i++) {
        matrix[RANKS[i] + RANKS[i]] = 1.0;
      }
    }
    // Handle suited ranges with + (e.g., "A2s+" means A2s,A3s,A4s,...,AKs)
    else if (part.endsWith('s+')) {
      const highRank = part[0];
      const lowRank = part[1];
      const lowIndex = RANKS.indexOf(lowRank);
      const highIndex = RANKS.indexOf(highRank);
      for (let i = highIndex + 1; i <= lowIndex; i++) {
        matrix[highRank + RANKS[i] + 's'] = 1.0;
      }
    }
    // Handle offsuit ranges with + (e.g., "A5o+" means A5o,A6o,A7o,...,AKo)
    else if (part.endsWith('o+')) {
      const highRank = part[0];
      const lowRank = part[1];
      const lowIndex = RANKS.indexOf(lowRank);
      const highIndex = RANKS.indexOf(highRank);
      for (let i = highIndex + 1; i <= lowIndex; i++) {
        matrix[highRank + RANKS[i] + 'o'] = 1.0;
      }
    }
    // Handle single hands like "AA", "AKs", "AKo"
    else if (part.length >= 2) {
      matrix[part] = 1.0;
    }
  }

  return matrix;
};

// Get hand label from grid position
const getHandLabel = (rank1: string, rank2: string): string => {
  const rankIndex1 = RANKS.indexOf(rank1);
  const rankIndex2 = RANKS.indexOf(rank2);

  if (rank1 === rank2) return rank1 + rank2;
  if (rankIndex1 < rankIndex2) return rank1 + rank2 + 's';
  return rank2 + rank1 + 'o';
};

// Count combos for a hand (FIXED: offsuit is 12, not 4)
const getHandCombos = (rank1: string, rank2: string): number => {
  if (rank1 === rank2) return 6;  // Pairs have 6 combos
  const rankIndex1 = RANKS.indexOf(rank1);
  const rankIndex2 = RANKS.indexOf(rank2);
  if (rankIndex1 < rankIndex2) return 4;   // Suited has 4 combos
  return 12;  // Offsuit has 12 combos
};

// Get frequency for a hand combo (single action mode)
const getHandFrequency = (rank1: string, rank2: string, rangeMatrix: Record<string, number>): number => {
  const handLabel = getHandLabel(rank1, rank2);
  return rangeMatrix[handLabel] || 0;
};

// Get blended color for multi-action hands
const getBlendedColor = (actions: HandActions, showFolds: boolean = true): string => {
  let r = 0, g = 0, b = 0, totalFreq = 0;

  for (const [action, freq] of Object.entries(actions)) {
    if (!showFolds && action === 'fold') continue;
    const color = ACTION_COLORS[action] || ACTION_COLORS.fold;
    r += color.r * (freq || 0);
    g += color.g * (freq || 0);
    b += color.b * (freq || 0);
    totalFreq += freq || 0;
  }

  if (totalFreq === 0) return 'rgb(255, 255, 255)';

  return `rgb(${Math.round(r/totalFreq)}, ${Math.round(g/totalFreq)}, ${Math.round(b/totalFreq)})`;
};

// Get color based on single frequency (gradient mode)
const getFrequencyColor = (frequency: number): string => {
  if (frequency === 0) return 'rgb(255, 255, 255)';

  // Interpolate from white to green based on frequency
  const r = Math.round(255 - (255 - 34) * frequency);
  const g = Math.round(255 - (255 - 139) * frequency);
  const b = Math.round(255 - (255 - 34) * frequency);

  return `rgb(${r}, ${g}, ${b})`;
};

const RangeGrid: React.FC<RangeGridProps> = ({
  rangeString,
  rangeMatrix,
  actionMatrix,
  title,
  highlightedHand,
  showFolds = false,
  onHandClick
}) => {
  const [hoveredHand, setHoveredHand] = useState<string | null>(null);

  // Parse range string if provided, otherwise use rangeMatrix
  const matrix = rangeMatrix || parseRangeString(rangeString || '');

  // Determine if we're in multi-action mode
  const isMultiAction = !!actionMatrix && Object.keys(actionMatrix).length > 0;

  // Get hand data based on mode
  const getHandData = (rank1: string, rank2: string) => {
    const handLabel = getHandLabel(rank1, rank2);

    if (isMultiAction && actionMatrix[handLabel]) {
      const actions = actionMatrix[handLabel];
      const totalFreq = Object.values(actions).reduce((a, b) => a + (b || 0), 0);
      return {
        actions,
        frequency: totalFreq,
        color: getBlendedColor(actions, showFolds)
      };
    }

    const freq = getHandFrequency(rank1, rank2, matrix);
    return {
      actions: { call: freq } as HandActions,
      frequency: freq,
      color: getFrequencyColor(freq)
    };
  };

  // Calculate total combos in range
  const totalCombos = RANKS.reduce((sum, rank1) => {
    return sum + RANKS.reduce((innerSum, rank2) => {
      const { frequency } = getHandData(rank1, rank2);
      if (frequency > 0) {
        const combos = getHandCombos(rank1, rank2);
        // For multi-action, we only count "continuing" (non-fold) combos
        if (isMultiAction) {
          const handLabel = getHandLabel(rank1, rank2);
          const actions = actionMatrix?.[handLabel] || {};
          const continuingFreq = (actions.call || 0) + (actions.raise || 0) +
                                  (actions['3bet'] || 0) + (actions['4bet'] || 0) +
                                  (actions['5bet'] || 0) + (actions.allin || 0);
          return innerSum + combos * continuingFreq;
        }
        return innerSum + combos * frequency;
      }
      return innerSum;
    }, 0);
  }, 0);

  const totalPossibleCombos = 1326;
  const rangePercentage = ((totalCombos / totalPossibleCombos) * 100).toFixed(1);

  // Get hover info for tooltip
  const getHoverInfo = (handLabel: string) => {
    // Find the hand in the grid
    const rank1 = handLabel[0];
    let rank2: string;
    let isSuited = false;
    let isPair = false;

    if (handLabel.length === 2) {
      rank2 = handLabel[1];
      isPair = true;
    } else {
      rank2 = handLabel[1];
      isSuited = handLabel[2] === 's';
    }

    const data = isPair
      ? getHandData(rank1, rank2)
      : (isSuited
          ? getHandData(rank1, rank2)  // Suited: rank1 < rank2 in index
          : getHandData(rank2, rank1)); // Offsuit: swap to get correct position

    return data;
  };

  return (
    <div className="space-y-4">
      {title && (
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          <div className="text-sm text-gray-600">
            <span className="font-medium">{Math.round(totalCombos)}</span> combos ({rangePercentage}%)
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 p-2 overflow-x-auto">
        <div className="inline-block min-w-full">
          <div
            className="grid gap-0.5"
            style={{
              gridTemplateColumns: 'repeat(13, minmax(28px, 1fr))',
              minWidth: '364px'
            }}
          >
            {RANKS.map((rank1) => (
              RANKS.map((rank2) => {
                const handLabel = getHandLabel(rank1, rank2);
                const { frequency, color, actions } = getHandData(rank1, rank2);
                const isHighlighted = highlightedHand === handLabel;
                const isHovered = hoveredHand === handLabel;

                // Get continuing frequency (non-fold)
                const continuingFreq = isMultiAction
                  ? (actions.call || 0) + (actions.raise || 0) + (actions['3bet'] || 0) +
                    (actions['4bet'] || 0) + (actions['5bet'] || 0) + (actions.allin || 0)
                  : frequency;

                return (
                  <div
                    key={`${rank1}-${rank2}`}
                    className={`
                      relative aspect-square flex items-center justify-center
                      text-[10px] sm:text-[11px] font-bold cursor-pointer transition-all
                      border border-gray-200
                      ${isHighlighted ? 'ring-4 ring-yellow-400 z-30 scale-125 shadow-xl' : ''}
                      ${isHovered && !isHighlighted ? 'ring-2 ring-blue-500 z-20 scale-110 shadow-lg' : ''}
                    `}
                    style={{
                      backgroundColor: continuingFreq > 0 ? color : '#f5f5f5',
                    }}
                    onMouseEnter={() => setHoveredHand(handLabel)}
                    onMouseLeave={() => setHoveredHand(null)}
                    onClick={() => onHandClick?.(handLabel)}
                  >
                    <span
                      className="select-none"
                      style={{
                        color: continuingFreq > 0 && frequency > 0.5 ? 'white' : '#374151',
                      }}
                    >
                      {handLabel}
                    </span>
                  </div>
                );
              })
            ))}
          </div>
        </div>
      </div>

      {/* Multi-action Legend */}
      {isMultiAction && (
        <div className="flex flex-wrap items-center gap-3 text-xs text-gray-600">
          <span className="font-medium">Actions:</span>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: `rgb(${ACTION_COLORS.raise.r}, ${ACTION_COLORS.raise.g}, ${ACTION_COLORS.raise.b})` }}></div>
            <span>Raise/3bet</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: `rgb(${ACTION_COLORS.call.r}, ${ACTION_COLORS.call.g}, ${ACTION_COLORS.call.b})` }}></div>
            <span>Call</span>
          </div>
          {showFolds && (
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded" style={{ backgroundColor: `rgb(${ACTION_COLORS.fold.r}, ${ACTION_COLORS.fold.g}, ${ACTION_COLORS.fold.b})` }}></div>
              <span>Fold</span>
            </div>
          )}
        </div>
      )}

      {/* Single-action Legend */}
      {!isMultiAction && (
        <div className="flex flex-wrap items-center gap-3 text-xs text-gray-600">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: 'rgb(34, 139, 34)' }}></div>
            <span>100%</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: 'rgb(144, 197, 144)' }}></div>
            <span>50%</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded border border-gray-200" style={{ backgroundColor: 'white' }}></div>
            <span>0%</span>
          </div>
        </div>
      )}

      {/* Hover Tooltip */}
      {hoveredHand && (
        <div className="bg-gray-800 text-white rounded-lg p-3 text-sm">
          <div className="font-bold text-lg mb-2">{hoveredHand}</div>
          {isMultiAction && actionMatrix?.[hoveredHand] ? (
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {Object.entries(actionMatrix[hoveredHand])
                .filter(([_, freq]) => (freq || 0) > 0)
                .sort((a, b) => (b[1] || 0) - (a[1] || 0))
                .map(([action, freq]) => (
                  <div key={action} className="flex justify-between gap-2">
                    <span className="capitalize text-gray-300">{action}:</span>
                    <span className="font-mono font-bold">{((freq || 0) * 100).toFixed(0)}%</span>
                  </div>
                ))}
            </div>
          ) : (
            <div className="flex justify-between">
              <span className="text-gray-300">Frequency:</span>
              <span className="font-mono font-bold">
                {(getHoverInfo(hoveredHand).frequency * 100).toFixed(0)}%
              </span>
            </div>
          )}
          <div className="text-gray-400 text-xs mt-2">
            {hoveredHand.length === 2 ? '6 combos (pair)' :
             hoveredHand.endsWith('s') ? '4 combos (suited)' : '12 combos (offsuit)'}
          </div>
        </div>
      )}

      {/* Highlighted Hand Info */}
      {highlightedHand && (
        <div className="bg-yellow-50 border-2 border-yellow-400 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <span className="text-yellow-600 font-bold text-lg">Your Hand:</span>
            <span className="bg-yellow-400 text-yellow-900 px-3 py-1 rounded font-bold text-lg">
              {highlightedHand}
            </span>
          </div>
          {isMultiAction && actionMatrix?.[highlightedHand] && (
            <div className="mt-2 text-sm text-yellow-800">
              GTO recommends: {
                Object.entries(actionMatrix[highlightedHand])
                  .filter(([_, freq]) => (freq || 0) > 0.1)
                  .sort((a, b) => (b[1] || 0) - (a[1] || 0))
                  .map(([action, freq]) => `${action} ${((freq || 0) * 100).toFixed(0)}%`)
                  .join(', ')
              }
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RangeGrid;
