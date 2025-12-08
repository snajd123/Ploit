import React, { useState, useEffect } from 'react';
import {
  Target, Clock, TrendingUp, TrendingDown, CheckCircle2,
  XCircle, AlertCircle, Loader2, ChevronDown, ChevronUp
} from 'lucide-react';
import type { SessionSegmentsResponse, SessionSegment, LeakProgress } from '../types';
import { api } from '../services/api';

interface SessionSegmentsViewProps {
  sessionId: number;
}

// Progress bar showing actual vs target
const GoalProgressBar: React.FC<{
  baseline: number;
  target: number;
  actual: number | null;
  gto: number;
}> = ({ baseline, target, actual, gto }) => {
  if (actual === null) return null;

  const min = Math.min(baseline, target, actual, gto) - 5;
  const max = Math.max(baseline, target, actual, gto) + 5;
  const range = max - min;

  const getPos = (val: number) => ((val - min) / range) * 100;

  return (
    <div className="relative h-6 bg-slate-100 rounded-full overflow-hidden">
      {/* GTO marker */}
      <div
        className="absolute top-0 bottom-0 w-0.5 bg-emerald-500 z-10"
        style={{ left: `${getPos(gto)}%` }}
      />
      {/* Target zone */}
      <div
        className="absolute top-0 bottom-0 bg-emerald-100"
        style={{
          left: `${getPos(Math.min(target, gto))}%`,
          width: `${Math.abs(getPos(target) - getPos(gto))}%`
        }}
      />
      {/* Baseline marker */}
      <div
        className="absolute top-1 bottom-1 w-1 bg-slate-400 rounded"
        style={{ left: `${getPos(baseline)}%` }}
      />
      {/* Actual value marker */}
      <div
        className="absolute top-0 bottom-0 w-2 bg-indigo-600 rounded"
        style={{ left: `${getPos(actual)}%` }}
      />
    </div>
  );
};

// Single leak progress item
const LeakProgressItem: React.FC<{ progress: LeakProgress }> = ({ progress }) => {
  const hasData = progress.actual_value !== null && progress.sample_size >= 3;

  return (
    <div className="border border-slate-200 rounded-lg p-4 bg-white">
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="font-medium text-slate-800">{progress.description}</div>
          <div className="text-xs text-slate-500">{progress.session_goal}</div>
        </div>
        {hasData && (
          <div className="flex-shrink-0">
            {progress.hit_target ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
                <CheckCircle2 size={12} />
                Hit Target
              </span>
            ) : progress.improved ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 bg-blue-50 px-2 py-1 rounded-full">
                <TrendingUp size={12} />
                Improved
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600 bg-amber-50 px-2 py-1 rounded-full">
                <TrendingDown size={12} />
                Needs Work
              </span>
            )}
          </div>
        )}
      </div>

      {hasData ? (
        <>
          <GoalProgressBar
            baseline={progress.baseline_value}
            target={progress.target_value}
            actual={progress.actual_value}
            gto={progress.gto_value}
          />
          <div className="flex justify-between mt-2 text-xs text-slate-500">
            <span>Baseline: {progress.baseline_value.toFixed(1)}%</span>
            <span className="font-medium text-indigo-600">
              Actual: {progress.actual_value?.toFixed(1)}%
            </span>
            <span>Target: {progress.target_value.toFixed(1)}%</span>
            <span className="text-emerald-600">GTO: {progress.gto_value.toFixed(1)}%</span>
          </div>
          <div className="text-xs text-slate-400 mt-1">
            {progress.sample_size} opportunities
          </div>
        </>
      ) : (
        <div className="text-sm text-slate-400 italic">
          Not enough data ({progress.sample_size} samples)
        </div>
      )}
    </div>
  );
};

