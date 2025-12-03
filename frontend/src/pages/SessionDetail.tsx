import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Calendar, Clock, TrendingUp, TrendingDown, Target, History, MessageSquare, FileText, Crosshair, BarChart3, Play, Loader2 } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import LeakProgressView from '../components/LeakProgressView';
import HandReplayModal from '../components/HandReplayModal';
import { api } from '../services/api';
import type { HandReplayResponse } from '../types';

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
  wtsd_pct: number;
  won_at_sd_pct: number;
}

interface GTOAnalysis {
  session_id: number;
  total_mistakes: number;
  total_ev_loss_bb: number;
  mistakes_by_street: Record<string, number>;
  mistakes_by_severity: Record<string, number>;
  biggest_mistakes: Array<{
    hand_id: number;
    street: string;
    hero_hand: string;
    action_taken: string;
    gto_action: string;
    ev_loss_bb: number;
    mistake_severity: string;
    opponents?: string;
    gto_frequency?: number;
    timestamp?: string;
    position?: string;
    scenario?: string;
  }>;
}

interface OpponentAnalysis {
  session_id: number;
  opponents_analyzed: number;
  opponents: Array<{
    opponent_name: string;
    hands_observed: number;
    vpip_pct: number;
    pfr_pct: number;
    three_bet_pct: number;
    tendencies: Record<string, string>;
    exploits: Array<{
      exploit_type: string;
      description: string;
      estimated_ev_gain_bb: number;
      priority: string;
    }>;
  }>;
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

type TabType = 'overview' | 'gto' | 'leaks' | 'hands' | 'claude' | 'notes';

const SessionDetail: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [session, setSession] = useState<Session | null>(null);
  const [stats, setStats] = useState<SessionStats | null>(null);
  const [hands, setHands] = useState<Hand[]>([]);
  const [gtoAnalysis, setGtoAnalysis] = useState<GTOAnalysis | null>(null);
  const [opponentAnalysis, setOpponentAnalysis] = useState<OpponentAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState('');
  const [savingNotes, setSavingNotes] = useState(false);
  const [selectedHandId, setSelectedHandId] = useState<number | null>(null);
  const [replayData, setReplayData] = useState<HandReplayResponse | null>(null);
  const [loadingReplay, setLoadingReplay] = useState(false);

  useEffect(() => {
    if (sessionId) {
      fetchSessionData();
    }
  }, [sessionId]);

