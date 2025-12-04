import React, { useState, useEffect, useMemo } from 'react';
import {
  TrendingDown, CheckCircle, AlertTriangle, Minus,
  ChevronDown, ChevronRight, AlertCircle, Loader2
} from 'lucide-react';
import type {
  SessionLeakComparisonResponse,
  ScenarioComparison,
  ImprovementStatus
} from '../types';
import { api } from '../services/api';

interface LeakProgressViewProps {
  sessionId: number;
}

// Status badge component
const StatusBadge: React.FC<{ status: ImprovementStatus | null }> = ({ status }) => {
  if (!status) return null;

  const config = {
    improved: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100', label: 'Improved' },
    same: { icon: Minus, color: 'text-gray-600', bg: 'bg-gray-100', label: 'Same' },
    worse: { icon: TrendingDown, color: 'text-red-600', bg: 'bg-red-100', label: 'Worse' },
    overcorrected: { icon: AlertTriangle, color: 'text-orange-600', bg: 'bg-orange-100', label: 'Overcorrected' }
  };

  const { icon: Icon, color, bg, label } = config[status];

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${bg} ${color}`}>
      <Icon size={12} />
      {label}
    </span>
  );
};

// Severity badge
const SeverityBadge: React.FC<{ severity: string }> = ({ severity }) => {
  const colors: Record<string, string> = {
    none: 'bg-gray-100 text-gray-600',
    minor: 'bg-yellow-100 text-yellow-700',
    moderate: 'bg-orange-100 text-orange-700',
    major: 'bg-red-100 text-red-700'
  };

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded ${colors[severity] || colors.none}`}>
      {severity.toUpperCase()}
    </span>
  );
};

// Spectrum visualization component
const SpectrumBar: React.FC<{
  gtoValue: number;
  overallValue: number;
  sessionValue: number | null;
  leakDirection: string | null;
}> = ({ gtoValue, overallValue, sessionValue, leakDirection }) => {
  // Determine the range for the spectrum
  const min = Math.min(0, gtoValue - 30, overallValue - 10, (sessionValue || overallValue) - 10);
  const max = Math.max(100, gtoValue + 30, overallValue + 10, (sessionValue || overallValue) + 10);
  const range = max - min;

  const getPosition = (value: number) => ((value - min) / range) * 100;

  const gtoPos = getPosition(gtoValue);
  const overallPos = getPosition(overallValue);
  const sessionPos = sessionValue !== null ? getPosition(sessionValue) : null;

  // GTO zone is +/- 5%
  const gtoZoneLeft = getPosition(gtoValue - 5);
  const gtoZoneRight = getPosition(gtoValue + 5);
  const gtoZoneWidth = gtoZoneRight - gtoZoneLeft;

  return (
    <div className="relative h-10 w-full">
      {/* Base bar */}
      <div className="absolute top-4 left-0 right-0 h-2 bg-gray-200 rounded-full" />

      {/* GTO zone */}
      <div
        className="absolute top-4 h-2 bg-green-200 rounded-full"
        style={{ left: `${gtoZoneLeft}%`, width: `${gtoZoneWidth}%` }}
      />

      {/* GTO marker */}
      <div
        className="absolute top-3 w-0.5 h-4 bg-green-600"
        style={{ left: `${gtoPos}%` }}
      />
      <div
        className="absolute top-0 text-[10px] text-green-700 font-medium transform -translate-x-1/2"
        style={{ left: `${gtoPos}%` }}
      >
        GTO {gtoValue.toFixed(0)}%
      </div>

      {/* Overall marker (hollow circle) */}
      <div
        className="absolute top-3.5 w-3 h-3 rounded-full border-2 border-gray-500 bg-white transform -translate-x-1/2"
        style={{ left: `${overallPos}%` }}
        title={`Overall: ${overallValue.toFixed(1)}%`}
      />

      {/* Session marker (filled circle) */}
      {sessionPos !== null && (
        <div
          className="absolute top-3.5 w-3 h-3 rounded-full bg-blue-600 transform -translate-x-1/2"
          style={{ left: `${sessionPos}%` }}
          title={`Session: ${sessionValue?.toFixed(1)}%`}
        />
      )}

      {/* Labels at bottom */}
      <div className="absolute top-7 left-0 text-[10px] text-gray-400">
        {leakDirection === 'too_tight' || leakDirection === 'too_low' ? 'Too Tight/Low' : '0%'}
      </div>
      <div className="absolute top-7 right-0 text-[10px] text-gray-400">
        {leakDirection === 'too_loose' || leakDirection === 'too_high' ? 'Too Loose/High' : '100%'}
      </div>
    </div>
  );
};

