import React, { useState, useEffect } from 'react';
import {
  X, Loader2, MessageSquare, TrendingUp, TrendingDown, Target,
  AlertTriangle, CheckCircle, Users, BookOpen, ChevronDown, ChevronRight,
  AlertCircle, Info, ExternalLink, Zap, ClipboardCheck, Activity, Code
} from 'lucide-react';
import HandReplayModal from './HandReplayModal';
import { api } from '../services/api';
import type { HandReplayResponse } from '../types';

interface DebriefModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: number | null;
  sessionIds?: number[];  // For multi-session debrief
}

interface Debrief {
  session_summary: {
    session_id: string | number;
    total_hands: number;
    profit_loss_bb: number;
    bb_100: number;
    duration_minutes: number;
    stake_level: string;
  };
  gto_analysis: {
    baselines: Record<string, number>;
    hero_stats: Record<string, {
      value: number;
      sample: number;
      count: number;
      confidence: { tier: string; label: string; language: string };
    }>;
    mistakes: Array<{
      hand_id: number;
      hand_number: string;
      scenario: string;
      hero_action: string;
      gto_action: string;
      gto_frequency: number | null;
      ev_loss_bb: number;
      explanation: string;
    }>;
    mistake_count: number;
  };
  exploit_analysis: {
    missed_opportunities: Array<{
      hand_id: number;
      hand_number: string;
      opponent: string;
      opportunity: string;
      opponent_tendency: string;
      hero_action: string;
      confidence: string;
    }>;
  };
  opponents: Array<{
    name: string;
    hands_in_session: number;
    db_total_hands: number;
    stats: Record<string, number | string | null> | null;
    confidence: { tier: string; label: string; language: string };
  }>;
  pregame_strategy: {
    strategy_id: number;
    created_at: string;
    table_classification: string;
    softness_score: number | null;
    general_strategy: {
      overview?: string;
      key_principle?: string;
      opening_adjustments?: string[];
      three_bet_adjustments?: string[];
    };
    strategy_reasoning?: string;  // Plain text AI reasoning for the strategy
    opponent_exploits: Array<{ name: string; exploit: string }>;
    priority_actions: string[];
  } | null;
  leak_progress: Array<{
    scenario_id: string;
    leak_name: string;
    category: string;
    position: string;
    action: string;
    lifetime_value: number;
    session_value: number;
    gto_value: number;
    session_sample: number;
    lifetime_sample: number;
    improved: boolean;
    closer_to_gto: boolean;
    severity: string;
    direction: string;
    priority_score: number;
  }>;
  strategy_goal_progress: Array<{
    leak_id: string;
    description: string;
    session_goal: string;
    baseline_value: number;
    target_value: number;
    gto_value: number;
    actual_value: number | null;
    sample_size: number;
    improved: boolean | null;
    hit_target: boolean | null;
    strategy_id: number;
  }>;
  exploit_execution: Array<{
    target_name: string;
    exploit_text: string;
    exploit_type: string;
    execution_status: 'executed' | 'partially' | 'not_executed' | 'no_opportunity' | 'insufficient_data' | 'inconclusive';
    hands_together: number;
    opportunities: number;
    actions_taken: number;
    hero_frequency: number | null;
    baseline_frequency: number | null;
    confidence: number;
    strategy_id: number;
  }>;
  ai_debrief: {
    executive_summary: string;
    went_well: string[];
    areas_for_improvement: string[];
    opponent_insights: Array<{
      name: string;
      tendency: string;
      recommendation: string;
    }>;
    strategy_execution: string | null;
    strategy_alignment: string | null;  // Assessment of alignment with "Why This Strategy?" reasoning
    strategy_goals_summary: string | null;
    exploit_execution_summary: string | null;
    leak_progress_summary: string | null;
    study_recommendations: string[];
  };
  ai_debug?: {
    prompt: string;
    response: string;
  };
  disclaimers: Record<string, string | null>;
}

