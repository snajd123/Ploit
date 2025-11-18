-- GTO Solutions Table
-- Stores pre-computed GTO solutions from TexasSolver

CREATE TABLE IF NOT EXISTS gto_solutions (
    solution_id SERIAL PRIMARY KEY,

    -- Scenario identification
    scenario_name VARCHAR(100) UNIQUE NOT NULL,
    scenario_type VARCHAR(50) NOT NULL,  -- 'preflop', 'srp_flop', '3bet_pot', etc.

    -- Board and game state
    position_oop VARCHAR(10),   -- 'BB', 'SB', 'UTG', etc.
    position_ip VARCHAR(10),    -- 'BTN', 'CO', etc.
    board VARCHAR(30),          -- 'Ks7c3d' or NULL for preflop
    pot_size DECIMAL(8,2) NOT NULL,
    stack_depth DECIMAL(8,2) NOT NULL,

    -- GTO frequencies (percentages 0-100)
    gto_bet_frequency DECIMAL(5,2),
    gto_check_frequency DECIMAL(5,2),
    gto_fold_frequency DECIMAL(5,2),
    gto_call_frequency DECIMAL(5,2),
    gto_raise_frequency DECIMAL(5,2),

    -- Bet sizing (as % of pot)
    gto_bet_size_small DECIMAL(5,2),    -- e.g., 33
    gto_bet_size_medium DECIMAL(5,2),   -- e.g., 66
    gto_bet_size_large DECIMAL(5,2),    -- e.g., 100

    -- Expected values (in big blinds)
    ev_oop DECIMAL(8,2),
    ev_ip DECIMAL(8,2),
    exploitability DECIMAL(6,4),  -- How far from Nash equilibrium

    -- Detailed range data (stored as JSON)
    gto_betting_range JSONB,     -- Hands that bet (with frequencies)
    gto_checking_range JSONB,    -- Hands that check
    gto_raising_range JSONB,     -- Hands that raise (if applicable)
    gto_calling_range JSONB,     -- Hands that call
    gto_folding_range JSONB,     -- Hands that fold

    -- Full strategy tree (optional, for complex spots)
    full_strategy_tree JSONB,    -- Complete game tree if needed

    -- Human-readable description
    description TEXT,

    -- Metadata
    solver_version VARCHAR(50) DEFAULT 'TexasSolver-0.2.0',
    solve_time_seconds INT,
    solved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- For fast lookups
    CONSTRAINT unique_scenario UNIQUE(scenario_name)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_gto_scenario_type ON gto_solutions(scenario_type);
CREATE INDEX IF NOT EXISTS idx_gto_board ON gto_solutions(board);
CREATE INDEX IF NOT EXISTS idx_gto_positions ON gto_solutions(position_oop, position_ip);
CREATE INDEX IF NOT EXISTS idx_gto_lookup ON gto_solutions(scenario_type, board, position_oop);

-- Full-text search on scenario names
CREATE INDEX IF NOT EXISTS idx_gto_scenario_name_search ON gto_solutions USING gin(to_tsvector('english', scenario_name));

-- Comments
COMMENT ON TABLE gto_solutions IS 'Pre-computed GTO poker solutions from TexasSolver for deviation analysis';
COMMENT ON COLUMN gto_solutions.scenario_name IS 'Unique identifier like BTN_steal_vs_BB or SRP_Ks7c3d_cbet';
COMMENT ON COLUMN gto_solutions.gto_bet_frequency IS 'Percentage of range that bets in GTO strategy (0-100)';
COMMENT ON COLUMN gto_solutions.ev_oop IS 'Expected value for out-of-position player in big blinds';
