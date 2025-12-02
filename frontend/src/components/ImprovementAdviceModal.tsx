import React, { useState, useEffect } from 'react';
import {
  X, ChevronDown, ChevronRight, Lightbulb, BookOpen, Target,
  AlertTriangle, CheckCircle, Sparkles, Loader2, TrendingUp, TrendingDown,
  Code, Eye, EyeOff
} from 'lucide-react';

// Types
interface HandCategory {
  name: string;
  description: string;
  hands: string[];
  priority: number;
}

interface QuickFix {
  heuristic: string;
  hands_to_add: string[];
  hands_to_remove: string[];
  adjustment: string;
}

interface DetailedExplanation {
  principle: string;
  hand_categories: HandCategory[];
  ev_implication: string;
  common_mistakes: string[];
  position_notes: string | null;
}

interface StudyResources {
  concepts: string[];
  solver_scenarios: string[];
  exercises: string[];
}

interface AIEnhanced {
  hand_recommendations: Array<{ hand: string; action: string; reason: string }> | string[];
  pattern_analysis: string;
  study_plan: string[];
  quick_adjustment: string;
  raw_response?: string | null;
}

interface RealDeviation {
  hand: string;
  player_freq: number;
  gto_freq: number;
  deviation: number;
  sample: number;
  recommendation: string;
}

interface MissingHand {
  hand: string;
  gto_freq: number;
}

interface RealData {
  deviations: RealDeviation[];
  missing_hands: MissingHand[];
  data_available: boolean;
}

interface DebugInfo {
  prompt: string;
  raw_response: string;
}

interface ImprovementAdviceData {
  leak_type: string;
  leak_category: string;
  position: string;
  vs_position: string | null;
  player_value: number;
  gto_value: number;
  deviation: number;
  sample_size_warning: string | null;
  tier1_quick_fix: QuickFix;
  tier2_detailed: DetailedExplanation;
  tier3_study: StudyResources;
  caveats: string[];
  ai_enhanced?: AIEnhanced;
  real_data?: RealData;
  debug?: DebugInfo;
}

interface ImprovementAdviceModalProps {
  isOpen: boolean;
  onClose: () => void;
  leakCategory: string;
  leakDirection: string;
  position: string;
  vsPosition?: string | null;
  playerValue: number;
  gtoValue: number;
  sampleSize: number;
  playerName?: string;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const ImprovementAdviceModal: React.FC<ImprovementAdviceModalProps> = ({
  isOpen,
  onClose,
  leakCategory,
  leakDirection,
  position,
  vsPosition,
  playerValue,
  gtoValue,
  sampleSize,
  playerName
}) => {
  const [advice, setAdvice] = useState<ImprovementAdviceData | null>(null);
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedTier, setExpandedTier] = useState<number>(1);
  const [showAiAdvice, setShowAiAdvice] = useState(false);
  const [showDebug, setShowDebug] = useState(false);

