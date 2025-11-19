-- Migration script to add board categorization columns to existing gto_solutions table

-- Add config/output file paths
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS config_file VARCHAR(255);
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS output_file VARCHAR(255);

-- Add flop card details
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS flop_card_1 VARCHAR(2);
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS flop_card_2 VARCHAR(2);
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS flop_card_3 VARCHAR(2);

-- Add multi-level board categorization
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS board_category_l1 VARCHAR(30);
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS board_category_l2 VARCHAR(50);
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS board_category_l3 VARCHAR(100);

-- Add board texture properties
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS is_paired BOOLEAN DEFAULT FALSE;
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS is_rainbow BOOLEAN DEFAULT FALSE;
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS is_two_tone BOOLEAN DEFAULT FALSE;
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS is_monotone BOOLEAN DEFAULT FALSE;
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS is_connected BOOLEAN DEFAULT FALSE;
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS is_highly_connected BOOLEAN DEFAULT FALSE;
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS has_broadway BOOLEAN DEFAULT FALSE;
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS is_dry BOOLEAN DEFAULT FALSE;
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS is_wet BOOLEAN DEFAULT FALSE;
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS high_card_rank VARCHAR(2);
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS middle_card_rank VARCHAR(2);
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS low_card_rank VARCHAR(2);

-- Add position context and action sequence
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS position_context VARCHAR(50);
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS action_sequence VARCHAR(100);

-- Add ranges
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS ip_range TEXT;
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS oop_range TEXT;

-- Add solver metadata
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS accuracy DECIMAL(5,3);
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS iterations INTEGER;
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS solving_time_seconds INTEGER;
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT;
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMP;

-- Rename effective_stack column if it exists as stack_depth
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'gto_solutions' AND column_name = 'stack_depth') THEN
        ALTER TABLE gto_solutions RENAME COLUMN stack_depth TO effective_stack;
    END IF;
EXCEPTION
    WHEN duplicate_column THEN
        -- Column already exists, ignore
        NULL;
END $$;

-- Add effective_stack if not exists
ALTER TABLE gto_solutions ADD COLUMN IF NOT EXISTS effective_stack DECIMAL(8,2);

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_gto_category_l1 ON gto_solutions(board_category_l1);
CREATE INDEX IF NOT EXISTS idx_gto_category_l2 ON gto_solutions(board_category_l2);
CREATE INDEX IF NOT EXISTS idx_gto_category_l3 ON gto_solutions(board_category_l3);
CREATE INDEX IF NOT EXISTS idx_gto_high_card ON gto_solutions(high_card_rank);
CREATE INDEX IF NOT EXISTS idx_gto_texture ON gto_solutions(is_rainbow, is_connected);

-- Verify migration
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'gto_solutions') as column_count
FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'gto_solutions';
