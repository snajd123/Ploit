import React, { useState, useEffect, useMemo } from 'react';
import {
  TrendingUp, TrendingDown, Target, ChevronDown, ChevronUp,
  AlertCircle, Loader2, ArrowRight, CheckCircle2, XCircle
} from 'lucide-react';
import type {
  SessionLeakComparisonResponse,
  ScenarioComparison,
} from '../types';
import { api } from '../services/api';

interface LeakProgressViewProps {
  sessionId: number;
}

// Single leak item - clean, minimal design
const LeakItem: React.FC<{
  scenario: ScenarioComparison;
  showSessionData: boolean;
}> = ({ scenario, showSessionData }) => {
  const hasSession = scenario.session_sample > 0 && scenario.session_value !== null;

  // Calculate if session is closer to GTO
  const sessionDiff = hasSession ? Math.abs((scenario.session_value || 0) - scenario.gto_value) : null;
  const lifetimeDiff = Math.abs(scenario.overall_value - scenario.gto_value);
  const isImproved = sessionDiff !== null && sessionDiff < lifetimeDiff;

  // Direction indicator
  const getDirectionLabel = () => {
    if (!scenario.leak_direction) return null;
    if (scenario.leak_direction === 'too_high' || scenario.leak_direction === 'too_loose') {
      return <span className="text-xs text-rose-600 font-medium">Too High</span>;
    }
    return <span className="text-xs text-amber-600 font-medium">Too Low</span>;
  };

  return (
    <div className="group">
      <div className="flex items-center justify-between py-3 px-4 hover:bg-slate-50 rounded-lg transition-colors">
        {/* Left: Scenario name and direction */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-slate-800 truncate">
              {scenario.display_name}
            </span>
            {getDirectionLabel()}
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            {scenario.overall_sample} lifetime samples
          </div>
        </div>

        {/* Center: Values comparison */}
        <div className="flex items-center gap-6 px-4">
          {/* Lifetime value */}
          <div className="text-center min-w-[60px]">
            <div className="text-sm font-semibold text-slate-600">
              {scenario.overall_value.toFixed(1)}%
            </div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wide">
              Lifetime
            </div>
          </div>

          {/* Arrow */}
          {hasSession && showSessionData && (
            <>
              <ArrowRight size={16} className="text-slate-300" />

              {/* Session value */}
              <div className="text-center min-w-[60px]">
                <div className={`text-sm font-semibold ${isImproved ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {scenario.session_value?.toFixed(1)}%
                </div>
                <div className="text-[10px] text-slate-400 uppercase tracking-wide">
                  Session
                </div>
              </div>
            </>
          )}

          {/* GTO target */}
          <div className="text-center min-w-[60px] pl-4 border-l border-slate-200">
            <div className="text-sm font-semibold text-emerald-600">
              {scenario.gto_value.toFixed(1)}%
            </div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wide">
              GTO
            </div>
          </div>
        </div>

        {/* Right: Status */}
        <div className="w-24 text-right">
          {hasSession && showSessionData ? (
            isImproved ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
                <CheckCircle2 size={12} />
                Improved
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-600 bg-rose-50 px-2 py-1 rounded-full">
                <XCircle size={12} />
                Regressed
              </span>
            )
          ) : (
            <span className="text-xs text-slate-400">
              {scenario.session_sample} obs
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

// Category section with cleaner accordion
const CategorySection: React.FC<{
  title: string;
  icon: React.ReactNode;
  scenarios: ScenarioComparison[];
  defaultExpanded?: boolean;
}> = ({ title, icon, scenarios, defaultExpanded = false }) => {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const leaksWithSession = scenarios.filter(s => s.is_leak && s.session_sample > 0);
  const improvedCount = leaksWithSession.filter(s => {
    const sessionDiff = Math.abs((s.session_value || 0) - s.gto_value);
    const lifetimeDiff = Math.abs(s.overall_value - s.gto_value);
    return sessionDiff < lifetimeDiff;
  }).length;

  const totalLeaks = scenarios.filter(s => s.is_leak).length;

  if (scenarios.length === 0) return null;

  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden bg-white">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-slate-100 rounded-lg text-slate-600">
            {icon}
          </div>
          <div className="text-left">
            <div className="font-semibold text-slate-800">{title}</div>
            <div className="text-xs text-slate-500">
              {scenarios.length} scenarios tracked
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {totalLeaks > 0 && (
            <div className="text-right">
              <div className="text-sm font-semibold text-slate-700">
                {improvedCount}/{leaksWithSession.length}
              </div>
              <div className="text-xs text-slate-500">improved</div>
            </div>
          )}
          {expanded ? (
            <ChevronUp size={20} className="text-slate-400" />
          ) : (
            <ChevronDown size={20} className="text-slate-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-slate-100">
          {/* Leaks first */}
          {scenarios.filter(s => s.is_leak).length > 0 && (
            <div className="divide-y divide-slate-100">
              {scenarios
                .filter(s => s.is_leak)
                .sort((a, b) => {
                  // Sort by session sample (those with data first)
                  if (a.session_sample > 0 && b.session_sample === 0) return -1;
                  if (a.session_sample === 0 && b.session_sample > 0) return 1;
                  return 0;
                })
                .map(scenario => (
                  <LeakItem
                    key={scenario.scenario_id}
                    scenario={scenario}
                    showSessionData={true}
                  />
                ))}
            </div>
          )}

          {/* Non-leaks collapsed */}
          {scenarios.filter(s => !s.is_leak).length > 0 && (
            <div className="px-4 py-3 bg-slate-50 border-t border-slate-100">
              <div className="text-xs text-slate-500 flex items-center gap-1">
                <CheckCircle2 size={12} className="text-emerald-500" />
                {scenarios.filter(s => !s.is_leak).length} scenarios within GTO range
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Summary card
const SummaryCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}> = ({ icon, label, value, color }) => (
  <div className={`flex items-center gap-3 p-4 rounded-xl ${color}`}>
    <div className="p-2 bg-white/50 rounded-lg">
      {icon}
    </div>
    <div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs opacity-75">{label}</div>
    </div>
  </div>
);

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

  // Group scenarios by category
  const groupedScenarios = useMemo(() => {
    if (!data) return { opening: [], defense: [], facing_3bet: [] };

    return {
      opening: data.scenarios.filter(s => s.category === 'opening'),
      defense: data.scenarios.filter(s => s.category === 'defense'),
      facing_3bet: data.scenarios.filter(s => s.category === 'facing_3bet')
    };
  }, [data]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="animate-spin text-slate-400 mb-3" size={32} />
        <span className="text-slate-500">Analyzing session leaks...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-16">
        <AlertCircle className="mx-auto mb-3 text-rose-400" size={40} />
        <p className="text-rose-600 font-medium">{error || 'No data available'}</p>
      </div>
    );
  }

  const { summary } = data;
  const totalWithSession = data.scenarios.filter(s => s.session_sample > 0 && s.is_leak).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-800">Leak Progress</h2>
        <p className="text-sm text-slate-500 mt-1">
          Comparing this session's play against your lifetime tendencies
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <SummaryCard
          icon={<TrendingUp size={18} className="text-emerald-600" />}
          label="Improved"
          value={summary.scenarios_improved}
          color="bg-emerald-50 text-emerald-700"
        />
        <SummaryCard
          icon={<TrendingDown size={18} className="text-rose-600" />}
          label="Regressed"
          value={summary.scenarios_worse}
          color="bg-rose-50 text-rose-700"
        />
        <SummaryCard
          icon={<Target size={18} className="text-slate-600" />}
          label="Total Leaks"
          value={summary.scenarios_with_leaks}
          color="bg-slate-100 text-slate-700"
        />
        <SummaryCard
          icon={<AlertCircle size={18} className="text-amber-600" />}
          label="Overcorrected"
          value={summary.scenarios_overcorrected}
          color="bg-amber-50 text-amber-700"
        />
      </div>

      {/* Progress Bar */}
      {totalWithSession > 0 && (
        <div className="bg-slate-100 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-700">Session Progress</span>
            <span className="text-sm text-slate-500">
              {summary.scenarios_improved} of {totalWithSession} leaks improved
            </span>
          </div>
          <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-emerald-400 to-emerald-500 rounded-full transition-all duration-500"
              style={{
                width: `${totalWithSession > 0 ? (summary.scenarios_improved / totalWithSession) * 100 : 0}%`
              }}
            />
          </div>
        </div>
      )}

      {/* Category Sections */}
      <div className="space-y-3">
        <CategorySection
          title="Opening Ranges (RFI)"
          icon={<Target size={18} />}
          scenarios={groupedScenarios.opening}
          defaultExpanded={groupedScenarios.opening.some(s => s.is_leak && s.session_sample > 0)}
        />

        <CategorySection
          title="Defense vs Opens"
          icon={<Target size={18} />}
          scenarios={groupedScenarios.defense}
          defaultExpanded={groupedScenarios.defense.some(s => s.is_leak && s.session_sample > 0)}
        />

        <CategorySection
          title="Facing 3-Bet"
          icon={<Target size={18} />}
          scenarios={groupedScenarios.facing_3bet}
          defaultExpanded={groupedScenarios.facing_3bet.some(s => s.is_leak && s.session_sample > 0)}
        />
      </div>

      {/* No leaks message */}
      {summary.scenarios_with_leaks === 0 && (
        <div className="text-center py-12 bg-emerald-50 rounded-xl border border-emerald-100">
          <CheckCircle2 className="mx-auto mb-3 text-emerald-500" size={40} />
          <p className="text-emerald-700 font-semibold">Great job!</p>
          <p className="text-sm text-emerald-600 mt-1">No significant leaks identified in your play</p>
        </div>
      )}

      {/* Footer */}
      <div className="text-center text-xs text-slate-400 pt-4 border-t border-slate-100">
        Based on {data.session_hands} hands this session
      </div>
    </div>
  );
};

export default LeakProgressView;
