-- GTO Solutions Database Schema
-- Adds support for GTO solver solutions with multi-level board categorization

-- ============================================
-- Table: gto_solutions
-- Stores individual GTO solver solutions
-- ============================================
CREATE TABLE IF NOT EXISTS gto_solutions (
    solution_id SERIAL PRIMARY KEY,

    -- Scenario identification
    scenario_name VARCHAR(100) NOT NULL UNIQUE,  -- e.g., "019_SRP_A83r_check"
    config_file VARCHAR(255),                    -- Path to config file
    output_file VARCHAR(255),                    -- Path to solution JSON

    -- Board information
    board VARCHAR(20) NOT NULL,                  -- e.g., "As8h3c" or "Ks9h4c"
    flop_card_1 VARCHAR(2),                      -- e.g., "As"
    flop_card_2 VARCHAR(2),                      -- e.g., "8h"
    flop_card_3 VARCHAR(2),                      -- e.g., "3c"

    -- Multi-level board categorization (Level 1: High-level, 7 categories)
    board_category_l1 VARCHAR(30) NOT NULL,      -- "Ace-high", "King-high", "Queen-high", "Jack-high",
                                                  -- "Ten-high", "Nine-or-lower", "Paired"

    -- Multi-level board categorization (Level 2: Medium granularity, ~20 categories)
    board_category_l2 VARCHAR(50) NOT NULL,      -- Examples:
                                                  -- "Ace-high-rainbow", "Ace-high-2tone", "Ace-high-monotone"
                                                  -- "King-high-rainbow", "King-high-2tone", etc.
                                                  -- "Paired-highcard", "Paired-lowcard"

    -- Multi-level board categorization (Level 3: Fine granularity, ~100+ categories)
    board_category_l3 VARCHAR(100) NOT NULL,     -- Examples:
                                                  -- "Ace-high-rainbow-dry", "Ace-high-rainbow-connected"
                                                  -- "King-high-2tone-broadway", "King-high-rainbow-lowconnected"
                                                  -- Captures very specific board properties

    -- Board texture properties (for fine-grained categorization)
    is_paired BOOLEAN DEFAULT FALSE,
    is_rainbow BOOLEAN DEFAULT FALSE,
    is_two_tone BOOLEAN DEFAULT FALSE,
    is_monotone BOOLEAN DEFAULT FALSE,
    is_connected BOOLEAN DEFAULT FALSE,          -- Any 2 cards within 1 rank
    is_highly_connected BOOLEAN DEFAULT FALSE,   -- All 3 cards within 3 ranks
    has_broadway BOOLEAN DEFAULT FALSE,          -- Contains T, J, Q, K, or A
    is_dry BOOLEAN DEFAULT FALSE,                -- Low connectivity, few draws
    is_wet BOOLEAN DEFAULT FALSE,                -- High connectivity, many draws
    high_card_rank VARCHAR(2),                   -- e.g., "A", "K", "Q"
    middle_card_rank VARCHAR(2),
    low_card_rank VARCHAR(2),

    -- Scenario context
    scenario_type VARCHAR(50),                   -- "SRP" (Single Raised Pot), "3BP" (3-bet pot), "4BP", etc.
    position_context VARCHAR(50),                -- "IP" (In Position), "OOP" (Out of Position)
    action_sequence VARCHAR(100),                -- "cbet", "check", "check_raise", etc.
    pot_size DECIMAL(8,2),
    effective_stack DECIMAL(8,2),

    -- Range information
    ip_range TEXT,                               -- Range string from config
    oop_range TEXT,

    -- Solution metadata
    accuracy DECIMAL(5,3),                       -- Solver accuracy setting (e.g., 0.5%)
    iterations INT,                               -- Max iterations used
    solving_time_seconds INT,
    file_size_bytes BIGINT,

    -- Timestamps
    solved_at TIMESTAMP,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP,

    -- Indexes for fast lookups
    CONSTRAINT unique_scenario UNIQUE(scenario_name)
);

