import React, { useState } from 'react';
import { AlertCircle } from 'lucide-react';
import RangeGrid from '../components/RangeGrid';

interface ActionStep {
  position: string;
  action: string;
  size_bb?: number;
}

interface GTOAction {
  action: string;
  frequency: number;
  range_string?: string;
  range_matrix?: Record<string, number>;
  combos?: number;
}

interface MatchedScenario {
  found: boolean;
  scenario_id?: number;
  scenario_name?: string;
  category?: string;
  description?: string;
  gto_actions?: GTOAction[];
  message?: string;
  searched_for?: any;
}

const POSITIONS = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB'];

const GTOBrowser: React.FC = () => {
  const [actionSequence, setActionSequence] = useState<ActionStep[]>([]);
  const [currentPositionIndex, setCurrentPositionIndex] = useState(0);
  const [matchedScenario, setMatchedScenario] = useState<MatchedScenario | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedActionTab, setSelectedActionTab] = useState<string>('');

  const currentPosition = POSITIONS[currentPositionIndex];

  const getAvailableActions = (): Array<{label: string, action: string, size_bb?: number}> => {
    // Check if there's an open before current position
    const hasOpen = actionSequence.some(a => a.action === 'raise' || a.action === 'open');
    const has3Bet = actionSequence.filter(a => a.action === '3bet').length > 0;

    if (!hasOpen) {
      // No one has acted yet, can fold or raise (open)
      return [
        { label: 'Fold', action: 'fold' },
        { label: 'Raise 2.5bb', action: 'raise', size_bb: 2.5 },
        { label: 'Raise 3bb', action: 'raise', size_bb: 3.0 },
      ];
    } else if (hasOpen && !has3Bet) {
      // Facing an open, can fold/call/3bet
      return [
        { label: 'Fold', action: 'fold' },
        { label: 'Call', action: 'call' },
        { label: '3-Bet 8bb', action: '3bet', size_bb: 8 },
        { label: '3-Bet 10bb', action: '3bet', size_bb: 10 },
      ];
    } else if (has3Bet) {
      // Facing a 3-bet, can fold/call/4bet
      return [
        { label: 'Fold', action: 'fold' },
        { label: 'Call', action: 'call' },
        { label: '4-Bet 22bb', action: '4bet', size_bb: 22 },
        { label: 'All-in', action: 'allin' },
      ];
    }

    return [{ label: 'Fold', action: 'fold' }];
  };

  const handleAction = async (action: string, size_bb?: number) => {
    const newAction: ActionStep = {
      position: currentPosition,
      action,
      size_bb,
    };

    const newSequence = [...actionSequence, newAction];
    setActionSequence(newSequence);

    // If action is not fold, query GTO solution
    if (action !== 'fold') {
      await matchScenario(newSequence, currentPosition, action);
    } else {
      // Move to next position
      if (currentPositionIndex < POSITIONS.length - 1) {
        setCurrentPositionIndex(currentPositionIndex + 1);
      }
    }
  };

  const matchScenario = async (sequence: ActionStep[], heroPosition: string, heroAction: string) => {
    setLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      const response = await fetch(`${apiUrl}/api/gto/match-scenario`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table_size: '6max',
          actions: sequence,
          hero_position: heroPosition,
          hero_action: heroAction,
        }),
      });

      const data = await response.json();
      setMatchedScenario(data);

      // Set default selected action tab to the first action with highest frequency
      if (data.found && data.gto_actions && data.gto_actions.length > 0) {
        const sortedActions = [...data.gto_actions].sort((a, b) => b.frequency - a.frequency);
        setSelectedActionTab(sortedActions[0].action);
      }
    } catch (error) {
      console.error('Error matching scenario:', error);
      setMatchedScenario({
        found: false,
        message: 'Error connecting to server',
      });
    } finally {
      setLoading(false);
    }
  };

  const resetScenario = () => {
    setActionSequence([]);
    setCurrentPositionIndex(0);
    setMatchedScenario(null);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">GTO Scenario Builder</h1>
          <p className="text-gray-600">Build preflop scenarios and see GTO solutions with range visualization</p>
        </div>

        {/* Action Sequence Display */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Action Sequence</h2>
          <div className="flex flex-wrap items-center gap-2 mb-4">
            {actionSequence.length === 0 ? (
              <div className="text-gray-400 italic">No actions yet - click buttons below to build scenario</div>
            ) : (
              actionSequence.map((step, index) => (
                <React.Fragment key={index}>
                  <div className="px-3 py-1 bg-blue-100 text-blue-800 rounded-md font-medium">
                    {step.position}: {step.action}
                    {step.size_bb && ` (${step.size_bb}bb)`}
                  </div>
                  {index < actionSequence.length - 1 && (
                    <span className="text-gray-400">→</span>
                  )}
                </React.Fragment>
              ))
            )}
          </div>

          {!matchedScenario && (
            <>
              <div className="mb-4">
                <span className="text-sm font-medium text-gray-700">
                  Action to: <span className="text-blue-600 font-bold">{currentPosition}</span>
                </span>
              </div>

              <div className="flex flex-wrap gap-3">
                {getAvailableActions().map((actionOption) => (
                  <button
                    key={`${actionOption.action}-${actionOption.size_bb || 0}`}
                    onClick={() => handleAction(actionOption.action, actionOption.size_bb)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium"
                  >
                    {actionOption.label}
                  </button>
                ))}
              </div>
            </>
          )}

          <button
            onClick={resetScenario}
            className="mt-4 px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
          >
            Reset Scenario
          </button>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Searching for GTO solution...</p>
          </div>
        )}

        {/* Matched Scenario Display */}
        {!loading && matchedScenario && matchedScenario.found && (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <h2 className="text-xl font-bold text-gray-900">
                GTO Solution: {matchedScenario.scenario_name}
              </h2>
            </div>

            {matchedScenario.description && (
              <p className="text-gray-600 mb-6">{matchedScenario.description}</p>
            )}

            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">GTO Actions:</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {matchedScenario.gto_actions?.map((action) => (
                  <div key={action.action} className="border border-gray-200 rounded-lg p-4">
                    <div className="text-sm font-medium text-gray-600 mb-1">
                      {action.action.toUpperCase()}
                    </div>
                    <div className="text-3xl font-bold text-blue-600">
                      {action.frequency.toFixed(1)}%
                    </div>
                    {action.combos && (
                      <div className="text-sm text-gray-500 mt-1">
                        {action.combos} combos
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Action Tabs */}
            {matchedScenario.gto_actions && matchedScenario.gto_actions.length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Range Visualization:</h3>
                <div className="flex flex-wrap gap-2 mb-4">
                  {matchedScenario.gto_actions.map((action) => (
                    <button
                      key={action.action}
                      onClick={() => setSelectedActionTab(action.action)}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        selectedActionTab === action.action
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {action.action.toUpperCase()} ({action.frequency.toFixed(1)}%)
                    </button>
                  ))}
                </div>

                {/* Show RangeGrid for selected action */}
                {selectedActionTab && (
                  <RangeGrid
                    rangeString={
                      matchedScenario.gto_actions.find(a => a.action === selectedActionTab)?.range_string
                    }
                    rangeMatrix={
                      matchedScenario.gto_actions.find(a => a.action === selectedActionTab)?.range_matrix
                    }
                    title={`${selectedActionTab.toUpperCase()} Range`}
                  />
                )}

                {/* Message if no range data available */}
                {selectedActionTab &&
                 !matchedScenario.gto_actions.find(a => a.action === selectedActionTab)?.range_string &&
                 !matchedScenario.gto_actions.find(a => a.action === selectedActionTab)?.range_matrix && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
                    <p className="text-yellow-800">
                      Range data not available for this action in the database.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Not Found Display */}
        {!loading && matchedScenario && !matchedScenario.found && (
          <div className="bg-white rounded-lg shadow-sm p-6 border-l-4 border-red-500">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-6 h-6 text-red-500 flex-shrink-0 mt-1" />
              <div className="flex-1">
                <h2 className="text-xl font-bold text-gray-900 mb-2">
                  No GTO Solution Found
                </h2>
                <p className="text-gray-600 mb-4">
                  {matchedScenario.message || 'This scenario is not in the GTO database'}
                </p>

                {matchedScenario.searched_for && (
                  <div className="bg-gray-50 rounded-md p-4 mb-4">
                    <p className="text-sm font-medium text-gray-700 mb-2">Searched for:</p>
                    <pre className="text-xs text-gray-600 overflow-auto">
                      {JSON.stringify(matchedScenario.searched_for, null, 2)}
                    </pre>
                  </div>
                )}

                <div className="text-sm text-gray-600">
                  <p className="mb-2">This could mean:</p>
                  <ul className="list-disc list-inside space-y-1">
                    <li>Scenario not yet solved/imported</li>
                    <li>Invalid action sequence</li>
                    <li>Uncommon spot not covered</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GTOBrowser;
