"""
Migration: Create pregame_strategies table

Stores AI-generated preflop exploitation strategies for tables.
"""

from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL")

def run_migration():
    """Create pregame_strategies table."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Create pregame_strategies table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pregame_strategies (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP DEFAULT NOW(),

                -- Context
                hero_nickname VARCHAR(100),
                stake_level VARCHAR(20),
                hand_id BIGINT,
                hand_number VARCHAR(50),

                -- Table assessment
                softness_score DECIMAL(2,1),
                table_classification VARCHAR(50),

                -- Strategy (AI-generated)
                strategy JSONB NOT NULL,

                -- Opponents snapshot at time of analysis
                opponents JSONB NOT NULL,

                -- Email tracking
                sender_email VARCHAR(255),
                email_sent BOOLEAN DEFAULT FALSE,
                email_sent_at TIMESTAMP
            )
        """))

        # Create index for quick lookups
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pregame_strategies_created
            ON pregame_strategies(created_at DESC)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pregame_strategies_hero
            ON pregame_strategies(hero_nickname)
        """))

        conn.commit()
        print("Created pregame_strategies table successfully")

if __name__ == "__main__":
    run_migration()
