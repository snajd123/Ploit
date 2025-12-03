import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, TrendingDown, CheckCircle, AlertTriangle,
  Minus, Loader2, AlertCircle, ChevronDown, ChevronRight,
  TrendingUp, Circle, ListOrdered
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine
} from 'recharts';
import { api } from '../services/api';
import type {
  SessionGroupAnalysisResponse,
  SessionTrendData,
  ScenarioComparison,
  ImprovementStatus
} from '../types';

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
    <div className={`flex flex-col items-center justify-center p-4 rounded-lg border-2 ${gradeColors[grade] || gradeColors.C}`}>
      <span className="text-4xl font-bold">{grade}</span>
      <span className="text-sm opacity-75">Score: {score.toFixed(0)}</span>
    </div>
  );
};

// Status badge
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

// View mode type
type ViewMode = 'trend' | 'aggregate' | 'priority';

// Spectrum visualization component (aggregate view)
const SpectrumBar: React.FC<{
  gtoValue: number;
  overallValue: number;
  sessionValue: number | null;
  leakDirection: string | null;
}> = ({ gtoValue, overallValue, sessionValue, leakDirection }) => {
  const min = Math.min(0, gtoValue - 30, overallValue - 10, (sessionValue || overallValue) - 10);
  const max = Math.max(100, gtoValue + 30, overallValue + 10, (sessionValue || overallValue) + 10);
  const range = max - min;

  const getPosition = (value: number) => ((value - min) / range) * 100;

  const gtoPos = getPosition(gtoValue);
  const overallPos = getPosition(overallValue);
  const sessionPos = sessionValue !== null ? getPosition(sessionValue) : null;

  const gtoZoneLeft = getPosition(gtoValue - 5);
  const gtoZoneRight = getPosition(gtoValue + 5);
  const gtoZoneWidth = gtoZoneRight - gtoZoneLeft;

  return (
    <div className="relative h-12 w-full">
      {/* Base bar */}
      <div className="absolute top-5 left-0 right-0 h-2 bg-gray-200 rounded-full" />

      {/* GTO zone */}
      <div
        className="absolute top-5 h-2 bg-green-200 rounded-full"
        style={{ left: `${gtoZoneLeft}%`, width: `${gtoZoneWidth}%` }}
      />

      {/* GTO marker */}
      <div
        className="absolute top-4 w-0.5 h-4 bg-green-600"
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
        className="absolute top-4.5 w-3 h-3 rounded-full border-2 border-gray-500 bg-white transform -translate-x-1/2"
        style={{ left: `${overallPos}%`, top: '14px' }}
        title={`Overall: ${overallValue.toFixed(1)}%`}
      />

      {/* Session/Combined marker (filled circle) */}
      {sessionPos !== null && (
        <div
          className="absolute w-3 h-3 rounded-full bg-blue-600 transform -translate-x-1/2"
          style={{ left: `${sessionPos}%`, top: '14px' }}
          title={`Combined: ${sessionValue?.toFixed(1)}%`}
        />
      )}

      {/* Labels at bottom */}
      <div className="absolute top-8 left-0 text-[10px] text-gray-400">
        {leakDirection === 'too_tight' || leakDirection === 'too_low' ? 'Too Tight/Low' : '0%'}
      </div>
      <div className="absolute top-8 right-0 text-[10px] text-gray-400">
        {leakDirection === 'too_loose' || leakDirection === 'too_high' ? 'Too Loose/High' : '100%'}
      </div>
    </div>
  );
};