// Scenario card component
const ScenarioCard: React.FC<{ scenario: ScenarioComparison }> = ({ scenario }) => {
  const hasSessionData = scenario.session_sample > 0;

  return (
    <div className={`p-3 rounded-lg border ${scenario.is_leak ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900 text-sm">{scenario.display_name}</span>
          {scenario.is_leak ? (
            <SeverityBadge severity={scenario.leak_severity} />
          ) : (
            <span className="px-2 py-0.5 text-xs font-medium rounded bg-green-100 text-green-700">OK</span>
          )}
        </div>
        {scenario.is_leak && hasSessionData && (
          <StatusBadge status={scenario.improvement_status} />
        )}
      </div>

      {/* Always show the spectrum bar */}
      <SpectrumBar
        gtoValue={scenario.gto_value}
        overallValue={scenario.overall_value}
        sessionValue={scenario.session_value}
        leakDirection={scenario.leak_direction}
      />

      <div className="mt-3 flex items-center justify-between text-xs">
        <div className="flex items-center gap-3">
          <span className="text-gray-500">
            <span className="inline-block w-2 h-2 rounded-full border border-gray-500 mr-1" />
            Overall: <span className="font-medium text-gray-700">{scenario.overall_value.toFixed(1)}%</span>
          </span>
          {hasSessionData && (
            <span className="text-gray-500">
              <span className="inline-block w-2 h-2 rounded-full bg-blue-600 mr-1" />
              Session: <span className="font-medium text-blue-700">{scenario.session_value?.toFixed(1)}%</span>
            </span>
          )}
          <span className="text-gray-500">
            GTO: <span className="font-medium text-green-700">{scenario.gto_value.toFixed(1)}%</span>
          </span>
        </div>
        <span className={`${scenario.confidence_level === 'insufficient' ? 'text-orange-500' : 'text-gray-400'}`}>
          {scenario.session_sample} obs ({scenario.confidence_level})
        </span>
      </div>

      {scenario.is_leak && scenario.overcorrected && (
        <div className="mt-2 text-xs text-orange-600 bg-orange-50 p-2 rounded flex items-start gap-1">
          <AlertTriangle size={12} className="mt-0.5 flex-shrink-0" />
          <span>
            Went from {scenario.leak_direction === 'too_high' || scenario.leak_direction === 'too_loose' ? 'too high' : 'too low'}
            {' '}({scenario.overall_value.toFixed(0)}%) to opposite side ({scenario.session_value?.toFixed(0)}%)
          </span>
        </div>
      )}
    </div>
  );
};

// Collapsible category section
const CategorySection: React.FC<{
  title: string;
  scenarios: ScenarioComparison[];
  defaultExpanded?: boolean;
}> = ({ title, scenarios, defaultExpanded = true }) => {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const leaksCount = scenarios.filter(s => s.is_leak).length;
  const improvedCount = scenarios.filter(s => s.is_leak && s.improvement_status === 'improved').length;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <span className="font-medium text-gray-800">{title}</span>
          {leaksCount > 0 && (
            <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
              {improvedCount}/{leaksCount} improved
            </span>
          )}
        </div>
      </button>
      {expanded && (
        <div className="p-3 space-y-2 bg-white">
          {scenarios.map(scenario => (
            <ScenarioCard key={scenario.scenario_id} scenario={scenario} />
          ))}
        </div>
      )}
    </div>
  );
};

// Grade display component
const GradeDisplay: React.FC<{ grade: string; score: number }> = ({ grade, score }) => {
  const gradeColors: Record<string, string> = {
    A: 'text-green-600 bg-green-100 border-green-300',
    B: 'text-blue-600 bg-blue-100 border-blue-300',
    C: 'text-yellow-600 bg-yellow-100 border-yellow-300',
    D: 'text-orange-600 bg-orange-100 border-orange-300',
    F: 'text-red-600 bg-red-100 border-red-300'
  };

  return (
    <div className={`flex flex-col items-center justify-center p-4 rounded-lg border ${gradeColors[grade] || gradeColors.C}`}>
      <span className="text-3xl font-bold">{grade}</span>
      <span className="text-sm opacity-75">Score: {score.toFixed(0)}</span>
    </div>
  );
};

const LeakProgressView: React.FC<LeakProgressViewProps> = ({ sessionId }) => {
  const [data, setData] = useState<SessionLeakComparisonResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await api.getSessionLeakComparison(sessionId);
        setData(result);
      } catch (err) {
        console.error('Error fetching leak comparison:', err);
        setError('Failed to load leak comparison data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [sessionId]);

  // Group scenarios by category, filtering out those with 0 observations
  const groupedScenarios = useMemo(() => {
    if (!data) return { opening: [], defense: [], facing_3bet: [] };

    // Only show scenarios that have session data (session_sample > 0)
    const hasSessionData = (s: ScenarioComparison) => s.session_sample > 0;

    return {
      opening: data.scenarios.filter(s => s.category === 'opening' && hasSessionData(s)),
      defense: data.scenarios.filter(s => s.category === 'defense' && hasSessionData(s)),
      facing_3bet: data.scenarios.filter(s => s.category === 'facing_3bet' && hasSessionData(s))
    };
  }, [data]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="animate-spin text-blue-600 mr-2" size={24} />
        <span className="text-gray-600">Loading leak comparison...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="mx-auto mb-3 text-red-500" size={40} />
        <p className="text-red-600">{error || 'No data available'}</p>
      </div>
    );
  }

  const { summary } = data;

  return (
    <div className="space-y-4">
      {/* Header with summary */}
      <div className="flex items-start gap-4 p-4 bg-gradient-to-r from-blue-50 to-white rounded-lg border border-blue-200">
        <GradeDisplay grade={summary.session_grade} score={summary.overall_improvement_score} />

        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-2">Session Leak Progress</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="flex items-center gap-2">
              <CheckCircle size={14} className="text-green-600" />
              <span className="text-gray-600">
                <span className="font-medium text-gray-900">{summary.scenarios_improved}</span> improved
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Minus size={14} className="text-gray-500" />
              <span className="text-gray-600">
                <span className="font-medium text-gray-900">{summary.scenarios_same}</span> same
              </span>
            </div>
            <div className="flex items-center gap-2">
              <TrendingDown size={14} className="text-red-600" />
              <span className="text-gray-600">
                <span className="font-medium text-gray-900">{summary.scenarios_worse}</span> worse
              </span>
            </div>
            <div className="flex items-center gap-2">
              <AlertTriangle size={14} className="text-orange-600" />
              <span className="text-gray-600">
                <span className="font-medium text-gray-900">{summary.scenarios_overcorrected}</span> overcorrected
              </span>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {summary.scenarios_with_leaks} scenarios with leaks identified (out of {summary.total_scenarios} total)
          </p>
        </div>

        <div className="text-right text-sm text-gray-500">
          <div>{data.session_hands} hands</div>
          <div className={`${data.confidence === 'low' ? 'text-orange-500' : ''}`}>
            {data.confidence} confidence
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-gray-500 px-2">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full border border-gray-500" /> Overall
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-blue-600" /> This Session
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-2 bg-green-200 rounded" /> GTO Zone
        </span>
      </div>

      {/* Scenario categories */}
      <CategorySection
        title="Opening (RFI)"
        scenarios={groupedScenarios.opening}
        defaultExpanded={groupedScenarios.opening.some(s => s.is_leak)}
      />

      <CategorySection
        title="Defense vs Opens"
        scenarios={groupedScenarios.defense}
        defaultExpanded={groupedScenarios.defense.some(s => s.is_leak)}
      />

      <CategorySection
        title="Facing 3-Bet"
        scenarios={groupedScenarios.facing_3bet}
        defaultExpanded={groupedScenarios.facing_3bet.some(s => s.is_leak)}
      />

      {/* No leaks message */}
      {summary.scenarios_with_leaks === 0 && (
        <div className="text-center py-8 bg-green-50 rounded-lg border border-green-200">
          <CheckCircle className="mx-auto mb-2 text-green-600" size={32} />
          <p className="text-green-700 font-medium">No significant leaks identified</p>
          <p className="text-sm text-green-600">Your overall play is within GTO ranges</p>
        </div>
      )}
    </div>
  );
};

export default LeakProgressView;
