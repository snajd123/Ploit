-- ============================================================================
-- NEW GTO ARCHITECTURE - DATABASE SCHEMA
-- Purpose: GTOWizard-based GTO data for leak detection & exploitation
-- ============================================================================

-- ----------------------------------------------------------------------------
-- TABLE: gto_scenarios
-- Metadata for each GTO scenario (preflop or postflop)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gto_scenarios (
    scenario_id SERIAL PRIMARY KEY,
    scenario_name VARCHAR(100) UNIQUE NOT NULL,  -- e.g., 'BB_vs_UTG_call', 'AsKsQs_BTN_cbet'

    -- Scenario classification
    street VARCHAR(10) NOT NULL,                 -- 'preflop', 'flop', 'turn', 'river'
    category VARCHAR(50) NOT NULL,               -- 'opening', 'defense', 'facing_3bet', 'cbet', etc.

    -- Preflop specific
    position VARCHAR(10),                        -- 'UTG', 'BB', 'BTN', etc.
    action VARCHAR(20),                          -- 'open', 'call', 'fold', '3bet', '4bet', 'allin'
    opponent_position VARCHAR(10),               -- 'UTG', NULL for opens

    -- Postflop specific (for future use)
    board VARCHAR(20),                           -- e.g., 'AsKsQs', 'PREFLOP'
    board_texture VARCHAR(50),                   -- e.g., 'monotone', 'dry', 'wet'
    position_context VARCHAR(20),                -- 'IP', 'OOP'
    action_node VARCHAR(50),                     -- 'facing_cbet', 'facing_raise'

    -- Metadata
    data_source VARCHAR(50) DEFAULT 'gtowizard', -- 'gtowizard', 'solver', 'custom'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_gto_scenarios_street ON gto_scenarios(street);
CREATE INDEX idx_gto_scenarios_category ON gto_scenarios(category);
CREATE INDEX idx_gto_scenarios_position ON gto_scenarios(position);
CREATE INDEX idx_gto_scenarios_board ON gto_scenarios(board);

-- ----------------------------------------------------------------------------
-- TABLE: gto_frequencies
-- Stores GTO frequencies for each hand in each scenario
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gto_frequencies (
    frequency_id SERIAL PRIMARY KEY,
    scenario_id INTEGER NOT NULL REFERENCES gto_scenarios(scenario_id) ON DELETE CASCADE,

    -- Hand identification
    hand VARCHAR(4) NOT NULL,                    -- 'AKo', 'JTs', '22', 'AhKd' (combo for postflop)

    -- Position (whose strategy is this?)
    position VARCHAR(10) NOT NULL,               -- 'BB', 'UTG', 'IP', 'OOP', 'BTN', etc.

    -- Frequency data
    frequency DECIMAL(10, 8) NOT NULL,           -- 0.0 to 1.0 (absolute frequency)

    -- Constraints
    CONSTRAINT unique_scenario_hand_position UNIQUE (scenario_id, hand, position),
    CONSTRAINT check_frequency_range CHECK (frequency >= 0 AND frequency <= 1)
);

CREATE INDEX idx_gto_frequencies_scenario ON gto_frequencies(scenario_id);
CREATE INDEX idx_gto_frequencies_hand ON gto_frequencies(hand);
CREATE INDEX idx_gto_frequencies_position ON gto_frequencies(position);
CREATE INDEX idx_gto_frequencies_freq ON gto_frequencies(frequency);

-- ----------------------------------------------------------------------------
-- TABLE: player_actions
-- Stores actual player actions from hand histories for leak detection
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_actions (
    action_id SERIAL PRIMARY KEY,

    -- Player identification
    player_name VARCHAR(100) NOT NULL,
    hand_id VARCHAR(100) NOT NULL,               -- External hand ID from tracker

    -- Action context
    timestamp TIMESTAMP NOT NULL,
    scenario_id INTEGER NOT NULL REFERENCES gto_scenarios(scenario_id),

    -- Hole cards
    hole_cards VARCHAR(4) NOT NULL,              -- 'AKo', 'JTs', etc.

    -- Action taken
    action_taken VARCHAR(20) NOT NULL,           -- 'fold', 'call', 'raise', '3bet', etc.

    -- GTO analysis (cached)
    gto_frequency DECIMAL(10, 8),                -- What GTO says for this hand/action
    ev_loss_bb DECIMAL(10, 4),                   -- Estimated EV loss in big blinds
    is_mistake BOOLEAN,                          -- True if significant deviation
    mistake_severity VARCHAR(20),                -- 'minor', 'moderate', 'major', 'critical'

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_player_actions_player ON player_actions(player_name);
CREATE INDEX idx_player_actions_scenario ON player_actions(scenario_id);
CREATE INDEX idx_player_actions_timestamp ON player_actions(timestamp);
CREATE INDEX idx_player_actions_mistake ON player_actions(is_mistake);
CREATE INDEX idx_player_actions_hand_id ON player_actions(hand_id);

-- ----------------------------------------------------------------------------
-- TABLE: player_gto_stats (renamed to avoid conflict with existing player_stats)
-- Aggregated leak statistics per player per scenario
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_gto_stats (
    stat_id SERIAL PRIMARY KEY,

    -- Player and scenario
    player_name VARCHAR(100) NOT NULL,
    scenario_id INTEGER NOT NULL REFERENCES gto_scenarios(scenario_id),

    -- Sample size
    total_hands INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Frequency comparison
    player_frequency DECIMAL(10, 8),             -- How often player takes this action
    gto_frequency DECIMAL(10, 8),                -- How often GTO says to take it
    frequency_diff DECIMAL(10, 8),               -- player - gto (positive = overfolding/overcalling)

    -- EV metrics
    total_ev_loss_bb DECIMAL(10, 4),             -- Total BB lost in this scenario
    avg_ev_loss_bb DECIMAL(10, 4),               -- Average BB lost per hand

    -- Leak classification
    leak_type VARCHAR(50),                       -- 'overfold', 'underfold', 'overcall', 'under3bet', etc.
    leak_severity VARCHAR(20),                   -- 'minor', 'moderate', 'major', 'critical'

    -- Exploit recommendation
    exploit_description TEXT,                     -- Human-readable exploit
    exploit_value_bb_100 DECIMAL(10, 4),         -- Expected value of exploit per 100 hands
    exploit_confidence DECIMAL(5, 2),            -- 0-100 confidence based on sample size

    CONSTRAINT unique_player_scenario UNIQUE (player_name, scenario_id)
);

CREATE INDEX idx_player_gto_stats_player ON player_gto_stats(player_name);
CREATE INDEX idx_player_gto_stats_scenario ON player_gto_stats(scenario_id);
CREATE INDEX idx_player_gto_stats_leak_severity ON player_gto_stats(leak_severity);
CREATE INDEX idx_player_gto_stats_ev_loss ON player_gto_stats(total_ev_loss_bb);

-- ----------------------------------------------------------------------------
-- TABLE: hand_types (Helper)
-- Maps combos to hand types for preflop aggregation
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hand_types (
    combo VARCHAR(4) PRIMARY KEY,                -- 'AhKd', '2c2d', etc.
    hand VARCHAR(4) NOT NULL,                    -- 'AKo', '22', 'JTs'
    rank1 VARCHAR(1) NOT NULL,
    rank2 VARCHAR(1) NOT NULL,
    suit1 VARCHAR(1) NOT NULL,
    suit2 VARCHAR(1) NOT NULL,
    is_pair BOOLEAN NOT NULL,
    is_suited BOOLEAN NOT NULL
);

CREATE INDEX idx_hand_types_hand ON hand_types(hand);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Check tables were created
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE 'gto_%' OR table_name IN ('player_actions', 'player_gto_stats', 'hand_types')
ORDER BY table_name;
