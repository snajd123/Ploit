import React from 'react';
import { CheckCircle, AlertCircle, HelpCircle } from 'lucide-react';
import { Tooltip } from './Tooltip';

interface StatWithConfidenceProps {
  label: string;
  value: number | null | undefined;
  format?: 'percent' | 'number' | 'ratio';
  sampleSize?: number;
  ciLower?: number;
  ciUpper?: number;
  gtoBaseline?: number;
  showDeviation?: boolean;
  size?: 'sm' | 'md' | 'lg';
  tooltip?: string;
}

/**
 * Calculate Wilson score confidence interval for a percentage
 * Returns [lower, upper] bounds as percentages
 */
function calculateCI(value: number, sampleSize: number): [number, number] {
  if (sampleSize === 0) return [0, 100];

  const z = 1.96; // 95% confidence
  const p = value / 100;

  const denominator = 1 + z * z / sampleSize;
  const center = (p + z * z / (2 * sampleSize)) / denominator;
  const spread = z * Math.sqrt((p * (1 - p) + z * z / (4 * sampleSize)) / sampleSize) / denominator;

  const lower = Math.max(0, (center - spread) * 100);
  const upper = Math.min(100, (center + spread) * 100);

  return [Math.round(lower * 10) / 10, Math.round(upper * 10) / 10];
}

/**
 * Get reliability level based on confidence interval width
 */
function getReliability(ciWidth: number): 'excellent' | 'good' | 'moderate' | 'low' | 'insufficient' {
  if (ciWidth <= 5) return 'excellent';
  if (ciWidth <= 10) return 'good';
  if (ciWidth <= 20) return 'moderate';
  if (ciWidth <= 40) return 'low';
  return 'insufficient';
}

const reliabilityConfig = {
  excellent: {
    icon: CheckCircle,
    color: 'text-green-500',
    bgColor: 'bg-green-50',
    label: 'High confidence'
  },
  good: {
    icon: CheckCircle,
    color: 'text-green-500',
    bgColor: 'bg-green-50',
    label: 'Good confidence'
  },
  moderate: {
    icon: AlertCircle,
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-50',
    label: 'Moderate confidence'
  },
  low: {
    icon: AlertCircle,
    color: 'text-orange-500',
    bgColor: 'bg-orange-50',
    label: 'Low confidence'
  },
  insufficient: {
    icon: HelpCircle,
    color: 'text-gray-400',
    bgColor: 'bg-gray-50',
    label: 'Insufficient data'
  }
};

