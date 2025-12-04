/**
 * Shared GTO utilities for consistent leak analysis across pages.
 * This ensures MyGame and PlayerProfile use identical logic.
 */

import type { PriorityLeak, GTOPositionalLeak } from '../types';

/**
 * Map category from backend format to display format.
 * Used consistently across all pages.
 */
export const mapCategory = (category: PriorityLeak['category']): string => {
  switch (category) {
    case 'opening': return 'Opening';
    case 'defense': return 'Defense';
    case 'facing_3bet': return 'Facing 3-Bet';
    case 'facing_4bet': return 'Facing 4-Bet';
    default: return category;
  }
};

/**
 * Map action from backend format to display format.
 * Used consistently across all pages.
 */
export const mapAction = (action: string): string => {
  switch (action) {
    case 'open': return 'Open';
    case 'fold': return 'Fold';
    case 'call': return 'Call';
    case '3bet': return '3-Bet';
    case '4bet': return '4-Bet';
    case '5bet': return '5-Bet';
    default: return action;
  }
};

/**
 * Map confidence level from backend format to LeakAnalysisView format.
 */
export const mapConfidence = (level: string): 'low' | 'moderate' | 'high' => {
  switch (level) {
    case 'high': return 'high';
    case 'moderate': return 'moderate';
    default: return 'low';
  }
};

/**
 * Convert priority_leaks from backend to GTOPositionalLeak format for LeakAnalysisView.
 * This is the single source of truth for this transformation.
 *
 * @param priorityLeaks - Array of priority leaks from backend API
 * @returns Array of GTOPositionalLeak objects for LeakAnalysisView
 */
export const mapPriorityLeaksToGTOLeaks = (
  priorityLeaks: PriorityLeak[] | undefined | null
): GTOPositionalLeak[] => {
  if (!priorityLeaks) return [];

  return priorityLeaks.map(pl => ({
    category: mapCategory(pl.category),
    position: pl.position,
    vsPosition: pl.vs_position || undefined,
    action: mapAction(pl.action),
    playerValue: pl.overall_value,
    gtoValue: pl.gto_value,
    deviation: pl.overall_deviation,
    severity: (pl.leak_severity === 'major' ? 'major' : 'moderate') as 'major' | 'moderate',
    sampleSize: pl.overall_sample,
    confidence: mapConfidence(pl.confidence_level),
  }));
};
