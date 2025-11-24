import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Calendar, Clock, TrendingUp, TrendingDown, Target, History, MessageSquare, FileText } from 'lucide-react';

interface Session {
  session_id: number;
  player_name: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  total_hands: number;
  profit_loss_bb: number;
  bb_100: number;
  table_stakes: string;
  table_name?: string;
  notes?: string;
  tags?: string[];
}

interface SessionStats {
  session_id: number;
  player_name: string;
  total_hands: number;
  profit_loss_bb: number;
  bb_100: number;
  duration_minutes: number;
  vpip_pct: number;
  pfr_pct: number;
  three_bet_pct: number;
  fold_to_3bet_pct: number;
  saw_flop_pct: number;
  cbet_flop_pct: number;
}

interface Hand {
  hand_id: number;
  player_name: string;
  position: string;
  hole_cards?: string;
  profit_loss: number;
  timestamp: string;
  table_name: string;
}

type TabType = 'overview' | 'gto' | 'hands' | 'claude' | 'notes';

const SessionDetail: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [session, setSession] = useState<Session | null>(null);
  const [stats, setStats] = useState<SessionStats | null>(null);
  const [hands, setHands] = useState<Hand[]>([]);
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState('');
  const [savingNotes, setSavingNotes] = useState(false);

  useEffect(() => {
    if (sessionId) {
      fetchSessionData();
    }
  }, [sessionId]);

  const fetchSessionData = async () => {
    setLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';

      // Fetch session details, stats, and hands in parallel
      const [sessionRes, statsRes, handsRes] = await Promise.all([
        fetch(`${apiUrl}/api/sessions/${sessionId}`),
        fetch(`${apiUrl}/api/sessions/${sessionId}/stats`),
        fetch(`${apiUrl}/api/sessions/${sessionId}/hands`)
      ]);

      const sessionData = await sessionRes.json();
      const statsData = await statsRes.json();
      const handsData = await handsRes.json();

      setSession(sessionData);
      setStats(statsData);
      setHands(handsData.hands);
      setNotes(sessionData.notes || '');
    } catch (error) {
      console.error('Error fetching session data:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveNotes = async () => {
    setSavingNotes(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      await fetch(`${apiUrl}/api/sessions/${sessionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes })
      });
    } catch (error) {
      console.error('Error saving notes:', error);
    } finally {
      setSavingNotes(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!session || !stats) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Session not found</p>
      </div>
    );
  }

  const tabs = [
    { id: 'overview' as TabType, label: 'Overview', icon: Target },
    { id: 'gto' as TabType, label: 'GTO Analysis', icon: TrendingUp },
    { id: 'hands' as TabType, label: 'Hand History', icon: History },
    { id: 'claude' as TabType, label: 'AI Analysis', icon: MessageSquare },
    { id: 'notes' as TabType, label: 'Notes', icon: FileText },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <button
          onClick={() => navigate('/sessions')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Sessions
        </button>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Session Analysis
            </h1>
            <div className="flex items-center gap-4 text-gray-600">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                <span>{formatDate(session.start_time)}</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span>
                  {formatTime(session.start_time)} - {formatTime(session.end_time)}
                </span>
              </div>
              <div className="text-sm">
                Duration: {formatDuration(session.duration_minutes)}
              </div>
            </div>
            <div className="mt-2 flex items-center gap-4 text-sm">
              <span className="text-gray-600">Stakes: <span className="font-medium text-gray-900">{session.table_stakes}</span></span>
              <span className="text-gray-600">Hands: <span className="font-medium text-gray-900">{session.total_hands}</span></span>
              <span className="text-gray-600">Player: <span className="font-medium text-gray-900">{session.player_name}</span></span>
            </div>
          </div>

          <div className="text-right">
            <div className={`text-3xl font-bold ${session.profit_loss_bb >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              <div className="flex items-center gap-2">
                {session.profit_loss_bb >= 0 ? (
                  <TrendingUp className="w-8 h-8" />
                ) : (
                  <TrendingDown className="w-8 h-8" />
                )}
                {session.profit_loss_bb >= 0 ? '+' : ''}{session.profit_loss_bb.toFixed(1)} bb
              </div>
            </div>
            <div className={`text-sm mt-1 ${session.bb_100 >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {session.bb_100 >= 0 ? '+' : ''}{session.bb_100.toFixed(1)} bb/100
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow-sm">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6" aria-label="Tabs">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm
                    ${activeTab === tab.id
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Session Statistics</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-sm text-gray-600">VPIP</div>
                    <div className="text-2xl font-bold text-gray-900">{stats.vpip_pct.toFixed(1)}%</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-sm text-gray-600">PFR</div>
                    <div className="text-2xl font-bold text-gray-900">{stats.pfr_pct.toFixed(1)}%</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-sm text-gray-600">3-Bet %</div>
                    <div className="text-2xl font-bold text-gray-900">{stats.three_bet_pct.toFixed(1)}%</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-sm text-gray-600">Fold to 3-Bet</div>
                    <div className="text-2xl font-bold text-gray-900">{stats.fold_to_3bet_pct.toFixed(1)}%</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-sm text-gray-600">Saw Flop</div>
                    <div className="text-2xl font-bold text-gray-900">{stats.saw_flop_pct.toFixed(1)}%</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-sm text-gray-600">C-Bet Flop</div>
                    <div className="text-2xl font-bold text-gray-900">{stats.cbet_flop_pct.toFixed(1)}%</div>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-gray-600">Total Hands</div>
                      <div className="text-xl font-bold text-gray-900">{stats.total_hands}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Duration</div>
                      <div className="text-xl font-bold text-gray-900">{formatDuration(stats.duration_minutes)}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Profit/Loss</div>
                      <div className={`text-xl font-bold ${stats.profit_loss_bb >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {stats.profit_loss_bb >= 0 ? '+' : ''}{stats.profit_loss_bb.toFixed(1)} bb
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">bb/100</div>
                      <div className={`text-xl font-bold ${stats.bb_100 >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {stats.bb_100 >= 0 ? '+' : ''}{stats.bb_100.toFixed(1)}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* GTO Analysis Tab */}
          {activeTab === 'gto' && (
            <div className="space-y-6">
              <div className="text-center py-12">
                <Target className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">GTO Analysis Coming Soon</h3>
                <p className="text-gray-600">
                  This will show your GTO mistakes, missed exploits, and optimization opportunities.
                </p>
              </div>
            </div>
          )}

          {/* Hand History Tab */}
          {activeTab === 'hands' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Hand History ({hands.length} hands)</h3>
              <div className="space-y-2">
                {hands.map((hand) => (
                  <div
                    key={hand.hand_id}
                    className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div>
                          <span className="text-sm text-gray-600">Position:</span>
                          <span className="ml-2 font-medium text-gray-900">{hand.position}</span>
                        </div>
                        {hand.hole_cards && (
                          <div>
                            <span className="text-sm text-gray-600">Cards:</span>
                            <span className="ml-2 font-mono font-bold text-blue-600">{hand.hole_cards}</span>
                          </div>
                        )}
                        <div className="text-xs text-gray-500">
                          {formatTime(hand.timestamp)}
                        </div>
                      </div>
                      <div className={`text-lg font-bold ${hand.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {hand.profit_loss >= 0 ? '+' : ''}{hand.profit_loss.toFixed(2)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Claude AI Tab */}
          {activeTab === 'claude' && (
            <div className="space-y-6">
              <div className="text-center py-12">
                <MessageSquare className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">AI Analysis Coming Soon</h3>
                <p className="text-gray-600">
                  Chat with Claude AI to analyze your session, discuss strategy, and get personalized insights.
                </p>
              </div>
            </div>
          )}

          {/* Notes Tab */}
          {activeTab === 'notes' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Session Notes</h3>
                <button
                  onClick={saveNotes}
                  disabled={savingNotes}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
                >
                  {savingNotes ? 'Saving...' : 'Save Notes'}
                </button>
              </div>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add notes about this session... (opponents, table dynamics, tilt, strategy adjustments, etc.)"
                className="w-full h-64 px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 resize-none"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SessionDetail;
