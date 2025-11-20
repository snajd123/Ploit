-- Migration: Redesign gto_solutions table to match actual JSON structure
-- Removes columns that don't exist in solver output
-- Adds columns for data that IS in the JSON

-- Drop old table
DROP TABLE IF EXISTS gto_solutions CASCADE;

-- Create new streamlined table based on actual JSON structure
CREATE TABLE gto_solutions (
    -- Primary key
    solution_id SERIAL PRIMARY KEY,

    -- Scenario identification
    scenario_name VARCHAR(255) UNIQUE NOT NULL,
    scenario_type VARCHAR(50),  -- SRP, 3BP, 4BP
    action_sequence VARCHAR(50), -- cbet, check, raise, etc.
    position_context VARCHAR(20), -- IP, OOP

    -- Board information
    board VARCHAR(10) NOT NULL,  -- e.g., "AhKs7d"
    flop_card_1 VARCHAR(2),
    flop_card_2 VARCHAR(2),
    flop_card_3 VARCHAR(2),

    -- Board categorization (from BoardCategorizer)
    board_category_l1 VARCHAR(30),  -- "Ace-high", "King-high", etc.
    board_category_l2 VARCHAR(50),  -- "Ace-high-rainbow", etc.
    board_category_l3 VARCHAR(100), -- "Ace-high-rainbow-dry", etc.
    is_paired BOOLEAN DEFAULT FALSE,
    is_rainbow BOOLEAN DEFAULT FALSE,
    is_two_tone BOOLEAN DEFAULT FALSE,
    is_monotone BOOLEAN DEFAULT FALSE,
    is_connected BOOLEAN DEFAULT FALSE,
    is_highly_connected BOOLEAN DEFAULT FALSE,
    has_broadway BOOLEAN DEFAULT FALSE,
    is_dry BOOLEAN DEFAULT FALSE,
    is_wet BOOLEAN DEFAULT FALSE,
    high_card_rank VARCHAR(2),
    middle_card_rank VARCHAR(2),
    low_card_rank VARCHAR(2),

    -- Scenario parameters (from config file)
    pot_size DECIMAL(10, 2),
    effective_stack DECIMAL(10, 2),
    ip_range TEXT,
    oop_range TEXT,

    -- Solver parameters (from config file)
    accuracy DECIMAL(10, 6),
    iterations INTEGER,

    -- Aggregated GTO frequencies (calculated from strategy)
    gto_check_frequency DECIMAL(5, 2),  -- % of range that checks
    gto_bet_frequency DECIMAL(5, 2),    -- % of range that bets
    gto_raise_frequency DECIMAL(5, 2),  -- % of range that raises
    gto_fold_frequency DECIMAL(5, 2),   -- % of range that folds
    gto_call_frequency DECIMAL(5, 2),   -- % of range that calls

    -- Raw JSON data (from solver output)
    actions JSONB,  -- Array of available actions: ["CHECK", "BET 2.000000", ...]
    node_type VARCHAR(50),  -- "action_node", etc.
    player SMALLINT,  -- 0 or 1 (which player acts)

    -- Full strategy data (optional - for advanced queries)
    -- Contains all 279 hand combos with their frequencies
    hand_strategies JSONB,  -- {"2d2c": [0.95, 0.05, ...], "AcKc": [...], ...}

    -- File metadata
    config_file TEXT,
    output_file TEXT,
    file_size_bytes BIGINT,
    solved_at TIMESTAMP,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes for common queries
    INDEX idx_gto_board_category_l1 (board_category_l1),
    INDEX idx_gto_board_category_l2 (board_category_l2),
    INDEX idx_gto_board_category_l3 (board_category_l3),
    INDEX idx_gto_scenario_type (scenario_type),
    INDEX idx_gto_is_paired (is_paired),
    INDEX idx_gto_is_rainbow (is_rainbow),
    INDEX idx_gto_is_dry (is_dry),
    INDEX idx_gto_is_wet (is_wet)
);

-- Verify table structure
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'gto_solutions'
ORDER BY ordinal_position;
