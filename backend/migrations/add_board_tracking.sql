-- Migration: Add board tracking to hand history tables
-- Purpose: Enable board-specific player stat tracking for GTO deviation analysis

-- Add board cards to raw_hands table
ALTER TABLE raw_hands
ADD COLUMN IF NOT EXISTS flop_card_1 VARCHAR(2),
ADD COLUMN IF NOT EXISTS flop_card_2 VARCHAR(2),
ADD COLUMN IF NOT EXISTS flop_card_3 VARCHAR(2),
ADD COLUMN IF NOT EXISTS turn_card VARCHAR(2),
ADD COLUMN IF NOT EXISTS river_card VARCHAR(2);

-- Add board categorization to player_hand_summary table
ALTER TABLE player_hand_summary
ADD COLUMN IF NOT EXISTS board_category_l1 VARCHAR(30),
ADD COLUMN IF NOT EXISTS board_category_l2 VARCHAR(50),
ADD COLUMN IF NOT EXISTS board_category_l3 VARCHAR(100),
ADD COLUMN IF NOT EXISTS is_paired BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_rainbow BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_two_tone BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_monotone BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_connected BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_highly_connected BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS has_broadway BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_dry BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_wet BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS high_card_rank VARCHAR(2),
ADD COLUMN IF NOT EXISTS middle_card_rank VARCHAR(2),
ADD COLUMN IF NOT EXISTS low_card_rank VARCHAR(2);

-- Create player_board_stats table for aggregated board-specific statistics
CREATE TABLE IF NOT EXISTS player_board_stats (
    stat_id SERIAL PRIMARY KEY,
    player_name VARCHAR(255) NOT NULL,
    board_category_l1 VARCHAR(30) NOT NULL,
    board_category_l2 VARCHAR(50),
    board_category_l3 VARCHAR(100),

    -- Sample size
    total_hands INTEGER DEFAULT 0,
    hands_saw_flop INTEGER DEFAULT 0,

    -- Preflop stats (same across board categories, but included for completeness)
    vpip_pct DECIMAL(5,2),
    pfr_pct DECIMAL(5,2),
    three_bet_pct DECIMAL(5,2),

    -- Board-specific postflop stats
    cbet_flop_pct DECIMAL(5,2),
    cbet_turn_pct DECIMAL(5,2),
    cbet_river_pct DECIMAL(5,2),

    fold_to_cbet_flop_pct DECIMAL(5,2),
    fold_to_cbet_turn_pct DECIMAL(5,2),
    fold_to_cbet_river_pct DECIMAL(5,2),

    call_cbet_flop_pct DECIMAL(5,2),
    call_cbet_turn_pct DECIMAL(5,2),

    raise_cbet_flop_pct DECIMAL(5,2),
    raise_cbet_turn_pct DECIMAL(5,2),

    -- Showdown stats by board type
    wtsd_pct DECIMAL(5,2),
    wsd_pct DECIMAL(5,2),

    -- Aggression by board type
    af DECIMAL(5,2),
    afq DECIMAL(5,2),

    -- Timestamps
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE(player_name, board_category_l1, board_category_l2, board_category_l3)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_player_board_stats_player ON player_board_stats(player_name);
CREATE INDEX IF NOT EXISTS idx_player_board_stats_l1 ON player_board_stats(board_category_l1);
CREATE INDEX IF NOT EXISTS idx_player_board_stats_l2 ON player_board_stats(board_category_l2);
CREATE INDEX IF NOT EXISTS idx_player_board_stats_l3 ON player_board_stats(board_category_l3);
CREATE INDEX IF NOT EXISTS idx_player_hand_summary_board_l1 ON player_hand_summary(board_category_l1);
CREATE INDEX IF NOT EXISTS idx_player_hand_summary_board_l2 ON player_hand_summary(board_category_l2);
CREATE INDEX IF NOT EXISTS idx_player_hand_summary_board_l3 ON player_hand_summary(board_category_l3);

-- Verify migration
SELECT
    'raw_hands' as table_name,
    COUNT(*) FILTER (WHERE column_name IN ('flop_card_1', 'flop_card_2', 'flop_card_3', 'turn_card', 'river_card')) as new_columns
FROM information_schema.columns
WHERE table_name = 'raw_hands'
UNION ALL
SELECT
    'player_hand_summary' as table_name,
    COUNT(*) FILTER (WHERE column_name IN ('board_category_l1', 'board_category_l2', 'board_category_l3', 'is_paired', 'is_rainbow')) as new_columns
FROM information_schema.columns
WHERE table_name = 'player_hand_summary'
UNION ALL
SELECT
    'player_board_stats' as table_name,
    COUNT(*) as columns
FROM information_schema.columns
WHERE table_name = 'player_board_stats';