CREATE INDEX IF NOT EXISTS idx_gto_board ON gto_solutions(board);
CREATE INDEX IF NOT EXISTS idx_gto_category_l1 ON gto_solutions(board_category_l1);
CREATE INDEX IF NOT EXISTS idx_gto_category_l2 ON gto_solutions(board_category_l2);
CREATE INDEX IF NOT EXISTS idx_gto_category_l3 ON gto_solutions(board_category_l3);
CREATE INDEX IF NOT EXISTS idx_gto_scenario_type ON gto_solutions(scenario_type);
CREATE INDEX IF NOT EXISTS idx_gto_high_card ON gto_solutions(high_card_rank);
CREATE INDEX IF NOT EXISTS idx_gto_texture ON gto_solutions(is_rainbow, is_connected);

-- ============================================
-- Table: gto_category_aggregates
-- Pre-computed aggregates for each category
-- ============================================
CREATE TABLE IF NOT EXISTS gto_category_aggregates (
    aggregate_id SERIAL PRIMARY KEY,

    -- Category information (one row per category)
    category_level INT NOT NULL,                 -- 1, 2, or 3
    category_name VARCHAR(100) NOT NULL,         -- The category name

    -- Aggregate statistics
    solution_count INT DEFAULT 0,                -- Number of solutions in this category
    total_scenarios INT,                          -- Total possible scenarios in category (for coverage %)
    coverage_pct DECIMAL(5,2),                   -- solution_count / total_scenarios * 100

    -- Representative board for this category
    representative_board VARCHAR(20),            -- Most "typical" board in category
    representative_solution_id INT REFERENCES gto_solutions(solution_id),

    -- Category characteristics (averaged across all solutions)
    avg_pot_size DECIMAL(8,2),
    avg_stack_size DECIMAL(8,2),

    -- Common actions in this category (JSON array)
    common_actions JSONB,                        -- e.g., ["CHECK", "BET 50%", "BET 75%"]

    -- Strategy patterns (aggregated from all solutions in category)
    avg_cbet_freq DECIMAL(5,2),                  -- Average c-bet frequency
    avg_check_freq DECIMAL(5,2),
    avg_fold_to_cbet_freq DECIMAL(5,2),

    -- Metadata
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_category UNIQUE(category_level, category_name)
);

CREATE INDEX IF NOT EXISTS idx_gto_agg_level ON gto_category_aggregates(category_level);
CREATE INDEX IF NOT EXISTS idx_gto_agg_name ON gto_category_aggregates(category_name);
CREATE INDEX IF NOT EXISTS idx_gto_agg_coverage ON gto_category_aggregates(coverage_pct);

-- ============================================
-- Table: gto_strategy_cache
-- Cached strategy data for quick lookup
-- ============================================
CREATE TABLE IF NOT EXISTS gto_strategy_cache (
    cache_id SERIAL PRIMARY KEY,
    solution_id INT REFERENCES gto_solutions(solution_id) ON DELETE CASCADE,

    -- Hand-specific strategy data
    hand VARCHAR(4) NOT NULL,                    -- e.g., "AKs", "QQ"
    position VARCHAR(10) NOT NULL,               -- "IP" or "OOP"
    street VARCHAR(10) DEFAULT 'flop',           -- "flop", "turn", "river"
    action_node VARCHAR(50),                     -- Node in game tree

    -- Strategy frequencies (JSON for flexibility)
    strategy_json JSONB NOT NULL,                -- Full strategy for this hand/node

    -- Most common action
    primary_action VARCHAR(50),                  -- e.g., "BET 75%", "CHECK", "FOLD"
    primary_action_freq DECIMAL(5,2),            -- Frequency of primary action (0-100)

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_cache_entry UNIQUE(solution_id, hand, position, street, action_node)
);

CREATE INDEX IF NOT EXISTS idx_gto_cache_solution ON gto_strategy_cache(solution_id);
CREATE INDEX IF NOT EXISTS idx_gto_cache_hand ON gto_strategy_cache(hand);
CREATE INDEX IF NOT EXISTS idx_gto_cache_position ON gto_strategy_cache(position);

-- ============================================
-- Verify Tables Created
-- ============================================
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
    AND table_name IN ('gto_solutions', 'gto_category_aggregates', 'gto_strategy_cache')
ORDER BY table_name;