const StatWithConfidence: React.FC<StatWithConfidenceProps> = ({
  label,
  value,
  format = 'percent',
  sampleSize = 0,
  ciLower,
  ciUpper,
  gtoBaseline,
  showDeviation = false,
  size = 'md',
  tooltip
}) => {
  if (value === null || value === undefined) {
    return (
      <div className="flex items-center justify-between py-2">
        <span className="text-gray-600">{label}</span>
        <span className="text-gray-400">N/A</span>
      </div>
    );
  }

  // Calculate CI if not provided
  let lower = ciLower;
  let upper = ciUpper;
  if (lower === undefined || upper === undefined) {
    if (format === 'percent' && sampleSize > 0) {
      [lower, upper] = calculateCI(value, sampleSize);
    } else {
      lower = value;
      upper = value;
    }
  }

  const ciWidth = upper - lower;
  const reliability = getReliability(ciWidth);
  const config = reliabilityConfig[reliability];
  const Icon = config.icon;

  // Calculate deviation from GTO
  let deviation: number | null = null;
  let deviationClass = '';
  if (showDeviation && gtoBaseline !== undefined) {
    deviation = value - gtoBaseline;
    if (Math.abs(deviation) > 15) {
      deviationClass = 'text-red-600 font-semibold';
    } else if (Math.abs(deviation) > 8) {
      deviationClass = 'text-orange-600';
    } else if (Math.abs(deviation) > 3) {
      deviationClass = 'text-yellow-600';
    } else {
      deviationClass = 'text-green-600';
    }
  }

  // Format value
  const formatValue = (v: number) => {
    if (format === 'percent') return `${v.toFixed(1)}%`;
    if (format === 'ratio') return v.toFixed(2);
    return v.toFixed(1);
  };

  const sizeClasses = {
    sm: {
      container: 'py-1.5',
      label: 'text-xs',
      value: 'text-sm font-semibold',
      ci: 'text-xs',
      icon: 14
    },
    md: {
      container: 'py-2',
      label: 'text-sm',
      value: 'text-base font-semibold',
      ci: 'text-xs',
      icon: 16
    },
    lg: {
      container: 'py-3',
      label: 'text-base',
      value: 'text-xl font-bold',
      ci: 'text-sm',
      icon: 18
    }
  };

  const classes = sizeClasses[size];

  return (
    <div className={`flex items-center justify-between ${classes.container} border-b border-gray-100 last:border-0`}>
      <div className="flex items-center gap-1.5">
        <span className={`text-gray-600 ${classes.label}`}>{label}</span>
        {tooltip && (
          <Tooltip content={tooltip} position="top" iconSize={classes.icon - 2} />
        )}
      </div>

      <div className="flex items-center gap-2">
        {/* Main value */}
        <span className={`text-gray-900 ${classes.value}`}>
          {formatValue(value)}
        </span>

        {/* Confidence interval */}
        {sampleSize > 0 && reliability !== 'insufficient' && (
          <span className={`${classes.ci} text-gray-400`}>
            ({lower?.toFixed(0)}-{upper?.toFixed(0)})
          </span>
        )}

        {/* GTO deviation */}
        {deviation !== null && (
          <span className={`${classes.ci} ${deviationClass}`}>
            {deviation >= 0 ? '+' : ''}{deviation.toFixed(0)}
          </span>
        )}

        {/* Reliability indicator */}
        <Tooltip
          content={
            <div className="text-xs">
              <div className="font-semibold">{config.label}</div>
              <div>Sample: {sampleSize} hands</div>
              {lower !== upper && <div>95% CI: {lower?.toFixed(1)}-{upper?.toFixed(1)}%</div>}
            </div>
          }
          position="left"
        >
          <Icon size={classes.icon} className={config.color} />
        </Tooltip>
      </div>
    </div>
  );
};

export default StatWithConfidence;

// Stat group component for organizing multiple stats
interface StatGroupProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

export const StatGroup: React.FC<StatGroupProps> = ({ title, children, className = '' }) => {
  return (
    <div className={`bg-white rounded-lg border border-gray-200 ${className}`}>
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 rounded-t-lg">
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
      </div>
      <div className="px-4 py-2">
        {children}
      </div>
    </div>
  );
};

// Reliability summary component
interface ReliabilitySummaryProps {
  totalHands: number;
  reliableStats: string[];
  preliminaryStats: string[];
  insufficientStats: string[];
}

export const ReliabilitySummary: React.FC<ReliabilitySummaryProps> = ({
  totalHands,
  reliableStats,
  preliminaryStats,
  insufficientStats
}) => {
  return (
    <div className="bg-gray-50 rounded-lg p-4 text-sm">
      <h4 className="font-semibold text-gray-700 mb-3">Stat Reliability ({totalHands.toLocaleString()} hands)</h4>

      {reliableStats.length > 0 && (
        <div className="flex items-start gap-2 mb-2">
          <CheckCircle size={16} className="text-green-500 mt-0.5 flex-shrink-0" />
          <div>
            <span className="font-medium text-green-700">Reliable:</span>
            <span className="text-gray-600 ml-1">{reliableStats.join(', ')}</span>
          </div>
        </div>
      )}

      {preliminaryStats.length > 0 && (
        <div className="flex items-start gap-2 mb-2">
          <AlertCircle size={16} className="text-yellow-500 mt-0.5 flex-shrink-0" />
          <div>
            <span className="font-medium text-yellow-700">Preliminary:</span>
            <span className="text-gray-600 ml-1">{preliminaryStats.join(', ')}</span>
          </div>
        </div>
      )}

      {insufficientStats.length > 0 && (
        <div className="flex items-start gap-2">
          <HelpCircle size={16} className="text-gray-400 mt-0.5 flex-shrink-0" />
          <div>
            <span className="font-medium text-gray-500">Need more data:</span>
            <span className="text-gray-500 ml-1">{insufficientStats.join(', ')}</span>
          </div>
        </div>
      )}
    </div>
  );
};
