-- Migration: Add facing 4-bet tracking columns to player_hand_summary
-- Purpose: Enable position-specific defense analysis and facing 4-bet GTO comparison
-- Date: 2025-01-XX

-- Add raiser_position to track who opened (for position-specific defense like BB vs BTN)
ALTER TABLE player_hand_summary
ADD COLUMN IF NOT EXISTS raiser_position VARCHAR(10);

-- Add facing 4-bet tracking columns
ALTER TABLE player_hand_summary
ADD COLUMN IF NOT EXISTS faced_four_bet BOOLEAN DEFAULT FALSE;

ALTER TABLE player_hand_summary
ADD COLUMN IF NOT EXISTS folded_to_four_bet BOOLEAN DEFAULT FALSE;

ALTER TABLE player_hand_summary
ADD COLUMN IF NOT EXISTS called_four_bet BOOLEAN DEFAULT FALSE;

ALTER TABLE player_hand_summary
ADD COLUMN IF NOT EXISTS five_bet BOOLEAN DEFAULT FALSE;

-- Add index for position-specific queries
CREATE INDEX IF NOT EXISTS idx_player_summary_raiser_pos ON player_hand_summary(raiser_position);

-- Verify columns added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'player_hand_summary'
  AND column_name IN ('raiser_position', 'faced_four_bet', 'folded_to_four_bet', 'called_four_bet', 'five_bet')
ORDER BY column_name;
