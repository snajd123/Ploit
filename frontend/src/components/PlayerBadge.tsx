import React from 'react';
import type { PlayerType } from '../types';

interface PlayerBadgeProps {
  playerType: PlayerType;
  size?: 'sm' | 'md' | 'lg';
}

const playerTypeConfig: Record<NonNullable<PlayerType>, { color: string; label: string; description: string }> = {
  NIT: {
    color: 'bg-gray-100 text-gray-800 border-gray-300',
    label: 'NIT',
    description: 'Tight/Passive - Folds too much',
  },
  TAG: {
    color: 'bg-green-100 text-green-800 border-green-300',
    label: 'TAG',
    description: 'Tight/Aggressive - Solid player',
  },
  LAG: {
    color: 'bg-blue-100 text-blue-800 border-blue-300',
    label: 'LAG',
    description: 'Loose/Aggressive - Very aggressive',
  },
  CALLING_STATION: {
    color: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    label: 'Station',
    description: 'Calls too much - Doesn\'t fold',
  },
  MANIAC: {
    color: 'bg-red-100 text-red-800 border-red-300',
    label: 'Maniac',
    description: 'Extremely aggressive and loose',
  },
  FISH: {
    color: 'bg-purple-100 text-purple-800 border-purple-300',
    label: 'Fish',
    description: 'Recreational player with major leaks',
  },
  LOOSE_PASSIVE: {
    color: 'bg-orange-100 text-orange-800 border-orange-300',
    label: 'Loose/Passive',
    description: 'Plays too many hands passively',
  },
  TIGHT: {
    color: 'bg-slate-100 text-slate-800 border-slate-300',
    label: 'Tight',
    description: 'Tight player - hard to categorize',
  },
  TIGHT_PASSIVE: {
    color: 'bg-indigo-100 text-indigo-800 border-indigo-300',
    label: 'Tight/Passive',
    description: 'Tight but too passive - bluff more',
  },
  UNKNOWN: {
    color: 'bg-gray-100 text-gray-600 border-gray-300',
    label: 'Unknown',
    description: 'Unable to classify - needs more data',
  },
};

const sizeClasses = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-3 py-1',
  lg: 'text-base px-4 py-2',
};

const PlayerBadge: React.FC<PlayerBadgeProps> = ({ playerType, size = 'md' }) => {
  if (!playerType) {
    return (
      <span className={`inline-flex items-center rounded-md border font-medium bg-gray-100 text-gray-600 border-gray-300 ${sizeClasses[size]}`}>
        Unknown
      </span>
    );
  }

  const config = playerTypeConfig[playerType];

  return (
    <span
      className={`inline-flex items-center rounded-md border font-medium ${config.color} ${sizeClasses[size]}`}
      title={config.description}
    >
      {config.label}
    </span>
  );
};

export default PlayerBadge;
