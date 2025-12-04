import React from 'react';
import { ArrowLeft, TrendingUp, Shield, Target, AlertTriangle } from 'lucide-react';
import type { GTOAnalysisResponse } from '../../types';

type GTOCategoryKey = 'opening' | 'defense' | 'facing_3bet' | 'facing_4bet';

interface ScenarioSelection {
  scenario: 'opening' | 'defense' | 'facing_3bet' | 'facing_4bet';
  position: string;
  vsPosition?: string;
  action?: string;  // Specific action for the leak (e.g., 'call', 'fold', 'raise')
}

interface GTOCategoryDetailViewProps {
  category: GTOCategoryKey;
  data: GTOAnalysisResponse;
  onBack: () => void;
  onRowClick: (selection: ScenarioSelection) => void;
}

const CATEGORY_CONFIG: Record<GTOCategoryKey, {
  title: string;
  subtitle: string;
  icon: React.ElementType;
}> = {
  opening: {
    title: 'Opening Ranges',
    subtitle: 'Your raise first in frequency by position compared to GTO',
    icon: TrendingUp,
  },
  defense: {
    title: 'Defense vs Opens',
    subtitle: 'How you respond when facing an open raise',
    icon: Shield,
  },
  facing_3bet: {
    title: 'Facing 3-Bet',
    subtitle: 'Your fold/call/4-bet frequencies when 3-bet after opening',
    icon: Target,
  },
  facing_4bet: {
    title: 'Facing 4-Bet',
    subtitle: 'Your response when your 3-bet gets 4-bet',
    icon: AlertTriangle,
  },
};

// Helper to get diff color
const getDiffColor = (diff: number, threshold: number = 5) => {
  const absDiff = Math.abs(diff);
  if (absDiff < threshold) return 'text-green-600';
  if (absDiff < threshold * 2) return 'text-yellow-600';
  return 'text-red-600';
};

// Helper to format diff with sign
const formatDiff = (diff: number) => {
  return diff > 0 ? `+${diff.toFixed(1)}%` : `${diff.toFixed(1)}%`;
};