// Priority Leak Card component (for priority view)
const PriorityLeakCard: React.FC<{
  scenario: ScenarioComparison;
  rank: number;
}> = ({ scenario, rank }) => {
  const severityColors = {
    major: 'border-l-red-500 bg-red-50',
    moderate: 'border-l-orange-500 bg-orange-50',
    minor: 'border-l-yellow-500 bg-yellow-50',
    none: 'border-l-gray-300 bg-gray-50'
  };

  const evWeightLabel = scenario.ev_weight
    ? scenario.ev_weight >= 1.4 ? 'High EV Impact'
    : scenario.ev_weight >= 1.2 ? 'Medium EV Impact'
    : 'Standard EV'
    : 'Standard EV';

  return (
    <div className={`rounded-lg border-l-4 ${severityColors[scenario.leak_severity]} p-4 shadow-sm`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-200 text-gray-700 font-bold text-sm">
            #{rank}
          </span>
          <div>
            <h4 className="font-semibold text-gray-900">{scenario.display_name}</h4>
            <div className="flex items-center gap-2 mt-1">
              <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                scenario.leak_severity === 'major' ? 'bg-red-100 text-red-700' :
                scenario.leak_severity === 'moderate' ? 'bg-orange-100 text-orange-700' :
                'bg-yellow-100 text-yellow-700'
              }`}>
                {scenario.leak_severity?.toUpperCase()}
              </span>
              <span className="text-xs text-gray-500">{evWeightLabel}</span>
              {scenario.priority_score && (
                <span className="text-xs text-gray-400">Score: {scenario.priority_score.toFixed(1)}</span>
              )}
            </div>
          </div>
        </div>

        <div className="text-right">
          <StatusBadge status={scenario.improvement_status} />
        </div>
      </div>

      {/* Stats row */}
      <div className="mt-3 grid grid-cols-4 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Overall:</span>
          <span className="ml-1 font-medium text-gray-700">{scenario.overall_value.toFixed(1)}%</span>
        </div>
        <div>
          <span className="text-gray-500">GTO:</span>
          <span className="ml-1 font-medium text-green-700">{scenario.gto_value.toFixed(1)}%</span>
        </div>
        <div>
          <span className="text-gray-500">Session:</span>
          <span className="ml-1 font-medium text-blue-700">
            {scenario.session_value?.toFixed(1) ?? '—'}%
          </span>
        </div>
        <div>
          <span className="text-gray-500">Deviation:</span>
          <span className={`ml-1 font-medium ${
            Math.abs(scenario.overall_deviation) >= 20 ? 'text-red-600' :
            Math.abs(scenario.overall_deviation) >= 10 ? 'text-orange-600' :
            'text-yellow-600'
          }`}>
            {scenario.overall_deviation > 0 ? '+' : ''}{scenario.overall_deviation.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Spectrum bar */}
      <div className="mt-3">
        <SpectrumBar
          gtoValue={scenario.gto_value}
          overallValue={scenario.overall_value}
          sessionValue={scenario.session_value}
          leakDirection={scenario.leak_direction}
        />
      </div>

      {/* Action recommendation */}
      <div className="mt-3 text-xs text-gray-600 bg-white rounded px-3 py-2">
        <span className="font-medium">Direction: </span>
        {scenario.leak_direction === 'too_tight' && 'Open wider / Call more / Be more aggressive'}
        {scenario.leak_direction === 'too_loose' && 'Tighten up / Be more selective'}
        {scenario.leak_direction === 'too_high' && 'Reduce frequency / Fold more'}
        {scenario.leak_direction === 'too_low' && 'Increase frequency / Play more'}
        {!scenario.leak_direction && 'Within acceptable range'}
      </div>
    </div>
  );
};

// Stats trend chart
const StatsTrendChart: React.FC<{
  trends: SessionTrendData[];
  statKey: keyof SessionTrendData['stats'];
  label: string;
  color: string;
}> = ({ trends, statKey, label, color }) => {
  const data = trends.map((t, idx) => ({
    name: t.date ? new Date(t.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : `S${idx + 1}`,
    value: t.stats[statKey] || 0,
    hands: t.hands
  }));

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h4 className="text-sm font-medium text-gray-700 mb-3">{label}</h4>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="name" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(1)}%`, label]}
            labelFormatter={(label) => label}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

