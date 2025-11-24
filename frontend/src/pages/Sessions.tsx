import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, Clock, TrendingUp, TrendingDown, Filter, RefreshCw } from 'lucide-react';

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
}

const Sessions: React.FC = () => {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [playerFilter, setPlayerFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      console.log('Fetching sessions from:', `${apiUrl}/api/sessions`);
      const response = await fetch(`${apiUrl}/api/sessions`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Fetched sessions:', data);
      setSessions(data);
    } catch (error) {
      console.error('Error fetching sessions:', error);
      alert(`Error fetching sessions: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const detectAllSessions = async () => {
    setDetecting(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      console.log('Detecting sessions at:', `${apiUrl}/api/sessions/detect-all`);
      const response = await fetch(`${apiUrl}/api/sessions/detect-all`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('Detection result:', result);
      alert(`Detected ${result.total_sessions_created} new sessions for ${result.players_processed} players`);

      // Wait a moment for database to commit, then refresh
      await new Promise(resolve => setTimeout(resolve, 500));
      await fetchSessions();
    } catch (error) {
      console.error('Error detecting sessions:', error);
      alert(`Failed to detect sessions: ${error}`);
    } finally {
      setDetecting(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
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

  const filteredSessions = playerFilter
    ? sessions.filter(s => s.player_name.toLowerCase().includes(playerFilter.toLowerCase()))
    : sessions;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Session Analysis</h1>
            <p className="text-gray-600 mt-1">Review and analyze your poker sessions</p>
          </div>
          <button
            onClick={detectAllSessions}
            disabled={detecting}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
          >
            <RefreshCw className={`w-4 h-4 ${detecting ? 'animate-spin' : ''}`} />
            {detecting ? 'Detecting...' : 'Detect New Sessions'}
          </button>
        </div>

        {/* Filters */}
        <div className="border-t border-gray-200 pt-4">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900"
          >
            <Filter className="w-4 h-4" />
            Filters
          </button>

          {showFilters && (
            <div className="mt-3">
              <input
                type="text"
                placeholder="Filter by player name..."
                value={playerFilter}
                onChange={(e) => setPlayerFilter(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          )}
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="text-sm text-gray-600">Total Sessions</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{filteredSessions.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="text-sm text-gray-600">Total Hands</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {filteredSessions.reduce((sum, s) => sum + s.total_hands, 0).toLocaleString()}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="text-sm text-gray-600">Total Profit/Loss</div>
          <div className={`text-2xl font-bold mt-1 ${filteredSessions.reduce((sum, s) => sum + s.profit_loss_bb, 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {filteredSessions.reduce((sum, s) => sum + s.profit_loss_bb, 0).toFixed(1)} bb
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="text-sm text-gray-600">Avg bb/100</div>
          <div className={`text-2xl font-bold mt-1 ${(filteredSessions.reduce((sum, s) => sum + s.bb_100, 0) / (filteredSessions.length || 1)) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {(filteredSessions.reduce((sum, s) => sum + s.bb_100, 0) / (filteredSessions.length || 1)).toFixed(1)}
          </div>
        </div>
      </div>

      {/* Sessions List */}
      {loading ? (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading sessions...</p>
        </div>
      ) : filteredSessions.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center">
          <p className="text-gray-600 mb-4">
            {sessions.length === 0 ? 'No sessions found. Click "Detect New Sessions" to analyze your uploaded hands.' : 'No sessions match your filters.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredSessions.map((session) => (
            <button
              key={session.session_id}
              onClick={() => navigate(`/sessions/${session.session_id}`)}
              className="w-full bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow text-left"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  {/* Date and Time */}
                  <div className="flex items-center gap-4 mb-3">
                    <div className="flex items-center gap-2 text-gray-900">
                      <Calendar className="w-4 h-4" />
                      <span className="font-semibold">{formatDate(session.start_time)}</span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-600">
                      <Clock className="w-4 h-4" />
                      <span className="text-sm">
                        {formatTime(session.start_time)} - {formatTime(session.end_time)}
                      </span>
                    </div>
                    <div className="text-sm text-gray-500">
                      Duration: {formatDuration(session.duration_minutes)}
                    </div>
                  </div>

                  {/* Session Details */}
                  <div className="flex items-center gap-6">
                    <div>
                      <span className="text-sm text-gray-600">Stakes: </span>
                      <span className="font-medium text-gray-900">{session.table_stakes}</span>
                    </div>
                    <div>
                      <span className="text-sm text-gray-600">Hands: </span>
                      <span className="font-medium text-gray-900">{session.total_hands}</span>
                    </div>
                    <div>
                      <span className="text-sm text-gray-600">Player: </span>
                      <span className="font-medium text-gray-900">{session.player_name}</span>
                    </div>
                    {session.table_name && (
                      <div>
                        <span className="text-sm text-gray-600">Table: </span>
                        <span className="font-medium text-gray-900">{session.table_name}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Profit/Loss */}
                <div className="ml-6 text-right">
                  <div className={`text-2xl font-bold ${session.profit_loss_bb >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    <div className="flex items-center gap-2">
                      {session.profit_loss_bb >= 0 ? (
                        <TrendingUp className="w-6 h-6" />
                      ) : (
                        <TrendingDown className="w-6 h-6" />
                      )}
                      {session.profit_loss_bb >= 0 ? '+' : ''}{session.profit_loss_bb.toFixed(1)} bb
                    </div>
                  </div>
                  <div className={`text-sm mt-1 ${session.bb_100 >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {session.bb_100 >= 0 ? '+' : ''}{session.bb_100.toFixed(1)} bb/100
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default Sessions;
