import React, { useState, useMemo } from 'react';
import { X, ChevronLeft, ChevronRight, Play, Pause, SkipBack, SkipForward, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import type { HandReplayResponse, HandReplayAction } from '../types';

interface HandReplayModalProps {
  data: HandReplayResponse;
  onClose: () => void;
}

// Card display component
const Card: React.FC<{ card: string; size?: 'sm' | 'md' | 'lg' }> = ({ card, size = 'md' }) => {
  const suit = card.slice(-1);
  const rank = card.slice(0, -1);

  const suitColors: Record<string, string> = {
    'h': 'text-red-600',
    'd': 'text-blue-600',
    'c': 'text-green-700',
    's': 'text-gray-900',
  };

  const suitSymbols: Record<string, string> = {
    'h': '\u2665',
    'd': '\u2666',
    'c': '\u2663',
    's': '\u2660',
  };

  const sizeClasses = {
    sm: 'w-6 h-8 text-xs',
    md: 'w-8 h-11 text-sm',
    lg: 'w-10 h-14 text-base',
  };

  return (
    <div className={`${sizeClasses[size]} bg-white rounded border border-gray-300 shadow-sm flex flex-col items-center justify-center font-bold ${suitColors[suit] || 'text-gray-900'}`}>
      <span>{rank}</span>
      <span className="text-xs">{suitSymbols[suit] || suit}</span>
    </div>
  );
};

// Empty card placeholder
const EmptyCard: React.FC<{ size?: 'sm' | 'md' | 'lg' }> = ({ size = 'md' }) => {
  const sizeClasses = {
    sm: 'w-6 h-8',
    md: 'w-8 h-11',
    lg: 'w-10 h-14',
  };

  return (
    <div className={`${sizeClasses[size]} bg-gray-200 rounded border border-gray-300 border-dashed`} />
  );
};

// Street tab component
const StreetTab: React.FC<{
  street: string;
  isActive: boolean;
  isAvailable: boolean;
  onClick: () => void;
}> = ({ street, isActive, isAvailable, onClick }) => {
  const labels: Record<string, string> = {
    preflop: 'Preflop',
    flop: 'Flop',
    turn: 'Turn',
    river: 'River',
  };

  return (
    <button
      onClick={onClick}
      disabled={!isAvailable}
      className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
        isActive
          ? 'bg-white text-blue-600 border-t border-l border-r border-gray-200'
          : isAvailable
          ? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          : 'bg-gray-50 text-gray-400 cursor-not-allowed'
      }`}
    >
      {labels[street] || street}
    </button>
  );
};

// Action row component
const ActionRow: React.FC<{
  action: HandReplayAction;
  isHero: boolean;
  heroName: string | null;
  position?: string | null;
  isHighlighted: boolean;
}> = ({ action, isHero, position, isHighlighted }) => {
  const actionColors: Record<string, string> = {
    fold: 'text-gray-600 bg-gray-100',
    check: 'text-gray-700 bg-gray-100',
    call: 'text-green-700 bg-green-100',
    bet: 'text-blue-700 bg-blue-100',
    raise: 'text-orange-700 bg-orange-100',
    'all-in': 'text-red-700 bg-red-100',
    post_sb: 'text-gray-500 bg-gray-50',
    post_bb: 'text-gray-500 bg-gray-50',
  };

  const formatAction = (a: HandReplayAction) => {
    if (a.action === 'fold') return 'folds';
    if (a.action === 'check') return 'checks';
    if (a.action === 'call') return `calls ${a.amount_bb}bb`;
    if (a.action === 'bet') return `bets ${a.amount_bb}bb`;
    if (a.action === 'raise') return `raises to ${a.amount_bb}bb`;
    if (a.action === 'all-in') return `all-in ${a.amount_bb}bb`;
    if (a.action === 'post_sb') return `posts SB ${a.amount_bb}bb`;
    if (a.action === 'post_bb') return `posts BB ${a.amount_bb}bb`;
    return a.action;
  };

  return (
    <div className={`flex items-center gap-3 py-1.5 px-2 rounded ${
      isHighlighted ? 'bg-yellow-100 ring-2 ring-yellow-400' : ''
    } ${isHero ? 'bg-blue-50' : ''}`}>
      <div className="w-20 flex items-center gap-1">
        {position && (
          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
            isHero ? 'bg-blue-200 text-blue-800' : 'bg-gray-200 text-gray-700'
          }`}>
            {position}
          </span>
        )}
      </div>
      <div className="flex-1">
        <span className={`font-medium ${isHero ? 'text-blue-700' : 'text-gray-700'}`}>
          {action.player}
        </span>
        <span className={`ml-2 px-2 py-0.5 rounded text-xs font-medium ${actionColors[action.action] || 'bg-gray-100'}`}>
          {formatAction(action)}
        </span>
        {action.is_all_in && (
          <span className="ml-1 px-1.5 py-0.5 rounded text-xs font-bold bg-red-600 text-white">
            ALL-IN
          </span>
        )}
      </div>
      <div className="text-right text-xs text-gray-500 w-24">
        Pot: {action.pot_after_bb}bb
      </div>
    </div>
  );
};