// Reusable table component
const GTOTable = ({
  title,
  subtitle,
  data,
  columns,
  onRowClick,
}: {
  title: string;
  subtitle?: string;
  data: any[];
  columns: { key: string; label: string; isPlayer?: boolean; isGTO?: boolean; isDiff?: boolean }[];
  onRowClick?: (row: any) => void;
}) => {
  if (!data || data.length === 0) return null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 mb-6">
      <div className="px-4 py-3 border-b border-gray-200">
        <h4 className="font-semibold text-gray-900">{title}</h4>
        {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              {columns.map(col => (
                <th key={col.key} className={`py-2 px-3 font-medium ${
                  col.isGTO ? 'text-blue-600 bg-blue-50' :
                  col.isDiff ? 'text-gray-600' : 'text-gray-600'
                } ${col.key === 'position' || col.key === 'vs_position' ? 'text-left' : 'text-right'}`}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, idx) => (
              <tr
                key={idx}
                className="border-b border-gray-100 hover:bg-blue-50 cursor-pointer transition-colors"
                onClick={() => onRowClick?.(row)}
              >
                {columns.map(col => {
                  const value = row[col.key];
                  const isPosition = col.key === 'position' || col.key === 'vs_position';
                  const isSampleSize = col.key === 'sample_size' || col.key === 'total_hands';

                  if (col.isDiff) {
                    return (
                      <td key={col.key} className={`py-2 px-3 text-right font-medium ${getDiffColor(value)}`}>
                        {value != null ? formatDiff(value) : '-'}
                      </td>
                    );
                  }

                  return (
                    <td key={col.key} className={`py-2 px-3 ${
                      isPosition ? 'font-medium' :
                      isSampleSize ? 'text-right text-gray-500' :
                      col.isGTO ? 'text-right text-blue-600 bg-blue-50/50' :
                      'text-right'
                    }`}>
                      {typeof value === 'number' && !isSampleSize ? `${value.toFixed(1)}%` : (value ?? '-')}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-400 px-4 py-2">Click a row to see individual hands</p>
    </div>
  );
};

const GTOCategoryDetailView: React.FC<GTOCategoryDetailViewProps> = ({
  category,
  data,
  onBack,
  onRowClick,
}) => {
  const config = CATEGORY_CONFIG[category];
  const Icon = config.icon;

  const renderOpeningTables = () => (
    <>
      <GTOTable
        title="Opening Ranges (RFI)"
        subtitle="All positions - raise first in frequency"
        data={data.opening_ranges}
        columns={[
          { key: 'position', label: 'Position' },
          { key: 'total_hands', label: 'Hands' },
          { key: 'player_frequency', label: 'Player', isPlayer: true },
          { key: 'gto_frequency', label: 'GTO', isGTO: true },
          { key: 'frequency_diff', label: 'Diff', isDiff: true },
        ]}
        onRowClick={(row) => onRowClick({ scenario: 'opening', position: row.position })}
      />
      {data.steal_attempts && data.steal_attempts.length > 0 && (
        <GTOTable
          title="Steal Attempts"
          subtitle="Late position opens (CO, BTN, SB)"
          data={data.steal_attempts}
          columns={[
            { key: 'position', label: 'Position' },
            { key: 'sample_size', label: 'Opportunities' },
            { key: 'player_frequency', label: 'Player', isPlayer: true },
            { key: 'gto_frequency', label: 'GTO', isGTO: true },
            { key: 'frequency_diff', label: 'Diff', isDiff: true },
          ]}
          onRowClick={(row) => onRowClick({ scenario: 'opening', position: row.position })}
        />
      )}
    </>
  );

  const renderDefenseTables = () => (
    <>
      <GTOTable
        title="Defense vs Opens (Aggregate)"
        subtitle="Your fold/call/3-bet frequencies by position"
        data={data.defense_vs_open}
        columns={[
          { key: 'position', label: 'Position' },
          { key: 'sample_size', label: 'Hands' },
          { key: 'player_fold', label: 'Fold', isPlayer: true },
          { key: 'gto_fold', label: 'GTO', isGTO: true },
          { key: 'fold_diff', label: 'Diff', isDiff: true },
          { key: 'player_call', label: 'Call', isPlayer: true },
          { key: 'gto_call', label: 'GTO', isGTO: true },
          { key: 'call_diff', label: 'Diff', isDiff: true },
          { key: 'player_3bet', label: '3-Bet', isPlayer: true },
          { key: 'gto_3bet', label: 'GTO', isGTO: true },
          { key: '3bet_diff', label: 'Diff', isDiff: true },
        ]}
        onRowClick={(row) => onRowClick({ scenario: 'defense', position: row.position })}
      />
      {data.blind_defense && data.blind_defense.length > 0 && (
        <GTOTable
          title="Blind Defense vs Steals"
          subtitle="Defending from SB/BB against late position opens"
          data={data.blind_defense}
          columns={[
            { key: 'position', label: 'Position' },
            { key: 'sample_size', label: 'Hands' },
            { key: 'player_fold', label: 'Fold', isPlayer: true },
            { key: 'gto_fold', label: 'GTO', isGTO: true },
            { key: 'fold_diff', label: 'Diff', isDiff: true },
            { key: 'player_call', label: 'Call', isPlayer: true },
            { key: 'gto_call', label: 'GTO', isGTO: true },
            { key: 'call_diff', label: 'Diff', isDiff: true },
            { key: 'player_3bet', label: '3-Bet', isPlayer: true },
            { key: 'gto_3bet', label: 'GTO', isGTO: true },
            { key: '3bet_diff', label: 'Diff', isDiff: true },
          ]}
          onRowClick={(row) => onRowClick({ scenario: 'defense', position: row.position })}
        />
      )}
      {data.position_matchups && data.position_matchups.length > 0 && (
        <GTOTable
          title="Defense by Position Matchup"
          subtitle="How you defend vs opens from specific positions"
          data={data.position_matchups}
          columns={[
            { key: 'position', label: 'Your Pos' },
            { key: 'vs_position', label: 'vs' },
            { key: 'sample_size', label: 'n' },
            { key: 'player_fold', label: 'Fold', isPlayer: true },
            { key: 'gto_fold', label: 'GTO', isGTO: true },
            { key: 'fold_diff', label: 'Diff', isDiff: true },
            { key: 'player_call', label: 'Call', isPlayer: true },
            { key: 'gto_call', label: 'GTO', isGTO: true },
            { key: 'call_diff', label: 'Diff', isDiff: true },
            { key: 'player_3bet', label: '3-Bet', isPlayer: true },
            { key: 'gto_3bet', label: 'GTO', isGTO: true },
            { key: '3bet_diff', label: 'Diff', isDiff: true },
          ]}
          onRowClick={(row) => onRowClick({ scenario: 'defense', position: row.position, vsPosition: row.vs_position })}
        />
      )}
    </>
  );

  const renderFacing3BetTables = () => (
    <>
      <GTOTable
        title="Facing 3-Bet (Aggregate)"
        subtitle="Your fold/call/4-bet frequencies after opening"
        data={data.facing_3bet}
        columns={[
          { key: 'position', label: 'Position' },
          { key: 'sample_size', label: 'Hands' },
          { key: 'player_fold', label: 'Fold', isPlayer: true },
          { key: 'gto_fold', label: 'GTO', isGTO: true },
          { key: 'fold_diff', label: 'Diff', isDiff: true },
          { key: 'player_call', label: 'Call', isPlayer: true },
          { key: 'gto_call', label: 'GTO', isGTO: true },
          { key: 'call_diff', label: 'Diff', isDiff: true },
          { key: 'player_4bet', label: '4-Bet', isPlayer: true },
          { key: 'gto_4bet', label: 'GTO', isGTO: true },
          { key: '4bet_diff', label: 'Diff', isDiff: true },
        ]}
        onRowClick={(row) => onRowClick({ scenario: 'facing_3bet', position: row.position })}
      />
      {data.facing_3bet_matchups && data.facing_3bet_matchups.length > 0 && (
        <GTOTable
          title="Facing 3-Bet by Matchup"
          subtitle="Response to 3-bets from specific positions"
          data={data.facing_3bet_matchups}
          columns={[
            { key: 'position', label: 'Your Pos' },
            { key: 'vs_position', label: 'vs 3-Bettor' },
            { key: 'sample_size', label: 'n' },
            { key: 'player_fold', label: 'Fold', isPlayer: true },
            { key: 'gto_fold', label: 'GTO', isGTO: true },
            { key: 'fold_diff', label: 'Diff', isDiff: true },
            { key: 'player_call', label: 'Call', isPlayer: true },
            { key: 'gto_call', label: 'GTO', isGTO: true },
            { key: 'call_diff', label: 'Diff', isDiff: true },
            { key: 'player_4bet', label: '4-Bet', isPlayer: true },
            { key: 'gto_4bet', label: 'GTO', isGTO: true },
            { key: '4bet_diff', label: 'Diff', isDiff: true },
          ]}
          onRowClick={(row) => onRowClick({ scenario: 'facing_3bet', position: row.position, vsPosition: row.vs_position })}
        />
      )}
    </>
  );

  const renderFacing4BetTables = () => (
    <>
      {data.facing_4bet_reference && data.facing_4bet_reference.length > 0 && (
        <GTOTable
          title="Facing 4-Bet"
          subtitle="Your response when your 3-bet gets 4-bet"
          data={data.facing_4bet_reference}
          columns={[
            { key: 'position', label: 'Your Pos' },
            { key: 'vs_position', label: 'vs' },
            { key: 'sample_size', label: 'n' },
            { key: 'player_fold', label: 'Fold', isPlayer: true },
            { key: 'gto_fold', label: 'GTO', isGTO: true },
            { key: 'fold_diff', label: 'Diff', isDiff: true },
            { key: 'player_call', label: 'Call', isPlayer: true },
            { key: 'gto_call', label: 'GTO', isGTO: true },
            { key: 'call_diff', label: 'Diff', isDiff: true },
            { key: 'player_5bet', label: '5-Bet', isPlayer: true },
            { key: 'gto_5bet', label: 'GTO', isGTO: true },
            { key: '5bet_diff', label: 'Diff', isDiff: true },
          ]}
          onRowClick={(row) => onRowClick({ scenario: 'facing_4bet', position: row.position, vsPosition: row.vs_position })}
        />
      )}
    </>
  );

  return (
    <div className="space-y-6">
      {/* Header with back button */}
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft size={20} />
          <span>Back</span>
        </button>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
            <Icon size={24} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">{config.title}</h2>
            <p className="text-sm text-gray-500">{config.subtitle}</p>
          </div>
        </div>
      </div>

      {/* Category-specific tables */}
      {category === 'opening' && renderOpeningTables()}
      {category === 'defense' && renderDefenseTables()}
      {category === 'facing_3bet' && renderFacing3BetTables()}
      {category === 'facing_4bet' && renderFacing4BetTables()}
    </div>
  );
};

export default GTOCategoryDetailView;
