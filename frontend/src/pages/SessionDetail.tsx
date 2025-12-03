import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Calendar, Clock, TrendingUp, TrendingDown } from 'lucide-react';
import LeakProgressView from '../components/LeakProgressView';
import PositionalPLView from '../components/PositionalPLView';
import PreflopMistakesView from '../components/PreflopMistakesView';
import GTOScoreView from '../components/GTOScoreView';

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
}

const SessionDetail: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (sessionId) {
      fetchSessionData();
    }
  }, [sessionId]);

  const fetchSessionData = async () => {
    setLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      const response = await fetch(`${apiUrl}/api/sessions/${sessionId}`);
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      const data = await response.json();
      setSession(data);
    } catch (error) {
      console.error('Error fetching session data:', error);
    } finally {
      setLoading(false);
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

  if (!session) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Session not found</p>
      </div>
    );
  }

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
              Session Leak Progress
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

      {/* GTO Deviation Score */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <GTOScoreView sessionId={parseInt(sessionId || '0')} />
      </div>

      {/* Positional P/L Breakdown */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <PositionalPLView sessionId={parseInt(sessionId || '0')} />
      </div>

      {/* Biggest Preflop Mistakes */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <PreflopMistakesView sessionId={parseInt(sessionId || '0')} />
      </div>

      {/* Leak Progress Analysis */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <LeakProgressView sessionId={parseInt(sessionId || '0')} />
      </div>
    </div>
  );
};

export default SessionDetail;