// Scenario trend chart with GTO reference line
const ScenarioTrendChart: React.FC<{
  scenario: ScenarioComparison;
  trends: SessionTrendData[];
}> = ({ scenario, trends }) => {
  const data = trends.map((t, idx) => {
    const scenarioData = t.scenarios[scenario.scenario_id];
    return {
      name: t.date ? new Date(t.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : `S${idx + 1}`,
      value: scenarioData?.value ?? null,
      sample: scenarioData?.sample ?? 0,
      overall: scenario.overall_value
    };
  }).filter(d => d.value !== null);

  if (data.length === 0) {
    return (
      <div className="text-sm text-gray-500 italic">
        No data for this scenario in selected sessions
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={150}>
      <LineChart data={data} margin={{ top: 20, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="name" tick={{ fontSize: 10 }} />
        <YAxis tick={{ fontSize: 10 }} domain={[0, 100]} />
        <Tooltip
          formatter={(value: number, name: string) => {
            if (name === 'value') return [`${value.toFixed(1)}%`, 'Session'];
            if (name === 'overall') return [`${value.toFixed(1)}%`, 'Overall'];
            return [value, name];
          }}
        />
        <Legend />
        {/* GTO reference line */}
        <ReferenceLine
          y={scenario.gto_value}
          stroke="#10b981"
          strokeDasharray="5 5"
          strokeWidth={2}
          label={{ value: `GTO ${scenario.gto_value.toFixed(0)}%`, fill: '#10b981', fontSize: 10, position: 'right' }}
        />
        {/* Overall average line */}
        <ReferenceLine
          y={scenario.overall_value}
          stroke="#9ca3af"
          strokeDasharray="3 3"
          label={{ value: 'Overall', fill: '#9ca3af', fontSize: 10, position: 'left' }}
        />
        {/* Session values */}
        <Line
          type="monotone"
          dataKey="value"
          name="Session"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={{ r: 5, fill: '#3b82f6' }}
          activeDot={{ r: 7 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

// Collapsible scenario section
const ScenarioSection: React.FC<{
  scenario: ScenarioComparison;
  trends: SessionTrendData[];
  viewMode: ViewMode;
  defaultExpanded?: boolean;
}> = ({ scenario, trends, viewMode, defaultExpanded = false }) => {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className={`border rounded-lg overflow-hidden ${scenario.is_leak ? 'border-gray-300 bg-white' : 'border-gray-200 bg-gray-50'}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <span className="font-medium text-gray-900">{scenario.display_name}</span>
          {scenario.is_leak && (
            <span className={`px-2 py-0.5 text-xs font-medium rounded ${
              scenario.leak_severity === 'major' ? 'bg-red-100 text-red-700' :
              scenario.leak_severity === 'moderate' ? 'bg-orange-100 text-orange-700' :
              'bg-yellow-100 text-yellow-700'
            }`}>
              {scenario.leak_severity?.toUpperCase()}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <div className="text-sm text-gray-600">
            Overall: {scenario.overall_value.toFixed(1)}% | GTO: {scenario.gto_value.toFixed(1)}%
          </div>
          {scenario.is_leak && scenario.improvement_status && (
            <StatusBadge status={scenario.improvement_status} />
          )}
        </div>
      </button>

      {expanded && (
        <div className="p-4 border-t border-gray-200 bg-white">
          {viewMode === 'trend' ? (
            <ScenarioTrendChart scenario={scenario} trends={trends} />
          ) : (
            <SpectrumBar
              gtoValue={scenario.gto_value}
              overallValue={scenario.overall_value}
              sessionValue={scenario.session_value}
              leakDirection={scenario.leak_direction}
            />
          )}
          {scenario.session_sample !== null && scenario.session_sample > 0 && (
            <div className="mt-3 flex items-center justify-between text-sm">
              <div className="text-gray-600">
                Combined: <span className="font-medium text-blue-700">{scenario.session_value?.toFixed(1)}%</span>
                <span className="text-gray-400 ml-2">({scenario.session_sample} obs)</span>
              </div>
              {scenario.improvement_score !== null && (
                <div className="text-gray-600">
                  Improvement Score: <span className="font-medium">{scenario.improvement_score.toFixed(0)}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Category section with scenarios
const CategorySection: React.FC<{
  title: string;
  scenarios: ScenarioComparison[];
  trends: SessionTrendData[];
  viewMode: ViewMode;
}> = ({ title, scenarios, trends, viewMode }) => {
  const [expanded, setExpanded] = useState(true);
  const leaksCount = scenarios.filter(s => s.is_leak).length;
  const improvedCount = scenarios.filter(s => s.is_leak && s.improvement_status === 'improved').length;

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          <span className="font-semibold text-gray-800">{title}</span>
          {leaksCount > 0 && (
            <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
              {improvedCount}/{leaksCount} improved
            </span>
          )}
        </div>
      </button>

      {expanded && (
        <div className="p-4 space-y-3">
          {scenarios.map(scenario => (
            <ScenarioSection
              key={scenario.scenario_id}
              scenario={scenario}
              trends={trends}
              viewMode={viewMode}
              defaultExpanded={scenario.is_leak && scenario.leak_severity === 'major'}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const SessionGroupAnalysis: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [data, setData] = useState<SessionGroupAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('trend');

  const sessionIds = useMemo(() => {
    const idsParam = searchParams.get('ids');
    if (!idsParam) return [];
    return idsParam.split(',').map(id => parseInt(id, 10)).filter(id => !isNaN(id));
  }, [searchParams]);

  useEffect(() => {
    const fetchData = async () => {
      if (sessionIds.length === 0) {
        setError('No session IDs provided');
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const result = await api.getSessionGroupAnalysis(sessionIds);
        setData(result);
      } catch (err) {
        console.error('Error fetching group analysis:', err);
        setError('Failed to load group analysis data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [sessionIds]);

  // Group scenarios by category
  const groupedScenarios = useMemo(() => {
    if (!data) return { opening: [], defense: [], facing_3bet: [] };

    return {
      opening: data.aggregated.scenarios.filter(s => s.category === 'opening'),
      defense: data.aggregated.scenarios.filter(s => s.category === 'defense'),
      facing_3bet: data.aggregated.scenarios.filter(s => s.category === 'facing_3bet')
    };
  }, [data]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="animate-spin text-blue-600 mr-3" size={32} />
        <span className="text-lg text-gray-600">Analyzing sessions...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-24">
        <AlertCircle className="mx-auto mb-4 text-red-500" size={48} />
        <p className="text-red-600 text-lg">{error || 'No data available'}</p>
        <button
          onClick={() => navigate('/sessions')}
          className="mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
        >
          Back to Sessions
        </button>
      </div>
    );
  }

  const { aggregated, session_trends } = data;
  const { summary } = aggregated;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <button
          onClick={() => navigate('/sessions')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft size={20} />
          Back to Sessions
        </button>

        <h1 className="text-2xl font-bold text-gray-900">Leak Progress Analysis</h1>
        <p className="text-gray-600 mt-1">
          Analyzing {data.session_count} sessions ({data.total_hands.toLocaleString()} hands)
          {data.date_range.start && data.date_range.end && (
            <span className="text-gray-500">
              {' '}from {new Date(data.date_range.start).toLocaleDateString()} to {new Date(data.date_range.end).toLocaleDateString()}
            </span>
          )}
        </p>
      </div>

      {/* Summary Card */}
      <div className="bg-gradient-to-r from-blue-50 to-white rounded-lg border border-blue-200 p-6">
        <div className="flex items-start gap-6">
          <GradeDisplay grade={summary.session_grade} score={summary.overall_improvement_score} />

          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Overall Progress</h2>
            <div className="grid grid-cols-4 gap-4">
              <div className="flex items-center gap-2">
                <CheckCircle size={18} className="text-green-600" />
                <div>
                  <div className="text-2xl font-bold text-gray-900">{summary.scenarios_improved}</div>
                  <div className="text-xs text-gray-600">Improved</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Minus size={18} className="text-gray-500" />
                <div>
                  <div className="text-2xl font-bold text-gray-900">{summary.scenarios_same}</div>
                  <div className="text-xs text-gray-600">Same</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <TrendingDown size={18} className="text-red-600" />
                <div>
                  <div className="text-2xl font-bold text-gray-900">{summary.scenarios_worse}</div>
                  <div className="text-xs text-gray-600">Worse</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <AlertTriangle size={18} className="text-orange-600" />
                <div>
                  <div className="text-2xl font-bold text-gray-900">{summary.scenarios_overcorrected}</div>
                  <div className="text-xs text-gray-600">Overcorrected</div>
                </div>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-3">
              {summary.scenarios_with_leaks} scenarios with leaks identified (out of {summary.total_scenarios} total)
            </p>
          </div>

          <div className="text-right">
            <div className={`text-2xl font-bold ${data.total_profit_bb >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {data.total_profit_bb >= 0 ? '+' : ''}{data.total_profit_bb.toFixed(1)} bb
            </div>
            <div className="text-sm text-gray-500">Total P/L</div>
            <div className={`text-sm mt-1 ${data.confidence === 'low' ? 'text-orange-500' : 'text-gray-500'}`}>
              {data.confidence} confidence
            </div>
          </div>
        </div>
      </div>

      {/* Stats Trends */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Stat Trends Over Sessions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatsTrendChart trends={session_trends} statKey="vpip_pct" label="VPIP%" color="#3b82f6" />
          <StatsTrendChart trends={session_trends} statKey="pfr_pct" label="PFR%" color="#10b981" />
          <StatsTrendChart trends={session_trends} statKey="three_bet_pct" label="3-Bet%" color="#f59e0b" />
          <StatsTrendChart trends={session_trends} statKey="fold_to_3bet_pct" label="Fold to 3-Bet%" color="#ef4444" />
        </div>
      </div>

      {/* Scenario Analysis */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Scenario Analysis</h2>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-2 bg-gray-100 p-1 rounded-lg">
            <button
              onClick={() => setViewMode('priority')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
                viewMode === 'priority'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <ListOrdered size={14} />
              Priority
            </button>
            <button
              onClick={() => setViewMode('trend')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
                viewMode === 'trend'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <TrendingUp size={14} />
              Trend
            </button>
            <button
              onClick={() => setViewMode('aggregate')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
                viewMode === 'aggregate'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Circle size={14} />
              Aggregate
            </button>
          </div>
        </div>

        {/* Legend for aggregate view */}
        {viewMode === 'aggregate' && (
          <div className="flex items-center gap-4 text-xs text-gray-500 px-2">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full border border-gray-500" /> Overall
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-600" /> Combined Sessions
            </span>
            <span className="flex items-center gap-1">
              <span className="w-4 h-2 bg-green-200 rounded" /> GTO Zone
            </span>
          </div>
        )}

        {/* Priority View */}
        {viewMode === 'priority' ? (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Priority Leaks</h3>
                <p className="text-sm text-gray-500 mt-1">
                  Leaks ranked by EV impact, severity, and sample confidence
                </p>
              </div>
              <div className="text-sm text-gray-500">
                {data.aggregated.priority_leaks?.length || 0} leaks to address
              </div>
            </div>

            {data.aggregated.priority_leaks && data.aggregated.priority_leaks.length > 0 ? (
              <div className="space-y-4">
                {data.aggregated.priority_leaks.map((scenario, idx) => (
                  <PriorityLeakCard
                    key={scenario.scenario_id}
                    scenario={scenario}
                    rank={idx + 1}
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle size={48} className="mx-auto mb-3 text-green-500" />
                <p>No significant leaks identified!</p>
                <p className="text-sm mt-1">Your play is within GTO ranges across all scenarios.</p>
              </div>
            )}
          </div>
        ) : (
          <>
            <CategorySection
              title="Opening (RFI)"
              scenarios={groupedScenarios.opening}
              trends={session_trends}
              viewMode={viewMode}
            />

            <CategorySection
              title="Defense vs Opens"
              scenarios={groupedScenarios.defense}
              trends={session_trends}
              viewMode={viewMode}
            />

            <CategorySection
              title="Facing 3-Bet"
              scenarios={groupedScenarios.facing_3bet}
              trends={session_trends}
              viewMode={viewMode}
            />
          </>
        )}
      </div>

      {/* Session Details Table */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Session Details</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Hands</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">P/L (bb)</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">VPIP</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">PFR</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">3-Bet</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Fold to 3B</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {session_trends.map((trend, idx) => (
                <tr key={trend.session_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {trend.date ? new Date(trend.date).toLocaleDateString() : `Session ${idx + 1}`}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 text-right">{trend.hands}</td>
                  <td className={`px-4 py-3 text-sm text-right font-medium ${trend.profit_bb >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {trend.profit_bb >= 0 ? '+' : ''}{trend.profit_bb.toFixed(1)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 text-right">{trend.stats.vpip_pct.toFixed(1)}%</td>
                  <td className="px-4 py-3 text-sm text-gray-600 text-right">{trend.stats.pfr_pct.toFixed(1)}%</td>
                  <td className="px-4 py-3 text-sm text-gray-600 text-right">{trend.stats.three_bet_pct.toFixed(1)}%</td>
                  <td className="px-4 py-3 text-sm text-gray-600 text-right">{trend.stats.fold_to_3bet_pct.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default SessionGroupAnalysis;
