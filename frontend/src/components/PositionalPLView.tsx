import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Loader2, AlertCircle } from 'lucide-react';
import type { PositionalPLResponse, PositionalPL } from '../types';
import { api } from '../services/api';

interface PositionalPLViewProps {
  sessionId: number;
}

// Position colors matching poker conventions
const POSITION_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  BTN: { bg: 'bg-green-50', border: 'border-green-300', text: 'text-green-800' },
  CO: { bg: 'bg-blue-50', border: 'border-blue-300', text: 'text-blue-800' },
  MP: { bg: 'bg-purple-50', border: 'border-purple-300', text: 'text-purple-800' },
  UTG: { bg: 'bg-orange-50', border: 'border-orange-300', text: 'text-orange-800' },
  SB: { bg: 'bg-red-50', border: 'border-red-300', text: 'text-red-800' },
  BB: { bg: 'bg-pink-50', border: 'border-pink-300', text: 'text-pink-800' },
};

// Horizontal bar component
const PLBar: React.FC<{ position: PositionalPL; maxAbsValue: number }> = ({ position, maxAbsValue }) => {
  const isPositive = position.profit_bb >= 0;
  const barWidth = Math.min((Math.abs(position.profit_bb) / maxAbsValue) * 100, 100);
  const colors = POSITION_COLORS[position.position] || POSITION_COLORS.MP;

  return (
    <div className={`p-3 rounded-lg border ${colors.border} ${colors.bg} transition-all hover:shadow-sm`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <span className={`font-bold text-lg ${colors.text}`}>{position.position}</span>
          <span className="text-xs text-gray-500">
            {position.hands} hands ({position.win_rate.toFixed(0)}% won)
          </span>
        </div>
        <div className="flex items-center gap-2">
          {position.performance === 'above' && (
            <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
              +{position.vs_expected.toFixed(0)} vs exp
            </span>
          )}
          {position.performance === 'below' && (
            <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">
              {position.vs_expected.toFixed(0)} vs exp
            </span>
          )}
          <span className={`font-bold text-lg ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
            {isPositive ? '+' : ''}{position.profit_bb.toFixed(1)} bb
          </span>
        </div>
      </div>

      {/* Bar chart */}
      <div className="relative h-6 flex items-center">
        {/* Center line (zero point) */}
        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-gray-400" />

        {/* Bar */}
        {isPositive ? (
          <div
            className="absolute left-1/2 h-4 rounded-r bg-green-500 transition-all"
            style={{ width: `${barWidth / 2}%` }}
          />
        ) : (
          <div
            className="absolute right-1/2 h-4 rounded-l bg-red-500 transition-all"
            style={{ width: `${barWidth / 2}%` }}
          />
        )}

        {/* Expected position marker */}
        <div
          className="absolute top-1/2 w-2 h-2 rounded-full bg-yellow-500 transform -translate-y-1/2 border border-white"
          style={{
            left: `${50 + (position.expected_bb_100 / (maxAbsValue * 100 / position.hands || 100) * 50)}%`
          }}
          title={`Expected: ${position.expected_bb_100} bb/100`}
        />
      </div>

      {/* Stats row */}
      <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
        <span>bb/100: <span className={`font-medium ${position.bb_100 >= 0 ? 'text-green-700' : 'text-red-700'}`}>
          {position.bb_100 >= 0 ? '+' : ''}{position.bb_100.toFixed(1)}
        </span></span>
        <span>Expected: <span className="font-medium text-gray-700">{position.expected_bb_100} bb/100</span></span>
      </div>
    </div>
  );
};

const PositionalPLView: React.FC<PositionalPLViewProps> = ({ sessionId }) => {
  const [data, setData] = useState<PositionalPLResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await api.getSessionPositionalPL(sessionId);
        setData(result);
      } catch (err) {
        console.error('Error fetching positional P/L:', err);
        setError('Failed to load positional P/L data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="animate-spin text-blue-600 mr-2" size={20} />
        <span className="text-gray-600">Loading positional P/L...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-8">
        <AlertCircle className="mx-auto mb-2 text-red-500" size={32} />
        <p className="text-red-600">{error || 'No data available'}</p>
      </div>
    );
  }

  // Calculate max absolute value for scaling bars
  const maxAbsValue = Math.max(...data.positions.map(p => Math.abs(p.profit_bb)), 1);

  return (
    <div className="space-y-4">
      {/* Summary header */}
      <div className="flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-white rounded-lg border">
        <div>
          <h3 className="font-semibold text-gray-900">Positional P/L Breakdown</h3>
          <p className="text-sm text-gray-500 mt-1">
            Profit/loss by position ({data.total_hands} hands)
          </p>
        </div>
        <div className="text-right">
          <div className={`text-2xl font-bold ${data.total_profit_bb >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {data.total_profit_bb >= 0 ? '+' : ''}{data.total_profit_bb.toFixed(1)} bb
          </div>
          <div className="text-xs text-gray-500">
            {data.summary.profitable_positions} profitable / {data.summary.losing_positions} losing
          </div>
        </div>
      </div>

      {/* Position cards */}
      <div className="space-y-2">
        {data.positions.map(position => (
          <PLBar key={position.position} position={position} maxAbsValue={maxAbsValue} />
        ))}
      </div>

      {/* Summary insights */}
      <div className="flex items-center gap-4 p-3 bg-blue-50 rounded-lg border border-blue-200 text-sm">
        <div className="flex items-center gap-2">
          {data.best_position && (
            <span className="flex items-center gap-1 text-green-700">
              <TrendingUp size={14} />
              Best: <span className="font-medium">{data.best_position}</span>
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {data.worst_position && (
            <span className="flex items-center gap-1 text-red-700">
              <TrendingDown size={14} />
              Worst: <span className="font-medium">{data.worst_position}</span>
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-gray-600">
          <span className="flex items-center gap-1">
            {data.summary.above_expected > 0 && (
              <>
                <span className="font-medium text-green-700">{data.summary.above_expected}</span>
                <span>above expected</span>
              </>
            )}
          </span>
          {data.summary.below_expected > 0 && (
            <span className="flex items-center gap-1 ml-2">
              <span className="font-medium text-red-700">{data.summary.below_expected}</span>
              <span>below expected</span>
            </span>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-green-500" /> Profit
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-red-500" /> Loss
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-yellow-500" /> Expected bb/100
        </span>
      </div>
    </div>
  );
};

export default PositionalPLView;
