import { useState, useEffect } from 'react';
import { RefreshCw, Trash2, AlertTriangle, CheckCircle, XCircle, Database, Shield, Upload, Clock, FileText } from 'lucide-react';
import { api } from '../services/api';
import type { ResetPreviewResponse, ClearDatabaseResponse, UploadSessionItem } from '../types';

const Settings = () => {
  const [recalculating, setRecalculating] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [loadingUploads, setLoadingUploads] = useState(false);
  const [recalcResult, setRecalcResult] = useState<any>(null);
  const [clearResult, setClearResult] = useState<ClearDatabaseResponse | null>(null);
  const [resetPreview, setResetPreview] = useState<ResetPreviewResponse | null>(null);
  const [uploadHistory, setUploadHistory] = useState<UploadSessionItem[]>([]);
  const [totalUploads, setTotalUploads] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  // Load reset preview
  const loadResetPreview = async () => {
    setLoadingPreview(true);
    try {
      const preview = await api.getResetPreview();
      setResetPreview(preview);
    } catch (err) {
      console.error('Failed to load preview:', err);
    } finally {
      setLoadingPreview(false);
    }
  };

  // Load upload history
  const loadUploadHistory = async () => {
    setLoadingUploads(true);
    try {
      const response = await api.getUploadHistory(50, 0);
      setUploadHistory(response.uploads);
      setTotalUploads(response.total);
    } catch (err) {
      console.error('Failed to load upload history:', err);
    } finally {
      setLoadingUploads(false);
    }
  };

  // Load data on mount
  useEffect(() => {
    loadResetPreview();
    loadUploadHistory();
  }, []);

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
      // Refresh data after clear
      loadResetPreview();
      loadUploadHistory();
    } catch (err) {
      setError((err as Error).message || 'Failed to clear database');
    } finally {
      setClearing(false);
    }
  };

  const handleShowConfirm = () => {
    setShowClearConfirm(true);
    loadResetPreview();
  };

  const formatNumber = (n: number) => n.toLocaleString();

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Unknown';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-50';
      case 'failed':
        return 'text-red-600 bg-red-50';
      case 'processing':
        return 'text-yellow-600 bg-yellow-50';
      default:
        return 'text-gray-600 bg-gray-50';
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

      {/* Upload History */}
      <div className="card">
        <div className="flex items-start space-x-4">
          <div className="p-3 bg-purple-100 rounded-lg">
            <Upload className="text-purple-600" size={24} />
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Upload History</h2>
              <button
                onClick={loadUploadHistory}
                disabled={loadingUploads}
                className="text-sm text-gray-500 hover:text-gray-700 flex items-center space-x-1"
              >
                <RefreshCw className={`${loadingUploads ? 'animate-spin' : ''}`} size={14} />
                <span>Refresh</span>
              </button>
            </div>
            <p className="mt-2 text-sm text-gray-600">
              {totalUploads} total uploads
            </p>

            {loadingUploads ? (
              <div className="mt-4 flex items-center justify-center py-8">
                <RefreshCw className="animate-spin text-gray-400" size={24} />
              </div>
            ) : uploadHistory.length === 0 ? (
              <div className="mt-4 p-6 bg-gray-50 rounded-lg text-center">
                <FileText className="mx-auto text-gray-400 mb-2" size={32} />
                <p className="text-sm text-gray-500">No uploads yet</p>
              </div>
            ) : (
              <div className="mt-4 space-y-2 max-h-80 overflow-y-auto">
                {uploadHistory.map((upload) => (
                  <div
                    key={upload.session_id}
                    className="p-3 bg-gray-50 rounded-lg border border-gray-100"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <FileText className="text-gray-400 flex-shrink-0" size={16} />
                          <span className="font-medium text-gray-900 truncate">
                            {upload.filename || 'Unknown file'}
                          </span>
                        </div>
                        <div className="flex items-center space-x-4 mt-1 text-xs text-gray-500">
                          <span className="flex items-center space-x-1">
                            <Clock size={12} />
                            <span>{formatDate(upload.upload_timestamp)}</span>
                          </span>
                          {upload.stake_level && (
                            <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
                              {upload.stake_level}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex flex-col items-end space-y-1 ml-4">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(upload.status)}`}>
                          {upload.status}
                        </span>
                        <span className="text-xs text-gray-500">
                          {formatNumber(upload.hands_parsed)} hands
                          {upload.hands_failed > 0 && (
                            <span className="text-red-500"> ({upload.hands_failed} failed)</span>
                          )}
                        </span>
                      </div>
                    </div>
                    {upload.error_message && (
                      <div className="mt-2 text-xs text-red-600 bg-red-50 p-2 rounded">
                        {upload.error_message}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
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

      {/* Reset Player Data */}
      <div className="card border-2 border-red-200">
        <div className="flex items-start space-x-4">
          <div className="p-3 bg-red-100 rounded-lg">
            <Trash2 className="text-red-600" size={24} />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-gray-900">Reset Player Data</h2>
            <p className="mt-2 text-sm text-gray-600">
              Delete all imported hand histories, player stats, and calculated data.
              <span className="font-semibold text-green-600"> GTO reference data will be preserved.</span>
            </p>

            {/* Current data preview */}
            {resetPreview && !showClearConfirm && (
              <div className="mt-4 grid grid-cols-2 gap-4">
                <div className="p-3 bg-red-50 rounded-lg border border-red-100">
                  <div className="flex items-center space-x-2 mb-2">
                    <Database className="text-red-500" size={16} />
                    <span className="text-sm font-medium text-red-800">Will be deleted</span>
                  </div>
                  <ul className="text-xs text-red-700 space-y-1">
                    <li>• {formatNumber(resetPreview.to_delete.raw_hands)} hands</li>
                    <li>• {formatNumber(resetPreview.to_delete.hand_actions)} actions</li>
                    <li>• {formatNumber(resetPreview.to_delete.player_stats)} player stats</li>
                  </ul>
                </div>
                <div className="p-3 bg-green-50 rounded-lg border border-green-100">
                  <div className="flex items-center space-x-2 mb-2">
                    <Shield className="text-green-500" size={16} />
                    <span className="text-sm font-medium text-green-800">Will be preserved</span>
                  </div>
                  <ul className="text-xs text-green-700 space-y-1">
                    <li>• {formatNumber(resetPreview.to_preserve.gto_scenarios)} GTO scenarios</li>
                    <li>• {formatNumber(resetPreview.to_preserve.gto_frequencies)} GTO frequencies</li>
                  </ul>
                </div>
              </div>
            )}

            {clearResult && (
              <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="flex items-start space-x-3">
                  <CheckCircle className="text-green-500 flex-shrink-0" size={20} />
                  <div>
                    <p className="text-sm font-medium text-green-800">{clearResult.message}</p>
                    <div className="mt-2 grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs font-medium text-red-700">Deleted:</p>
                        <ul className="text-xs text-red-600 mt-1 space-y-0.5">
                          <li>• {formatNumber(clearResult.deleted.raw_hands)} hands</li>
                          <li>• {formatNumber(clearResult.deleted.hand_actions)} actions</li>
                          <li>• {formatNumber(clearResult.deleted.player_stats)} player stats</li>
                          <li>• {formatNumber(clearResult.deleted.upload_sessions)} upload sessions</li>
                        </ul>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-green-700">Preserved:</p>
                        <ul className="text-xs text-green-600 mt-1 space-y-0.5">
                          <li>• {formatNumber(clearResult.preserved.gto_scenarios)} GTO scenarios</li>
                          <li>• {formatNumber(clearResult.preserved.gto_frequencies)} GTO frequencies</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {!showClearConfirm ? (
              <button
                onClick={handleShowConfirm}
                disabled={loadingPreview}
                className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center space-x-2 disabled:opacity-50"
              >
                <Trash2 size={16} />
                <span>Reset Player Data</span>
              </button>
            ) : (
              <div className="mt-4 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                <div className="flex items-start space-x-3 mb-4">
                  <AlertTriangle className="text-yellow-600 flex-shrink-0" size={20} />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-yellow-800">Confirm Reset</p>
                    <p className="text-sm text-yellow-700 mt-1">
                      This will permanently delete all player data. GTO reference data will be preserved.
                    </p>

                    {loadingPreview ? (
                      <div className="mt-3 flex items-center text-yellow-700">
                        <RefreshCw className="animate-spin mr-2" size={14} />
                        <span className="text-xs">Loading preview...</span>
                      </div>
                    ) : resetPreview && (
                      <div className="mt-3 p-3 bg-white rounded border border-yellow-200">
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          <div>
                            <p className="font-medium text-red-700 mb-1">Will delete:</p>
                            <ul className="text-red-600 space-y-0.5">
                              <li>• {formatNumber(resetPreview.to_delete.raw_hands)} hands</li>
                              <li>• {formatNumber(resetPreview.to_delete.hand_actions)} actions</li>
                              <li>• {formatNumber(resetPreview.to_delete.player_preflop_actions)} preflop actions</li>
                              <li>• {formatNumber(resetPreview.to_delete.player_scenario_stats)} scenario stats</li>
                              <li>• {formatNumber(resetPreview.to_delete.player_stats)} player stats</li>
                              <li>• {formatNumber(resetPreview.to_delete.upload_sessions)} upload sessions</li>
                            </ul>
                          </div>
                          <div>
                            <p className="font-medium text-green-700 mb-1">Will preserve:</p>
                            <ul className="text-green-600 space-y-0.5">
                              <li>• {formatNumber(resetPreview.to_preserve.gto_scenarios)} GTO scenarios</li>
                              <li>• {formatNumber(resetPreview.to_preserve.gto_frequencies)} GTO frequencies</li>
                            </ul>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex space-x-3">
                  <button
                    onClick={handleClearDatabase}
                    disabled={clearing || loadingPreview}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    {clearing ? (
                      <>
                        <RefreshCw className="animate-spin" size={16} />
                        <span>Resetting...</span>
                      </>
                    ) : (
                      <>
                        <Trash2 size={16} />
                        <span>Yes, Reset Data</span>
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
            <p className="font-semibold text-red-900">Reset Player Data:</p>
            <ul className="mt-1 space-y-1 ml-4">
              <li>• When you want to start fresh with hand analysis</li>
              <li>• To remove test data before production use</li>
              <li>• When database has corrupted or inconsistent data</li>
              <li>• <span className="text-green-700 font-medium">GTO reference data (188 scenarios, 53K+ frequencies) is always preserved</span></li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
