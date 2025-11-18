"""
Run GTO Solutions migration and import data.

This script:
1. Creates the gto_solutions table (if it doesn't exist)
2. Imports the parsed GTO solutions

Can be run locally with DATABASE_URL env var or via Railway CLI:
  railway run python scripts/run_gto_migration.py
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
    """Run the GTO solutions migration"""
    migration_file = Path(__file__).parent.parent / "migrations" / "011_add_gto_solutions.sql"

    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False

    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        with engine.connect() as conn:
            # Execute migration
            logger.info("Running migration: 011_add_gto_solutions.sql")
            conn.execute(text(migration_sql))
            conn.commit()
            logger.info("✓ Migration completed successfully")

        return True

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False


def import_solutions():
    """Import GTO solutions from SQL file"""
    import_file = Path(__file__).parent / "import_gto_solutions.sql"

    if not import_file.exists():
        logger.error(f"Import file not found: {import_file}")
        logger.info("Run parse_gto_solutions.py first to generate the import file")
        return False

    try:
        with open(import_file, 'r') as f:
            import_sql = f.read()

        with engine.connect() as conn:
            # Execute import (each INSERT statement separately)
            logger.info("Importing GTO solutions...")

            # Split by INSERT statements
            statements = [s.strip() for s in import_sql.split('INSERT INTO') if s.strip()]

            for i, statement in enumerate(statements, 1):
                if statement:
                    full_statement = 'INSERT INTO ' + statement
                    conn.execute(text(full_statement))
                    logger.info(f"  Imported solution {i}/{len(statements)}")

            conn.commit()
            logger.info("✓ All solutions imported successfully")

        return True

    except Exception as e:
        logger.error(f"Import failed: {str(e)}")
        return False


def check_table_exists():
    """Check if gto_solutions table exists"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'gto_solutions'
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
    logger.info("GTO Solutions Migration & Import")
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

    # Check if table exists
    table_exists = check_table_exists()

    if not table_exists:
        logger.info("Table gto_solutions does not exist. Running migration...")
        if not run_migration():
            return 1
    else:
        logger.info("✓ Table gto_solutions already exists")

    # Import solutions
    logger.info("\nImporting GTO solutions...")
    if not import_solutions():
        return 1

    # Verify import
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM gto_solutions"))
        count = result.scalar()
        logger.info(f"\n✓ Database now contains {count} GTO solutions")

    logger.info("\n" + "=" * 60)
    logger.info("Migration & Import Complete!")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
