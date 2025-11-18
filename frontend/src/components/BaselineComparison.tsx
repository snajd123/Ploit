/**
 * BaselineComparison Component
 *
 * Displays player statistics compared to poker theory baselines
 * with visual indicators for exploitable deviations.
 */

import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { Deviation } from '../types';

interface BaselineComparisonProps {
  deviations: Deviation[];
  playerName?: string;
}

const getSeverityColor = (severity: string): string => {
  switch (severity) {
    case 'extreme': return 'text-red-600 bg-red-50 border-red-200';
    case 'severe': return 'text-orange-600 bg-orange-50 border-orange-200';
    case 'moderate': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    case 'minor': return 'text-blue-600 bg-blue-50 border-blue-200';
    default: return 'text-green-600 bg-green-50 border-green-200';
  }
};

const getDeviationIcon = (direction: string, deviation: number) => {
  if (Math.abs(deviation) < 5) {
    return <Minus className="w-4 h-4" />;
  }
  return direction === 'over' ?
    <TrendingUp className="w-4 h-4" /> :
    <TrendingDown className="w-4 h-4" />;
};

const BaselineComparison: React.FC<BaselineComparisonProps> = ({
  deviations,
  playerName
}) => {
  // Sort by absolute deviation (most exploitable first)
  const sortedDeviations = [...deviations].sort(
    (a, b) => b.abs_deviation - a.abs_deviation
  );

  const exploitableCount = deviations.filter(d => d.exploitable).length;
  const totalEV = deviations
    .filter(d => d.estimated_ev)
    .reduce((sum, d) => sum + (d.estimated_ev || 0), 0);

  return (
    <div className="baseline-comparison">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          {playerName ? `${playerName} - Baseline Analysis` : 'Baseline Analysis'}
        </h2>
        <div className="flex gap-4 text-sm">
          <div className="px-3 py-1 bg-gray-100 rounded-lg">
            <span className="font-semibold">{exploitableCount}</span> Exploitable Deviations
          </div>
          {totalEV > 0 && (
            <div className="px-3 py-1 bg-green-100 rounded-lg text-green-800">
              <span className="font-semibold">+{totalEV.toFixed(2)}</span> BB/100 EV
            </div>
          )}
        </div>
      </div>

      {/* Deviations Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-4 font-semibold text-gray-700">Statistic</th>
              <th className="text-right py-3 px-4 font-semibold text-gray-700">Player</th>
              <th className="text-right py-3 px-4 font-semibold text-gray-700">Baseline</th>
              <th className="text-right py-3 px-4 font-semibold text-gray-700">Deviation</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700">Severity</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700">Exploit</th>
            </tr>
          </thead>
          <tbody>
            {sortedDeviations.map((dev, idx) => (
              <tr
                key={idx}
                className={`border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                  dev.exploitable ? 'bg-red-50/30' : ''
                }`}
              >
                {/* Statistic Name */}
                <td className="py-3 px-4 font-medium text-gray-900">
                  {dev.stat}
                </td>

                {/* Player Value */}
                <td className="py-3 px-4 text-right text-gray-900">
                  {dev.player.toFixed(1)}%
                </td>

                {/* Baseline Value */}
                <td className="py-3 px-4 text-right text-gray-600">
                  {(dev.baseline ?? dev.gto ?? 0).toFixed(1)}%
                </td>

                {/* Deviation */}
                <td className="py-3 px-4 text-right">
                  <div className="flex items-center justify-end gap-1">
                    {getDeviationIcon(dev.direction, dev.deviation)}
                    <span className={`font-semibold ${
                      dev.exploitable ? 'text-red-600' : 'text-gray-600'
                    }`}>
                      {dev.deviation > 0 ? '+' : ''}{dev.deviation.toFixed(1)}%
                    </span>
                  </div>
                </td>

                {/* Severity Badge */}
                <td className="py-3 px-4">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${
                    getSeverityColor(dev.severity)
                  }`}>
                    {dev.severity}
                  </span>
                </td>

                {/* Exploit Direction */}
                <td className="py-3 px-4">
                  {dev.exploitable ? (
                    <div className="text-sm">
                      <div className="font-medium text-gray-900">
                        {dev.exploit_direction}
                      </div>
                      {dev.estimated_ev && dev.estimated_ev > 0 && (
                        <div className="text-green-600 text-xs">
                          +{dev.estimated_ev.toFixed(2)} BB/100
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="text-gray-400 text-sm">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Baseline Source */}
      <div className="mt-4 text-xs text-gray-500 text-right">
        Baselines: Modern Poker Theory + GTO Approximations
      </div>
    </div>
  );
};

export default BaselineComparison;
