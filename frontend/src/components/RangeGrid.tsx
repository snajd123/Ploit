import React, { useState } from 'react';

interface RangeGridProps {
  rangeString?: string;
  rangeMatrix?: Record<string, number>;
  title?: string;
}

const RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];

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

// Get frequency for a hand combo
const getHandFrequency = (rank1: string, rank2: string, rangeMatrix: Record<string, number>): number => {
  const rankIndex1 = RANKS.indexOf(rank1);
  const rankIndex2 = RANKS.indexOf(rank2);

  // Pairs (diagonal)
  if (rank1 === rank2) {
    return rangeMatrix[rank1 + rank2] || 0;
  }

  // Suited (above diagonal)
  if (rankIndex1 < rankIndex2) {
    return rangeMatrix[rank1 + rank2 + 's'] || 0;
  }

  // Offsuit (below diagonal)
  return rangeMatrix[rank2 + rank1 + 'o'] || 0;
};

// Get color based on frequency
const getFrequencyColor = (frequency: number): string => {
  if (frequency === 0) return 'bg-white border-gray-200';
  if (frequency >= 0.99) return 'bg-green-700 text-white border-green-800';
  if (frequency >= 0.75) return 'bg-green-600 text-white border-green-700';
  if (frequency >= 0.50) return 'bg-yellow-400 text-gray-900 border-yellow-500';
  if (frequency >= 0.25) return 'bg-orange-400 text-gray-900 border-orange-500';
  return 'bg-gray-300 text-gray-700 border-gray-400';
};

// Get hand label
const getHandLabel = (rank1: string, rank2: string): string => {
  const rankIndex1 = RANKS.indexOf(rank1);
  const rankIndex2 = RANKS.indexOf(rank2);

  if (rank1 === rank2) return rank1 + rank2;
  if (rankIndex1 < rankIndex2) return rank1 + rank2 + 's';
  return rank2 + rank1 + 'o';
};

// Count combos for a hand
const getHandCombos = (rank1: string, rank2: string): number => {
  if (rank1 === rank2) return 6;  // Pairs have 6 combos
  return 4;  // Suited/offsuit have 4 combos each
};

const RangeGrid: React.FC<RangeGridProps> = ({ rangeString, rangeMatrix, title }) => {
  const [hoveredHand, setHoveredHand] = useState<string | null>(null);

  // Parse range string if provided, otherwise use rangeMatrix
  const matrix = rangeMatrix || parseRangeString(rangeString || '');

  // Calculate total combos in range
  const totalCombos = RANKS.reduce((sum, rank1) => {
    return sum + RANKS.reduce((innerSum, rank2) => {
      const freq = getHandFrequency(rank1, rank2, matrix);
      if (freq > 0) {
        return innerSum + getHandCombos(rank1, rank2) * freq;
      }
      return innerSum;
    }, 0);
  }, 0);

  const totalPossibleCombos = 1326;
  const rangePercentage = ((totalCombos / totalPossibleCombos) * 100).toFixed(1);

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

      <div className="bg-white rounded-lg border border-gray-200 p-4 overflow-x-auto">
        <div className="inline-block min-w-full">
          <div className="grid grid-cols-13 gap-1" style={{ gridTemplateColumns: 'repeat(13, minmax(0, 1fr))' }}>
            {RANKS.map((rank1, i) => (
              RANKS.map((rank2, j) => {
                const frequency = getHandFrequency(rank1, rank2, matrix);
                const handLabel = getHandLabel(rank1, rank2);
                const combos = getHandCombos(rank1, rank2);
                const colorClass = getFrequencyColor(frequency);
                const isHovered = hoveredHand === handLabel;

                return (
                  <div
                    key={`${rank1}-${rank2}`}
                    className={`
                      relative aspect-square flex items-center justify-center text-xs sm:text-sm font-bold
                      border transition-all cursor-pointer
                      ${colorClass}
                      ${isHovered ? 'ring-2 ring-blue-500 scale-110 z-10 shadow-lg' : ''}
                    `}
                    onMouseEnter={() => setHoveredHand(handLabel)}
                    onMouseLeave={() => setHoveredHand(null)}
                    title={`${handLabel}: ${(frequency * 100).toFixed(0)}% (${Math.round(combos * frequency)} combos)`}
                  >
                    <span className="select-none">{handLabel}</span>
                  </div>
                );
              })
            ))}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-gray-600">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-700 border border-green-800 rounded"></div>
          <span>Always (100%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-600 border border-green-700 rounded"></div>
          <span>Often (75-99%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-yellow-400 border border-yellow-500 rounded"></div>
          <span>Sometimes (50-74%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-orange-400 border border-orange-500 rounded"></div>
          <span>Rarely (25-49%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-gray-300 border border-gray-400 rounded"></div>
          <span>Very Rare (1-24%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-white border border-gray-200 rounded"></div>
          <span>Never (0%)</span>
        </div>
      </div>

      {hoveredHand && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="text-sm">
            <span className="font-bold text-blue-900">{hoveredHand}</span>
            <span className="text-gray-600 ml-2">
              Frequency: {(getHandFrequency(hoveredHand[0], hoveredHand[1], matrix) * 100).toFixed(1)}%
            </span>
            <span className="text-gray-600 ml-2">
              Combos: {Math.round(getHandCombos(hoveredHand[0], hoveredHand[1]) * getHandFrequency(hoveredHand[0], hoveredHand[1], matrix))}
            </span>
          </div>
        </div>
      )}

      {rangeString && (
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="text-xs font-mono text-gray-700 break-all">
            {rangeString}
          </div>
        </div>
      )}
    </div>
  );
};

export default RangeGrid;
