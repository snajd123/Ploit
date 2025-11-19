import React, { useState } from 'react';
import { Target, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';

interface GTOMatch {
  solution_id: number;
  scenario_name: string;
  board: string;
  match_type: string;
  confidence: number;
  similarity_score: number;
  category_l1: string;
  category_l2: string;
  category_l3: string;
}

interface GTOBoardMatchProps {
  board: string;
  onMatch?: (matches: GTOMatch[]) => void;
}

const GTOBoardMatch: React.FC<GTOBoardMatchProps> = ({ board, onMatch }) => {
  const [matches, setMatches] = useState<GTOMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [boardCategory, setBoardCategory] = useState<{
    l1: string;
    l2: string;
    l3: string;
  } | null>(null);

  const fetchGTOMatches = async () => {
    if (!board || board.length < 6) {
      setError('Invalid board format');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `http://localhost:8000/api/gto/match?board=${encodeURIComponent(board)}&top_n=5`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch GTO matches');
      }

      const data = await response.json();

      setMatches(data.matches || []);
      setBoardCategory({
        l1: data.board_category_l1,
        l2: data.board_category_l2,
        l3: data.board_category_l3
      });

      if (onMatch) {
        onMatch(data.matches || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch GTO matches');
      setMatches([]);
      setBoardCategory(null);
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 90) return 'text-green-600 bg-green-50 border-green-200';
    if (confidence >= 70) return 'text-blue-600 bg-blue-50 border-blue-200';
    if (confidence >= 50) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-orange-600 bg-orange-50 border-orange-200';
  };

  const getMatchTypeLabel = (matchType: string): string => {
    const labels: Record<string, string> = {
      'exact': 'Exact Match',
      'l3': 'L3 Category Match',
      'l2': 'L2 Category Match',
      'l1': 'L1 Category Match'
    };
    return labels[matchType] || matchType.toUpperCase();
  };

  const getMatchTypeIcon = (matchType: string) => {
    if (matchType === 'exact') return <CheckCircle size={16} className="text-green-600" />;
    if (matchType === 'l3') return <Target size={16} className="text-blue-600" />;
    if (matchType === 'l2') return <TrendingUp size={16} className="text-yellow-600" />;
    return <AlertTriangle size={16} className="text-orange-600" />;
  };

  return (
    <div className="space-y-4">
      {/* Board Input & Search Button */}
      <div className="card">
        <div className="flex items-center space-x-3 mb-4">
          <Target size={24} className="text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">GTO Board Analysis</h3>
        </div>

        <div className="flex space-x-3">
          <input
            type="text"
            value={board}
            readOnly
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 font-mono"
            placeholder="Board (e.g., As8h3c)"
          />
          <button
            onClick={fetchGTOMatches}
            disabled={loading || !board}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Searching...' : 'Find GTO Matches'}
          </button>
        </div>

        {error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}
      </div>

      {/* Board Categorization */}
      {boardCategory && (
        <div className="card bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Board Classification</h4>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <p className="text-xs text-gray-600 mb-1">Level 1 (Broad)</p>
              <p className="text-sm font-medium text-blue-900">{boardCategory.l1}</p>
            </div>
            <div>
              <p className="text-xs text-gray-600 mb-1">Level 2 (Medium)</p>
              <p className="text-sm font-medium text-blue-900">{boardCategory.l2}</p>
            </div>
            <div>
              <p className="text-xs text-gray-600 mb-1">Level 3 (Fine)</p>
              <p className="text-sm font-medium text-blue-900">{boardCategory.l3}</p>
            </div>
          </div>
        </div>
      )}

      {/* Matches List */}
      {matches.length > 0 && (
        <div className="card">
          <h4 className="text-lg font-semibold text-gray-900 mb-4">
            Matching GTO Solutions ({matches.length})
          </h4>

          <div className="space-y-3">
            {matches.map((match, index) => (
              <div
                key={match.solution_id}
                className={`p-4 border rounded-lg transition-all hover:shadow-md ${
                  index === 0 ? 'border-blue-400 bg-blue-50' : 'border-gray-200 bg-white'
                }`}
              >
                {/* Match Header */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      {getMatchTypeIcon(match.match_type)}
                      <span className="font-semibold text-gray-900">{match.scenario_name}</span>
                      {index === 0 && (
                        <span className="text-xs px-2 py-0.5 bg-blue-600 text-white rounded">
                          Best Match
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 font-mono">{match.board}</p>
                  </div>

                  <div className="text-right">
                    <span className={`text-xs px-2 py-1 rounded border font-medium ${getConfidenceColor(match.confidence)}`}>
                      {match.confidence.toFixed(1)}% confidence
                    </span>
                  </div>
                </div>

                {/* Match Details */}
                <div className="grid grid-cols-2 gap-3 mt-3 pt-3 border-t border-gray-200">
                  <div>
                    <p className="text-xs text-gray-600 mb-1">Match Type</p>
                    <p className="text-sm font-medium text-gray-900">
                      {getMatchTypeLabel(match.match_type)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-600 mb-1">Similarity Score</p>
                    <p className="text-sm font-medium text-gray-900">
                      {match.similarity_score.toFixed(1)}%
                    </p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-xs text-gray-600 mb-1">Category</p>
                    <p className="text-sm text-gray-700">{match.category_l3}</p>
                  </div>
                </div>

                {/* Action Button */}
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                    View Full Solution →
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Matches */}
      {!loading && matches.length === 0 && boardCategory && (
        <div className="card text-center py-8">
          <AlertTriangle size={48} className="mx-auto text-gray-400 mb-4" />
          <p className="text-gray-600">No GTO solutions found for this board</p>
          <p className="text-sm text-gray-500 mt-2">
            Try a different board or check if solvers have completed
          </p>
        </div>
      )}
    </div>
  );
};

export default GTOBoardMatch;
