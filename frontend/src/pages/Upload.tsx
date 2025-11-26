import { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Upload as UploadIcon, FileText, CheckCircle, XCircle, AlertCircle, X, Users, Calendar, Target, ArrowRight, Loader2, Folder } from 'lucide-react';
import { api } from '../services/api';
import type { UploadResponse } from '../types';

interface SessionDetectionResult {
  players_processed: number;
  total_sessions_created: number;
  sessions_by_player: Record<string, any[]>;
}

const Upload = () => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [folderName, setFolderName] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [detectingSessions, setDetectingSessions] = useState(false);
  const [sessionResult, setSessionResult] = useState<SessionDetectionResult | null>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files) {
      const files = Array.from(e.dataTransfer.files).filter(file => file.name.endsWith('.txt'));
      if (files.length > 0) {
        setSelectedFiles(files);
        setError(null);
        setResult(null);

        // Extract folder name from webkitRelativePath if available
        const firstFile = files[0] as File & { webkitRelativePath?: string };
        if (firstFile.webkitRelativePath) {
          const pathParts = firstFile.webkitRelativePath.split('/');
          if (pathParts.length > 1) {
            setFolderName(pathParts[0]);
          }
        } else {
          // For drag & drop without folder info, set a generic name
          setFolderName('Dropped files');
        }
      } else {
        setError('Please drop a folder containing .txt files');
        setFolderName(null);
      }
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files).filter(file => file.name.endsWith('.txt'));
      if (files.length > 0) {
        setSelectedFiles(files);
        setError(null);
        setResult(null);

        // Extract folder name from webkitRelativePath
        const firstFile = files[0] as File & { webkitRelativePath?: string };
        if (firstFile.webkitRelativePath) {
          const pathParts = firstFile.webkitRelativePath.split('/');
          if (pathParts.length > 1) {
            setFolderName(pathParts[0]);
          }
        }
      } else {
        setError('Please select a folder containing .txt files');
        setFolderName(null);
      }
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;

    setUploading(true);
    setProgress(0);
    setError(null);
    setResult(null);
    setSessionResult(null);

    try {
      const response = selectedFiles.length === 1
        ? await api.uploadHandHistory(selectedFiles[0], setProgress)
        : await api.uploadHandHistoryBatch(selectedFiles, setProgress);

      setResult(response);
      setSelectedFiles([]);
      setFolderName(null);

      // Auto-trigger session detection after successful upload
      setDetectingSessions(true);
      try {
        const sessions = await api.detectAllSessions();
        setSessionResult(sessions);
      } catch (sessionErr) {
        // Session detection failure is non-critical, just log it
        console.warn('Session detection failed:', sessionErr);
      } finally {
        setDetectingSessions(false);
      }
    } catch (err) {
      setError((err as Error).message || 'Upload failed');
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };

  const totalSize = selectedFiles.reduce((acc, file) => acc + file.size, 0);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Upload Hand History</h1>
        <p className="mt-2 text-gray-600">
          Import a folder containing PokerStars .txt hand history files for analysis
        </p>
      </div>

      {/* Upload area */}
      <div className="card">
        <div
          className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
            dragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <UploadIcon className="mx-auto h-12 w-12 text-gray-400" />
          <div className="mt-4">
            <label htmlFor="file-upload" className="cursor-pointer">
              <span className="mt-2 block text-sm font-semibold text-gray-900">
                Drop a folder here, or{' '}
                <span className="text-blue-600 hover:text-blue-500">browse for folder</span>
              </span>
              <input
                id="file-upload"
                name="file-upload"
                type="file"
                accept=".txt"
                className="sr-only"
                onChange={handleFileSelect}
                disabled={uploading}
                {...{ webkitdirectory: '', directory: '' } as any}
              />
            </label>
            <p className="mt-1 text-xs text-gray-500">
              Select a folder containing PokerStars .txt files
            </p>
          </div>
        </div>

        {/* Selected folder */}
        {selectedFiles.length > 0 && !uploading && !result && (
          <div className="mt-4 space-y-3">
            {/* Folder card */}
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Folder className="text-blue-600" size={24} />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">{folderName || 'Selected Folder'}</p>
                    <p className="text-sm text-gray-600">
                      {selectedFiles.length} .txt file{selectedFiles.length > 1 ? 's' : ''} • {(totalSize / 1024).toFixed(2)} KB total
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setSelectedFiles([]);
                    setFolderName(null);
                  }}
                  className="p-2 rounded-full hover:bg-blue-100 transition-colors"
                  title="Clear selection"
                >
                  <X size={18} className="text-gray-500" />
                </button>
              </div>
            </div>

            {/* Upload button */}
            <button
              onClick={handleUpload}
              className="w-full btn-primary py-3"
            >
              Upload & Parse {selectedFiles.length} File{selectedFiles.length > 1 ? 's' : ''}
            </button>

            {/* Collapsible file list */}
            <details className="text-sm">
              <summary className="cursor-pointer text-gray-500 hover:text-gray-700">
                View {selectedFiles.length} files
              </summary>
              <div className="mt-2 max-h-48 overflow-y-auto space-y-1 pl-2">
                {selectedFiles.map((file, index) => (
                  <div key={index} className="flex items-center space-x-2 text-gray-600 py-1">
                    <FileText className="text-gray-400 flex-shrink-0" size={14} />
                    <span className="truncate">{file.name}</span>
                    <span className="text-gray-400 text-xs flex-shrink-0">({(file.size / 1024).toFixed(1)} KB)</span>
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}

        {/* Progress */}
        {uploading && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">
                Uploading {folderName ? `"${folderName}"` : `${selectedFiles.length} files`}...
              </span>
              <span className="text-sm font-medium text-gray-700">{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 rounded-lg border border-red-200 flex items-start space-x-3">
            <XCircle className="text-red-500 flex-shrink-0" size={20} />
            <div>
              <p className="text-sm font-medium text-red-800">Upload Failed</p>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Success */}
        {result && (
          <div className="mt-4 space-y-4">
            <div className="p-4 bg-green-50 rounded-lg border border-green-200 flex items-start space-x-3">
              <CheckCircle className="text-green-500 flex-shrink-0" size={20} />
              <div className="flex-1">
                <p className="text-sm font-medium text-green-800">Upload Successful!</p>
                <p className="text-sm text-green-700 mt-1">{result.message}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-white rounded-lg border border-gray-200">
                <p className="text-sm text-gray-600">Hands Parsed</p>
                <p className="text-2xl font-semibold text-gray-900 mt-1">
                  {result.hands_parsed}
                </p>
              </div>
              <div className="p-4 bg-white rounded-lg border border-gray-200">
                <p className="text-sm text-gray-600">Players Updated</p>
                <p className="text-2xl font-semibold text-gray-900 mt-1">
                  {result.players_updated}
                </p>
              </div>
              {result.stake_level && (
                <div className="p-4 bg-white rounded-lg border border-gray-200">
                  <p className="text-sm text-gray-600">Stake Level</p>
                  <p className="text-2xl font-semibold text-gray-900 mt-1">
                    {result.stake_level}
                  </p>
                </div>
              )}
              <div className="p-4 bg-white rounded-lg border border-gray-200">
                <p className="text-sm text-gray-600">Processing Time</p>
                <p className="text-2xl font-semibold text-gray-900 mt-1">
                  {result.processing_time}s
                </p>
              </div>
            </div>

            {result.hands_failed > 0 && (
              <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200 flex items-start space-x-3">
                <AlertCircle className="text-yellow-500 flex-shrink-0" size={20} />
                <div>
                  <p className="text-sm font-medium text-yellow-800">Partial Success</p>
                  <p className="text-sm text-yellow-700 mt-1">
                    {result.hands_failed} hands failed to parse and were skipped.
                  </p>
                </div>
              </div>
            )}

            {/* Session Detection Status */}
            {detectingSessions && (
              <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200 flex items-center space-x-3">
                <Loader2 className="text-blue-500 animate-spin flex-shrink-0" size={20} />
                <div>
                  <p className="text-sm font-medium text-blue-800">Detecting Sessions...</p>
                  <p className="text-sm text-blue-700">Organizing your hands into sessions for analysis</p>
                </div>
              </div>
            )}

            {/* Session Detection Results */}
            {sessionResult && sessionResult.total_sessions_created > 0 && (
              <div className="mt-4 p-4 bg-indigo-50 rounded-lg border border-indigo-200">
                <div className="flex items-center space-x-2 mb-2">
                  <Calendar className="text-indigo-600" size={18} />
                  <p className="text-sm font-medium text-indigo-800">Sessions Detected</p>
                </div>
                <p className="text-sm text-indigo-700">
                  Found <span className="font-semibold">{sessionResult.total_sessions_created}</span> sessions across{' '}
                  <span className="font-semibold">{sessionResult.players_processed}</span> players
                </p>
              </div>
            )}

            {/* What's Next? Section */}
            <div className="mt-6 p-5 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">What's Next?</h3>
              <p className="text-sm text-gray-600 mb-4">
                Your data is ready for analysis. Choose where to go:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <Link
                  to="/players"
                  className="flex items-center justify-between p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all group"
                >
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-blue-100 rounded-lg group-hover:bg-blue-200 transition-colors">
                      <Users className="text-blue-600" size={20} />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Browse Players</p>
                      <p className="text-xs text-gray-500">View opponent stats</p>
                    </div>
                  </div>
                  <ArrowRight className="text-gray-400 group-hover:text-blue-500 transition-colors" size={18} />
                </Link>

                <Link
                  to="/sessions"
                  className="flex items-center justify-between p-4 bg-white rounded-lg border border-gray-200 hover:border-green-300 hover:shadow-md transition-all group"
                >
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-green-100 rounded-lg group-hover:bg-green-200 transition-colors">
                      <Calendar className="text-green-600" size={20} />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">View Sessions</p>
                      <p className="text-xs text-gray-500">
                        {sessionResult && sessionResult.total_sessions_created > 0
                          ? `${sessionResult.total_sessions_created} ready`
                          : 'Analyze your play'}
                      </p>
                    </div>
                  </div>
                  <ArrowRight className="text-gray-400 group-hover:text-green-500 transition-colors" size={18} />
                </Link>

                <Link
                  to="/strategy"
                  className="flex items-center justify-between p-4 bg-white rounded-lg border border-gray-200 hover:border-purple-300 hover:shadow-md transition-all group"
                >
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-purple-100 rounded-lg group-hover:bg-purple-200 transition-colors">
                      <Target className="text-purple-600" size={20} />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Generate Strategy</p>
                      <p className="text-xs text-gray-500">Exploit opponents</p>
                    </div>
                  </div>
                  <ArrowRight className="text-gray-400 group-hover:text-purple-500 transition-colors" size={18} />
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Instructions */}
      <div className="card bg-blue-50 border border-blue-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">How to Upload</h2>
        <ol className="space-y-2 text-sm text-gray-700">
          <li className="flex items-start">
            <span className="font-semibold text-blue-600 mr-2">1.</span>
            <span>Export hand history from PokerStars (Request My Data → Hand History)</span>
          </li>
          <li className="flex items-start">
            <span className="font-semibold text-blue-600 mr-2">2.</span>
            <span>Select the folder containing your .txt files, or drag it into the upload area</span>
          </li>
          <li className="flex items-start">
            <span className="font-semibold text-blue-600 mr-2">3.</span>
            <span>Click "Upload & Parse" to process all hands at once</span>
          </li>
          <li className="flex items-start">
            <span className="font-semibold text-blue-600 mr-2">4.</span>
            <span>Player statistics will be automatically calculated and updated</span>
          </li>
        </ol>
      </div>
    </div>
  );
};

export default Upload;
