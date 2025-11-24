import React, { useState, useEffect } from 'react';
import { Filter, X } from 'lucide-react';
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

const CATEGORIES = [
  { id: 'opening', label: 'Opening', description: 'Open raises from each position' },
  { id: 'defense', label: 'Defense', description: 'Defending against opens heads-up' },
  { id: 'facing_3bet', label: 'Facing 3-Bet', description: '3-betting and facing 3-bets' },
  { id: 'facing_4bet', label: 'Facing 4-Bet', description: 'Facing 4-bets' },
  { id: 'multiway', label: 'Multiway', description: 'Multiple players in the pot' },
];

const POSITIONS = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB'];

const GTOBrowser: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState('opening');
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [filteredScenarios, setFilteredScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<ScenarioDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);

  // Filters
  const [positionFilter, setPositionFilter] = useState<string>('');
  const [opponentFilter, setOpponentFilter] = useState<string>('');
  const [showFilters, setShowFilters] = useState(false);

  // Fetch scenarios for selected category
  useEffect(() => {
    fetchScenarios();
  }, [selectedCategory]);

  // Apply filters
  useEffect(() => {
    let filtered = [...scenarios];

    if (positionFilter) {
      filtered = filtered.filter(s => s.position === positionFilter);
    }

    if (opponentFilter) {
      filtered = filtered.filter(s => s.opponent_position === opponentFilter);
    }

    setFilteredScenarios(filtered);
  }, [scenarios, positionFilter, opponentFilter]);

  const fetchScenarios = async () => {
    setLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      const response = await fetch(`${apiUrl}/api/gto/scenarios?category=${selectedCategory}`);
      const data = await response.json();
      setScenarios(data);
      setFilteredScenarios(data);
    } catch (error) {
      console.error('Error fetching scenarios:', error);
    } finally {
      setLoading(false);
    }
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

  const clearFilters = () => {
    setPositionFilter('');
    setOpponentFilter('');
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

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">GTO Scenario Browser</h1>
          <p className="text-gray-600">Browse and study all {scenarios.length} GTO scenarios with range visualization</p>
        </div>

        {/* Category Tabs */}
        <div className="bg-white rounded-lg shadow-sm mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px overflow-x-auto">
              {CATEGORIES.map((category) => (
                <button
                  key={category.id}
                  onClick={() => {
                    setSelectedCategory(category.id);
                    setSelectedScenario(null);
                    clearFilters();
                  }}
                  className={`
                    px-6 py-4 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
                    ${selectedCategory === category.id
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }
                  `}
                >
                  <div>{category.label}</div>
                  <div className="text-xs font-normal mt-1 text-gray-500">{category.description}</div>
                </button>
              ))}
            </nav>
          </div>

          {/* Filters */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between mb-3">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
              >
                <Filter className="w-4 h-4" />
                Filters
                {(positionFilter || opponentFilter) && (
                  <span className="ml-1 px-2 py-0.5 bg-blue-600 text-white text-xs rounded-full">
                    {[positionFilter, opponentFilter].filter(Boolean).length}
                  </span>
                )}
              </button>

              {(positionFilter || opponentFilter) && (
                <button
                  onClick={clearFilters}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  Clear filters
                </button>
              )}
            </div>

            {showFilters && (
              <div className="flex flex-wrap gap-4 pt-3 border-t border-gray-200">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Position</label>
                  <select
                    value={positionFilter}
                    onChange={(e) => setPositionFilter(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">All Positions</option>
                    {POSITIONS.map((pos) => (
                      <option key={pos} value={pos}>{pos}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Opponent</label>
                  <select
                    value={opponentFilter}
                    onChange={(e) => setOpponentFilter(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">All Opponents</option>
                    {POSITIONS.map((pos) => (
                      <option key={pos} value={pos}>{pos}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* Scenario Count */}
          <div className="px-4 py-3 bg-gray-50 text-sm text-gray-600">
            Showing {filteredScenarios.length} of {scenarios.length} scenarios
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading scenarios...</p>
          </div>
        )}

        {/* Scenario Cards Grid */}
        {!loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredScenarios.map((scenario) => (
              <div key={scenario.scenario_id}>
                <button
                  onClick={() => handleScenarioClick(scenario)}
                  className={`
                    w-full text-left p-4 rounded-lg border-2 transition-all
                    ${selectedScenario?.scenario_id === scenario.scenario_id
                      ? 'border-blue-600 bg-blue-50 shadow-lg'
                      : 'border-gray-200 bg-white hover:border-blue-300 hover:shadow-md'
                    }
                  `}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="font-semibold text-gray-900">{scenario.scenario_name}</div>
                    <span className={`
                      px-2 py-1 text-xs font-medium rounded border
                      ${getActionBadgeColor(scenario.action)}
                    `}>
                      {scenario.action.toUpperCase()}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="font-medium text-blue-600">{scenario.position}</span>
                    {scenario.opponent_position && (
                      <>
                        <span>vs</span>
                        <span className="font-medium text-orange-600">{scenario.opponent_position}</span>
                      </>
                    )}
                  </div>

                  {scenario.description && (
                    <p className="mt-2 text-xs text-gray-500">{scenario.description}</p>
                  )}
                </button>

                {/* Expanded Details */}
                {selectedScenario?.scenario_id === scenario.scenario_id && (
                  <div className="mt-4 bg-white rounded-lg border-2 border-blue-600 p-6">
                    {detailsLoading ? (
                      <div className="text-center py-8">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        <p className="mt-2 text-sm text-gray-600">Loading range data...</p>
                      </div>
                    ) : selectedScenario.gto_action ? (
                      <div>
                        <div className="mb-4">
                          <h3 className="text-lg font-semibold text-gray-900 mb-2">
                            {selectedScenario.scenario_name}
                          </h3>
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
                          onClick={() => setSelectedScenario(null)}
                          className="mt-4 w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors flex items-center justify-center gap-2"
                        >
                          <X className="w-4 h-4" />
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

        {/* Empty State */}
        {!loading && filteredScenarios.length === 0 && (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <p className="text-gray-600">No scenarios found matching your filters</p>
            <button
              onClick={clearFilters}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Clear Filters
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default GTOBrowser;
