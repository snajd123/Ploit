/**
 * DeviationHeatmap Component
 *
 * Visual heatmap showing player deviations from baseline across multiple stats
 */

import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer } from 'recharts';
import type { Deviation } from '../types';

interface DeviationHeatmapProps {
  deviations: Deviation[];
  playerName?: string;
}

const getSeverityColor = (severity: string): string => {
  switch (severity) {
    case 'extreme': return '#dc2626'; // red-600
    case 'severe': return '#ea580c'; // orange-600
    case 'moderate': return '#ca8a04'; // yellow-600
    case 'minor': return '#2563eb'; // blue-600
    default: return '#16a34a'; // green-600
  }
};

const DeviationHeatmap: React.FC<DeviationHeatmapProps> = ({
  deviations,
  playerName
}) => {
  // Transform data for the chart
  const chartData = deviations.map(dev => ({
    stat: dev.stat,
    player: dev.player,
    baseline: dev.baseline ?? dev.gto ?? 0,
    deviation: dev.deviation,
    abs_deviation: dev.abs_deviation,
    severity: dev.severity,
    exploitable: dev.exploitable,
    color: getSeverityColor(dev.severity)
  }));

  // Sort by absolute deviation
  const sortedData = [...chartData].sort((a, b) => b.abs_deviation - a.abs_deviation);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border border-gray-200 rounded shadow-lg">
          <p className="font-semibold text-gray-900 mb-1">{data.stat}</p>
          <div className="text-sm space-y-1">
            <p className="text-gray-700">
              Player: <span className="font-medium">{data.player.toFixed(1)}%</span>
            </p>
            <p className="text-gray-700">
              Baseline: <span className="font-medium">{data.baseline.toFixed(1)}%</span>
            </p>
            <p className={`font-semibold ${data.deviation > 0 ? 'text-red-600' : 'text-blue-600'}`}>
              Deviation: {data.deviation > 0 ? '+' : ''}{data.deviation.toFixed(1)}%
            </p>
            <p className="text-gray-600">
              Severity: <span className="font-medium capitalize">{data.severity}</span>
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="deviation-heatmap bg-white border border-gray-200 rounded-lg shadow-sm p-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          {playerName ? `${playerName} - Deviation Heatmap` : 'Deviation Heatmap'}
        </h2>
        <p className="text-sm text-gray-600">
          Visual representation of deviations from baseline strategy
        </p>
      </div>

      {/* Heatmap Chart */}
      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={sortedData}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 120, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            type="number"
            domain={[-50, 50]}
            label={{ value: 'Deviation (%)', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            type="category"
            dataKey="stat"
            width={110}
            tick={{ fontSize: 12 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="deviation" radius={[0, 4, 4, 0]}>
            {sortedData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="mt-6 flex flex-wrap gap-4 justify-center text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: '#16a34a' }}></div>
          <span className="text-gray-700">Negligible</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: '#2563eb' }}></div>
          <span className="text-gray-700">Minor</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: '#ca8a04' }}></div>
          <span className="text-gray-700">Moderate</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: '#ea580c' }}></div>
          <span className="text-gray-700">Severe</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: '#dc2626' }}></div>
          <span className="text-gray-700">Extreme</span>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="mt-6 pt-4 border-t border-gray-200 grid grid-cols-3 gap-4 text-center">
        <div>
          <div className="text-2xl font-bold text-gray-900">
            {deviations.length}
          </div>
          <div className="text-sm text-gray-600">Total Stats</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-red-600">
            {deviations.filter(d => d.exploitable).length}
          </div>
          <div className="text-sm text-gray-600">Exploitable</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-green-600">
            {deviations.filter(d => !d.exploitable).length}
          </div>
          <div className="text-sm text-gray-600">Baseline Range</div>
        </div>
      </div>
    </div>
  );
};

export default DeviationHeatmap;
