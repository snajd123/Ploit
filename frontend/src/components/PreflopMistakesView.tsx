import React, { useState, useEffect } from 'react';
import { AlertTriangle, XCircle, AlertCircle, Loader2, ExternalLink, ArrowRight } from 'lucide-react';
import type { PreflopMistakesResponse, PreflopMistake } from '../types';
import { api } from '../services/api';

interface PreflopMistakesViewProps {
  sessionId: number;
  onHandClick?: (handId: number) => void;
}

// Severity badge component
const SeverityBadge: React.FC<{ severity: string }> = ({ severity }) => {
  const config: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    major: { bg: 'bg-red-100', text: 'text-red-700', icon: <XCircle size={12} /> },
    moderate: { bg: 'bg-orange-100', text: 'text-orange-700', icon: <AlertTriangle size={12} /> },
    minor: { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: <AlertCircle size={12} /> }
  };

  const { bg, text, icon } = config[severity] || config.minor;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${bg} ${text}`}>
      {icon}
      {severity.toUpperCase()}
    </span>
  );
};

// Card suit/rank styling
const formatHoleCards = (cards: string): React.ReactNode => {
  if (!cards || cards.length < 4) return cards;

  const getSuitColor = (suit: string): string => {
    switch (suit.toLowerCase()) {
      case 'h': return 'text-red-600';
      case 'd': return 'text-blue-600';
      case 'c': return 'text-green-700';
      case 's': return 'text-gray-800';
      default: return 'text-gray-800';
    }
  };

  const getSuitSymbol = (suit: string): string => {
    switch (suit.toLowerCase()) {
      case 'h': return '\u2665'; // hearts
      case 'd': return '\u2666'; // diamonds
      case 'c': return '\u2663'; // clubs
      case 's': return '\u2660'; // spades
      default: return suit;
    }
  };

  // Parse "AhKd" format
  const card1Rank = cards[0];
  const card1Suit = cards[1];
  const card2Rank = cards[2];
  const card2Suit = cards[3];

  return (
    <span className="font-mono font-bold">
      <span className={getSuitColor(card1Suit)}>{card1Rank}{getSuitSymbol(card1Suit)}</span>
      <span className={getSuitColor(card2Suit)}>{card2Rank}{getSuitSymbol(card2Suit)}</span>
    </span>
  );
};

// Mistake card component
const MistakeCard: React.FC<{ mistake: PreflopMistake; rank: number; onHandClick?: (handId: number) => void }> = ({
  mistake,
  rank,
  onHandClick
}) => {
  return (
    <div className="p-4 rounded-lg border border-gray-200 bg-white hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-4">
        {/* Rank and severity */}
        <div className="flex items-center gap-3">
          <span className="flex items-center justify-center w-7 h-7 rounded-full bg-gray-100 text-gray-600 font-bold text-sm">
            {rank}
          </span>
          <div>
            <div className="flex items-center gap-2 mb-1">
              {formatHoleCards(mistake.hole_cards)}
              <span className="text-gray-400">in</span>
              <span className="font-medium text-gray-700">{mistake.position}</span>
              <SeverityBadge severity={mistake.severity} />
            </div>
            <div className="text-sm text-gray-600">{mistake.scenario}</div>
          </div>
        </div>

        {/* EV loss */}
        <div className="text-right flex-shrink-0">
          <div className="text-lg font-bold text-red-600">
            -{mistake.ev_loss_bb.toFixed(2)} bb
          </div>
          <div className="text-xs text-gray-500">EV loss</div>
        </div>
      </div>

      {/* Action comparison */}
      <div className="mt-3 flex items-center gap-2 text-sm">
        <span className="px-2 py-1 rounded bg-red-50 text-red-700 font-medium">
          {mistake.action_taken}
        </span>
        <ArrowRight size={14} className="text-gray-400" />
        <span className="px-2 py-1 rounded bg-green-50 text-green-700 font-medium">
          {mistake.gto_action} ({(mistake.gto_frequency * 100).toFixed(0)}%)
        </span>
        {!mistake.in_gto_range && (
          <span className="text-xs text-orange-600 bg-orange-50 px-2 py-1 rounded">
            Outside GTO range
          </span>
        )}
      </div>

      {/* Description */}
      <p className="mt-2 text-sm text-gray-600">{mistake.description}</p>

      {/* View hand button */}
      {onHandClick && (
        <button
          onClick={() => onHandClick(mistake.hand_id)}
          className="mt-3 flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
        >
          <ExternalLink size={12} />
          View hand replay
        </button>
      )}
    </div>
  );
};

const PreflopMistakesView: React.FC<PreflopMistakesViewProps> = ({ sessionId, onHandClick }) => {
  const [data, setData] = useState<PreflopMistakesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await api.getSessionPreflopMistakes(sessionId, 10);
        setData(result);
      } catch (err) {
        console.error('Error fetching preflop mistakes:', err);
        setError('Failed to load preflop mistakes');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="animate-spin text-blue-600 mr-2" size={20} />
        <span className="text-gray-600">Analyzing preflop decisions...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-8">
        <AlertCircle className="mx-auto mb-2 text-red-500" size={32} />
        <p className="text-red-600">{error || 'No data available'}</p>
      </div>
    );
  }

  if (data.mistakes.length === 0) {
    return (
      <div className="text-center py-8 bg-green-50 rounded-lg border border-green-200">
        <div className="text-3xl mb-2">No preflop mistakes found</div>
        <p className="text-green-700 font-medium">Great session! No significant GTO deviations detected.</p>
        <p className="text-sm text-green-600 mt-1">
          (Requires hands with visible hole cards for analysis)
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary header */}
      <div className="flex items-center justify-between p-4 bg-gradient-to-r from-red-50 to-white rounded-lg border border-red-200">
        <div>
          <h3 className="font-semibold text-gray-900">Biggest Preflop Mistakes</h3>
          <p className="text-sm text-gray-500 mt-1">
            GTO deviations ranked by estimated EV loss
          </p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-red-600">
            -{data.total_ev_loss_bb.toFixed(1)} bb
          </div>
          <div className="text-xs text-gray-500">
            {data.total_mistakes} mistakes
          </div>
        </div>
      </div>

      {/* Severity breakdown */}
      <div className="flex items-center gap-4 text-sm">
        {data.mistakes_by_severity.major !== undefined && data.mistakes_by_severity.major > 0 && (
          <span className="flex items-center gap-1">
            <XCircle size={14} className="text-red-600" />
            <span className="text-gray-600">
              <span className="font-medium text-gray-900">{data.mistakes_by_severity.major}</span> major
            </span>
          </span>
        )}
        {data.mistakes_by_severity.moderate !== undefined && data.mistakes_by_severity.moderate > 0 && (
          <span className="flex items-center gap-1">
            <AlertTriangle size={14} className="text-orange-600" />
            <span className="text-gray-600">
              <span className="font-medium text-gray-900">{data.mistakes_by_severity.moderate}</span> moderate
            </span>
          </span>
        )}
        {data.mistakes_by_severity.minor !== undefined && data.mistakes_by_severity.minor > 0 && (
          <span className="flex items-center gap-1">
            <AlertCircle size={14} className="text-yellow-600" />
            <span className="text-gray-600">
              <span className="font-medium text-gray-900">{data.mistakes_by_severity.minor}</span> minor
            </span>
          </span>
        )}
      </div>

      {/* Mistakes list */}
      <div className="space-y-3">
        {data.mistakes.map((mistake, index) => (
          <MistakeCard
            key={mistake.hand_id}
            mistake={mistake}
            rank={index + 1}
            onHandClick={onHandClick}
          />
        ))}
      </div>

      {/* Note about analysis */}
      <p className="text-xs text-gray-400 text-center">
        Analysis based on GTO solver frequencies for standard 100bb cash game spots.
        Actual EV loss may vary based on opponent tendencies.
      </p>
    </div>
  );
};

export default PreflopMistakesView;
