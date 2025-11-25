import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Target, Users, TrendingUp, Lightbulb, Focus, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import PlayerAutocompleteInput from '../components/PlayerAutocompleteInput';

interface OpponentSummary {
  player_name: string;
  player_type: string | null;
  total_hands: number;
  exploitability_index: number | null;
  top_exploits: string[];
  key_stats: Record<string, string>;
}

interface StrategyResponse {
  session_summary: string;
  table_dynamics: string;
  overall_strategy: string;
  opponent_summaries: OpponentSummary[];
  focus_areas: string[];
  quick_tips: string[];
}

const PreGameStrategy = () => {
  const [searchParams] = useSearchParams();
  const [opponentNames, setOpponentNames] = useState('');
  const [heroName, setHeroName] = useState('');
  const [stakes, setStakes] = useState('');
  const [gameType, setGameType] = useState('6-max Cash');

  // Load opponent from URL query parameter
  useEffect(() => {
    const opponentFromUrl = searchParams.get('opponent');
    if (opponentFromUrl) {
      setOpponentNames(prev => {
        // If there are already opponents, append; otherwise set
        if (prev && !prev.includes(opponentFromUrl)) {
          return `${prev}, ${opponentFromUrl}`;
        } else if (!prev) {
          return opponentFromUrl;
        }
        return prev;
      });
    }
  }, [searchParams]);

  // Load saved hero name from localStorage on mount
  useEffect(() => {
    const savedHeroName = localStorage.getItem('poker-hero-name');
    if (savedHeroName) {
      setHeroName(savedHeroName);
    }
  }, []);

  // Save hero name to localStorage when it changes
  useEffect(() => {
    if (heroName) {
      localStorage.setItem('poker-hero-name', heroName);
    }
  }, [heroName]);

  const generateStrategy = useMutation({
    mutationFn: async () => {
      const names = opponentNames
        .split(',')
        .map(n => n.trim())
        .filter(n => n.length > 0);

      if (names.length === 0) {
        throw new Error('Please enter at least one opponent name');
      }

      return api.generatePreGameStrategy({
        opponent_names: names,
        hero_name: heroName || undefined,
        stakes: stakes || undefined,
        game_type: gameType
      });
    }
  });

  const strategy = generateStrategy.data as StrategyResponse | undefined;

  const handleGenerate = () => {
    generateStrategy.mutate();
  };

  const getPlayerTypeColor = (type: string | null) => {
    switch (type) {
      case 'TAG': return 'text-blue-600 bg-blue-100';
      case 'LAG': return 'text-purple-600 bg-purple-100';
      case 'NIT': return 'text-gray-600 bg-gray-100';
      case 'CALLING_STATION': return 'text-green-600 bg-green-100';
      case 'MANIAC': return 'text-red-600 bg-red-100';
      case 'FISH': return 'text-orange-600 bg-orange-100';
      default: return 'text-gray-500 bg-gray-50';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Pre-Game Strategy</h1>
        <p className="text-gray-600 mt-2">
          Prepare for your session with AI-generated strategy tailored to your opponents
        </p>
      </div>

      {/* Input Form */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Session Details</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Opponent Names (comma-separated)
            </label>
            <PlayerAutocompleteInput
              value={opponentNames}
              onChange={setOpponentNames}
              placeholder="Start typing player names..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Start typing to see autocomplete suggestions from your database
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Your Player Name (optional)
            </label>
            <input
              type="text"
              value={heroName}
              onChange={(e) => setHeroName(e.target.value)}
              placeholder="e.g., snajd"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Personalize the strategy based on your playing style and stats
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Stakes (optional)
              </label>
              <input
                type="text"
                value={stakes}
                onChange={(e) => setStakes(e.target.value)}
                placeholder="e.g., NL50, NL100"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Game Type
              </label>
              <select
                value={gameType}
                onChange={(e) => setGameType(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option>6-max Cash</option>
                <option>9-max Cash</option>
                <option>Heads-up Cash</option>
                <option>Tournament</option>
              </select>
            </div>
          </div>

          <button
            onClick={handleGenerate}
            disabled={generateStrategy.isPending || opponentNames.trim().length === 0}
            className="btn-primary w-full md:w-auto"
          >
            {generateStrategy.isPending ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Generating Strategy...
              </>
            ) : (
              <>
                <Target className="w-4 h-4 mr-2" />
                Generate Strategy
              </>
            )}
          </button>

          {generateStrategy.isError && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-900">Error generating strategy</p>
                <p className="text-sm text-red-700 mt-1">
                  {(generateStrategy.error as Error)?.message || 'Please try again'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Strategy Output */}
      {strategy && (
        <div className="space-y-6">
          {/* Session Summary */}
          <div className="card bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
            <div className="flex items-start gap-3">
              <Users className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Session Summary</h3>
                <p className="text-gray-700">{strategy.session_summary}</p>
              </div>
            </div>
          </div>

          {/* Table Dynamics */}
          <div className="card">
            <div className="flex items-start gap-3 mb-4">
              <TrendingUp className="w-6 h-6 text-purple-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Table Dynamics</h3>
              </div>
            </div>
            <p className="text-gray-700">{strategy.table_dynamics}</p>
          </div>

          {/* Overall Strategy */}
          <div className="card">
            <div className="flex items-start gap-3 mb-4">
              <Target className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Overall Strategy</h3>
              </div>
            </div>
            <p className="text-gray-700 whitespace-pre-line">{strategy.overall_strategy}</p>
          </div>

          {/* Opponent Summaries */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Opponent Analysis</h3>
            <div className="space-y-4">
              {strategy.opponent_summaries.map((opponent, idx) => (
                <div
                  key={idx}
                  className="p-4 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h4 className="font-semibold text-gray-900">{opponent.player_name}</h4>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${getPlayerTypeColor(opponent.player_type)}`}>
                          {opponent.player_type || 'UNKNOWN'}
                        </span>
                        <span className="text-sm text-gray-600">
                          {opponent.total_hands.toLocaleString()} hands
                        </span>
                      </div>
                    </div>
                    {opponent.exploitability_index !== null && (
                      <div className="text-right">
                        <div className="text-2xl font-bold text-gray-900">
                          {opponent.exploitability_index.toFixed(0)}
                        </div>
                        <div className="text-xs text-gray-600">Exploit Score</div>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
                    {Object.entries(opponent.key_stats).map(([stat, value]) => (
                      <div key={stat} className="text-center p-2 bg-white rounded">
                        <div className="text-xs text-gray-600">{stat}</div>
                        <div className="text-sm font-semibold text-gray-900">{value}</div>
                      </div>
                    ))}
                  </div>

                  <div>
                    <p className="text-xs font-medium text-gray-700 mb-2">Top Exploits:</p>
                    <ul className="space-y-1">
                      {opponent.top_exploits.map((exploit, i) => (
                        <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                          <span className="text-red-600 flex-shrink-0">•</span>
                          <span>{exploit}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Focus Areas */}
          <div className="card">
            <div className="flex items-start gap-3 mb-4">
              <Focus className="w-6 h-6 text-orange-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Focus Areas</h3>
              </div>
            </div>
            <ul className="space-y-2">
              {strategy.focus_areas.map((area, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-sm font-semibold">
                    {idx + 1}
                  </span>
                  <span className="text-gray-700 pt-0.5">{area}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Quick Tips */}
          <div className="card bg-gradient-to-br from-yellow-50 to-amber-50 border-yellow-200">
            <div className="flex items-start gap-3 mb-4">
              <Lightbulb className="w-6 h-6 text-yellow-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Quick Tips</h3>
              </div>
            </div>
            <ul className="space-y-2">
              {strategy.quick_tips.map((tip, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-yellow-600 flex-shrink-0">💡</span>
                  <span className="text-gray-700">{tip}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default PreGameStrategy;