// Confidence badge component
const ConfidenceBadge: React.FC<{ confidence: string }> = ({ confidence }) => {
  const colors: Record<string, string> = {
    'High': 'bg-green-100 text-green-700 border-green-200',
    'Good': 'bg-green-100 text-green-700 border-green-200',
    'Moderate': 'bg-yellow-100 text-yellow-700 border-yellow-200',
    'Low': 'bg-orange-100 text-orange-700 border-orange-200',
    'Insufficient': 'bg-gray-100 text-gray-600 border-gray-200'
  };
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${colors[confidence] || colors['Insufficient']}`}>
      {confidence}
    </span>
  );
};

// Collapsible section
const CollapsibleSection: React.FC<{
  title: string;
  icon: React.ReactNode;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  badge?: React.ReactNode;
}> = ({ title, icon, isExpanded, onToggle, children, badge }) => (
  <div className="border border-gray-200 rounded-lg overflow-hidden">
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 transition-colors"
    >
      <div className="flex items-center gap-2">
        {icon}
        <span className="font-medium text-gray-800">{title}</span>
        {badge}
      </div>
      {isExpanded ? (
        <ChevronDown size={18} className="text-gray-500" />
      ) : (
        <ChevronRight size={18} className="text-gray-500" />
      )}
    </button>
    {isExpanded && (
      <div className="p-4 bg-white">
        {children}
      </div>
    )}
  </div>
);

const DebriefModal: React.FC<DebriefModalProps> = ({ isOpen, onClose, sessionId, sessionIds }) => {
  const [debrief, setDebrief] = useState<Debrief | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['summary', 'recommendations'])
  );
  const [replayData, setReplayData] = useState<HandReplayResponse | null>(null);
  const [loadingReplay, setLoadingReplay] = useState(false);
  const [showAiDebug, setShowAiDebug] = useState(false);

  const handleViewHand = async (handId: number) => {
    setLoadingReplay(true);
    try {
      const data = await api.getHandReplay(handId);
      setReplayData(data);
    } catch (err) {
      console.error('Error loading hand replay:', err);
    } finally {
      setLoadingReplay(false);
    }
  };

  useEffect(() => {
    if (isOpen && (sessionId || sessionIds?.length)) {
      fetchDebrief();
    }
  }, [isOpen, sessionId, sessionIds]);

  const fetchDebrief = async () => {
    setLoading(true);
    setError(null);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      let response: Response;

      if (sessionIds && sessionIds.length > 1) {
        // Multi-session debrief
        response = await fetch(`${apiUrl}/api/sessions/debrief`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_ids: sessionIds })
        });
      } else {
        // Single session debrief
        const id = sessionId || sessionIds?.[0];
        response = await fetch(`${apiUrl}/api/sessions/${id}/debrief`);
      }

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const data = await response.json();
      setDebrief(data);
    } catch (err) {
      console.error('Error fetching debrief:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate debrief');
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="fixed inset-0 bg-black/50" onClick={onClose} />

        <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-indigo-600 to-purple-600 text-white">
            <div className="flex items-center gap-3">
              <MessageSquare className="w-6 h-6" />
              <h2 className="text-xl font-bold">Session Debrief</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 hover:bg-white/20 rounded-lg transition-colors"
            >
              <X size={24} />
            </button>
          </div>

          {/* Content */}
          <div className="overflow-y-auto max-h-[calc(90vh-80px)] p-4 space-y-4">
            {loading && (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="w-12 h-12 animate-spin text-indigo-600 mb-4" />
                <p className="text-gray-600">Analyzing your session...</p>
                <p className="text-sm text-gray-400 mt-1">This may take a few seconds</p>
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-red-800">Failed to generate debrief</h4>
                  <p className="text-sm text-red-600 mt-1">{error}</p>
                </div>
              </div>
            )}

            {debrief && !loading && (
              <>
                {/* Session Summary */}
                <div className="bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium text-gray-700">Session Overview</h3>
                      <p className="text-sm text-gray-500">
                        {debrief.session_summary.total_hands} hands | {debrief.session_summary.stake_level}
                      </p>
                    </div>
                    <div className={`text-2xl font-bold ${debrief.session_summary.profit_loss_bb >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      <div className="flex items-center gap-2">
                        {debrief.session_summary.profit_loss_bb >= 0 ? (
                          <TrendingUp className="w-6 h-6" />
                        ) : (
                          <TrendingDown className="w-6 h-6" />
                        )}
                        {debrief.session_summary.profit_loss_bb >= 0 ? '+' : ''}
                        {debrief.session_summary.profit_loss_bb.toFixed(1)} bb
                      </div>
                    </div>
                  </div>
                </div>

                {/* Executive Summary */}
                <CollapsibleSection
                  title="Executive Summary"
                  icon={<Target size={18} className="text-indigo-600" />}
                  isExpanded={expandedSections.has('summary')}
                  onToggle={() => toggleSection('summary')}
                >
                  <p className="text-gray-700 leading-relaxed">
                    {debrief.ai_debrief.executive_summary}
                  </p>
                </CollapsibleSection>

                {/* What Went Well */}
                {debrief.ai_debrief.went_well?.length > 0 && (
                  <CollapsibleSection
                    title="What Went Well"
                    icon={<CheckCircle size={18} className="text-green-600" />}
                    isExpanded={expandedSections.has('well')}
                    onToggle={() => toggleSection('well')}
                    badge={<span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">{debrief.ai_debrief.went_well.length}</span>}
                  >
                    <ul className="space-y-2">
                      {debrief.ai_debrief.went_well.map((item, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <CheckCircle size={16} className="text-green-500 mt-0.5 flex-shrink-0" />
                          <span className="text-gray-700">{item}</span>
                        </li>
                      ))}
                    </ul>
                  </CollapsibleSection>
                )}

                {/* Areas for Improvement */}
                {debrief.ai_debrief.areas_for_improvement?.length > 0 && (
                  <CollapsibleSection
                    title="Areas for Improvement"
                    icon={<AlertTriangle size={18} className="text-amber-600" />}
                    isExpanded={expandedSections.has('improvement')}
                    onToggle={() => toggleSection('improvement')}
                    badge={<span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">{debrief.ai_debrief.areas_for_improvement.length}</span>}
                  >
                    <ul className="space-y-2">
                      {debrief.ai_debrief.areas_for_improvement.map((item, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <AlertTriangle size={16} className="text-amber-500 mt-0.5 flex-shrink-0" />
                          <span className="text-gray-700">{item}</span>
                        </li>
                      ))}
                    </ul>
                  </CollapsibleSection>
                )}

                {/* Strategy Execution */}
                <CollapsibleSection
                  title="Strategy Execution"
                  icon={<ClipboardCheck size={18} className="text-cyan-600" />}
                  isExpanded={expandedSections.has('strategy')}
                  onToggle={() => toggleSection('strategy')}
                >
                  {debrief.pregame_strategy ? (
                    <div className="space-y-3">
                      {/* Strategy Reasoning - Why This Strategy? */}
                      {debrief.pregame_strategy.strategy_reasoning && (
                        <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                          <h4 className="font-medium text-slate-800 mb-2 flex items-center gap-2">
                            <span className="text-slate-500">💡</span>
                            Why This Strategy?
                          </h4>
                          <p className="text-sm text-slate-700 leading-relaxed">
                            {debrief.pregame_strategy.strategy_reasoning}
                          </p>
                        </div>
                      )}

                      {/* Strategy Alignment Assessment - Did player follow the reasoning? */}
                      {debrief.ai_debrief.strategy_alignment && (
                        <div className="bg-indigo-50 rounded-lg p-4 border border-indigo-200">
                          <h4 className="font-medium text-indigo-800 mb-2 flex items-center gap-2">
                            <span className="text-indigo-500">🎯</span>
                            Did You Follow the Plan?
                          </h4>
                          <p className="text-sm text-indigo-700 leading-relaxed">
                            {debrief.ai_debrief.strategy_alignment}
                          </p>
                        </div>
                      )}

                      <div className="bg-cyan-50 rounded-lg p-3 border border-cyan-200">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium text-cyan-800">Pre-Game Strategy</span>
                          <span className="text-xs text-cyan-600">
                            {debrief.pregame_strategy.table_classification} table
                            {debrief.pregame_strategy.softness_score && ` (${debrief.pregame_strategy.softness_score}/10)`}
                          </span>
                        </div>
                        {debrief.pregame_strategy.general_strategy?.key_principle && (
                          <p className="text-sm text-cyan-700 mb-2">
                            <strong>Key Principle:</strong> {debrief.pregame_strategy.general_strategy.key_principle}
                          </p>
                        )}
                        {debrief.pregame_strategy.priority_actions?.length > 0 && (
                          <div className="text-sm text-cyan-700">
                            <strong>Priority Actions:</strong>
                            <ul className="list-disc list-inside mt-1">
                              {debrief.pregame_strategy.priority_actions.slice(0, 3).map((action, i) => (
                                <li key={i}>{action}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                      {debrief.ai_debrief.strategy_execution && (
                        <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                          <span className="font-medium text-gray-700">Execution Assessment:</span>
                          <p className="text-sm text-gray-600 mt-1">{debrief.ai_debrief.strategy_execution}</p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 text-center">
                      <ClipboardCheck size={24} className="mx-auto text-gray-400 mb-2" />
                      <p className="text-sm text-gray-600">
                        No pre-game strategy was generated for this session.
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        To get strategy execution analysis, email a hand history to your import address before starting a session.
                      </p>
                    </div>
                  )}
                </CollapsibleSection>

                {/* Strategy Goal Progress */}
                {debrief.strategy_goal_progress?.length > 0 && (
                  <CollapsibleSection
                    title="Strategy Goals"
                    icon={<Target size={18} className="text-emerald-600" />}
                    isExpanded={expandedSections.has('strategyGoals')}
                    onToggle={() => toggleSection('strategyGoals')}
                    badge={
                      <span className="text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                        {debrief.strategy_goal_progress.filter(g => g.hit_target).length}/{debrief.strategy_goal_progress.filter(g => g.actual_value !== null).length} hit
                      </span>
                    }
                  >
                    <div className="space-y-3">
                      {debrief.ai_debrief.strategy_goals_summary && (
                        <p className="text-sm text-gray-700 mb-3">{debrief.ai_debrief.strategy_goals_summary}</p>
                      )}
                      {debrief.strategy_goal_progress.filter(g => g.actual_value !== null).map((goal, i) => (
                        <div
                          key={i}
                          className={`rounded-lg p-3 border ${
                            goal.hit_target
                              ? 'bg-emerald-50 border-emerald-200'
                              : goal.improved
                              ? 'bg-blue-50 border-blue-200'
                              : 'bg-amber-50 border-amber-200'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <span className={`font-medium ${
                                goal.hit_target ? 'text-emerald-800' : goal.improved ? 'text-blue-800' : 'text-amber-800'
                              }`}>
                                {goal.description}
                              </span>
                            </div>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              goal.hit_target
                                ? 'bg-emerald-200 text-emerald-800'
                                : goal.improved
                                ? 'bg-blue-200 text-blue-800'
                                : 'bg-amber-200 text-amber-800'
                            }`}>
                              {goal.hit_target ? '✓ Hit Target' : goal.improved ? '↗ Improved' : 'Needs Work'}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 mb-2">{goal.session_goal}</p>
                          <div className="flex items-center gap-4 mt-2 text-sm">
                            <div className="text-center">
                              <div className="text-gray-500 text-xs">Baseline</div>
                              <div className="font-medium text-gray-600">{goal.baseline_value.toFixed(1)}%</div>
                            </div>
                            <div className="text-gray-400">→</div>
                            <div className="text-center">
                              <div className={`text-xs ${goal.hit_target ? 'text-emerald-600' : goal.improved ? 'text-blue-600' : 'text-amber-600'}`}>
                                Actual
                              </div>
                              <div className={`font-bold ${goal.hit_target ? 'text-emerald-700' : goal.improved ? 'text-blue-700' : 'text-amber-700'}`}>
                                {goal.actual_value?.toFixed(1)}%
                              </div>
                            </div>
                            <div className="text-gray-400">|</div>
                            <div className="text-center">
                              <div className="text-gray-500 text-xs">Target</div>
                              <div className="font-medium text-gray-600">{goal.target_value.toFixed(1)}%</div>
                            </div>
                            <div className="text-emerald-400">|</div>
                            <div className="text-center">
                              <div className="text-emerald-500 text-xs">GTO</div>
                              <div className="font-medium text-emerald-600">{goal.gto_value.toFixed(1)}%</div>
                            </div>
                          </div>
                          <div className="text-xs text-gray-500 mt-2">
                            {goal.sample_size} opportunities
                          </div>
                        </div>
                      ))}
                    </div>
                  </CollapsibleSection>
                )}

                {/* Exploit Execution */}
                {debrief.exploit_execution?.length > 0 && (
                  <CollapsibleSection
                    title="Exploit Execution"
                    icon={<Zap size={18} className="text-rose-600" />}
                    isExpanded={expandedSections.has('exploitExecution')}
                    onToggle={() => toggleSection('exploitExecution')}
                    badge={
                      <span className="text-xs text-rose-600 bg-rose-50 px-2 py-0.5 rounded-full">
                        {debrief.exploit_execution.filter(e => e.execution_status === 'executed').length}/
                        {debrief.exploit_execution.filter(e => !['no_opportunity', 'insufficient_data'].includes(e.execution_status)).length} executed
                      </span>
                    }
                  >
                    <div className="space-y-3">
                      {debrief.ai_debrief.exploit_execution_summary && (
                        <p className="text-sm text-gray-700 mb-3">{debrief.ai_debrief.exploit_execution_summary}</p>
                      )}
                      {debrief.exploit_execution.map((exploit, i) => {
                        const statusColors = {
                          executed: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-800', badge: 'bg-green-200 text-green-800' },
                          partially: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-800', badge: 'bg-blue-200 text-blue-800' },
                          not_executed: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-800', badge: 'bg-amber-200 text-amber-800' },
                          no_opportunity: { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-600', badge: 'bg-gray-200 text-gray-600' },
                          insufficient_data: { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-600', badge: 'bg-gray-200 text-gray-600' },
                          inconclusive: { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-600', badge: 'bg-gray-200 text-gray-600' }
                        };
                        const statusLabels = {
                          executed: '✓ Executed',
                          partially: '↗ Partial',
                          not_executed: 'Not Executed',
                          no_opportunity: 'No Opportunity',
                          insufficient_data: 'Insufficient Data',
                          inconclusive: 'Inconclusive'
                        };
                        const colors = statusColors[exploit.execution_status] || statusColors.inconclusive;

                        return (
                          <div
                            key={i}
                            className={`rounded-lg p-3 border ${colors.bg} ${colors.border}`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center gap-2">
                                <span className={`font-medium ${colors.text}`}>
                                  vs {exploit.target_name}
                                </span>
                              </div>
                              <span className={`text-xs px-2 py-0.5 rounded-full ${colors.badge}`}>
                                {statusLabels[exploit.execution_status]}
                              </span>
                            </div>
                            <p className="text-sm text-gray-600 mb-2">{exploit.exploit_text}</p>
                            {exploit.hero_frequency !== null && exploit.baseline_frequency !== null && (
                              <div className="flex items-center gap-4 mt-2 text-sm">
                                <div className="text-center">
                                  <div className="text-gray-500 text-xs">Baseline</div>
                                  <div className="font-medium text-gray-600">{exploit.baseline_frequency.toFixed(1)}%</div>
                                </div>
                                <div className="text-gray-400">→</div>
                                <div className="text-center">
                                  <div className={`text-xs ${
                                    exploit.execution_status === 'executed' ? 'text-green-600' :
                                    exploit.execution_status === 'partially' ? 'text-blue-600' :
                                    'text-amber-600'
                                  }`}>
                                    vs Target
                                  </div>
                                  <div className={`font-bold ${
                                    exploit.execution_status === 'executed' ? 'text-green-700' :
                                    exploit.execution_status === 'partially' ? 'text-blue-700' :
                                    'text-amber-700'
                                  }`}>
                                    {exploit.hero_frequency.toFixed(1)}%
                                  </div>
                                </div>
                                <div className="text-gray-400">|</div>
                                <div className="text-center">
                                  <div className="text-gray-500 text-xs">Diff</div>
                                  <div className={`font-medium ${
                                    exploit.hero_frequency > exploit.baseline_frequency ? 'text-green-600' : 'text-amber-600'
                                  }`}>
                                    {(exploit.hero_frequency - exploit.baseline_frequency) >= 0 ? '+' : ''}
                                    {(exploit.hero_frequency - exploit.baseline_frequency).toFixed(1)}%
                                  </div>
                                </div>
                              </div>
                            )}
                            <div className="text-xs text-gray-500 mt-2">
                              {exploit.hands_together} hands together, {exploit.opportunities} opportunities
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </CollapsibleSection>
                )}

                {/* Leak Progress */}
                {debrief.leak_progress?.length > 0 && (
                  <CollapsibleSection
                    title="Leak Progress"
                    icon={<Activity size={18} className="text-violet-600" />}
                    isExpanded={expandedSections.has('leakProgress')}
                    onToggle={() => toggleSection('leakProgress')}
                    badge={
                      <span className="text-xs text-violet-600 bg-violet-50 px-2 py-0.5 rounded-full">
                        {debrief.leak_progress.filter(l => l.improved).length}/{debrief.leak_progress.length} improved
                      </span>
                    }
                  >
                    <div className="space-y-3">
                      {debrief.ai_debrief.leak_progress_summary && (
                        <p className="text-sm text-gray-700 mb-3">{debrief.ai_debrief.leak_progress_summary}</p>
                      )}
                      {debrief.leak_progress.map((leak, i) => (
                        <div
                          key={i}
                          className={`rounded-lg p-3 border ${
                            leak.improved
                              ? 'bg-green-50 border-green-200'
                              : 'bg-amber-50 border-amber-200'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <span className={`font-medium ${leak.improved ? 'text-green-800' : 'text-amber-800'}`}>
                                {leak.leak_name}
                              </span>
                              <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">
                                {leak.category === 'opening' ? 'Opening' :
                                 leak.category === 'defense' ? 'Defense' :
                                 leak.category === 'facing_3bet' ? 'vs 3-Bet' :
                                 leak.category === 'facing_4bet' ? 'vs 4-Bet' : leak.category}
                              </span>
                            </div>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              leak.improved
                                ? 'bg-green-200 text-green-800'
                                : 'bg-amber-200 text-amber-800'
                            }`}>
                              {leak.improved ? '✓ Improved' : 'Needs Work'}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 mt-2 text-sm">
                            <div className="flex-1">
                              <div className="flex items-center justify-between text-gray-600 mb-1">
                                <span>Session</span>
                                <span className={`font-semibold ${leak.improved ? 'text-green-700' : 'text-amber-700'}`}>
                                  {leak.session_value.toFixed(1)}%
                                </span>
                              </div>
                              <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${leak.improved ? 'bg-green-500' : 'bg-amber-500'}`}
                                  style={{ width: `${Math.min(leak.session_value, 100)}%` }}
                                />
                              </div>
                            </div>
                            <div className="text-center text-gray-400">→</div>
                            <div className="flex-1">
                              <div className="flex items-center justify-between text-gray-600 mb-1">
                                <span>Lifetime</span>
                                <span className="font-medium">{leak.lifetime_value.toFixed(1)}%</span>
                              </div>
                              <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                <div className="h-full bg-gray-400 rounded-full" style={{ width: `${Math.min(leak.lifetime_value, 100)}%` }} />
                              </div>
                            </div>
                            <div className="text-center text-blue-400">|</div>
                            <div className="text-center">
                              <div className="text-gray-500 text-xs">GTO</div>
                              <div className="font-medium text-blue-600">{leak.gto_value.toFixed(1)}%</div>
                            </div>
                          </div>
                          <div className="text-xs text-gray-500 mt-2 flex justify-between">
                            <span>{leak.session_sample} session opportunities</span>
                            <span className={`${leak.severity === 'major' ? 'text-red-600' : 'text-amber-600'}`}>
                              {leak.severity === 'major' ? '🔴 Major' : '🟡 Moderate'} leak
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CollapsibleSection>
                )}

                {/* GTO Mistakes */}
                {debrief.gto_analysis.mistakes?.length > 0 && (
                  <CollapsibleSection
                    title="GTO Mistakes"
                    icon={<Target size={18} className="text-red-600" />}
                    isExpanded={expandedSections.has('mistakes')}
                    onToggle={() => toggleSection('mistakes')}
                    badge={<span className="text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full">{debrief.gto_analysis.mistake_count}</span>}
                  >
                    <div className="space-y-3">
                      {debrief.gto_analysis.mistakes.slice(0, 5).map((mistake, i) => (
                        <div key={i} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleViewHand(mistake.hand_id)}
                                className="text-sm font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1"
                                disabled={loadingReplay}
                              >
                                <ExternalLink size={12} />
                                Hand #{mistake.hand_number.slice(-8)}
                              </button>
                              <span className="text-sm text-gray-500">
                                {mistake.scenario}
                              </span>
                            </div>
                            <span className="text-sm font-medium text-red-600">
                              -{mistake.ev_loss_bb.toFixed(2)} bb
                            </span>
                          </div>
                          <div className="mt-1 text-sm text-gray-600">
                            Hero: <span className="font-medium">{mistake.hero_action}</span>
                            {' | '}
                            GTO: <span className="font-medium">{mistake.gto_action}</span>
                            {mistake.gto_frequency && (
                              <span className="text-gray-400"> ({(mistake.gto_frequency * 100).toFixed(0)}%)</span>
                            )}
                          </div>
                          {mistake.explanation && (
                            <p className="mt-1 text-sm text-gray-500">{mistake.explanation}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </CollapsibleSection>
                )}

                {/* Exploit Opportunities */}
                {debrief.exploit_analysis?.missed_opportunities?.length > 0 && (
                  <CollapsibleSection
                    title="Exploit Opportunities"
                    icon={<Zap size={18} className="text-orange-600" />}
                    isExpanded={expandedSections.has('exploits')}
                    onToggle={() => toggleSection('exploits')}
                    badge={<span className="text-xs text-orange-600 bg-orange-50 px-2 py-0.5 rounded-full">{debrief.exploit_analysis.missed_opportunities.length}</span>}
                  >
                    <div className="space-y-3">
                      {debrief.exploit_analysis.missed_opportunities.map((opp, i) => (
                        <div key={i} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-gray-900">{opp.opportunity}</span>
                              <span className="text-sm text-gray-500">vs {opp.opponent}</span>
                              <ConfidenceBadge confidence={opp.confidence} />
                            </div>
                            {opp.hand_id && (
                              <button
                                onClick={() => handleViewHand(opp.hand_id)}
                                className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                                disabled={loadingReplay}
                              >
                                <ExternalLink size={10} />
                                View hand
                              </button>
                            )}
                          </div>
                          <p className="text-sm text-gray-600">{opp.opponent_tendency}</p>
                          <p className="text-sm text-orange-600 mt-1 font-medium">{opp.hero_action}</p>
                        </div>
                      ))}
                    </div>
                  </CollapsibleSection>
                )}

                {/* Opponent Insights */}
                {debrief.ai_debrief.opponent_insights?.length > 0 && (
                  <CollapsibleSection
                    title="Opponent Insights"
                    icon={<Users size={18} className="text-purple-600" />}
                    isExpanded={expandedSections.has('opponents')}
                    onToggle={() => toggleSection('opponents')}
                    badge={<span className="text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full">{debrief.ai_debrief.opponent_insights.length}</span>}
                  >
                    <div className="space-y-3">
                      {debrief.ai_debrief.opponent_insights.map((opp, i) => (
                        <div key={i} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-gray-900">{opp.name}</span>
                            {debrief.opponents.find(o => o.name === opp.name)?.confidence && (
                              <ConfidenceBadge
                                confidence={debrief.opponents.find(o => o.name === opp.name)?.confidence.label || 'Insufficient'}
                              />
                            )}
                          </div>
                          <p className="text-sm text-gray-600">{opp.tendency}</p>
                          <p className="text-sm text-indigo-600 mt-1 font-medium">{opp.recommendation}</p>
                        </div>
                      ))}
                    </div>
                  </CollapsibleSection>
                )}

                {/* Study Recommendations */}
                {debrief.ai_debrief.study_recommendations?.length > 0 && (
                  <CollapsibleSection
                    title="Study Recommendations"
                    icon={<BookOpen size={18} className="text-blue-600" />}
                    isExpanded={expandedSections.has('recommendations')}
                    onToggle={() => toggleSection('recommendations')}
                  >
                    <ol className="space-y-2 list-decimal list-inside">
                      {debrief.ai_debrief.study_recommendations.map((rec, i) => (
                        <li key={i} className="text-gray-700">{rec}</li>
                      ))}
                    </ol>
                  </CollapsibleSection>
                )}

                {/* Disclaimers */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
                  <div className="flex items-start gap-2">
                    <Info size={18} className="text-blue-500 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-blue-700">
                      <p className="font-medium mb-1">Analysis Limitations</p>
                      <ul className="space-y-1 text-blue-600">
                        {Object.values(debrief.disclaimers).map((disclaimer, i) => (
                          <li key={i}>{disclaimer}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>

                {/* View AI Prompt button */}
                <div className="flex justify-center pt-2">
                  <button
                    onClick={() => setShowAiDebug(true)}
                    className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors text-sm"
                  >
                    <Code size={16} />
                    <span>View AI Prompt</span>
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Hand Replay Modal */}
      {replayData && (
        <HandReplayModal
          data={replayData}
          onClose={() => setReplayData(null)}
        />
      )}

      {/* AI Debug Modal */}
      {showAiDebug && debrief && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
          <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <Code className="w-5 h-5 text-purple-500" />
                <span>AI Prompt & Response</span>
              </h2>
              <button
                onClick={() => setShowAiDebug(false)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X size={20} className="text-gray-500" />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-6 space-y-6">
              {/* Prompt */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-2">Prompt Sent to Claude</h3>
                <pre className="bg-gray-900 text-gray-100 p-4 rounded-xl text-sm overflow-x-auto whitespace-pre-wrap font-mono">
                  {debrief.ai_debug?.prompt || 'No prompt data available'}
                </pre>
              </div>
              {/* Response */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-2">Claude's Response</h3>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-xl text-sm overflow-x-auto whitespace-pre-wrap font-mono">
                  {debrief.ai_debug?.response || 'No response data available'}
                </pre>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
              <button
                onClick={() => setShowAiDebug(false)}
                className="w-full py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DebriefModal;
