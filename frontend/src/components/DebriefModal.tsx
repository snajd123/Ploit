import React, { useState, useEffect } from 'react';
import {
  X, Loader2, MessageSquare, TrendingUp, TrendingDown, Target,
  AlertTriangle, CheckCircle, Users, BookOpen, ChevronDown, ChevronRight,
  AlertCircle, Info, ExternalLink, Zap
} from 'lucide-react';
import HandReplayModal from './HandReplayModal';
import api from '../services/api';
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
  ai_debrief: {
    executive_summary: string;
    went_well: string[];
    areas_for_improvement: string[];
    opponent_insights: Array<{
      name: string;
      tendency: string;
      recommendation: string;
    }>;
    study_recommendations: string[];
  };
  disclaimers: Record<string, string>;
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
    </div>
  );
};

export default DebriefModal;