const HandReplayModal: React.FC<HandReplayModalProps> = ({ data, onClose }) => {
  const streetOrder = ['preflop', 'flop', 'turn', 'river'];
  const availableStreets = streetOrder.filter(s => data.streets[s]);

  const [currentStreet, setCurrentStreet] = useState(availableStreets[0] || 'preflop');
  const [currentActionIndex, setCurrentActionIndex] = useState(-1); // -1 means show all
  const [isPlaying, setIsPlaying] = useState(false);

  // Get player positions map
  const playerPositions = useMemo(() => {
    const map: Record<string, string | null> = {};
    data.players.forEach(p => {
      map[p.name] = p.position;
    });
    return map;
  }, [data.players]);

  // Current street data
  const streetData = data.streets[currentStreet];
  const streetActions = streetData?.actions || [];

  // Board cards up to current street
  const visibleBoard = useMemo(() => {
    const board: string[] = [];
    const streetIdx = streetOrder.indexOf(currentStreet);

    for (let i = 0; i <= streetIdx; i++) {
      const s = streetOrder[i];
      if (data.streets[s]?.board) {
        board.push(...data.streets[s].board!);
      }
    }
    return board;
  }, [currentStreet, data.streets]);

  // Visible actions based on playback
  const visibleActions = currentActionIndex === -1
    ? streetActions
    : streetActions.slice(0, currentActionIndex + 1);

  // Current pot (from last visible action or 0)
  const currentPot = visibleActions.length > 0
    ? visibleActions[visibleActions.length - 1].pot_after_bb
    : streetActions.length > 0
    ? streetActions[0].pot_before_bb
    : 0;

  // Hero result
  const heroResult = data.hero ? data.results[data.hero] : null;

  // Find hero's hole cards
  const heroCards = data.players.find(p => p.is_hero)?.hole_cards?.split(' ') || [];

  // Navigation functions
  const goToStreet = (street: string) => {
    setCurrentStreet(street);
    setCurrentActionIndex(-1);
  };

  const nextAction = () => {
    if (currentActionIndex < streetActions.length - 1) {
      setCurrentActionIndex(prev => prev + 1);
    } else {
      // Move to next street
      const currentIdx = availableStreets.indexOf(currentStreet);
      if (currentIdx < availableStreets.length - 1) {
        setCurrentStreet(availableStreets[currentIdx + 1]);
        setCurrentActionIndex(0);
      }
    }
  };

  const prevAction = () => {
    if (currentActionIndex > 0) {
      setCurrentActionIndex(prev => prev - 1);
    } else if (currentActionIndex === 0) {
      // Move to previous street
      const currentIdx = availableStreets.indexOf(currentStreet);
      if (currentIdx > 0) {
        const prevStreet = availableStreets[currentIdx - 1];
        setCurrentStreet(prevStreet);
        setCurrentActionIndex((data.streets[prevStreet]?.actions.length || 1) - 1);
      }
    } else {
      // From "show all" (-1), go to last action
      setCurrentActionIndex(streetActions.length - 1);
    }
  };

  const goToStart = () => {
    setCurrentStreet(availableStreets[0]);
    setCurrentActionIndex(0);
  };

  const goToEnd = () => {
    setCurrentStreet(availableStreets[availableStreets.length - 1]);
    setCurrentActionIndex(-1);
  };

  // Playback timer
  React.useEffect(() => {
    if (!isPlaying) return;

    const timer = setInterval(() => {
      if (currentActionIndex === -1) {
        setCurrentActionIndex(0);
      } else if (currentActionIndex < streetActions.length - 1) {
        setCurrentActionIndex(prev => prev + 1);
      } else {
        const currentIdx = availableStreets.indexOf(currentStreet);
        if (currentIdx < availableStreets.length - 1) {
          setCurrentStreet(availableStreets[currentIdx + 1]);
          setCurrentActionIndex(0);
        } else {
          setIsPlaying(false);
        }
      }
    }, 800);

    return () => clearInterval(timer);
  }, [isPlaying, currentActionIndex, currentStreet, streetActions.length, availableStreets]);

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-emerald-600 to-teal-600 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">
              Hand #{data.hand_id}
            </h2>
            <p className="text-emerald-100 text-sm">
              {data.stake_level} | {data.table_name}
              {data.timestamp && ` | ${new Date(data.timestamp).toLocaleString()}`}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Hero Cards & Board */}
        <div className="bg-gradient-to-b from-green-800 to-green-900 px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Hero Cards */}
            <div className="flex flex-col items-center">
              <span className="text-green-300 text-xs mb-1">Your Hand</span>
              <div className="flex gap-1">
                {heroCards.length > 0 ? (
                  heroCards.map((card, i) => <Card key={i} card={card} size="lg" />)
                ) : (
                  <>
                    <EmptyCard size="lg" />
                    <EmptyCard size="lg" />
                  </>
                )}
              </div>
            </div>

            {/* Board */}
            <div className="flex flex-col items-center">
              <span className="text-green-300 text-xs mb-1">Board</span>
              <div className="flex gap-1">
                {[0, 1, 2, 3, 4].map(i => (
                  visibleBoard[i] ? (
                    <Card key={i} card={visibleBoard[i]} size="lg" />
                  ) : (
                    <EmptyCard key={i} size="lg" />
                  )
                ))}
              </div>
            </div>

            {/* Pot */}
            <div className="flex flex-col items-center">
              <span className="text-green-300 text-xs mb-1">Pot</span>
              <div className="bg-yellow-400 text-yellow-900 px-4 py-2 rounded-lg font-bold text-lg">
                {currentPot}bb
              </div>
            </div>
          </div>
        </div>

        {/* Street Tabs */}
        <div className="bg-gray-100 px-4 pt-2 flex gap-1 border-b border-gray-200">
          {streetOrder.map(street => (
            <StreetTab
              key={street}
              street={street}
              isActive={currentStreet === street}
              isAvailable={availableStreets.includes(street)}
              onClick={() => goToStreet(street)}
            />
          ))}
        </div>

        {/* GTO Analysis Panel (Preflop only) */}
        {currentStreet === 'preflop' && data.hero_gto_analysis && (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-4 py-3 border-b border-blue-200">
            <div className="flex items-start justify-between gap-4">
              {/* Hero's Action Assessment */}
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${
                  data.hero_gto_analysis.deviation_type === 'correct' ? 'bg-green-100' :
                  data.hero_gto_analysis.deviation_type === 'suboptimal' ? 'bg-yellow-100' : 'bg-red-100'
                }`}>
                  {data.hero_gto_analysis.deviation_type === 'correct' && <CheckCircle className="text-green-600" size={20} />}
                  {data.hero_gto_analysis.deviation_type === 'suboptimal' && <AlertTriangle className="text-yellow-600" size={20} />}
                  {data.hero_gto_analysis.deviation_type === 'mistake' && <XCircle className="text-red-600" size={20} />}
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-800">
                    Hero {data.hero_gto_analysis.hero_action}
                    {data.hero_gto_analysis.vs_position && (
                      <span className="text-gray-500 ml-1">vs {data.hero_gto_analysis.vs_position}</span>
                    )}
                  </div>
                  <div className={`text-xs ${
                    data.hero_gto_analysis.deviation_type === 'correct' ? 'text-green-600' :
                    data.hero_gto_analysis.deviation_type === 'suboptimal' ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {data.hero_gto_analysis.deviation_description}
                  </div>
                </div>
              </div>

              {/* GTO Frequencies */}
              <div className="flex items-center gap-3">
                <div className="text-xs text-gray-500">GTO:</div>
                {Object.entries(data.hero_gto_analysis.gto_frequencies)
                  .sort((a, b) => b[1] - a[1])
                  .map(([action, freq]) => (
                    <div
                      key={action}
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        action === data.hero_gto_analysis?.hero_action
                          ? data.hero_gto_analysis.deviation_type === 'correct'
                            ? 'bg-green-200 text-green-800 ring-2 ring-green-400'
                            : data.hero_gto_analysis.deviation_type === 'suboptimal'
                            ? 'bg-yellow-200 text-yellow-800 ring-2 ring-yellow-400'
                            : 'bg-red-200 text-red-800 ring-2 ring-red-400'
                          : 'bg-gray-200 text-gray-700'
                      }`}
                    >
                      {action}: {freq}%
                    </div>
                  ))}
              </div>
            </div>
          </div>
        )}

        {/* Actions List */}
        <div className="flex-1 overflow-y-auto p-4 bg-white">
          <div className="space-y-1">
            {streetActions.map((action, idx) => (
              <ActionRow
                key={idx}
                action={action}
                isHero={action.player === data.hero}
                heroName={data.hero}
                position={playerPositions[action.player]}
                isHighlighted={currentActionIndex !== -1 && idx === currentActionIndex}
              />
            ))}
            {streetActions.length === 0 && (
              <div className="text-center text-gray-500 py-8">
                No actions on this street
              </div>
            )}
          </div>
        </div>

        {/* Playback Controls */}
        <div className="border-t border-gray-200 px-6 py-3 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={goToStart}
                className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
                title="Go to start"
              >
                <SkipBack size={18} />
              </button>
              <button
                onClick={prevAction}
                className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
                title="Previous action"
              >
                <ChevronLeft size={18} />
              </button>
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className={`p-2 rounded-lg transition-colors ${
                  isPlaying ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-200'
                }`}
                title={isPlaying ? 'Pause' : 'Play'}
              >
                {isPlaying ? <Pause size={18} /> : <Play size={18} />}
              </button>
              <button
                onClick={nextAction}
                className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
                title="Next action"
              >
                <ChevronRight size={18} />
              </button>
              <button
                onClick={goToEnd}
                className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
                title="Go to end"
              >
                <SkipForward size={18} />
              </button>
            </div>

            {/* Result */}
            {heroResult && (
              <div className={`px-4 py-2 rounded-lg font-medium ${
                heroResult.profit_loss_bb > 0
                  ? 'bg-green-100 text-green-700'
                  : heroResult.profit_loss_bb < 0
                  ? 'bg-red-100 text-red-700'
                  : 'bg-gray-100 text-gray-700'
              }`}>
                {heroResult.profit_loss_bb > 0 ? '+' : ''}{heroResult.profit_loss_bb}bb
                {heroResult.showdown && ' (showdown)'}
              </div>
            )}

            <div className="text-sm text-gray-500">
              {currentActionIndex === -1
                ? `${streetActions.length} actions`
                : `${currentActionIndex + 1} / ${streetActions.length}`}
            </div>
          </div>
        </div>

        {/* Keyboard shortcuts hint */}
        <div className="px-6 py-2 bg-gray-100 border-t border-gray-200 text-xs text-gray-500">
          Keyboard: <span className="font-mono">←/→</span> navigate actions | <span className="font-mono">1-4</span> jump to street | <span className="font-mono">Space</span> play/pause
        </div>
      </div>
    </div>
  );
};

export default HandReplayModal;