  // Fetch advice when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchAdvice();
    }
  }, [isOpen, leakCategory, leakDirection, position, vsPosition, playerValue, gtoValue, sampleSize]);

  const fetchAdvice = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        leak_category: leakCategory,
        leak_direction: leakDirection,
        position: position,
        player_value: playerValue.toString(),
        gto_value: gtoValue.toString(),
        sample_size: sampleSize.toString()
      });

      if (vsPosition) {
        params.append('vs_position', vsPosition);
      }

      const response = await fetch(`${API_BASE}/api/improvement-advice?${params}`);

      if (!response.ok) {
        throw new Error('Failed to fetch advice');
      }

      const data = await response.json();
      setAdvice(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load advice');
    } finally {
      setLoading(false);
    }
  };

  const fetchAiAdvice = async () => {
    if (!advice) return;

    setAiLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/improvement-advice/ai`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          leak_category: leakCategory,
          leak_direction: leakDirection,
          position: position,
          vs_position: vsPosition,
          player_value: playerValue,
          gto_value: gtoValue,
          sample_size: sampleSize,
          player_name: playerName
        })
      });

      if (!response.ok) {
        throw new Error('Failed to fetch AI advice');
      }

      const data = await response.json();
      setAdvice(prev => prev ? {
        ...prev,
        ai_enhanced: data.ai_enhanced,
        real_data: data.real_data,
        debug: data.debug
      } : null);
      setShowAiAdvice(true);
      setExpandedTier(4); // Auto-expand AI section
    } catch (err) {
      console.error('AI advice error:', err);
    } finally {
      setAiLoading(false);
    }
  };

  if (!isOpen) return null;

  const deviation = playerValue - gtoValue;
  const isOverDoing = deviation > 0;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isOverDoing ? 'bg-red-100' : 'bg-blue-100'}`}>
              {isOverDoing ? (
                <TrendingUp className="text-red-600" size={20} />
              ) : (
                <TrendingDown className="text-blue-600" size={20} />
              )}
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">
                Improvement Plan: {leakCategory.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </h2>
              <p className="text-sm text-gray-500">
                {position}{vsPosition ? ` vs ${vsPosition}` : ''} • {playerValue.toFixed(0)}% vs {gtoValue.toFixed(0)}% GTO
                <span className={`ml-2 font-medium ${deviation > 0 ? 'text-red-600' : 'text-blue-600'}`}>
                  ({deviation > 0 ? '+' : ''}{deviation.toFixed(0)}%)
                </span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={20} className="text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="animate-spin text-purple-600" size={32} />
              <span className="ml-3 text-gray-600">Loading improvement advice...</span>
            </div>
          ) : error ? (
            <div className="text-center py-12 text-red-600">
              <AlertTriangle className="mx-auto mb-2" size={32} />
              <p>{error}</p>
            </div>
          ) : advice ? (
            <div className="space-y-4">
              {/* Sample Size Warning */}
              {advice.sample_size_warning && (
                <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <AlertTriangle className="text-yellow-600 flex-shrink-0 mt-0.5" size={16} />
                  <p className="text-sm text-yellow-800">{advice.sample_size_warning}</p>
                </div>
              )}

              {/* Tier 1: Quick Fix */}
              <TierSection
                tier={1}
                title="Quick Fix"
                subtitle="Apply immediately"
                icon={<Lightbulb className="text-yellow-600" size={18} />}
                bgColor="bg-yellow-50"
                borderColor="border-yellow-200"
                isExpanded={expandedTier === 1}
                onToggle={() => setExpandedTier(expandedTier === 1 ? 0 : 1)}
              >
                <div className="space-y-4">
                  {/* Heuristic */}
                  <div className="p-3 bg-white rounded-lg border border-yellow-100">
                    <p className="text-gray-800 font-medium">{advice.tier1_quick_fix.heuristic}</p>
                  </div>

                  {/* Adjustment */}
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-yellow-100 rounded-full">
                    <Target size={14} className="text-yellow-700" />
                    <span className="text-sm font-medium text-yellow-800">{advice.tier1_quick_fix.adjustment}</span>
                  </div>

                  {/* Hands to Add/Remove */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {advice.tier1_quick_fix.hands_to_add.length > 0 && (
                      <div className="p-3 bg-green-50 rounded-lg border border-green-200">
                        <div className="flex items-center gap-2 mb-2">
                          <CheckCircle size={14} className="text-green-600" />
                          <span className="text-sm font-semibold text-green-800">Add These Hands</span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {advice.tier1_quick_fix.hands_to_add.map((hand, idx) => (
                            <span key={idx} className="px-2 py-0.5 bg-green-100 text-green-800 text-xs font-mono rounded">
                              {hand}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {advice.tier1_quick_fix.hands_to_remove.length > 0 && (
                      <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                        <div className="flex items-center gap-2 mb-2">
                          <X size={14} className="text-red-600" />
                          <span className="text-sm font-semibold text-red-800">Remove These Hands</span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {advice.tier1_quick_fix.hands_to_remove.map((hand, idx) => (
                            <span key={idx} className="px-2 py-0.5 bg-red-100 text-red-800 text-xs font-mono rounded">
                              {hand}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </TierSection>

              {/* Tier 2: Detailed Explanation */}
              <TierSection
                tier={2}
                title="Detailed Explanation"
                subtitle="Understand the theory"
                icon={<BookOpen className="text-blue-600" size={18} />}
                bgColor="bg-blue-50"
                borderColor="border-blue-200"
                isExpanded={expandedTier === 2}
                onToggle={() => setExpandedTier(expandedTier === 2 ? 0 : 2)}
              >
                <div className="space-y-4">
                  {/* Principle */}
                  <div className="p-3 bg-white rounded-lg border border-blue-100">
                    <h4 className="text-sm font-semibold text-blue-800 mb-1">Core Principle</h4>
                    <p className="text-gray-700">{advice.tier2_detailed.principle}</p>
                  </div>

                  {/* Hand Categories */}
                  {advice.tier2_detailed.hand_categories.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-2">Hand Categories (by priority)</h4>
                      <div className="space-y-2">
                        {advice.tier2_detailed.hand_categories
                          .sort((a, b) => a.priority - b.priority)
                          .map((cat, idx) => (
                            <div key={idx} className="p-3 bg-white rounded-lg border border-gray-200">
                              <div className="flex items-start justify-between mb-2">
                                <div>
                                  <span className="font-medium text-gray-900">{cat.name}</span>
                                  <p className="text-xs text-gray-500">{cat.description}</p>
                                </div>
                                <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">
                                  Priority {cat.priority}
                                </span>
                              </div>
                              <div className="flex flex-wrap gap-1.5">
                                {cat.hands.map((hand, hidx) => (
                                  <span key={hidx} className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs font-mono rounded">
                                    {hand}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}

                  {/* EV Implication */}
                  <div className="p-3 bg-purple-50 rounded-lg border border-purple-200">
                    <h4 className="text-sm font-semibold text-purple-800 mb-1">EV Impact</h4>
                    <p className="text-gray-700">{advice.tier2_detailed.ev_implication}</p>
                  </div>

                  {/* Common Mistakes */}
                  {advice.tier2_detailed.common_mistakes.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-2">Common Mistakes to Avoid</h4>
                      <ul className="space-y-1">
                        {advice.tier2_detailed.common_mistakes.map((mistake, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                            <AlertTriangle size={14} className="text-orange-500 flex-shrink-0 mt-0.5" />
                            {mistake}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Position Notes */}
                  {advice.tier2_detailed.position_notes && (
                    <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <h4 className="text-sm font-semibold text-gray-700 mb-1">Position-Specific Note</h4>
                      <p className="text-sm text-gray-600">{advice.tier2_detailed.position_notes}</p>
                    </div>
                  )}
                </div>
              </TierSection>

              {/* Tier 3: Study Resources */}
              <TierSection
                tier={3}
                title="Study Resources"
                subtitle="Deep dive into theory"
                icon={<Target className="text-green-600" size={18} />}
                bgColor="bg-green-50"
                borderColor="border-green-200"
                isExpanded={expandedTier === 3}
                onToggle={() => setExpandedTier(expandedTier === 3 ? 0 : 3)}
              >
                <div className="space-y-4">
                  {/* Concepts */}
                  {advice.tier3_study.concepts.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-2">Concepts to Learn</h4>
                      <div className="flex flex-wrap gap-2">
                        {advice.tier3_study.concepts.map((concept, idx) => (
                          <span key={idx} className="px-3 py-1 bg-green-100 text-green-800 text-sm rounded-full">
                            {concept}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Solver Scenarios */}
                  {advice.tier3_study.solver_scenarios.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-2">Solver Scenarios to Run</h4>
                      <ul className="space-y-1">
                        {advice.tier3_study.solver_scenarios.map((scenario, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                            <span className="text-green-600">•</span>
                            {scenario}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Practice Exercises */}
                  {advice.tier3_study.exercises.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-2">Practice Exercises</h4>
                      <ul className="space-y-1">
                        {advice.tier3_study.exercises.map((exercise, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                            <CheckCircle size={14} className="text-green-600 flex-shrink-0 mt-0.5" />
                            {exercise}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </TierSection>

              {/* AI Enhanced Section */}
              <div className="mt-6 pt-4 border-t border-gray-200">
                {!advice.ai_enhanced && !showAiAdvice ? (
                  <button
                    onClick={fetchAiAdvice}
                    disabled={aiLoading}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-500 to-indigo-500 text-white rounded-lg hover:from-purple-600 hover:to-indigo-600 transition-all disabled:opacity-50"
                  >
                    {aiLoading ? (
                      <>
                        <Loader2 className="animate-spin" size={18} />
                        Generating AI Analysis...
                      </>
                    ) : (
                      <>
                        <Sparkles size={18} />
                        Get AI-Powered Personalized Advice
                      </>
                    )}
                  </button>
                ) : advice.ai_enhanced && (
                  <TierSection
                    tier={4}
                    title="AI-Powered Analysis"
                    subtitle="Based on YOUR actual hands"
                    icon={<Sparkles className="text-purple-600" size={18} />}
                    bgColor="bg-purple-50"
                    borderColor="border-purple-200"
                    isExpanded={expandedTier === 4}
                    onToggle={() => setExpandedTier(expandedTier === 4 ? 0 : 4)}
                  >
                    <div className="space-y-4">
                      {/* REAL DATA: Your Actual Hand Deviations */}
                      {advice.real_data?.data_available && (
                        <div className="p-3 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200">
                          <h4 className="text-sm font-bold text-blue-800 mb-3 flex items-center gap-2">
                            <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                            Your Actual Hand Deviations (from database)
                          </h4>

                          {/* Deviations list */}
                          {advice.real_data.deviations && advice.real_data.deviations.length > 0 && (
                            <div className="space-y-2 mb-3">
                              {advice.real_data.deviations.map((dev, idx) => (
                                <div key={idx} className="flex items-center justify-between p-2 bg-white rounded border border-gray-200">
                                  <div className="flex items-center gap-2">
                                    <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${
                                      dev.deviation > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                                    }`}>
                                      {dev.deviation > 0 ? 'OVER' : 'UNDER'}
                                    </span>
                                    <span className="font-mono font-bold text-gray-900">{dev.hand}</span>
                                  </div>
                                  <div className="flex items-center gap-3 text-xs">
                                    <span className="text-gray-500">
                                      You: <span className="font-medium text-gray-700">{dev.player_freq}%</span>
                                    </span>
                                    <span className="text-gray-500">
                                      GTO: <span className="font-medium text-blue-600">{dev.gto_freq}%</span>
                                    </span>
                                    <span className={`font-bold ${dev.deviation > 0 ? 'text-red-600' : 'text-green-600'}`}>
                                      {dev.deviation > 0 ? '+' : ''}{dev.deviation}%
                                    </span>
                                    <span className="text-gray-400">({dev.sample})</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Missing hands */}
                          {advice.real_data.missing_hands && advice.real_data.missing_hands.length > 0 && (
                            <div>
                              <h5 className="text-xs font-semibold text-orange-700 mb-2">Hands GTO plays that you never played:</h5>
                              <div className="flex flex-wrap gap-2">
                                {advice.real_data.missing_hands.map((m, idx) => (
                                  <span key={idx} className="px-2 py-1 bg-orange-100 text-orange-800 text-xs font-mono rounded">
                                    {m.hand} ({m.gto_freq}%)
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Quick Adjustment */}
                      {advice.ai_enhanced.quick_adjustment && (
                        <div className="p-3 bg-white rounded-lg border border-purple-200">
                          <h4 className="text-sm font-semibold text-purple-800 mb-1">AI Quick Adjustment</h4>
                          <p className="text-gray-700">{advice.ai_enhanced.quick_adjustment}</p>
                        </div>
                      )}

                      {/* Hand Recommendations */}
                      {advice.ai_enhanced.hand_recommendations && advice.ai_enhanced.hand_recommendations.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-700 mb-2">AI Hand Recommendations</h4>
                          <div className="space-y-2">
                            {Array.isArray(advice.ai_enhanced.hand_recommendations) &&
                              advice.ai_enhanced.hand_recommendations.map((rec, idx) => (
                                <div key={idx} className="flex items-start gap-2 p-2 bg-white rounded border border-gray-200 text-sm">
                                  {typeof rec === 'string' ? (
                                    <span className="text-gray-700">{rec}</span>
                                  ) : (
                                    <>
                                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                                        rec.action === 'add' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                      }`}>
                                        {rec.action === 'add' ? '+' : '-'}
                                      </span>
                                      <span className="font-mono font-medium text-purple-700">{rec.hand}</span>
                                      <span className="text-gray-600 flex-1">{rec.reason}</span>
                                    </>
                                  )}
                                </div>
                              ))}
                          </div>
                        </div>
                      )}

                      {/* Pattern Analysis */}
                      {advice.ai_enhanced.pattern_analysis && (
                        <div className="p-3 bg-white rounded-lg border border-gray-200">
                          <h4 className="text-sm font-semibold text-gray-700 mb-1">Pattern Analysis</h4>
                          <p className="text-sm text-gray-600">{advice.ai_enhanced.pattern_analysis}</p>
                        </div>
                      )}

                      {/* Study Plan */}
                      {advice.ai_enhanced.study_plan && advice.ai_enhanced.study_plan.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-700 mb-2">Personalized Study Plan</h4>
                          <ul className="space-y-1">
                            {advice.ai_enhanced.study_plan.map((item, idx) => (
                              <li key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                                <span className="w-5 h-5 flex items-center justify-center bg-purple-100 text-purple-700 rounded-full text-xs font-medium flex-shrink-0">
                                  {idx + 1}
                                </span>
                                {item}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Raw Response (if structured parsing failed) */}
                      {advice.ai_enhanced.raw_response && (
                        <div className="p-3 bg-gray-50 rounded-lg">
                          <h4 className="text-sm font-semibold text-gray-700 mb-2">AI Analysis</h4>
                          <div className="text-sm text-gray-600 whitespace-pre-wrap">
                            {advice.ai_enhanced.raw_response}
                          </div>
                        </div>
                      )}

                      {/* Debug Toggle - Show Prompt & Response */}
                      {advice.debug && (
                        <div className="mt-4 pt-4 border-t border-gray-200">
                          <button
                            onClick={() => setShowDebug(!showDebug)}
                            className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-700 transition-colors"
                          >
                            <Code size={14} />
                            {showDebug ? <EyeOff size={14} /> : <Eye size={14} />}
                            {showDebug ? 'Hide' : 'Show'} AI Prompt & Response
                          </button>

                          {showDebug && (
                            <div className="mt-3 space-y-3">
                              {/* Prompt */}
                              <div>
                                <h5 className="text-xs font-semibold text-gray-600 mb-1 flex items-center gap-1">
                                  <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                                  Prompt sent to AI
                                </h5>
                                <pre className="p-3 bg-gray-900 text-green-400 text-xs font-mono rounded-lg overflow-auto max-h-64 whitespace-pre-wrap">
                                  {advice.debug.prompt}
                                </pre>
                              </div>

                              {/* Response */}
                              <div>
                                <h5 className="text-xs font-semibold text-gray-600 mb-1 flex items-center gap-1">
                                  <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                                  Raw AI Response
                                </h5>
                                <pre className="p-3 bg-gray-900 text-purple-400 text-xs font-mono rounded-lg overflow-auto max-h-64 whitespace-pre-wrap">
                                  {advice.debug.raw_response}
                                </pre>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </TierSection>
                )}
              </div>

              {/* Caveats */}
              {advice.caveats.length > 0 && (
                <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Important Caveats</h4>
                  <ul className="space-y-1">
                    {advice.caveats.map((caveat, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-gray-500">
                        <span className="text-gray-400">•</span>
                        {caveat}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50 rounded-b-xl">
          <p className="text-xs text-gray-500 text-center">
            Advice based on GTO theory. Adjust for specific opponent tendencies and game conditions.
          </p>
        </div>
      </div>
    </div>
  );
};

// Tier Section Component
interface TierSectionProps {
  tier: number;
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  bgColor: string;
  borderColor: string;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

const TierSection: React.FC<TierSectionProps> = ({
  tier,
  title,
  subtitle,
  icon,
  bgColor,
  borderColor,
  isExpanded,
  onToggle,
  children
}) => {
  return (
    <div className={`rounded-lg border ${borderColor} overflow-hidden`}>
      <button
        onClick={onToggle}
        className={`w-full flex items-center justify-between p-3 ${bgColor} hover:opacity-90 transition-opacity`}
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 bg-white rounded-full shadow-sm">
            {icon}
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-500">Tier {tier}</span>
              <span className="font-semibold text-gray-900">{title}</span>
            </div>
            <p className="text-xs text-gray-500">{subtitle}</p>
          </div>
        </div>
        {isExpanded ? (
          <ChevronDown size={20} className="text-gray-500" />
        ) : (
          <ChevronRight size={20} className="text-gray-500" />
        )}
      </button>
      {isExpanded && (
        <div className="p-4 bg-white border-t border-gray-100">
          {children}
        </div>
      )}
    </div>
  );
};

export default ImprovementAdviceModal;
