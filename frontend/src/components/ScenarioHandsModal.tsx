import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { X, CheckCircle, AlertTriangle, XCircle, Grid3X3, Play } from 'lucide-react';
import { api } from '../services/api';
import RangeGrid from './RangeGrid';
import type { HandActions } from './RangeGrid';
import HandReplayModal from './HandReplayModal';
import type { ScenarioHandsResponse } from '../types';

// Scenario drill-down selection
export interface ScenarioSelection {
  scenario: 'opening' | 'defense' | 'facing_3bet' | 'facing_4bet';
  position: string;
  vsPosition?: string;
  action?: string;  // Specific action for the leak (e.g., 'call', 'fold', 'raise')
  deviation?: number;  // Deviation from GTO - used to show mistakes (negative = under-doing, positive = over-doing)
}

interface ScenarioHandsModalProps {
  data: ScenarioHandsResponse | undefined;
  isLoading: boolean;
  onClose: () => void;
  selection: ScenarioSelection;
}

// Scenario Hands Drill-down Modal
const ScenarioHandsModal = ({
  data,
  isLoading,
  onClose,
  selection
}: ScenarioHandsModalProps) => {
  const [selectedHand, setSelectedHand] = useState<string | null>(null);
  const [selectedHandVsPos, setSelectedHandVsPos] = useState<string | null>(null);
  const [showRangeGrid, setShowRangeGrid] = useState(false);
  const [replayHandId, setReplayHandId] = useState<number | null>(null);

  // For range matrix: use the specific hand's opponent if selected, otherwise use selection's vsPosition
  const effectiveVsPosition = selectedHandVsPos || selection.vsPosition;

  // Fetch GTO range matrix for this scenario
  const { data: rangeMatrix, isLoading: rangeLoading } = useQuery({
    queryKey: ['rangeMatrix', selection.scenario, selection.position, effectiveVsPosition],
    queryFn: () => api.getGTORangeMatrix(
      selection.scenario,
      selection.position,
      effectiveVsPosition || undefined
    ),
    enabled: showRangeGrid,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  // Fetch hand replay data when a hand is selected for replay
  const { data: replayData, isLoading: replayLoading } = useQuery({
    queryKey: ['handReplay', replayHandId],
    queryFn: () => api.getHandReplay(replayHandId!),
    enabled: replayHandId !== null,
    staleTime: 5 * 60 * 1000,
  });

  const scenarioLabels: Record<string, string> = {
    opening: 'Opening Range',
    defense: 'Defense vs Open',
    facing_3bet: 'Facing 3-Bet',
    facing_4bet: 'Facing 4-Bet'
  };

  const actionColors: Record<string, string> = {
    fold: 'text-gray-600 bg-gray-100',
    call: 'text-green-700 bg-green-100',
    raise: 'text-blue-700 bg-blue-100',
    '3bet': 'text-orange-700 bg-orange-100',
    '4bet': 'text-red-700 bg-red-100',
    '5bet': 'text-purple-700 bg-purple-100',
    limp: 'text-yellow-700 bg-yellow-100',
  };

  const tierColors: Record<number, string> = {
    1: 'bg-purple-100 text-purple-800',  // Premium
    2: 'bg-blue-100 text-blue-800',      // Strong
    3: 'bg-green-100 text-green-800',    // Playable
    4: 'bg-yellow-100 text-yellow-800',  // Speculative
    5: 'bg-red-100 text-red-800',        // Weak
  };

  const deviationStyles: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    correct: { bg: 'bg-green-50', text: 'text-green-700', icon: <CheckCircle size={14} className="mr-1" /> },
    suboptimal: { bg: 'bg-yellow-50', text: 'text-yellow-700', icon: <AlertTriangle size={14} className="mr-1" /> },
    mistake: { bg: 'bg-red-50', text: 'text-red-700', icon: <XCircle size={14} className="mr-1" /> },
  };

  // Handle clicking a hand row to show it in the range grid
  const handleHandClick = (handCombo: string | null, vsPosition?: string | null) => {
    if (handCombo) {
      setSelectedHand(handCombo);
      setSelectedHandVsPos(vsPosition || null);
      setShowRangeGrid(true);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">
              {scenarioLabels[selection.scenario]} - {selection.position}
              {selection.vsPosition && ` vs ${selection.vsPosition}`}
              {selection.action && ` - ${selection.action.charAt(0).toUpperCase() + selection.action.slice(1)}`}
            </h2>
            {data && (
              <p className="text-blue-100 text-sm mt-1">
                {data.total_hands} hands analyzed
                {data.hands_with_hole_cards > 0 && ` - ${data.hands_with_hole_cards} with hole cards`}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            {/* Range Grid Toggle */}
            <button
              onClick={() => setShowRangeGrid(!showRangeGrid)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors ${
                showRangeGrid
                  ? 'bg-white text-blue-600'
                  : 'bg-blue-500/30 text-white hover:bg-blue-500/50'
              }`}
            >
              <Grid3X3 size={18} />
              <span className="text-sm font-medium">Range Grid</span>
            </button>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white transition-colors"
            >
              <X size={24} />
            </button>
          </div>
        </div>

        {/* Enhanced Summary Bar */}
        {data?.summary && (
          <div className="bg-gradient-to-r from-gray-50 to-blue-50 px-6 py-3 border-b border-gray-200">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <CheckCircle size={16} className="text-green-600" />
                <span className="text-sm">
                  <span className="font-semibold text-green-700">{data.summary.correct}</span>
                  <span className="text-gray-500 ml-1">correct ({data.summary.correct_pct}%)</span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <AlertTriangle size={16} className="text-yellow-600" />
                <span className="text-sm">
                  <span className="font-semibold text-yellow-700">{data.summary.suboptimal}</span>
                  <span className="text-gray-500 ml-1">suboptimal ({data.summary.suboptimal_pct}%)</span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <XCircle size={16} className="text-red-600" />
                <span className="text-sm">
                  <span className="font-semibold text-red-700">{data.summary.mistakes}</span>
                  <span className="text-gray-500 ml-1">mistakes ({data.summary.mistake_pct}%)</span>
                </span>
              </div>
            </div>
          </div>
        )}

        {/* GTO Reference Bar */}
        {data && Object.keys(data.gto_frequencies).length > 0 && (
          <div className="bg-blue-50 px-6 py-3 border-b border-blue-100">
            <div className="text-sm text-blue-800 font-medium mb-2">GTO Frequencies:</div>
            <div className="flex gap-4 flex-wrap">
              {Object.entries(data.gto_frequencies)
                .sort((a, b) => b[1] - a[1])
                .map(([action, freq]) => (
                  <span key={action} className="text-sm">
                    <span className={`px-2 py-0.5 rounded ${actionColors[action] || 'bg-gray-100'}`}>
                      {action}
                    </span>
                    <span className="text-blue-600 ml-1 font-medium">{freq.toFixed(1)}%</span>
                  </span>
                ))}
            </div>
          </div>
        )}

        {/* Content - Split view when range grid is shown */}
        <div className={`overflow-hidden ${showRangeGrid ? 'flex' : ''}`} style={{ maxHeight: '55vh' }}>
          {/* Range Grid Panel */}
          {showRangeGrid && (
            <div className="w-96 flex-shrink-0 border-r border-gray-200 p-4 overflow-y-auto bg-gray-50">
              <div className="sticky top-0 bg-gray-50 pb-2 mb-2">
                <h3 className="text-sm font-semibold text-gray-700 mb-1">
                  GTO Range: {selection.position}
                  {effectiveVsPosition && ` vs ${effectiveVsPosition}`}
                  {!effectiveVsPosition && selection.scenario !== 'opening' && ' (aggregated)'}
                </h3>
                <p className="text-xs text-gray-500">
                  {selectedHandVsPos ? `Showing ${selection.position} vs ${selectedHandVsPos} ranges` : 'Click a hand in the table to highlight it'}
                </p>
              </div>
              {rangeLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin h-6 w-6 border-2 border-blue-600 border-t-transparent rounded-full" />
                </div>
              ) : rangeMatrix && Object.keys(rangeMatrix).length > 0 ? (
                <RangeGrid
                  actionMatrix={rangeMatrix as Record<string, HandActions>}
                  highlightedHand={selectedHand || undefined}
                  showFolds={false}
                  onHandClick={(hand) => setSelectedHand(hand)}
                />
              ) : (
                <div className="text-center text-gray-500 py-8 text-sm">
                  No GTO data available for this scenario
                </div>
              )}
            </div>
          )}

          {/* Hands Table */}
          <div className={`overflow-y-auto p-6 ${showRangeGrid ? 'flex-1' : 'w-full'}`}>
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin h-8 w-8 border-2 border-blue-600 border-t-transparent rounded-full" />
              </div>
            ) : data && data.hands.length > 0 ? (
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-white">
                  <tr className="border-b-2 border-gray-200">
                    <th className="text-left py-3 px-2 font-semibold text-gray-700">Hand</th>
                    <th className="text-left py-3 px-2 font-semibold text-gray-700">Category</th>
                    <th className="text-center py-3 px-2 font-semibold text-gray-700">Stack</th>
                    {selection.vsPosition === undefined && (
                      <th className="text-left py-3 px-2 font-semibold text-gray-700">vs</th>
                    )}
                    <th className="text-left py-3 px-2 font-semibold text-gray-700">Action</th>
                    <th className="text-right py-3 px-2 font-semibold text-gray-700">GTO%</th>
                    <th className="text-left py-3 px-2 font-semibold text-gray-700">Assessment</th>
                    <th className="text-center py-3 px-2 font-semibold text-gray-700 w-16">Replay</th>
                  </tr>
                </thead>
                <tbody>
                  {data.hands.map((hand) => {
                    const devStyle = deviationStyles[hand.deviation_type] || deviationStyles.correct;
                    const isSelected = selectedHand === hand.hand_combo;
                    return (
                      <tr
                        key={hand.hand_id}
                        className={`border-b border-gray-100 cursor-pointer transition-colors ${
                          isSelected ? 'bg-yellow-100 ring-2 ring-yellow-400' : `hover:bg-gray-50 ${devStyle.bg}`
                        }`}
                        onClick={() => handleHandClick(hand.hand_combo, hand.vs_position)}
                      >
                        {/* Hole Cards */}
                        <td className="py-3 px-2">
                          {hand.hole_cards ? (
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-bold text-gray-800">
                                {hand.hand_combo || hand.hole_cards}
                              </span>
                              {hand.hand_tier && (
                                <span className={`px-1.5 py-0.5 rounded text-xs ${tierColors[hand.hand_tier]}`}>
                                  T{hand.hand_tier}
                                </span>
                              )}
                              {showRangeGrid && (
                                <span title="Click to view in range grid">
                                  <Grid3X3 size={14} className="text-blue-400" />
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-gray-400 italic">Unknown</span>
                          )}
                        </td>
                        {/* Hand Category */}
                        <td className="py-3 px-2 text-gray-600 text-xs">
                          {hand.hand_category || '-'}
                        </td>
                        {/* Effective Stack */}
                        <td className="py-3 px-2 text-center">
                          {hand.effective_stack_bb ? (
                            <span className="font-mono text-gray-700">
                              {hand.effective_stack_bb.toFixed(0)}bb
                            </span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        {/* vs Position */}
                        {selection.vsPosition === undefined && (
                          <td className="py-3 px-2 text-gray-600">{hand.vs_position || '-'}</td>
                        )}
                        {/* Player Action */}
                        <td className="py-3 px-2">
                          <span className={`px-2 py-1 rounded font-medium text-xs ${
                            actionColors[hand.player_action] || 'bg-gray-100'
                          }`}>
                            {hand.player_action}
                          </span>
                        </td>
                        {/* GTO Frequency */}
                        <td className="py-3 px-2 text-right">
                          <span className={`font-mono ${
                            hand.action_gto_freq < 15 ? 'text-red-600 font-bold' :
                            hand.action_gto_freq < 40 ? 'text-yellow-600' : 'text-gray-600'
                          }`}>
                            {hand.action_gto_freq.toFixed(0)}%
                          </span>
                        </td>
                        {/* Assessment */}
                        <td className="py-3 px-2">
                          <div className={`inline-flex items-center text-xs font-medium ${devStyle.text}`}>
                            {devStyle.icon}
                            <span className="capitalize">{hand.deviation_type}</span>
                            {hand.deviation_severity && (
                              <span className="ml-1 opacity-75">({hand.deviation_severity})</span>
                            )}
                          </div>
                          {hand.deviation_type !== 'correct' && (
                            <div className="text-xs text-gray-500 mt-0.5">
                              {hand.deviation_description}
                            </div>
                          )}
                        </td>
                        {/* Replay Button */}
                        <td className="py-3 px-2 text-center">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setReplayHandId(hand.hand_id);
                            }}
                            className="p-1.5 rounded-lg bg-emerald-100 text-emerald-700 hover:bg-emerald-200 transition-colors"
                            title="Replay this hand"
                          >
                            <Play size={14} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <div className="text-center text-gray-500 py-12">
                No hands found for this scenario
              </div>
            )}
          </div>
        </div>

        {/* Footer Legend */}
        <div className="border-t border-gray-200 px-6 py-4 bg-gray-50">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap gap-4 text-xs text-gray-500">
              <span>Hand Tiers:</span>
              <span className={`px-1.5 py-0.5 rounded ${tierColors[1]}`}>T1 Premium</span>
              <span className={`px-1.5 py-0.5 rounded ${tierColors[2]}`}>T2 Strong</span>
              <span className={`px-1.5 py-0.5 rounded ${tierColors[3]}`}>T3 Playable</span>
              <span className={`px-1.5 py-0.5 rounded ${tierColors[4]}`}>T4 Speculative</span>
              <span className={`px-1.5 py-0.5 rounded ${tierColors[5]}`}>T5 Weak</span>
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>

      {/* Hand Replay Modal */}
      {replayHandId && replayData && (
        <HandReplayModal
          data={replayData}
          onClose={() => setReplayHandId(null)}
        />
      )}

      {/* Loading overlay for replay */}
      {replayHandId && replayLoading && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-60">
          <div className="bg-white rounded-lg p-6 shadow-xl flex items-center gap-3">
            <div className="animate-spin h-6 w-6 border-2 border-emerald-600 border-t-transparent rounded-full" />
            <span className="text-gray-700">Loading hand...</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default ScenarioHandsModal;
