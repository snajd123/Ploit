-- Poker Analysis App - Database Schema
-- Run this SQL in Supabase SQL Editor to create all tables

-- ============================================
-- Table 1: raw_hands
-- Stores complete hand history text
-- ============================================
CREATE TABLE IF NOT EXISTS raw_hands (
    hand_id BIGINT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    table_name VARCHAR(255),
    stake_level VARCHAR(50),
    game_type VARCHAR(50),
    raw_hand_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_raw_hands_timestamp ON raw_hands(timestamp);
CREATE INDEX IF NOT EXISTS idx_raw_hands_stake ON raw_hands(stake_level);

-- ============================================
-- Table 2: hand_actions
-- Every single action in every hand
-- ============================================
CREATE TABLE IF NOT EXISTS hand_actions (
    action_id SERIAL PRIMARY KEY,
    hand_id BIGINT REFERENCES raw_hands(hand_id) ON DELETE CASCADE,
    player_name VARCHAR(100) NOT NULL,
    position VARCHAR(10),
    street VARCHAR(10),
    action_type VARCHAR(20),
    amount DECIMAL(10,2),
    pot_size_before DECIMAL(10,2),
    pot_size_after DECIMAL(10,2),
    is_aggressive BOOLEAN,
    facing_bet BOOLEAN,
    stack_size DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hand_actions_player ON hand_actions(player_name);
CREATE INDEX IF NOT EXISTS idx_hand_actions_hand ON hand_actions(hand_id);
CREATE INDEX IF NOT EXISTS idx_hand_actions_street ON hand_actions(street);
CREATE INDEX IF NOT EXISTS idx_hand_actions_position ON hand_actions(position);

-- ============================================
-- Table 3: player_hand_summary
-- Per-player per-hand boolean flags
-- ============================================
CREATE TABLE IF NOT EXISTS player_hand_summary (
    summary_id SERIAL PRIMARY KEY,
    hand_id BIGINT REFERENCES raw_hands(hand_id) ON DELETE CASCADE,
    player_name VARCHAR(100) NOT NULL,
    position VARCHAR(10),

    -- Preflop flags
    vpip BOOLEAN DEFAULT FALSE,
    pfr BOOLEAN DEFAULT FALSE,
    limp BOOLEAN DEFAULT FALSE,
    faced_raise BOOLEAN DEFAULT FALSE,
    three_bet_opportunity BOOLEAN DEFAULT FALSE,
    faced_three_bet BOOLEAN DEFAULT FALSE,
    folded_to_three_bet BOOLEAN DEFAULT FALSE,
    called_three_bet BOOLEAN DEFAULT FALSE,
    made_three_bet BOOLEAN DEFAULT FALSE,
    four_bet BOOLEAN DEFAULT FALSE,
    cold_call BOOLEAN DEFAULT FALSE,
    squeeze BOOLEAN DEFAULT FALSE,

    -- Street visibility
    saw_flop BOOLEAN DEFAULT FALSE,
    saw_turn BOOLEAN DEFAULT FALSE,
    saw_river BOOLEAN DEFAULT FALSE,

    -- Continuation bet opportunities and actions (as aggressor)
    cbet_opportunity_flop BOOLEAN DEFAULT FALSE,
    cbet_made_flop BOOLEAN DEFAULT FALSE,
    cbet_opportunity_turn BOOLEAN DEFAULT FALSE,
    cbet_made_turn BOOLEAN DEFAULT FALSE,
    cbet_opportunity_river BOOLEAN DEFAULT FALSE,
    cbet_made_river BOOLEAN DEFAULT FALSE,

    -- Facing continuation bets
    faced_cbet_flop BOOLEAN DEFAULT FALSE,
    folded_to_cbet_flop BOOLEAN DEFAULT FALSE,
    called_cbet_flop BOOLEAN DEFAULT FALSE,
    raised_cbet_flop BOOLEAN DEFAULT FALSE,

    faced_cbet_turn BOOLEAN DEFAULT FALSE,
    folded_to_cbet_turn BOOLEAN DEFAULT FALSE,
    called_cbet_turn BOOLEAN DEFAULT FALSE,
    raised_cbet_turn BOOLEAN DEFAULT FALSE,

    faced_cbet_river BOOLEAN DEFAULT FALSE,
    folded_to_cbet_river BOOLEAN DEFAULT FALSE,
    called_cbet_river BOOLEAN DEFAULT FALSE,
    raised_cbet_river BOOLEAN DEFAULT FALSE,

    -- Check-raise flags
    check_raise_opportunity_flop BOOLEAN DEFAULT FALSE,
    check_raised_flop BOOLEAN DEFAULT FALSE,
    check_raise_opportunity_turn BOOLEAN DEFAULT FALSE,
    check_raised_turn BOOLEAN DEFAULT FALSE,
    check_raise_opportunity_river BOOLEAN DEFAULT FALSE,
    check_raised_river BOOLEAN DEFAULT FALSE,

    -- Donk bets (betting into aggressor)
    donk_bet_flop BOOLEAN DEFAULT FALSE,
    donk_bet_turn BOOLEAN DEFAULT FALSE,
    donk_bet_river BOOLEAN DEFAULT FALSE,

    -- Float plays (call flop, bet/raise later when checked to)
    float_flop BOOLEAN DEFAULT FALSE,

    -- Steal and blind defense
    steal_attempt BOOLEAN DEFAULT FALSE,
    faced_steal BOOLEAN DEFAULT FALSE,
    fold_to_steal BOOLEAN DEFAULT FALSE,
    call_steal BOOLEAN DEFAULT FALSE,
    three_bet_vs_steal BOOLEAN DEFAULT FALSE,

    -- Showdown
    went_to_showdown BOOLEAN DEFAULT FALSE,
    won_at_showdown BOOLEAN DEFAULT FALSE,
    showed_bluff BOOLEAN DEFAULT FALSE,

    -- Hand result
    won_hand BOOLEAN DEFAULT FALSE,
    profit_loss DECIMAL(10,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(hand_id, player_name)
);

CREATE INDEX IF NOT EXISTS idx_player_summary_player ON player_hand_summary(player_name);
CREATE INDEX IF NOT EXISTS idx_player_summary_hand ON player_hand_summary(hand_id);

-- ============================================
-- Table 4: player_stats
-- Pre-calculated traditional and composite statistics
-- ============================================
CREATE TABLE IF NOT EXISTS player_stats (
    player_name VARCHAR(100) PRIMARY KEY,
    total_hands INT DEFAULT 0,

    -- Preflop statistics (percentages 0-100)
    vpip_pct DECIMAL(5,2),
    pfr_pct DECIMAL(5,2),
    limp_pct DECIMAL(5,2),
    three_bet_pct DECIMAL(5,2),
    fold_to_three_bet_pct DECIMAL(5,2),
    four_bet_pct DECIMAL(5,2),
    cold_call_pct DECIMAL(5,2),
    squeeze_pct DECIMAL(5,2),

    -- Positional VPIP
    vpip_utg DECIMAL(5,2),
    vpip_hj DECIMAL(5,2),
    vpip_mp DECIMAL(5,2),
    vpip_co DECIMAL(5,2),
    vpip_btn DECIMAL(5,2),
    vpip_sb DECIMAL(5,2),
    vpip_bb DECIMAL(5,2),

    -- Steal and blind defense
    steal_attempt_pct DECIMAL(5,2),
    fold_to_steal_pct DECIMAL(5,2),
    three_bet_vs_steal_pct DECIMAL(5,2),

    -- Postflop aggression (continuation betting)
    cbet_flop_pct DECIMAL(5,2),
    cbet_turn_pct DECIMAL(5,2),
    cbet_river_pct DECIMAL(5,2),

    -- Postflop defense (facing cbets)
    fold_to_cbet_flop_pct DECIMAL(5,2),
    fold_to_cbet_turn_pct DECIMAL(5,2),
    fold_to_cbet_river_pct DECIMAL(5,2),

    call_cbet_flop_pct DECIMAL(5,2),
    call_cbet_turn_pct DECIMAL(5,2),
    call_cbet_river_pct DECIMAL(5,2),

    raise_cbet_flop_pct DECIMAL(5,2),
    raise_cbet_turn_pct DECIMAL(5,2),
    raise_cbet_river_pct DECIMAL(5,2),

    -- Check-raise frequency
    check_raise_flop_pct DECIMAL(5,2),
    check_raise_turn_pct DECIMAL(5,2),
    check_raise_river_pct DECIMAL(5,2),

    -- Donk betting
    donk_bet_flop_pct DECIMAL(5,2),
    donk_bet_turn_pct DECIMAL(5,2),
    donk_bet_river_pct DECIMAL(5,2),

    -- Float frequency
    float_flop_pct DECIMAL(5,2),

    -- Aggression metrics
    af DECIMAL(5,2),
    afq DECIMAL(5,2),

    -- Showdown metrics
    wtsd_pct DECIMAL(5,2),
    wsd_pct DECIMAL(5,2),

    -- Win rate
    total_profit_loss DECIMAL(12,2),
    bb_per_100 DECIMAL(8,2),

    -- Composite Metrics (calculated and stored)
    exploitability_index DECIMAL(5,2),
    pressure_vulnerability_score DECIMAL(5,2),
    aggression_consistency_ratio DECIMAL(5,2),
    positional_awareness_index DECIMAL(5,2),
    blind_defense_efficiency DECIMAL(5,2),
    value_bluff_imbalance_ratio DECIMAL(5,2),
    range_polarization_factor DECIMAL(5,2),
    street_fold_gradient DECIMAL(5,2),
    delayed_aggression_coefficient DECIMAL(5,2),
    multi_street_persistence_score DECIMAL(5,2),
    optimal_stake_skill_rating DECIMAL(5,2),
    player_type VARCHAR(20),

    -- Metadata
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_hand_date TIMESTAMP,
    last_hand_date TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_player_stats_hands ON player_stats(total_hands);
CREATE INDEX IF NOT EXISTS idx_player_stats_vpip ON player_stats(vpip_pct);
CREATE INDEX IF NOT EXISTS idx_player_stats_pfr ON player_stats(pfr_pct);
CREATE INDEX IF NOT EXISTS idx_player_stats_ei ON player_stats(exploitability_index);
CREATE INDEX IF NOT EXISTS idx_player_stats_pvs ON player_stats(pressure_vulnerability_score);
CREATE INDEX IF NOT EXISTS idx_player_stats_type ON player_stats(player_type);

-- ============================================
-- Table 5: upload_sessions
-- Track hand history file uploads
-- ============================================
CREATE TABLE IF NOT EXISTS upload_sessions (
    session_id SERIAL PRIMARY KEY,
    filename VARCHAR(255),
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hands_parsed INT DEFAULT 0,
    hands_failed INT DEFAULT 0,
    players_updated INT DEFAULT 0,
    stake_level VARCHAR(50),
    status VARCHAR(50) DEFAULT 'processing',
    error_message TEXT,
    processing_time_seconds INT
);

CREATE INDEX IF NOT EXISTS idx_upload_sessions_timestamp ON upload_sessions(upload_timestamp);

-- ============================================
-- Verify Tables Created
-- ============================================
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
    AND table_name IN ('raw_hands', 'hand_actions', 'player_hand_summary', 'player_stats', 'upload_sessions')
ORDER BY table_name;
