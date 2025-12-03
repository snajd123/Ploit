import React, { useState, useEffect } from 'react';
import { Target, AlertCircle, Loader2, HelpCircle, Lightbulb } from 'lucide-react';
import type { GTOScoreResponse } from '../types';
import { api } from '../services/api';

interface GTOScoreViewProps {
  sessionId: number;
}

// Grade color mapping
const getGradeColors = (grade: string): { bg: string; text: string; border: string; ring: string } => {
  if (grade.startsWith('A')) {
    return { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300', ring: 'stroke-green-500' };
  } else if (grade.startsWith('B')) {
    return { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300', ring: 'stroke-blue-500' };
  } else if (grade === 'C') {
    return { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-300', ring: 'stroke-yellow-500' };
  } else if (grade === 'D') {
    return { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-300', ring: 'stroke-orange-500' };
  } else {
    return { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-300', ring: 'stroke-red-500' };
  }
};

// Circular progress ring component
const ScoreRing: React.FC<{ score: number; size?: number; strokeWidth?: number }> = ({
  score,
  size = 120,
  strokeWidth = 8
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (score / 100) * circumference;
  const colors = getGradeColors(score >= 90 ? 'A+' : score >= 80 ? 'A' : score >= 70 ? 'B+' : score >= 60 ? 'B' : score >= 50 ? 'C' : score >= 40 ? 'D' : 'F');

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="transform -rotate-90" width={size} height={size}>
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          className="stroke-gray-200 fill-none"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={`${colors.ring} fill-none transition-all duration-1000`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold text-gray-900">{score.toFixed(0)}</span>
        <span className="text-xs text-gray-500">/ 100</span>
      </div>
    </div>
  );
};

// Component score bar
const ComponentBar: React.FC<{
  label: string;
  score: number;
  weight: number;
  description: string;
  isWeakest: boolean;
}> = ({ label, score, weight, description, isWeakest }) => {
  const barColor = score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-blue-500' : score >= 40 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className={`p-3 rounded-lg border ${isWeakest ? 'border-orange-300 bg-orange-50' : 'border-gray-200 bg-gray-50'}`}>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-700 text-sm">{label}</span>
          {isWeakest && (
            <span className="text-xs bg-orange-200 text-orange-700 px-1.5 py-0.5 rounded">Focus Area</span>
          )}
        </div>
        <span className="font-bold text-gray-900">{score.toFixed(0)}</span>
      </div>
      <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`absolute left-0 top-0 h-full ${barColor} rounded-full transition-all duration-500`}
          style={{ width: `${score}%` }}
        />
      </div>
      <div className="flex items-center justify-between mt-1 text-xs text-gray-500">
        <span>{description}</span>
        <span>{(weight * 100).toFixed(0)}% weight</span>
      </div>
    </div>
  );
};

const GTOScoreView: React.FC<GTOScoreViewProps> = ({ sessionId }) => {
  const [data, setData] = useState<GTOScoreResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await api.getSessionGTOScore(sessionId);
        setData(result);
      } catch (err) {
        console.error('Error fetching GTO score:', err);
        setError('Failed to load GTO score');
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
        <span className="text-gray-600">Calculating GTO score...</span>
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

  const gradeColors = getGradeColors(data.grade);

  return (
    <div className="space-y-4">
      {/* Main score display */}
      <div className="flex items-center gap-6 p-6 bg-gradient-to-r from-gray-50 to-white rounded-lg border">
        <ScoreRing score={data.gto_score} />

        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className={`text-4xl font-bold px-3 py-1 rounded ${gradeColors.bg} ${gradeColors.text}`}>
              {data.grade}
            </span>
            <span className="text-xl font-medium text-gray-700">{data.rating}</span>
          </div>
          <p className="text-gray-600">
            GTO Deviation Score measures how closely your preflop decisions aligned with
            game-theoretically optimal play.
          </p>
          <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
            <span>{data.total_hands} hands analyzed</span>
            <span className={data.confidence === 'low' ? 'text-orange-500' : ''}>
              {data.confidence} confidence
            </span>
          </div>
        </div>
      </div>

      {/* Component breakdown */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
          <Target size={16} />
          Score Components
        </div>

        <ComponentBar
          label="Frequency Accuracy"
          score={data.components.frequency_accuracy.score}
          weight={data.components.frequency_accuracy.weight}
          description={data.components.frequency_accuracy.description}
          isWeakest={data.weakest_area === 'frequency_accuracy'}
        />

        <ComponentBar
          label="Mistake Avoidance"
          score={data.components.mistake_avoidance.score}
          weight={data.components.mistake_avoidance.weight}
          description={data.components.mistake_avoidance.description}
          isWeakest={data.weakest_area === 'mistake_avoidance'}
        />

        <ComponentBar
          label="EV Preservation"
          score={data.components.ev_preservation.score}
          weight={data.components.ev_preservation.weight}
          description={data.components.ev_preservation.description}
          isWeakest={data.weakest_area === 'ev_preservation'}
        />
      </div>

      {/* Improvement suggestion */}
      {data.improvement_suggestion && (
        <div className="flex items-start gap-3 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <Lightbulb className="text-blue-600 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <div className="font-medium text-blue-800 mb-1">Improvement Focus</div>
            <p className="text-blue-700 text-sm">{data.improvement_suggestion}</p>
          </div>
        </div>
      )}

      {/* Mistake summary */}
      {data.mistakes_summary.total > 0 && (
        <div className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg border text-sm">
          <span className="text-gray-600">
            Mistakes: <span className="font-medium text-gray-900">{data.mistakes_summary.total}</span>
            {data.mistakes_summary.major > 0 && (
              <span className="text-red-600 ml-1">({data.mistakes_summary.major} major)</span>
            )}
          </span>
          <span className="text-gray-600">
            EV Loss: <span className="font-medium text-red-600">-{data.mistakes_summary.ev_loss_bb.toFixed(1)} bb</span>
          </span>
        </div>
      )}

      {/* Score explanation */}
      <div className="flex items-start gap-2 text-xs text-gray-400">
        <HelpCircle size={14} className="flex-shrink-0 mt-0.5" />
        <span>
          Score based on frequency accuracy (40%), mistake avoidance (35%), and EV preservation (25%).
          100 = perfect GTO play, 50 = average deviation.
        </span>
      </div>
    </div>
  );
};

export default GTOScoreView;
