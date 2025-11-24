import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import RangeGrid from '../components/RangeGrid';

interface Scenario {
  scenario_id: number;
  scenario_name: string;
  category: string;
  position: string;
  action: string;
  opponent_position?: string;
  description?: string;
}

interface ScenarioDetails extends Scenario {
  gto_action?: {
    action: string;
    frequency: number;
    range_matrix?: Record<string, number>;
    combos?: number;
  };
}

interface GroupedScenarios {
  opening: Scenario[];
  facingOpen: Scenario[];
  facing3Bet: Scenario[];
  facing4Bet: Scenario[];
  multiway: Scenario[];
}

const POSITIONS = [
  { id: 'UTG', label: 'UTG', description: 'Under the Gun' },
  { id: 'MP', label: 'MP', description: 'Middle Position' },
  { id: 'CO', label: 'CO', description: 'Cutoff' },
  { id: 'BTN', label: 'BTN', description: 'Button' },
  { id: 'SB', label: 'SB', description: 'Small Blind' },
  { id: 'BB', label: 'BB', description: 'Big Blind' },
];

const GTOBrowser: React.FC = () => {
  const [selectedPosition, setSelectedPosition] = useState('UTG');
  const [allScenarios, setAllScenarios] = useState<Scenario[]>([]);
  const [groupedScenarios, setGroupedScenarios] = useState<GroupedScenarios>({
    opening: [],
    facingOpen: [],
    facing3Bet: [],
    facing4Bet: [],
    multiway: [],
  });
  const [selectedScenario, setSelectedScenario] = useState<ScenarioDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['opening', 'facingOpen']));

  // Fetch all scenarios on mount
  useEffect(() => {
    fetchAllScenarios();
  }, []);

  // Group scenarios when position changes
  useEffect(() => {
    groupScenariosByType();
  }, [selectedPosition, allScenarios]);

  const fetchAllScenarios = async () => {
    setLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      const response = await fetch(`${apiUrl}/api/gto/scenarios`);
      const data = await response.json();
      setAllScenarios(data);
    } catch (error) {
      console.error('Error fetching scenarios:', error);
    } finally {
      setLoading(false);
    }
  };

  const groupScenariosByType = () => {
    const positionScenarios = allScenarios.filter(s => s.position === selectedPosition);

    const grouped: GroupedScenarios = {
      opening: [],
      facingOpen: [],
      facing3Bet: [],
      facing4Bet: [],
      multiway: [],
    };

    positionScenarios.forEach(scenario => {
      if (scenario.category === 'opening') {
        grouped.opening.push(scenario);
      } else if (scenario.category === 'defense' || (scenario.category === 'facing_3bet' && scenario.action === '3bet' && !scenario.scenario_name.includes('3bet_'))) {
        // Defense (fold/call) OR 3-betting vs open (not facing a 3-bet)
        grouped.facingOpen.push(scenario);
      } else if (scenario.category === 'facing_3bet' && scenario.action !== '3bet') {
        // Facing a 3-bet (responding with fold/call/4bet/allin)
        grouped.facing3Bet.push(scenario);
      } else if (scenario.category === 'facing_4bet') {
        grouped.facing4Bet.push(scenario);
      } else if (scenario.category === 'multiway') {
        grouped.multiway.push(scenario);
      }
    });

    // Sort scenarios within each group by opponent position
    Object.keys(grouped).forEach(key => {
      grouped[key as keyof GroupedScenarios].sort((a, b) => {
        const opponentOrder = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB'];
        const aIndex = a.opponent_position ? opponentOrder.indexOf(a.opponent_position) : 999;
        const bIndex = b.opponent_position ? opponentOrder.indexOf(b.opponent_position) : 999;
        return aIndex - bIndex;
      });
    });

    setGroupedScenarios(grouped);
  };

  const fetchScenarioDetails = async (scenarioId: number) => {
    setDetailsLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      const response = await fetch(`${apiUrl}/api/gto/scenario/${scenarioId}`);
      const data = await response.json();
      setSelectedScenario(data);
    } catch (error) {
      console.error('Error fetching scenario details:', error);
    } finally {
      setDetailsLoading(false);
    }
  };

  const handleScenarioClick = (scenario: Scenario) => {
    if (selectedScenario?.scenario_id === scenario.scenario_id) {
      setSelectedScenario(null);
    } else {
      fetchScenarioDetails(scenario.scenario_id);
    }
  };

  const toggleGroup = (groupKey: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(groupKey)) {
      newExpanded.delete(groupKey);
    } else {
      newExpanded.add(groupKey);
    }
    setExpandedGroups(newExpanded);
  };

  const getActionBadgeColor = (action: string) => {
    switch (action) {
      case 'open':
      case 'raise':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'fold':
        return 'bg-gray-100 text-gray-800 border-gray-300';
      case 'call':
        return 'bg-green-100 text-green-800 border-green-300';
      case '3bet':
      case '4bet':
      case '5bet':
        return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'allin':
        return 'bg-red-100 text-red-800 border-red-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const renderScenarioGroup = (title: string, groupKey: keyof GroupedScenarios, scenarios: Scenario[]) => {
    if (scenarios.length === 0) return null;

    const isExpanded = expandedGroups.has(groupKey);

    // Group scenarios by opponent within this category
    const scenariosByOpponent: Record<string, Scenario[]> = {};
    scenarios.forEach(scenario => {
      const opponent = scenario.opponent_position || 'no_opponent';
      if (!scenariosByOpponent[opponent]) {
        scenariosByOpponent[opponent] = [];
      }
      scenariosByOpponent[opponent].push(scenario);
    });

    // Sort opponent keys by position order
    const opponentOrder = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB', 'no_opponent'];
    const sortedOpponents = Object.keys(scenariosByOpponent).sort((a, b) => {
      return opponentOrder.indexOf(a) - opponentOrder.indexOf(b);
    });

    return (
      <div key={groupKey} className="mb-4">
        <button
          onClick={() => toggleGroup(groupKey)}
          className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <div className="flex items-center gap-3">
            {isExpanded ? <ChevronDown className="w-5 h-5 text-gray-500" /> : <ChevronRight className="w-5 h-5 text-gray-500" />}
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            <span className="text-sm text-gray-500">({scenarios.length})</span>
          </div>
        </button>

        {isExpanded && (
          <div className="mt-2 space-y-3 pl-4">
            {sortedOpponents.map((opponent) => {
              const opponentScenarios = scenariosByOpponent[opponent];
              const opponentKey = `${groupKey}_${opponent}`;
              const isOpponentExpanded = expandedGroups.has(opponentKey);

              return (
                <div key={opponent}>
                  {/* Opponent Sub-group Header */}
                  {opponent !== 'no_opponent' ? (
                    <button
                      onClick={() => toggleGroup(opponentKey)}
                      className="w-full flex items-center gap-2 p-2 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                    >
                      {isOpponentExpanded ? <ChevronDown className="w-4 h-4 text-gray-500" /> : <ChevronRight className="w-4 h-4 text-gray-500" />}
                      <span className="text-sm font-semibold text-gray-700">
                        vs <span className="text-orange-600">{opponent}</span>
                      </span>
                      <span className="text-xs text-gray-500">({opponentScenarios.length})</span>
                    </button>
                  ) : null}

                  {/* Scenarios for this opponent */}
                  {(opponent === 'no_opponent' || isOpponentExpanded) && (
                    <div className="space-y-2 pl-2">
                      {opponentScenarios.map((scenario) => (
                        <div key={scenario.scenario_id}>
                          <button
                            onClick={() => handleScenarioClick(scenario)}
                            className={`
                              w-full text-left p-3 rounded-lg border transition-all
                              ${selectedScenario?.scenario_id === scenario.scenario_id
                                ? 'border-blue-500 bg-blue-50 shadow-md'
                                : 'border-gray-200 bg-white hover:border-blue-300 hover:shadow-sm'
                              }
                            `}
                          >
                            <div className="flex items-center gap-3">
                              <span className={`
                                px-2 py-1 text-xs font-medium rounded border
                                ${getActionBadgeColor(scenario.action)}
                              `}>
                                {scenario.action.toUpperCase()}
                              </span>
                              <span className="text-sm font-medium text-gray-700">
                                {scenario.scenario_name}
                              </span>
                            </div>
                          </button>

                          {/* Expanded Details */}
                          {selectedScenario?.scenario_id === scenario.scenario_id && (
                            <div className="mt-2 ml-4 bg-white rounded-lg border-2 border-blue-500 p-6">
                              {detailsLoading ? (
                                <div className="text-center py-8">
                                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                                  <p className="mt-2 text-sm text-gray-600">Loading range data...</p>
                                </div>
                              ) : selectedScenario.gto_action ? (
                                <div>
                                  <div className="mb-4">
                                    <h4 className="text-lg font-semibold text-gray-900 mb-2">
                                      {selectedScenario.scenario_name}
                                    </h4>
                                    <div className="flex items-center gap-4 text-sm text-gray-600">
                                      <span>
                                        <span className="font-medium">Frequency:</span>{' '}
                                        <span className="text-blue-600 font-bold">
                                          {selectedScenario.gto_action.frequency.toFixed(1)}%
                                        </span>
                                      </span>
                                      {selectedScenario.gto_action.combos && (
                                        <span>
                                          <span className="font-medium">Combos:</span>{' '}
                                          <span className="text-gray-900 font-bold">
                                            {selectedScenario.gto_action.combos}
                                          </span>
                                        </span>
                                      )}
                                    </div>
                                  </div>

                                  {selectedScenario.gto_action.range_matrix ? (
                                    <RangeGrid
                                      rangeMatrix={selectedScenario.gto_action.range_matrix}
                                      title={`${selectedScenario.action.toUpperCase()} Range`}
                                    />
                                  ) : (
                                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
                                      <p className="text-yellow-800">Range data not available for this scenario</p>
                                    </div>
                                  )}

                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setSelectedScenario(null);
                                    }}
                                    className="mt-4 w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
                                  >
                                    Close
                                  </button>
                                </div>
                              ) : (
                                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                                  <p className="text-red-800">No GTO data available for this scenario</p>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const totalScenarios = Object.values(groupedScenarios).reduce((sum, arr) => sum + arr.length, 0);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">GTO Scenario Browser</h1>
          <p className="text-gray-600">Study GTO ranges by position - select your position below</p>
        </div>

        {/* Position Selector */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-sm font-medium text-gray-700 mb-4">Select Position:</h2>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            {POSITIONS.map((position) => (
              <button
                key={position.id}
                onClick={() => {
                  setSelectedPosition(position.id);
                  setSelectedScenario(null);
                }}
                className={`
                  px-6 py-4 rounded-lg border-2 font-semibold transition-all
                  ${selectedPosition === position.id
                    ? 'border-blue-600 bg-blue-600 text-white shadow-lg scale-105'
                    : 'border-gray-300 bg-white text-gray-700 hover:border-blue-300 hover:shadow-md'
                  }
                `}
              >
                <div className="text-lg">{position.label}</div>
                <div className="text-xs font-normal opacity-75">{position.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading scenarios...</p>
          </div>
        )}

        {/* Scenarios */}
        {!loading && (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">
                {selectedPosition} Scenarios ({totalScenarios})
              </h2>
            </div>

            {totalScenarios === 0 ? (
              <div className="text-center py-12 text-gray-500">
                No scenarios available for {selectedPosition}
              </div>
            ) : (
              <div className="space-y-2">
                {renderScenarioGroup('Opening', 'opening', groupedScenarios.opening)}
                {renderScenarioGroup('Facing an Open', 'facingOpen', groupedScenarios.facingOpen)}
                {renderScenarioGroup('Facing a 3-Bet', 'facing3Bet', groupedScenarios.facing3Bet)}
                {renderScenarioGroup('Facing a 4-Bet', 'facing4Bet', groupedScenarios.facing4Bet)}
                {renderScenarioGroup('Multiway', 'multiway', groupedScenarios.multiway)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default GTOBrowser;