  const fetchSessionData = async () => {
    setLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';

      console.log('Fetching session data for ID:', sessionId);

      // Fetch session details, stats, hands, GTO analysis, and opponent analysis in parallel
      const [sessionRes, statsRes, handsRes, gtoRes, opponentsRes] = await Promise.all([
        fetch(`${apiUrl}/api/sessions/${sessionId}`),
        fetch(`${apiUrl}/api/sessions/${sessionId}/stats`),
        fetch(`${apiUrl}/api/sessions/${sessionId}/hands`),
        fetch(`${apiUrl}/api/sessions/${sessionId}/gto-analysis`),
        fetch(`${apiUrl}/api/sessions/${sessionId}/opponents`)
      ]);

      console.log('Response statuses:', {
        session: sessionRes.status,
        stats: statsRes.status,
        hands: handsRes.status,
        gto: gtoRes.status,
        opponents: opponentsRes.status
      });

      if (!sessionRes.ok || !statsRes.ok || !handsRes.ok) {
        throw new Error(`HTTP errors - session: ${sessionRes.status}, stats: ${statsRes.status}, hands: ${handsRes.status}`);
      }

      const sessionData = await sessionRes.json();
      const statsData = await statsRes.json();
      const handsData = await handsRes.json();
      const gtoData = gtoRes.ok ? await gtoRes.json() : null;
      const opponentsData = opponentsRes.ok ? await opponentsRes.json() : null;

      console.log('Fetched data:', { sessionData, statsData, handsData, gtoData, opponentsData });

      setSession(sessionData);
      setStats(statsData);
      setHands(handsData.hands);
      setGtoAnalysis(gtoData);
      setOpponentAnalysis(opponentsData);
      setNotes(sessionData.notes || '');
    } catch (error) {
      console.error('Error fetching session data:', error);
      alert(`Error loading session: ${error}`);
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

  const openHandReplay = async (handId: number) => {
    setSelectedHandId(handId);
    setLoadingReplay(true);
    try {
      const data = await api.getHandReplay(handId);
      setReplayData(data);
    } catch (error) {
      console.error('Error fetching hand replay:', error);
      alert('Failed to load hand replay');
      setSelectedHandId(null);
    } finally {
      setLoadingReplay(false);
    }
  };

  const closeHandReplay = () => {
    setSelectedHandId(null);
    setReplayData(null);
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
    { id: 'leaks' as TabType, label: 'Leak Progress', icon: BarChart3 },
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
                    <div className="text-sm text-gray-600">WTSD%</div>
                    <div className="text-2xl font-bold text-gray-900">{stats.wtsd_pct.toFixed(1)}%</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-sm text-gray-600">W$SD%</div>
                    <div className="text-2xl font-bold text-gray-900">{stats.won_at_sd_pct.toFixed(1)}%</div>
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
              {gtoAnalysis && (
                <>
                  {/* Hero Mistakes Summary */}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Your GTO Mistakes</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                      <div className="bg-red-50 rounded-lg p-4">
                        <div className="text-sm text-red-600">Total Mistakes</div>
                        <div className="text-2xl font-bold text-red-700">{gtoAnalysis.total_mistakes}</div>
                      </div>
                      <div className="bg-red-50 rounded-lg p-4">
                        <div className="text-sm text-red-600">Total EV Loss</div>
                        <div className="text-2xl font-bold text-red-700">{gtoAnalysis.total_ev_loss_bb.toFixed(2)} bb</div>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="text-sm text-gray-600">Cost per Hand</div>
                        <div className="text-2xl font-bold text-gray-900">
                          {(gtoAnalysis.total_ev_loss_bb / (session?.total_hands || 1)).toFixed(2)} bb/hand
                        </div>
                      </div>
                    </div>

                    {/* Biggest Mistakes */}
                    {gtoAnalysis.biggest_mistakes && gtoAnalysis.biggest_mistakes.length > 0 && (
                      <div className="bg-white border border-gray-200 rounded-lg p-4">
                        <h4 className="font-semibold text-gray-900 mb-3">Biggest Mistakes</h4>
                        <div className="space-y-2">
                          {gtoAnalysis.biggest_mistakes.map((mistake, idx) => (
                            <div key={idx} className="p-3 bg-gray-50 rounded">
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-3">
                                  <span className="font-mono font-bold text-blue-600">{mistake.hero_hand}</span>
                                  {mistake.scenario && (
                                    <span className="text-sm font-medium text-purple-600 bg-purple-50 px-2 py-0.5 rounded">
                                      {mistake.scenario}
                                    </span>
                                  )}
                                  <span className="text-sm text-gray-600">{mistake.street}</span>
                                  <span className="text-sm">
                                    <span className="text-red-600">{mistake.action_taken}</span>
                                    {' → should '}
                                    <span className="text-green-600">{mistake.gto_action}</span>
                                  </span>
                                </div>
                                <div className="text-red-600 font-semibold">-{mistake.ev_loss_bb.toFixed(2)} bb</div>
                              </div>
                              {mistake.opponents && (
                                <div className="flex items-center gap-2 text-xs text-gray-500">
                                  <span>vs:</span>
                                  <span className="font-medium">{mistake.opponents}</span>
                                  {mistake.gto_frequency !== undefined && (
                                    <>
                                      <span className="mx-1">•</span>
                                      <span>GTO freq: {(mistake.gto_frequency * 100).toFixed(1)}%</span>
                                    </>
                                  )}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Mistake Visualizations */}
                    {gtoAnalysis.total_mistakes > 0 && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                        {/* Mistakes by Severity */}
                        <div className="bg-white border border-gray-200 rounded-lg p-4">
                          <h4 className="font-semibold text-gray-900 mb-3">Mistakes by Severity</h4>
                          <ResponsiveContainer width="100%" height={250}>
                            <PieChart>
                              <Pie
                                data={Object.entries(gtoAnalysis.mistakes_by_severity).map(([severity, count]) => ({
                                  name: severity.charAt(0).toUpperCase() + severity.slice(1),
                                  value: count
                                }))}
                                cx="50%"
                                cy="50%"
                                labelLine={false}
                                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                outerRadius={80}
                                fill="#8884d8"
                                dataKey="value"
                              >
                                {Object.keys(gtoAnalysis.mistakes_by_severity).map((severity, index) => (
                                  <Cell
                                    key={`cell-${index}`}
                                    fill={severity === 'major' ? '#DC2626' : severity === 'moderate' ? '#F59E0B' : '#6B7280'}
                                  />
                                ))}
                              </Pie>
                              <Tooltip />
                              <Legend />
                            </PieChart>
                          </ResponsiveContainer>
                        </div>

                        {/* Mistakes by Street */}
                        <div className="bg-white border border-gray-200 rounded-lg p-4">
                          <h4 className="font-semibold text-gray-900 mb-3">Mistakes by Street</h4>
                          <ResponsiveContainer width="100%" height={250}>
                            <BarChart
                              data={Object.entries(gtoAnalysis.mistakes_by_street).map(([street, count]) => ({
                                street: street.charAt(0).toUpperCase() + street.slice(1),
                                count: count
                              }))}
                              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                            >
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis dataKey="street" />
                              <YAxis />
                              <Tooltip />
                              <Bar dataKey="count" fill="#3B82F6" />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Opponent Exploits */}
                  {opponentAnalysis && opponentAnalysis.opponents && opponentAnalysis.opponents.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Opponent Tendencies & Exploits</h3>
                      <div className="space-y-4">
                        {opponentAnalysis.opponents.map((opp, idx) => (
                          <div key={idx} className="bg-white border border-gray-200 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-3">
                              <div>
                                <h4 className="font-semibold text-gray-900">{opp.opponent_name}</h4>
                                <p className="text-sm text-gray-500">{opp.hands_observed} hands observed</p>
                              </div>
                              <div className="flex items-center gap-4">
                                <div className="text-sm text-gray-600">
                                  VPIP: {opp.vpip_pct?.toFixed(1)}% | PFR: {opp.pfr_pct?.toFixed(1)}%
                                </div>
                                <Link
                                  to={`/strategy?opponent=${encodeURIComponent(opp.opponent_name)}`}
                                  className="inline-flex items-center space-x-1 px-3 py-1.5 text-xs font-medium text-purple-700 bg-purple-100 rounded-md hover:bg-purple-200 transition-colors"
                                  title="Generate strategy against this opponent"
                                >
                                  <Crosshair size={14} />
                                  <span>Strategy</span>
                                </Link>
                              </div>
                            </div>

                            {/* Tendencies */}
                            {opp.tendencies && Object.keys(opp.tendencies).length > 0 && (
                              <div className="mb-3">
                                <div className="flex flex-wrap gap-2">
                                  {Object.entries(opp.tendencies).map(([key, value]) => (
                                    <span key={key} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                                      {key}: {value}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Exploits */}
                            {opp.exploits && opp.exploits.length > 0 && (
                              <div>
                                <p className="text-sm font-medium text-gray-700 mb-2">Recommended Exploits:</p>
                                <div className="space-y-2">
                                  {opp.exploits.map((exploit, eidx) => (
                                    <div key={eidx} className="flex items-start gap-2 p-2 bg-green-50 rounded">
                                      <div className="flex-1">
                                        <p className="text-sm text-gray-900">{exploit.description}</p>
                                        <p className="text-xs text-gray-500 mt-1">
                                          Expected EV gain: +{exploit.estimated_ev_gain_bb.toFixed(2)} bb
                                        </p>
                                      </div>
                                      <span className={`px-2 py-1 text-xs rounded ${
                                        exploit.priority === 'high' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                                      }`}>
                                        {exploit.priority}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

              {!gtoAnalysis && (
                <div className="text-center py-12">
                  <Target className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">No GTO analysis available for this session.</p>
                </div>
              )}
            </div>
          )}

          {/* Leak Progress Tab */}
          {activeTab === 'leaks' && (
            <LeakProgressView sessionId={parseInt(sessionId || '0')} />
          )}

          {/* Hand History Tab */}
          {activeTab === 'hands' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Hand History ({hands.length} hands)</h3>
                <p className="text-sm text-gray-500">Click a hand to replay</p>
              </div>
              <div className="space-y-2">
                {hands.map((hand) => (
                  <button
                    key={hand.hand_id}
                    onClick={() => openHandReplay(hand.hand_id)}
                    disabled={loadingReplay && selectedHandId === hand.hand_id}
                    className="w-full bg-gray-50 rounded-lg p-4 hover:bg-blue-50 hover:border-blue-200 border border-transparent transition-colors text-left group"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                          {loadingReplay && selectedHandId === hand.hand_id ? (
                            <Loader2 size={16} className="animate-spin text-blue-600" />
                          ) : (
                            <Play size={16} className="text-gray-400 group-hover:text-blue-600 transition-colors" />
                          )}
                          <span className="text-xs text-gray-500">#{hand.hand_id}</span>
                        </div>
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
                  </button>
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

      {/* Hand Replay Modal */}
      {replayData && (
        <HandReplayModal data={replayData} onClose={closeHandReplay} />
      )}
    </div>
  );
};

export default SessionDetail;
