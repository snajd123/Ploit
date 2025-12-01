import React from 'react';
import { ChevronRight } from 'lucide-react';

interface GTOCategorySummaryCardProps {
  title: string;
  subtitle: string;
  icon: React.ElementType;
  avgDeviation: number;
  totalHands: number;
  leakCount: number;
  onClick: () => void;
}

const getDeviationColor = (deviation: number) => {
  const absDeviation = Math.abs(deviation);
  if (absDeviation < 5) return 'bg-green-100 text-green-700';
  if (absDeviation < 10) return 'bg-yellow-100 text-yellow-700';
  return 'bg-red-100 text-red-700';
};

const GTOCategorySummaryCard: React.FC<GTOCategorySummaryCardProps> = ({
  title,
  subtitle,
  icon: Icon,
  avgDeviation,
  totalHands,
  leakCount,
  onClick,
}) => {
  return (
    <button
      onClick={onClick}
      className="card w-full text-left hover:shadow-md transition-shadow cursor-pointer group"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-lg bg-blue-50 text-blue-600">
            <Icon className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{title}</h3>
            <p className="text-sm text-gray-500">{subtitle}</p>
          </div>
        </div>
        <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
      </div>

      <div className="mt-4 flex items-center gap-4">
        <div className={`px-3 py-1.5 rounded-full text-sm font-medium ${getDeviationColor(avgDeviation)}`}>
          {avgDeviation >= 0 ? '+' : ''}{avgDeviation.toFixed(1)}% avg deviation
        </div>
        <span className="text-sm text-gray-500">
          {totalHands.toLocaleString()} hands
        </span>
        {leakCount > 0 && (
          <span className="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
            {leakCount} leak{leakCount !== 1 ? 's' : ''}
          </span>
        )}
      </div>
    </button>
  );
};

export default GTOCategorySummaryCard;
