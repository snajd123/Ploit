#!/usr/bin/env python3
"""
Database Migration: Preflop-Only GTO Schema

This script:
1. Creates new optimized tables (player_preflop_actions, player_scenario_stats)
2. Removes postflop columns from player_stats
3. Drops deprecated tables (player_hand_summary, old GTO tables, etc.)

Run with: DATABASE_URL=... python3 migrate_to_preflop_only.py
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get('DATABASE_URL',
    'postgresql://postgres.lyvnuiuatuggtirdxiht:r7e2fQfDBrkIRYHD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def create_new_tables(db):
    """Create new optimized tables for preflop GTO analysis."""
    print("\n=== Creating New Tables ===\n")

    # 1. player_preflop_actions - Individual preflop actions with GTO comparison
    print("Creating player_preflop_actions...")
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS player_preflop_actions (
            action_id BIGSERIAL PRIMARY KEY,

            -- Linkage
            player_name VARCHAR(100) NOT NULL,
            hand_id BIGINT REFERENCES raw_hands(hand_id) ON DELETE CASCADE,
            scenario_id INTEGER REFERENCES gto_scenarios(scenario_id),

            -- Context
            timestamp TIMESTAMP NOT NULL,
            hero_position VARCHAR(10) NOT NULL,
            villain_position VARCHAR(10),
            effective_stack_bb INTEGER,

            -- Action details
            hole_cards VARCHAR(4),
            action_taken VARCHAR(20) NOT NULL,

            -- GTO comparison
            gto_frequency DECIMAL(10, 8),
            is_mistake BOOLEAN,
            ev_loss_bb DECIMAL(10, 4),
            mistake_severity VARCHAR(20),

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    db.commit()
    print("  ✓ player_preflop_actions created")

    # Create indices for player_preflop_actions
    print("Creating indices for player_preflop_actions...")
    try:
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_preflop_player ON player_preflop_actions(player_name)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_preflop_scenario ON player_preflop_actions(scenario_id)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_preflop_player_scenario ON player_preflop_actions(player_name, scenario_id)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_preflop_timestamp ON player_preflop_actions(player_name, timestamp DESC)"))
        db.commit()
        print("  ✓ Indices created")
    except Exception as e:
        print(f"  ⚠ Index creation warning: {e}")
        db.rollback()

    # 2. player_scenario_stats - Aggregated per-action stats per scenario
    print("\nCreating player_scenario_stats...")
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS player_scenario_stats (
            stat_id SERIAL PRIMARY KEY,
            player_name VARCHAR(100) NOT NULL,
            scenario_id INTEGER NOT NULL REFERENCES gto_scenarios(scenario_id),

            -- Sample size
            total_opportunities INTEGER NOT NULL DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            -- Action counts
            fold_count INTEGER DEFAULT 0,
            call_count INTEGER DEFAULT 0,
            open_count INTEGER DEFAULT 0,
            three_bet_count INTEGER DEFAULT 0,
            four_bet_count INTEGER DEFAULT 0,
            allin_count INTEGER DEFAULT 0,

            -- Player frequencies
            fold_freq DECIMAL(10, 8),
            call_freq DECIMAL(10, 8),
            open_freq DECIMAL(10, 8),
            three_bet_freq DECIMAL(10, 8),
            four_bet_freq DECIMAL(10, 8),
            allin_freq DECIMAL(10, 8),

            -- GTO frequencies
            gto_fold_freq DECIMAL(10, 8),
            gto_call_freq DECIMAL(10, 8),
            gto_open_freq DECIMAL(10, 8),
            gto_three_bet_freq DECIMAL(10, 8),
            gto_four_bet_freq DECIMAL(10, 8),
            gto_allin_freq DECIMAL(10, 8),

            -- Deviations
            fold_deviation DECIMAL(10, 8),
            call_deviation DECIMAL(10, 8),
            open_deviation DECIMAL(10, 8),
            three_bet_deviation DECIMAL(10, 8),
            four_bet_deviation DECIMAL(10, 8),

            -- Primary leak detection
            primary_leak VARCHAR(50),
            primary_leak_severity VARCHAR(20),
            total_ev_loss_bb DECIMAL(10, 4),

            -- Exploit recommendation
            exploit_description TEXT,
            exploit_value_bb_100 DECIMAL(10, 4),
            exploit_confidence DECIMAL(5, 2),

            UNIQUE(player_name, scenario_id)
        )
    """))
    db.commit()
    print("  ✓ player_scenario_stats created")

    # Create indices for player_scenario_stats
    print("Creating indices for player_scenario_stats...")
    try:
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_scenario_stats_player ON player_scenario_stats(player_name)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_scenario_stats_leak ON player_scenario_stats(player_name, primary_leak_severity DESC)"))
        db.commit()
        print("  ✓ Indices created")
    except Exception as e:
        print(f"  ⚠ Index creation warning: {e}")
        db.rollback()


