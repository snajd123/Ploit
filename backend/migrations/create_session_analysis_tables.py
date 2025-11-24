"""
Migration: Create tables for session analysis feature

This migration creates:
1. sessions - Store session metadata
2. hero_gto_mistakes - Track hero's GTO mistakes with hole cards
3. opponent_session_stats - Track opponent tendencies without hole cards
4. missed_exploits - Track missed exploit opportunities
5. Add session_id to raw_hands table
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def run_migration():
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("Creating session analysis tables...")

        # 1. Create sessions table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id SERIAL PRIMARY KEY,
                player_name VARCHAR(100) NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                duration_minutes INT,
                total_hands INT DEFAULT 0,
                profit_loss_bb DECIMAL(10, 2),
                bb_100 DECIMAL(10, 2),
                table_stakes VARCHAR(20),
                table_name VARCHAR(100),
                notes TEXT,
                tags TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("✓ Created sessions table")

        # 2. Add session_id to raw_hands table
        conn.execute(text("""
            ALTER TABLE raw_hands
            ADD COLUMN IF NOT EXISTS session_id INT REFERENCES sessions(session_id);
        """))
        print("✓ Added session_id to raw_hands table")

        # 3. Create index on session_id
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_raw_hands_session_id ON raw_hands(session_id);
        """))
        print("✓ Created index on raw_hands.session_id")

        # 4. Create hero_gto_mistakes table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS hero_gto_mistakes (
                mistake_id SERIAL PRIMARY KEY,
                hand_id BIGINT REFERENCES raw_hands(hand_id),
                session_id INT REFERENCES sessions(session_id),
                street VARCHAR(10),
                hero_hand VARCHAR(4),
                hero_hand_suited BOOLEAN,
                action_taken VARCHAR(20),
                gto_action VARCHAR(20),
                gto_frequency DECIMAL(5, 4),
                ev_loss_bb DECIMAL(10, 4),
                scenario_id INT REFERENCES gto_scenarios(scenario_id),
                hand_in_gto_range BOOLEAN,
                mistake_severity VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("✓ Created hero_gto_mistakes table")

        # 5. Create indexes for hero_gto_mistakes
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_hero_mistakes_session ON hero_gto_mistakes(session_id);
            CREATE INDEX IF NOT EXISTS idx_hero_mistakes_hand ON hero_gto_mistakes(hand_id);
        """))
        print("✓ Created indexes on hero_gto_mistakes")

        # 6. Create opponent_session_stats table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS opponent_session_stats (
                stat_id SERIAL PRIMARY KEY,
                session_id INT REFERENCES sessions(session_id),
                opponent_name VARCHAR(100) NOT NULL,
                hands_observed INT DEFAULT 0,

                -- Preflop frequencies
                vpip_pct DECIMAL(5, 2),
                pfr_pct DECIMAL(5, 2),
                three_bet_pct DECIMAL(5, 2),
                fold_to_three_bet_pct DECIMAL(5, 2),
                four_bet_pct DECIMAL(5, 2),

                -- Postflop frequencies
                cbet_flop_pct DECIMAL(5, 2),
                cbet_turn_pct DECIMAL(5, 2),
                fold_to_cbet_flop_pct DECIMAL(5, 2),
                fold_to_cbet_turn_pct DECIMAL(5, 2),

                -- GTO comparisons (deviation from GTO)
                vpip_vs_gto DECIMAL(5, 2),
                three_bet_vs_gto DECIMAL(5, 2),
                fold_to_3bet_vs_gto DECIMAL(5, 2),
                cbet_vs_gto DECIMAL(5, 2),

                -- Tendencies and exploits (JSONB for flexibility)
                tendency_summary JSONB,
                exploits JSONB,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT unique_opponent_session UNIQUE(session_id, opponent_name)
            );
        """))
        print("✓ Created opponent_session_stats table")

        # 7. Create index on opponent_session_stats
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_opponent_stats_session ON opponent_session_stats(session_id);
        """))
        print("✓ Created index on opponent_session_stats")

        # 8. Create missed_exploits table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS missed_exploits (
                exploit_id SERIAL PRIMARY KEY,
                session_id INT REFERENCES sessions(session_id),
                opponent_name VARCHAR(100),
                exploit_type VARCHAR(50),
                situation_description TEXT,
                current_frequency DECIMAL(5, 2),
                optimal_frequency DECIMAL(5, 2),
                frequency_difference DECIMAL(5, 2),
                estimated_ev_gain_bb DECIMAL(10, 4),
                hands_analyzed INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("✓ Created missed_exploits table")

        # 9. Create index on missed_exploits
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_missed_exploits_session ON missed_exploits(session_id);
        """))
        print("✓ Created index on missed_exploits")

        # 10. Create session_gto_summary table (cache for aggregated analysis)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS session_gto_summary (
                summary_id SERIAL PRIMARY KEY,
                session_id INT REFERENCES sessions(session_id) UNIQUE,
                total_mistakes INT DEFAULT 0,
                total_ev_loss_bb DECIMAL(10, 4),
                biggest_mistake_hand_id BIGINT REFERENCES raw_hands(hand_id),
                biggest_mistake_ev_loss DECIMAL(10, 4),
                total_missed_exploit_value DECIMAL(10, 4),
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                analysis_version VARCHAR(20)
            );
        """))
        print("✓ Created session_gto_summary table")

        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("\nCreated tables:")
        print("  - sessions")
        print("  - hero_gto_mistakes")
        print("  - opponent_session_stats")
        print("  - missed_exploits")
        print("  - session_gto_summary")
        print("\nAdded columns:")
        print("  - raw_hands.session_id")

if __name__ == "__main__":
    run_migration()
