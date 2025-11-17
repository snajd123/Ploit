import { useState } from 'react';
import { RefreshCw, Trash2, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { api } from '../services/api';

const Settings = () => {
  const [recalculating, setRecalculating] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [recalcResult, setRecalcResult] = useState<any>(null);
  const [clearResult, setClearResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  const handleRecalculate = async () => {
    if (recalculating) return;

    setRecalculating(true);
    setError(null);
    setRecalcResult(null);

    try {
      const result = await api.recalculateStats();
      setRecalcResult(result);
    } catch (err) {
      setError((err as Error).message || 'Failed to recalculate statistics');
    } finally {
      setRecalculating(false);
    }
  };

  const handleClearDatabase = async () => {
    if (clearing) return;

    setClearing(true);
    setError(null);
    setClearResult(null);

    try {
      const result = await api.clearDatabase();
      setClearResult(result);
      setShowClearConfirm(false);
    } catch (err) {
      setError((err as Error).message || 'Failed to clear database');
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="mt-2 text-gray-600">
          Database maintenance and administrative tools
        </p>
      </div>

      {/* Recalculate Statistics */}
      <div className="card">
        <div className="flex items-start space-x-4">
          <div className="p-3 bg-blue-100 rounded-lg">
            <RefreshCw className="text-blue-600" size={24} />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-gray-900">Recalculate Statistics</h2>
            <p className="mt-2 text-sm text-gray-600">
              Recalculate all player statistics using the latest flag calculation logic.
              Use this after bug fixes or algorithm improvements to update existing data without re-uploading hands.
            </p>

            {recalcResult && (
              <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="flex items-start space-x-3">
                  <CheckCircle className="text-green-500 flex-shrink-0" size={20} />
                  <div>
                    <p className="text-sm font-medium text-green-800">{recalcResult.message}</p>
                    <div className="text-sm text-green-700 mt-2 space-y-1">
                      <p>• Hands recalculated: {recalcResult.hands_recalculated} (failed: {recalcResult.hands_failed})</p>
                      <p>• Players updated: {recalcResult.players_updated} of {recalcResult.players_processed} (failed: {recalcResult.players_failed})</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <button
              onClick={handleRecalculate}
              disabled={recalculating}
              className="mt-4 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {recalculating ? (
                <>
                  <RefreshCw className="animate-spin" size={16} />
                  Recalculating...
                </>
              ) : (
                <>
                  <RefreshCw size={16} />
                  Recalculate All Stats
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Clear Database */}
      <div className="card border-2 border-red-200">
        <div className="flex items-start space-x-4">
          <div className="p-3 bg-red-100 rounded-lg">
            <Trash2 className="text-red-600" size={24} />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-gray-900">Clear Database</h2>
            <p className="mt-2 text-sm text-gray-600">
              Delete all data from the database including hands, actions, summaries, and player statistics.
              <span className="font-semibold text-red-600"> This action cannot be undone.</span>
            </p>

            {clearResult && (
              <div className="mt-4 p-4 bg-red-50 rounded-lg border border-red-200">
                <div className="flex items-start space-x-3">
                  <CheckCircle className="text-red-500 flex-shrink-0" size={20} />
                  <div>
                    <p className="text-sm font-medium text-red-800">{clearResult.message}</p>
                    <p className="text-sm text-red-700 mt-2">Deleted:</p>
                    <ul className="text-sm text-red-700 mt-1 space-y-1">
                      <li>• Raw hands: {clearResult.deleted.raw_hands}</li>
                      <li>• Hand actions: {clearResult.deleted.hand_actions}</li>
                      <li>• Player hand summaries: {clearResult.deleted.player_hand_summary}</li>
                      <li>• Player stats: {clearResult.deleted.player_stats}</li>
                      <li>• Upload sessions: {clearResult.deleted.upload_sessions}</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {!showClearConfirm ? (
              <button
                onClick={() => setShowClearConfirm(true)}
                className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center space-x-2"
              >
                <Trash2 size={16} />
                <span>Clear Database</span>
              </button>
            ) : (
              <div className="mt-4 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                <div className="flex items-start space-x-3 mb-4">
                  <AlertTriangle className="text-yellow-600 flex-shrink-0" size={20} />
                  <div>
                    <p className="text-sm font-medium text-yellow-800">Are you absolutely sure?</p>
                    <p className="text-sm text-yellow-700 mt-1">
                      This will permanently delete all data. This action cannot be undone.
                    </p>
                  </div>
                </div>
                <div className="flex space-x-3">
                  <button
                    onClick={handleClearDatabase}
                    disabled={clearing}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    {clearing ? (
                      <>
                        <RefreshCw className="animate-spin" size={16} />
                        <span>Clearing...</span>
                      </>
                    ) : (
                      <>
                        <Trash2 size={16} />
                        <span>Yes, Clear Everything</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => setShowClearConfirm(false)}
                    disabled={clearing}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="p-4 bg-red-50 rounded-lg border border-red-200 flex items-start space-x-3">
          <XCircle className="text-red-500 flex-shrink-0" size={20} />
          <div>
            <p className="text-sm font-medium text-red-800">Error</p>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="card bg-blue-50 border border-blue-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">When to Use These Tools</h3>
        <div className="space-y-3 text-sm text-gray-700">
          <div>
            <p className="font-semibold text-blue-900">Recalculate Statistics:</p>
            <ul className="mt-1 space-y-1 ml-4">
              <li>• After bug fixes to flag calculation logic</li>
              <li>• When statistics show as N/A but should have values</li>
              <li>• After algorithm improvements to update existing data</li>
              <li>• Much faster than re-uploading all hands</li>
            </ul>
          </div>
          <div>
            <p className="font-semibold text-red-900">Clear Database:</p>
            <ul className="mt-1 space-y-1 ml-4">
              <li>• When you want to start completely fresh</li>
              <li>• To remove test data before production use</li>
              <li>• When database has corrupted or inconsistent data</li>
              <li>• <span className="font-semibold">Warning:</span> All data will be permanently lost</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