def remove_postflop_columns(db):
    """Remove postflop columns from player_stats table."""
    print("\n=== Removing Postflop Columns from player_stats ===\n")

    # List of postflop columns to drop
    postflop_columns = [
        # C-bet columns
        'cbet_flop_pct', 'cbet_turn_pct', 'cbet_river_pct',
        # Fold to c-bet columns
        'fold_to_cbet_flop_pct', 'fold_to_cbet_turn_pct', 'fold_to_cbet_river_pct',
        # Call c-bet columns
        'call_cbet_flop_pct', 'call_cbet_turn_pct', 'call_cbet_river_pct',
        # Raise c-bet columns
        'raise_cbet_flop_pct', 'raise_cbet_turn_pct', 'raise_cbet_river_pct',
        # Check-raise columns
        'check_raise_flop_pct', 'check_raise_turn_pct', 'check_raise_river_pct',
        # Donk bet columns
        'donk_bet_flop_pct', 'donk_bet_turn_pct', 'donk_bet_river_pct',
        # Float column
        'float_flop_pct',
        # Aggression columns
        'af', 'afq',
        # Showdown columns
        'wtsd_pct', 'wsd_pct',
        # Postflop composite metrics
        'pressure_vulnerability_score',
        'aggression_consistency_ratio',
        'value_bluff_imbalance_ratio',
        'range_polarization_factor',
        'street_fold_gradient',
        'delayed_aggression_coefficient',
        'multi_street_persistence_score',
    ]

    dropped = 0
    for column in postflop_columns:
        try:
            db.execute(text(f"ALTER TABLE player_stats DROP COLUMN IF EXISTS {column}"))
            db.commit()
            print(f"  ✓ Dropped {column}")
            dropped += 1
        except Exception as e:
            print(f"  ⚠ Could not drop {column}: {e}")
            db.rollback()

    print(f"\n  Total columns dropped: {dropped}/{len(postflop_columns)}")


def drop_deprecated_tables(db):
    """Drop tables no longer needed for preflop-only analysis."""
    print("\n=== Dropping Deprecated Tables ===\n")

    tables_to_drop = [
        'player_hand_summary',      # 90+ column legacy table
        'player_actions',           # Old GTO actions (no proper FK)
        'player_gto_stats',         # Old GTO stats (single aggregate)
        'hand_types',               # Compute in code instead
        'gto_solutions',            # Postflop solver data
        'postflop_hand_frequencies', # Postflop frequencies
        'gto_category_aggregates',  # Postflop aggregates
    ]

    for table in tables_to_drop:
        try:
            db.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            db.commit()
            print(f"  ✓ Dropped {table}")
        except Exception as e:
            print(f"  ⚠ Could not drop {table}: {e}")
            db.rollback()


def clear_postflop_gto_data(db):
    """Clear postflop data from GTO tables."""
    print("\n=== Clearing Postflop GTO Data ===\n")

    # Delete postflop scenarios and their frequencies
    try:
        # First delete frequencies for postflop scenarios
        result = db.execute(text("""
            DELETE FROM gto_frequencies
            WHERE scenario_id IN (
                SELECT scenario_id FROM gto_scenarios WHERE street != 'preflop'
            )
        """))
        db.commit()
        print(f"  ✓ Deleted postflop frequencies: {result.rowcount} rows")

        # Then delete postflop scenarios
        result = db.execute(text("""
            DELETE FROM gto_scenarios WHERE street != 'preflop'
        """))
        db.commit()
        print(f"  ✓ Deleted postflop scenarios: {result.rowcount} rows")

    except Exception as e:
        print(f"  ⚠ Error clearing postflop data: {e}")
        db.rollback()


def verify_schema(db):
    """Verify the schema is correct after migration."""
    print("\n=== Verifying Schema ===\n")

    # Check new tables exist
    new_tables = ['player_preflop_actions', 'player_scenario_stats']
    for table in new_tables:
        result = db.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = '{table}'
            )
        """)).fetchone()
        exists = result[0] if result else False
        print(f"  {'✓' if exists else '✗'} {table} exists: {exists}")

    # Check player_stats columns
    result = db.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'player_stats'
        ORDER BY ordinal_position
    """)).fetchall()
    columns = [r[0] for r in result]
    print(f"\n  player_stats columns ({len(columns)}):")
    for col in columns:
        print(f"    - {col}")

    # Check GTO scenarios
    result = db.execute(text("""
        SELECT COUNT(*) FROM gto_scenarios WHERE street = 'preflop'
    """)).fetchone()
    print(f"\n  Preflop GTO scenarios: {result[0] if result else 0}")

    result = db.execute(text("""
        SELECT COUNT(*) FROM gto_frequencies
    """)).fetchone()
    print(f"  GTO frequencies: {result[0] if result else 0}")


def main():
    """Run the migration."""
    print("=" * 70)
    print("PREFLOP-ONLY DATABASE MIGRATION")
    print("=" * 70)

    db = SessionLocal()

    try:
        # Step 1: Create new tables
        create_new_tables(db)

        # Step 2: Remove postflop columns from player_stats
        remove_postflop_columns(db)

        # Step 3: Clear postflop GTO data
        clear_postflop_gto_data(db)

        # Step 4: Drop deprecated tables
        drop_deprecated_tables(db)

        # Step 5: Verify schema
        verify_schema(db)

        print("\n" + "=" * 70)
        print("MIGRATION COMPLETE")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Run import_gtowizard_preflop.py to import 188 scenarios")
        print("  2. Update ORM models in database_models.py")
        print("  3. Update services (stats_calculator, gto_service)")
        print("  4. Update frontend")

    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    main()