// Single segment card
const SegmentCard: React.FC<{
  segment: SessionSegment;
  index: number;
}> = ({ segment, index }) => {
  const [expanded, setExpanded] = useState(segment.has_strategy && segment.leak_progress.length > 0);

  const formatTime = (isoString: string | null) => {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const goalsHit = segment.leak_progress.filter(p => p.hit_target).length;
  const goalsImproved = segment.leak_progress.filter(p => p.improved && !p.hit_target).length;
  const totalGoals = segment.leak_progress.filter(p => p.actual_value !== null).length;

  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden bg-white">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-4">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            segment.has_strategy ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-100 text-slate-400'
          }`}>
            {segment.has_strategy ? <Target size={20} /> : <AlertCircle size={20} />}
          </div>
          <div className="text-left">
            <div className="font-semibold text-slate-800">
              {segment.has_strategy ? `Strategy Segment ${index + 1}` : 'No Strategy'}
            </div>
            <div className="text-xs text-slate-500 flex items-center gap-2">
              <Clock size={12} />
              {formatTime(segment.segment_start)} - {formatTime(segment.segment_end)}
              <span className="text-slate-300">|</span>
              {segment.hands_count} hands
              {segment.softness_score && (
                <>
                  <span className="text-slate-300">|</span>
                  <span className={segment.softness_score >= 3 ? 'text-emerald-600' : 'text-amber-600'}>
                    {segment.table_classification}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {segment.has_strategy && totalGoals > 0 && (
            <div className="text-right">
              <div className="text-sm font-semibold text-slate-700">
                {goalsHit + goalsImproved}/{totalGoals} goals
              </div>
              <div className="text-xs text-slate-500">
                {goalsHit} hit, {goalsImproved} improved
              </div>
            </div>
          )}
          <div className={`text-lg font-bold ${segment.segment_profit >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
            {segment.segment_profit >= 0 ? '+' : ''}{segment.segment_profit.toFixed(1)} bb
          </div>
          {expanded ? (
            <ChevronUp size={20} className="text-slate-400" />
          ) : (
            <ChevronDown size={20} className="text-slate-400" />
          )}
        </div>
      </button>

      {expanded && segment.has_strategy && (
        <div className="border-t border-slate-100 p-4 bg-slate-50">
          {segment.leak_progress.length > 0 ? (
            <div className="space-y-3">
              <div className="text-sm font-medium text-slate-700 mb-3">
                Goal Progress
              </div>
              {segment.leak_progress.map((progress, i) => (
                <LeakProgressItem key={i} progress={progress} />
              ))}
            </div>
          ) : segment.leak_reminders.length > 0 ? (
            <div className="text-sm text-slate-500">
              <div className="font-medium mb-2">Strategy Goals:</div>
              {segment.leak_reminders.map((reminder, i) => (
                <div key={i} className="text-xs text-slate-600 mb-1">
                  {reminder.description} - {reminder.session_goal}
                </div>
              ))}
              <div className="text-xs text-slate-400 mt-2 italic">
                Not enough hands to calculate progress
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-500 italic">
              No leak goals were set in this strategy
            </div>
          )}
        </div>
      )}

      {expanded && !segment.has_strategy && (
        <div className="border-t border-slate-100 p-4 bg-slate-50">
          <div className="text-sm text-slate-500 italic">
            These hands were played before a strategy was generated.
            Generate a strategy before your session to track goal progress.
          </div>
        </div>
      )}
    </div>
  );
};

const SessionSegmentsView: React.FC<SessionSegmentsViewProps> = ({ sessionId }) => {
  const [data, setData] = useState<SessionSegmentsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await api.getSessionSegments(sessionId);
        setData(result);
      } catch (err) {
        console.error('Error fetching segments:', err);
        setError('Failed to load session segments');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="animate-spin text-slate-400 mb-3" size={32} />
        <span className="text-slate-500">Loading session segments...</span>
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-800">Strategy Segments</h2>
        <p className="text-sm text-slate-500 mt-1">
          Track your progress against strategy goals throughout the session
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-indigo-50 rounded-xl p-4">
          <div className="text-2xl font-bold text-indigo-700">{data.total_segments}</div>
          <div className="text-xs text-indigo-600">Total Segments</div>
        </div>
        <div className="bg-emerald-50 rounded-xl p-4">
          <div className="text-2xl font-bold text-emerald-700">{data.segments_with_strategy}</div>
          <div className="text-xs text-emerald-600">With Strategy</div>
        </div>
        <div className="bg-slate-100 rounded-xl p-4">
          <div className="text-2xl font-bold text-slate-700">
            {data.segments.reduce((sum, s) => sum + s.hands_count, 0)}
          </div>
          <div className="text-xs text-slate-600">Total Hands</div>
        </div>
        <div className="bg-amber-50 rounded-xl p-4">
          <div className="text-2xl font-bold text-amber-700">
            {data.segments.reduce((sum, s) => sum + s.leak_progress.filter(p => p.hit_target).length, 0)}
          </div>
          <div className="text-xs text-amber-600">Goals Hit</div>
        </div>
      </div>

      {/* Segments */}
      <div className="space-y-3">
        {data.segments.map((segment, index) => (
          <SegmentCard key={segment.strategy_id || `no-strategy-${index}`} segment={segment} index={index} />
        ))}
      </div>

      {data.segments.length === 0 && (
        <div className="text-center py-12 bg-slate-50 rounded-xl">
          <AlertCircle className="mx-auto mb-3 text-slate-400" size={40} />
          <p className="text-slate-600 font-medium">No segments found</p>
          <p className="text-sm text-slate-500 mt-1">
            This session has no hands associated with it
          </p>
        </div>
      )}
    </div>
  );
};

export default SessionSegmentsView;
