"""
Migration: Add AI prompt/response columns to pregame_strategies

Allows viewing the exact prompt sent to Claude and the response received.
"""

from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL")

def run_migration():
    """Add ai_prompt and ai_response columns."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Add ai_prompt column
        conn.execute(text("""
            ALTER TABLE pregame_strategies
            ADD COLUMN IF NOT EXISTS ai_prompt TEXT
        """))

        # Add ai_response column
        conn.execute(text("""
            ALTER TABLE pregame_strategies
            ADD COLUMN IF NOT EXISTS ai_response TEXT
        """))

        conn.commit()
        print("Added ai_prompt and ai_response columns successfully")

if __name__ == "__main__":
    run_migration()
