-- ============================================================================
-- PLOIT GTO DATABASE SCHEMA
-- Purpose: Store GTOWizard preflop ranges for leak detection & exploitation
-- ============================================================================

-- ----------------------------------------------------------------------------
-- TABLE: scenarios
-- Metadata about each preflop scenario
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scenarios (
    id SERIAL PRIMARY KEY,
    scenario_name VARCHAR(100) UNIQUE NOT NULL,  -- e.g., 'BB_vs_UTG_call'
    category VARCHAR(50) NOT NULL,               -- e.g., 'defense', 'facing_3bet', 'opening'
    position VARCHAR(10) NOT NULL,               -- e.g., 'BB', 'UTG', 'BTN'
    action VARCHAR(20) NOT NULL,                 -- e.g., 'call', 'fold', '3bet', 'allin'
    opponent_position VARCHAR(10),               -- e.g., 'UTG', NULL for opens
    description TEXT,                            -- Human-readable description
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scenarios_category ON scenarios(category);
CREATE INDEX idx_scenarios_position ON scenarios(position);
CREATE INDEX idx_scenarios_action ON scenarios(action);

-- ----------------------------------------------------------------------------
-- TABLE: preflop_combos
-- Raw combo-level frequency data from GTOWizard
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS preflop_combos (
    id SERIAL PRIMARY KEY,
    scenario_id INTEGER NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    combo VARCHAR(4) NOT NULL,                   -- e.g., 'AhKd', '2d2c'
    frequency DECIMAL(10, 8) NOT NULL,           -- e.g., 0.595 (59.5%)

    CONSTRAINT unique_scenario_combo UNIQUE (scenario_id, combo),
    CONSTRAINT check_frequency CHECK (frequency >= 0 AND frequency <= 1),
    CONSTRAINT check_combo_format CHECK (length(combo) = 4)
);

CREATE INDEX idx_combos_scenario ON preflop_combos(scenario_id);
CREATE INDEX idx_combos_combo ON preflop_combos(combo);
CREATE INDEX idx_combos_frequency ON preflop_combos(frequency);

-- ----------------------------------------------------------------------------
-- TABLE: hand_types
-- Mapping of combos to hand types (for aggregation)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hand_types (
    combo VARCHAR(4) PRIMARY KEY,
    hand VARCHAR(4) NOT NULL,                    -- e.g., 'AKo', 'JTs', '22'
    rank1 VARCHAR(1) NOT NULL,                   -- e.g., 'A', 'J', '2'
    rank2 VARCHAR(1) NOT NULL,
    suit1 VARCHAR(1) NOT NULL,                   -- e.g., 'h', 'd', 's', 'c'
    suit2 VARCHAR(1) NOT NULL,
    is_pair BOOLEAN NOT NULL,
    is_suited BOOLEAN NOT NULL
);

CREATE INDEX idx_hand_types_hand ON hand_types(hand);
CREATE INDEX idx_hand_types_pair ON hand_types(is_pair);
CREATE INDEX idx_hand_types_suited ON hand_types(is_suited);

-- ----------------------------------------------------------------------------
-- VIEW: preflop_hands
-- Aggregated hand-level frequencies (average of all combos for each hand)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW preflop_hands AS
SELECT
    s.scenario_name,
    s.category,
    s.position,
    s.action,
    s.opponent_position,
    ht.hand,
    AVG(pc.frequency) as avg_frequency,
    COUNT(pc.combo) as num_combos,
    SUM(pc.frequency) as total_frequency,
    ht.is_pair,
    ht.is_suited
FROM preflop_combos pc
JOIN scenarios s ON pc.scenario_id = s.id
JOIN hand_types ht ON pc.combo = ht.combo
GROUP BY s.scenario_name, s.category, s.position, s.action, s.opponent_position,
         ht.hand, ht.is_pair, ht.is_suited;

-- ----------------------------------------------------------------------------
-- VIEW: scenario_summaries
-- Quick stats for each scenario
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW scenario_summaries AS
SELECT
    s.scenario_name,
    s.category,
    s.position,
    s.action,
    COUNT(pc.combo) as total_combos,
    SUM(pc.frequency) as weighted_combos,
    (SUM(pc.frequency) / 13.26) * 100 as range_percentage,  -- 1326 total combos / 100
    COUNT(DISTINCT ht.hand) as unique_hands,
    COUNT(CASE WHEN pc.frequency = 1.0 THEN 1 END) as pure_combos,
    COUNT(CASE WHEN pc.frequency > 0 AND pc.frequency < 1.0 THEN 1 END) as mixed_combos
FROM scenarios s
JOIN preflop_combos pc ON s.id = pc.scenario_id
JOIN hand_types ht ON pc.combo = ht.combo
GROUP BY s.scenario_name, s.category, s.position, s.action;

-- ----------------------------------------------------------------------------
-- FUNCTION: get_gto_frequency
-- Get GTO frequency for a specific hand in a scenario
-- Usage: SELECT get_gto_frequency('BB_vs_UTG_call', 'AKo');
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_gto_frequency(
    p_scenario VARCHAR(100),
    p_hand VARCHAR(4)
) RETURNS DECIMAL(10, 8) AS $$
DECLARE
    v_frequency DECIMAL(10, 8);
BEGIN
    SELECT AVG(pc.frequency) INTO v_frequency
    FROM preflop_combos pc
    JOIN scenarios s ON pc.scenario_id = s.id
    JOIN hand_types ht ON pc.combo = ht.combo
    WHERE s.scenario_name = p_scenario
      AND ht.hand = p_hand;

    RETURN COALESCE(v_frequency, 0);
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
-- FUNCTION: get_hand_action_breakdown
-- Get all action frequencies for a hand in a situation
-- Usage: SELECT * FROM get_hand_action_breakdown('BB', 'UTG', 'AKo');
-- Returns: fold%, call%, 3bet%, etc.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_hand_action_breakdown(
    p_position VARCHAR(10),
    p_opponent VARCHAR(10),
    p_hand VARCHAR(4)
) RETURNS TABLE (
    action VARCHAR(20),
    frequency DECIMAL(10, 8),
    percentage DECIMAL(5, 2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.action,
        AVG(pc.frequency) as frequency,
        ROUND((AVG(pc.frequency) * 100)::numeric, 2) as percentage
    FROM preflop_combos pc
    JOIN scenarios s ON pc.scenario_id = s.id
    JOIN hand_types ht ON pc.combo = ht.combo
    WHERE s.position = p_position
      AND s.opponent_position = p_opponent
      AND ht.hand = p_hand
    GROUP BY s.action
    ORDER BY frequency DESC;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
-- TABLE: player_hands (for leak detection)
-- Store actual hands played for analysis
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_hands (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(100) NOT NULL,
    hand_id VARCHAR(100) NOT NULL,               -- External hand ID from tracker
    timestamp TIMESTAMP NOT NULL,
    position VARCHAR(10) NOT NULL,
    hole_cards VARCHAR(4) NOT NULL,              -- e.g., 'AKo', 'JTs'
    scenario VARCHAR(100) NOT NULL,              -- e.g., 'BB_vs_UTG_call'
    action_taken VARCHAR(20) NOT NULL,           -- e.g., 'fold', 'call', '3bet'
    gto_frequency DECIMAL(10, 8),                -- Cached GTO frequency
    is_gto BOOLEAN,                              -- Did player take GTO action?
    ev_loss DECIMAL(10, 4),                      -- Estimated EV loss from deviation

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_player_hands_player ON player_hands(player_name);
CREATE INDEX idx_player_hands_scenario ON player_hands(scenario);
CREATE INDEX idx_player_hands_timestamp ON player_hands(timestamp);
CREATE INDEX idx_player_hands_is_gto ON player_hands(is_gto);

-- ----------------------------------------------------------------------------
-- TABLE: player_stats
-- Aggregated leak statistics per player
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_stats (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,               -- e.g., 'defense', 'facing_3bet'
    scenario VARCHAR(100) NOT NULL,              -- e.g., 'BB_vs_UTG_call'

    total_hands INTEGER NOT NULL DEFAULT 0,
    gto_hands INTEGER NOT NULL DEFAULT 0,        -- Hands played according to GTO
    leak_hands INTEGER NOT NULL DEFAULT 0,       -- Hands with deviations

    gto_percentage DECIMAL(5, 2),                -- % of hands played GTO
    avg_ev_loss DECIMAL(10, 4),                  -- Average EV loss per hand
    total_ev_loss DECIMAL(10, 4),                -- Total EV lost in this scenario

    biggest_leak VARCHAR(200),                   -- Description of main leak
    exploit_recommendation TEXT,                 -- How to exploit this leak

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_player_scenario UNIQUE (player_name, scenario)
);

CREATE INDEX idx_player_stats_player ON player_stats(player_name);
CREATE INDEX idx_player_stats_category ON player_stats(category);
CREATE INDEX idx_player_stats_ev_loss ON player_stats(total_ev_loss);

-- ============================================================================
-- SAMPLE QUERIES FOR LEAK DETECTION
-- ============================================================================

-- Query 1: Get GTO frequency for BB calling vs UTG with AKo
-- SELECT get_gto_frequency('BB_vs_UTG_call', 'AKo');

-- Query 2: Get full action breakdown for BB facing UTG open with JTs
-- SELECT * FROM get_hand_action_breakdown('BB', 'UTG', 'JTs');

-- Query 3: Find all scenarios where a hand should be played >50%
-- SELECT scenario_name, hand, avg_frequency
-- FROM preflop_hands
-- WHERE hand = 'AKo' AND avg_frequency > 0.5
-- ORDER BY avg_frequency DESC;

-- Query 4: Compare player action to GTO
-- SELECT
--     ph.player_name,
--     ph.scenario,
--     ph.hole_cards,
--     ph.action_taken,
--     ph.gto_frequency,
--     CASE
--         WHEN ph.gto_frequency > 0.5 AND ph.is_gto THEN 'Correct (pure GTO)'
--         WHEN ph.gto_frequency > 0 AND ph.gto_frequency <= 0.5 THEN 'Mixed (acceptable)'
--         WHEN ph.gto_frequency = 0 THEN 'LEAK - should never take this action'
--     END as analysis
-- FROM player_hands ph
-- WHERE player_name = 'Hero'
-- ORDER BY ph.timestamp DESC
-- LIMIT 10;

-- Query 5: Find player's biggest leaks by EV loss
-- SELECT
--     scenario,
--     total_hands,
--     leak_hands,
--     ROUND(gto_percentage, 1) as gto_pct,
--     ROUND(total_ev_loss, 2) as bb_lost,
--     biggest_leak
-- FROM player_stats
-- WHERE player_name = 'Villain1'
-- ORDER BY total_ev_loss DESC
-- LIMIT 10;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. All frequencies stored as decimals (0.0 to 1.0), converted to % in queries
-- 2. Combo format: 4 characters (rank+suit+rank+suit), e.g., 'AhKd'
-- 3. Hand format: 2-3 characters, e.g., 'AKo', 'JTs', '22'
-- 4. Scenario naming: {position}_vs_{opponent}_{action} or {position}_open
-- 5. Categories: 'opening', 'defense', 'cold_call', 'facing_3bet', 'facing_4bet', 'multiway'
