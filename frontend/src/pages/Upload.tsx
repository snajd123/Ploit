import { useState, useCallback } from 'react';
import { Upload as UploadIcon, FileText, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import type { UploadResponse } from '../types';

const Upload = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

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

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.txt')) {
        setSelectedFile(file);
        setError(null);
        setResult(null);
      } else {
        setError('Please select a .txt file');
      }
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.name.endsWith('.txt')) {
        setSelectedFile(file);
        setError(null);
        setResult(null);
      } else {
        setError('Please select a .txt file');
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setProgress(0);
    setError(null);
    setResult(null);

    try {
      const response = await api.uploadHandHistory(selectedFile, setProgress);
      setResult(response);
      setSelectedFile(null);
    } catch (err) {
      setError((err as Error).message || 'Upload failed');
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Upload Hand History</h1>
        <p className="mt-2 text-gray-600">
          Import PokerStars .txt hand history files for analysis
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
                Drop your file here, or{' '}
                <span className="text-blue-600 hover:text-blue-500">browse</span>
              </span>
              <input
                id="file-upload"
                name="file-upload"
                type="file"
                accept=".txt"
                className="sr-only"
                onChange={handleFileSelect}
                disabled={uploading}
              />
            </label>
            <p className="mt-1 text-xs text-gray-500">
              PokerStars .txt files only
            </p>
          </div>
        </div>

        {/* Selected file */}
        {selectedFile && !uploading && !result && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileText className="text-gray-400" size={24} />
              <div>
                <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
                <p className="text-xs text-gray-500">
                  {(selectedFile.size / 1024).toFixed(2)} KB
                </p>
              </div>
            </div>
            <button
              onClick={handleUpload}
              className="btn-primary"
            >
              Upload & Parse
            </button>
          </div>
        )}

        {/* Progress */}
        {uploading && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Uploading...</span>
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
            <span>Select or drag the .txt file into the upload area</span>
          </li>
          <li className="flex items-start">
            <span className="font-semibold text-blue-600 mr-2">3.</span>
            <span>Click "Upload & Parse" to process the hands</span>
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
