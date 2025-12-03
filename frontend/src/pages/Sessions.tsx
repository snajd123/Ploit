import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, Clock, TrendingUp, TrendingDown, Filter, RefreshCw, BarChart3, CheckSquare, Square } from 'lucide-react';

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

type DateRange = 'all' | 'today' | 'last7' | 'last30' | 'thisWeek' | 'thisMonth' | 'custom';

const Sessions: React.FC = () => {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [playerFilter, setPlayerFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Selection state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [dateRange, setDateRange] = useState<DateRange>('all');

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      const response = await fetch(`${apiUrl}/api/sessions/`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
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
      const response = await fetch(`${apiUrl}/api/sessions/detect-all`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      alert(`Detected ${result.total_sessions_created} new sessions for ${result.players_processed} players`);

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

  // Date range filtering
  const getDateRangeFilter = (range: DateRange): ((date: Date) => boolean) => {
    const now = new Date();
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());

    switch (range) {
      case 'today':
        return (date) => date >= startOfDay;
      case 'last7':
        const last7 = new Date(startOfDay);
        last7.setDate(last7.getDate() - 7);
        return (date) => date >= last7;
      case 'last30':
        const last30 = new Date(startOfDay);
        last30.setDate(last30.getDate() - 30);
        return (date) => date >= last30;
      case 'thisWeek':
        const startOfWeek = new Date(startOfDay);
        startOfWeek.setDate(startOfWeek.getDate() - startOfWeek.getDay());
        return (date) => date >= startOfWeek;
      case 'thisMonth':
        const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
        return (date) => date >= startOfMonth;
      default:
        return () => true;
    }
  };

  const filteredSessions = useMemo(() => {
    let filtered = sessions;

    // Player filter
    if (playerFilter) {
      filtered = filtered.filter(s =>
        s.player_name.toLowerCase().includes(playerFilter.toLowerCase())
      );
    }

    // Date range filter
    if (dateRange !== 'all') {
      const dateFilter = getDateRangeFilter(dateRange);
      filtered = filtered.filter(s => dateFilter(new Date(s.start_time)));
    }

    return filtered;
  }, [sessions, playerFilter, dateRange]);

  // Selection handlers
  const toggleSelection = (sessionId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(sessionId)) {
        next.delete(sessionId);
      } else {
        next.add(sessionId);
      }
      return next;
    });
  };

  const selectAll = () => {
    setSelectedIds(new Set(filteredSessions.map(s => s.session_id)));
  };

  const clearSelection = () => {
    setSelectedIds(new Set());
  };

  const selectByDateRange = (range: DateRange) => {
    setDateRange(range);
    // Also select all sessions in that range
    const dateFilter = getDateRangeFilter(range);
    const filtered = sessions.filter(s => dateFilter(new Date(s.start_time)));
    if (playerFilter) {
      const playerFiltered = filtered.filter(s =>
        s.player_name.toLowerCase().includes(playerFilter.toLowerCase())
      );
      setSelectedIds(new Set(playerFiltered.map(s => s.session_id)));
    } else {
      setSelectedIds(new Set(filtered.map(s => s.session_id)));
    }
  };

  const handleAnalyzeSelected = () => {
    if (selectedIds.size < 1) {
      alert('Please select at least one session to analyze');
      return;
    }
    const ids = Array.from(selectedIds).join(',');
    navigate(`/sessions/analysis?ids=${ids}`);
  };

  const selectedSessions = filteredSessions.filter(s => selectedIds.has(s.session_id));
  const totalSelectedHands = selectedSessions.reduce((sum, s) => sum + s.total_hands, 0);
  const totalSelectedProfit = selectedSessions.reduce((sum, s) => sum + s.profit_loss_bb, 0);

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

        {/* Filters & Date Range */}
        <div className="border-t border-gray-200 pt-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900"
            >
              <Filter className="w-4 h-4" />
              Filters
            </button>

            {/* Date Range Quick Selects */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Quick Select:</span>
              {[
                { key: 'last7' as DateRange, label: 'Last 7 Days' },
                { key: 'thisWeek' as DateRange, label: 'This Week' },
                { key: 'last30' as DateRange, label: 'Last 30 Days' },
                { key: 'thisMonth' as DateRange, label: 'This Month' },
              ].map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => selectByDateRange(key)}
                  className={`px-3 py-1 text-xs rounded-full transition-colors ${
                    dateRange === key
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {label}
                </button>
              ))}
              {dateRange !== 'all' && (
                <button
                  onClick={() => { setDateRange('all'); clearSelection(); }}
                  className="px-3 py-1 text-xs rounded-full bg-gray-100 text-gray-700 hover:bg-gray-200"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

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

      {/* Selection Summary Bar */}
      {selectedIds.size > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <CheckSquare className="w-5 h-5 text-blue-600" />
              <span className="font-medium text-blue-900">
                {selectedIds.size} session{selectedIds.size !== 1 ? 's' : ''} selected
              </span>
            </div>
            <div className="text-sm text-blue-700">
              {totalSelectedHands.toLocaleString()} hands
            </div>
            <div className={`text-sm font-medium ${totalSelectedProfit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {totalSelectedProfit >= 0 ? '+' : ''}{totalSelectedProfit.toFixed(1)} bb
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={clearSelection}
              className="text-sm text-gray-600 hover:text-gray-800"
            >
              Clear Selection
            </button>
            <button
              onClick={handleAnalyzeSelected}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <BarChart3 className="w-4 h-4" />
              Analyze Progress
            </button>
          </div>
        </div>
      )}

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
        <div className="space-y-2">
          {/* Select All Row */}
          <div className="flex items-center justify-between px-4 py-2 bg-gray-50 rounded-lg">
            <button
              onClick={selectAll}
              className="flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900"
            >
              <CheckSquare className="w-4 h-4" />
              Select All ({filteredSessions.length})
            </button>
            {selectedIds.size > 0 && (
              <button
                onClick={clearSelection}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Deselect All
              </button>
            )}
          </div>

          {filteredSessions.map((session) => {
            const isSelected = selectedIds.has(session.session_id);

            return (
              <div
                key={session.session_id}
                className={`w-full bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow ${
                  isSelected ? 'ring-2 ring-blue-500 bg-blue-50/30' : ''
                }`}
              >
                <div className="flex items-start">
                  {/* Checkbox */}
                  <button
                    onClick={(e) => toggleSelection(session.session_id, e)}
                    className="mr-4 mt-1 flex-shrink-0"
                  >
                    {isSelected ? (
                      <CheckSquare className="w-5 h-5 text-blue-600" />
                    ) : (
                      <Square className="w-5 h-5 text-gray-400 hover:text-gray-600" />
                    )}
                  </button>

                  {/* Session Content - Clickable to navigate */}
                  <button
                    onClick={() => navigate(`/sessions/${session.session_id}`)}
                    className="flex-1 text-left"
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
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Sessions;
