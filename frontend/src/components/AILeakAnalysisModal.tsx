import React, { useState, useEffect } from 'react';
import {
  X, Loader2, AlertTriangle, User, Target, Lightbulb, TrendingUp,
  AlertCircle, CheckCircle, ChevronDown, ChevronRight
} from 'lucide-react';
import type { AILeakAnalysisResponse, AIRootCause, AIPriorityImprovement } from '../types';
import { api } from '../services/api';

interface AILeakAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  playerName: string;
}

// Severity badge component
const SeverityBadge: React.FC<{ severity: 'critical' | 'major' | 'minor' }> = ({ severity }) => {
  const colors = {
    critical: 'bg-red-100 text-red-700 border-red-200',
    major: 'bg-orange-100 text-orange-700 border-orange-200',
    minor: 'bg-yellow-100 text-yellow-700 border-yellow-200'
  };
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${colors[severity]}`}>
      {severity.toUpperCase()}
    </span>
  );
};

// Player type badge component
const PlayerTypeBadge: React.FC<{ type: string }> = ({ type }) => {
  const getColors = (playerType: string) => {
    const t = playerType.toLowerCase();
    if (t.includes('nit')) return 'bg-blue-100 text-blue-700 border-blue-300';
    if (t.includes('tag')) return 'bg-green-100 text-green-700 border-green-300';
    if (t.includes('lag')) return 'bg-purple-100 text-purple-700 border-purple-300';
    if (t.includes('fish') || t.includes('passive')) return 'bg-orange-100 text-orange-700 border-orange-300';
    if (t.includes('station')) return 'bg-red-100 text-red-700 border-red-300';
    if (t.includes('maniac')) return 'bg-pink-100 text-pink-700 border-pink-300';
    return 'bg-gray-100 text-gray-700 border-gray-300';
  };

  return (
    <span className={`px-3 py-1 text-sm font-semibold rounded-lg border ${getColors(type)}`}>
      {type}
    </span>
  );
};

// Collapsible section component
const CollapsibleSection: React.FC<{
  title: string;
  icon: React.ReactNode;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  headerContent?: React.ReactNode;
}> = ({ title, icon, isExpanded, onToggle, children, headerContent }) => (
  <div className="border border-gray-200 rounded-lg overflow-hidden">
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 transition-colors"
    >
      <div className="flex items-center gap-2">
        {icon}
        <span className="font-medium text-gray-800">{title}</span>
        {headerContent}
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

// Root cause card component
const RootCauseCard: React.FC<{ cause: AIRootCause; index: number }> = ({ cause, index }) => (
  <div className="p-4 bg-white rounded-lg border border-gray-200 space-y-2">
    <div className="flex items-start justify-between">
      <div className="flex items-center gap-2">
        <span className="flex items-center justify-center w-6 h-6 bg-purple-100 text-purple-700 rounded-full text-sm font-bold">
          {index + 1}
        </span>
        <h4 className="font-medium text-gray-900">{cause.cause}</h4>
      </div>
      <SeverityBadge severity={cause.severity} />
    </div>
    <div className="pl-8 space-y-1.5">
      <p className="text-sm text-gray-600">
        <span className="font-medium text-gray-700">Evidence:</span> {cause.evidence}
      </p>
      <p className="text-sm text-gray-600">
        <span className="font-medium text-gray-700">Impact:</span> {cause.impact}
      </p>
    </div>
  </div>
);

// Priority improvement card component
const ImprovementCard: React.FC<{ improvement: AIPriorityImprovement }> = ({ improvement }) => (
  <div className="p-4 bg-gradient-to-r from-green-50 to-white rounded-lg border border-green-200 space-y-3">
    <div className="flex items-start gap-3">
      <div className="flex items-center justify-center w-8 h-8 bg-green-600 text-white rounded-full text-lg font-bold flex-shrink-0">
        {improvement.priority}
      </div>
      <div>
        <h4 className="font-semibold text-gray-900">{improvement.area}</h4>
        <p className="text-sm text-gray-600">{improvement.issue}</p>
      </div>
    </div>

    {/* Heuristic - highlighted */}
    <div className="p-3 bg-green-100 rounded-lg border border-green-200">
      <div className="flex items-start gap-2">
        <Lightbulb size={16} className="text-green-700 mt-0.5 flex-shrink-0" />
        <p className="text-sm font-medium text-green-800">{improvement.heuristic}</p>
      </div>
    </div>

    {/* Target metric */}
    <div className="flex items-center gap-2 text-sm">
      <Target size={14} className="text-gray-500" />
      <span className="text-gray-600">Target: </span>
      <span className="font-medium text-gray-900">{improvement.target_metric}</span>
    </div>

    {/* Specific actions */}
    {improvement.specific_actions && improvement.specific_actions.length > 0 && (
      <div className="space-y-1">
        <p className="text-xs font-medium text-gray-500 uppercase">Specific Actions:</p>
        <ul className="space-y-1">
          {improvement.specific_actions.map((action, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
              <CheckCircle size={14} className="text-green-500 mt-0.5 flex-shrink-0" />
              {action}
            </li>
          ))}
        </ul>
      </div>
    )}
  </div>
);

const AILeakAnalysisModal: React.FC<AILeakAnalysisModalProps> = ({
  isOpen,
  onClose,
  playerName
}) => {
  const [analysis, setAnalysis] = useState<AILeakAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    profile: true,
    causes: true,
    improvements: true,
    heuristics: false,
    analysis: false
  });

  useEffect(() => {
    if (isOpen && playerName) {
      fetchAnalysis();
    }
  }, [isOpen, playerName]);

  const fetchAnalysis = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await api.getAILeakAnalysis(playerName);
      setAnalysis(data);

      if (data.error) {
        setError(data.error);
      }
    } catch (err) {
      console.error('AI leak analysis error:', err);
      setError('Failed to fetch AI analysis. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  if (!isOpen) return null;

  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'high': return 'text-green-600';
      case 'moderate': return 'text-yellow-600';
      default: return 'text-red-600';
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-white">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-100">
              <TrendingUp className="text-purple-600" size={20} />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">
                AI Preflop Leak Analysis
              </h2>
              <p className="text-sm text-gray-500">
                {playerName}
                {analysis && (
                  <span className={`ml-2 ${getConfidenceColor(analysis.confidence)}`}>
                    ({analysis.total_hands.toLocaleString()} hands - {analysis.confidence} confidence)
                  </span>
                )}
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
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="animate-spin text-purple-600 mb-3" size={40} />
              <p className="text-gray-600 font-medium">Analyzing preflop leaks...</p>
              <p className="text-sm text-gray-500 mt-1">Claude is reviewing your data</p>
            </div>
          ) : error && !analysis?.success ? (
            <div className="text-center py-12">
              <AlertTriangle className="mx-auto mb-3 text-red-500" size={40} />
              <p className="text-red-600 font-medium">{error}</p>
              <button
                onClick={fetchAnalysis}
                className="mt-4 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          ) : analysis ? (
            <div className="space-y-4">
              {/* Confidence Warning */}
              {analysis.confidence === 'low' && (
                <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <AlertCircle className="text-yellow-600 flex-shrink-0 mt-0.5" size={16} />
                  <p className="text-sm text-yellow-800">
                    <span className="font-medium">Low sample size warning:</span> Results are preliminary.
                    Play more hands for more reliable analysis.
                  </p>
                </div>
              )}

              {/* Player Profile Section */}
              <CollapsibleSection
                title="Player Profile"
                icon={<User size={18} className="text-purple-600" />}
                isExpanded={expandedSections.profile}
                onToggle={() => toggleSection('profile')}
                headerContent={
                  <PlayerTypeBadge type={analysis.player_profile?.type || 'Unknown'} />
                }
              >
                <div className="space-y-3">
                  <p className="text-gray-700">{analysis.player_profile?.summary}</p>
                  <div className="flex flex-wrap gap-4 text-sm">
                    <div className="flex items-center gap-1.5">
                      <span className="text-gray-500">VPIP:</span>
                      <span className="font-semibold text-gray-900">
                        {analysis.player_profile?.key_indicators?.vpip?.toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-gray-500">PFR:</span>
                      <span className="font-semibold text-gray-900">
                        {analysis.player_profile?.key_indicators?.pfr?.toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-gray-500">Gap:</span>
                      <span className={`font-semibold ${
                        (analysis.player_profile?.key_indicators?.gap || 0) > 8
                          ? 'text-red-600'
                          : 'text-green-600'
                      }`}>
                        {analysis.player_profile?.key_indicators?.gap?.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </CollapsibleSection>

              {/* Root Causes Section */}
              {analysis.root_causes && analysis.root_causes.length > 0 && (
                <CollapsibleSection
                  title="Root Causes"
                  icon={<AlertCircle size={18} className="text-red-500" />}
                  isExpanded={expandedSections.causes}
                  onToggle={() => toggleSection('causes')}
                  headerContent={
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                      {analysis.root_causes.length} issue{analysis.root_causes.length !== 1 ? 's' : ''}
                    </span>
                  }
                >
                  <div className="space-y-3">
                    {analysis.root_causes.map((cause, i) => (
                      <RootCauseCard key={i} cause={cause} index={i} />
                    ))}
                  </div>
                </CollapsibleSection>
              )}

              {/* Priority Improvements Section */}
              {analysis.priority_improvements && analysis.priority_improvements.length > 0 && (
                <CollapsibleSection
                  title="Priority Improvements"
                  icon={<Target size={18} className="text-green-600" />}
                  isExpanded={expandedSections.improvements}
                  onToggle={() => toggleSection('improvements')}
                >
                  <div className="space-y-4">
                    {analysis.priority_improvements.map((improvement, i) => (
                      <ImprovementCard key={i} improvement={improvement} />
                    ))}
                  </div>
                </CollapsibleSection>
              )}

              {/* Quick Heuristics Section */}
              {analysis.quick_heuristics && analysis.quick_heuristics.length > 0 && (
                <CollapsibleSection
                  title="Quick Rules for the Table"
                  icon={<Lightbulb size={18} className="text-yellow-600" />}
                  isExpanded={expandedSections.heuristics}
                  onToggle={() => toggleSection('heuristics')}
                >
                  <div className="grid gap-2">
                    {analysis.quick_heuristics.map((rule, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-2 p-3 bg-yellow-50 rounded-lg border border-yellow-200"
                      >
                        <CheckCircle size={16} className="text-yellow-600 mt-0.5 flex-shrink-0" />
                        <p className="text-sm text-yellow-800">{rule}</p>
                      </div>
                    ))}
                  </div>
                </CollapsibleSection>
              )}

              {/* Full Analysis Text Section */}
              {analysis.analysis_text && (
                <CollapsibleSection
                  title="Detailed Analysis"
                  icon={<TrendingUp size={18} className="text-blue-600" />}
                  isExpanded={expandedSections.analysis}
                  onToggle={() => toggleSection('analysis')}
                >
                  <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
                    {analysis.analysis_text}
                  </div>
                </CollapsibleSection>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
          >
            Close
          </button>
          {analysis && !loading && (
            <button
              onClick={fetchAnalysis}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              Refresh Analysis
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AILeakAnalysisModal;
