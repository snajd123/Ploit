"""
Run Claude Conversation migration.

This script creates the claude_conversations and claude_messages tables.

Can be run locally with DATABASE_URL env var or via Railway CLI:
  railway run python backend/scripts/run_conversation_migration.py
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from backend.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Run the conversation migration"""
    migration_file = Path(__file__).parent.parent / "migrations" / "005_add_claude_conversations.sql"

    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False

    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        with engine.connect() as conn:
            # Execute migration
            logger.info("Running migration: 005_add_claude_conversations.sql")
            conn.execute(text(migration_sql))
            conn.commit()
            logger.info("✓ Migration completed successfully")

        return True

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False


def check_tables_exist():
    """Check if conversation tables exist"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'claude_conversations'
                );
            """))
            exists = result.scalar()
            return exists
    except Exception as e:
        logger.error(f"Error checking table: {str(e)}")
        return False


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("Claude Conversation Tables Migration")
    logger.info("=" * 60)

    # Check database connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✓ Database connection successful")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {str(e)}")
        logger.error("Make sure DATABASE_URL environment variable is set")
        return 1

    # Check if tables exist
    tables_exist = check_tables_exist()

    if not tables_exist:
        logger.info("Tables do not exist. Running migration...")
        if not run_migration():
            return 1
    else:
        logger.info("✓ Tables already exist")

    # Verify tables
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM claude_conversations"))
        count = result.scalar()
        logger.info(f"\n✓ claude_conversations table contains {count} conversations")

    logger.info("\n" + "=" * 60)
    logger.info("Migration Complete!")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
