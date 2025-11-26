"""
Migration script to add facing 4-bet tracking and raiser position columns.

This script:
1. Adds new columns to player_hand_summary table:
   - raiser_position: Position of the first raiser (opener)
   - faced_four_bet: True if player faced a 4-bet
   - folded_to_four_bet, called_four_bet, five_bet: Response flags
2. Recalculates all these flags for existing hands

Usage:
    python -m backend.migrations.add_facing_4bet_tracking
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database_models import PlayerHandSummary, RawHand, HandAction


def get_db_url():
    """Get database URL from environment or use default"""
    return os.getenv('DATABASE_URL', 'postgresql://ploit_user:ploit123@localhost:5432/ploit_db')


def add_columns_if_not_exists(engine):
    """Add new columns if they don't exist"""
    print("Step 1: Adding new columns...")

    columns_to_add = [
        ('raiser_position', 'VARCHAR(10)'),
        ('faced_four_bet', 'BOOLEAN DEFAULT FALSE'),
        ('folded_to_four_bet', 'BOOLEAN DEFAULT FALSE'),
        ('called_four_bet', 'BOOLEAN DEFAULT FALSE'),
        ('five_bet', 'BOOLEAN DEFAULT FALSE'),
    ]

    with engine.connect() as conn:
        for col_name, col_type in columns_to_add:
            # Check if column exists
            result = conn.execute(text(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='player_hand_summary'
                AND column_name='{col_name}'
            """))

            if result.fetchone():
                print(f"  - Column '{col_name}' already exists")
            else:
                # Add column
                conn.execute(text(f"""
                    ALTER TABLE player_hand_summary
                    ADD COLUMN {col_name} {col_type}
                """))
                conn.commit()
                print(f"  + Column '{col_name}' added successfully")

        # Add index for raiser_position
        result = conn.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'player_hand_summary'
            AND indexname = 'idx_player_summary_raiser_pos'
        """))

        if result.fetchone():
            print("  - Index 'idx_player_summary_raiser_pos' already exists")
        else:
            conn.execute(text("""
                CREATE INDEX idx_player_summary_raiser_pos
                ON player_hand_summary(raiser_position)
            """))
            conn.commit()
            print("  + Index 'idx_player_summary_raiser_pos' created")


def recalculate_flags(session):
    """Recalculate the new tracking flags for all existing hands"""
    print("\nStep 2: Recalculating flags for all hands...")

    # Get all unique hand IDs
    hand_ids = session.query(RawHand.hand_id).all()
    total_hands = len(hand_ids)
    print(f"  Processing {total_hands} hands...")

    processed = 0
    updated = 0

    for (hand_id,) in hand_ids:
        # Get all preflop actions for this hand
        preflop_actions = session.query(HandAction).filter_by(
            hand_id=hand_id,
            street='preflop'
        ).order_by(HandAction.action_id).all()

        # Find all preflop raises
        raises = [a for a in preflop_actions
                 if a.action_type == 'raise' and a.is_aggressive]

        # Get all summaries for this hand
        summaries = session.query(PlayerHandSummary).filter_by(hand_id=hand_id).all()

        # Identify first raiser (opener) position
        first_raiser_pos = None
        if raises:
            first_raise = raises[0]
            first_raiser_pos = first_raise.position

        # Calculate flags for each player
        for summary in summaries:
            changes_made = False

            # Set raiser_position for players who faced a raise
            if summary.faced_raise and first_raiser_pos:
                if summary.raiser_position != first_raiser_pos:
                    summary.raiser_position = first_raiser_pos
                    changes_made = True

            # Check for facing 4-bet (3rd raise)
            if len(raises) >= 3:
                third_raise = raises[2]
                third_raise_idx = preflop_actions.index(third_raise)

                # Get player actions after the 3rd raise (4-bet)
                player_actions_after = [a for a in preflop_actions[third_raise_idx + 1:]
                                       if a.player_name == summary.player_name
                                       and a.action_type not in ['post_sb', 'post_bb', 'post_ante']]

                faced_4bet = len(player_actions_after) > 0

                if summary.faced_four_bet != faced_4bet:
                    summary.faced_four_bet = faced_4bet
                    changes_made = True

                if faced_4bet and player_actions_after:
                    last_action = player_actions_after[-1]

                    new_fold = (last_action.action_type == 'fold')
                    new_call = (last_action.action_type == 'call')

                    if summary.folded_to_four_bet != new_fold:
                        summary.folded_to_four_bet = new_fold
                        changes_made = True
                    if summary.called_four_bet != new_call:
                        summary.called_four_bet = new_call
                        changes_made = True

            # Check for 5-bet (4th raise)
            if len(raises) >= 4:
                made_5bet = (raises[3].player_name == summary.player_name)
                if summary.five_bet != made_5bet:
                    summary.five_bet = made_5bet
                    changes_made = True

            if changes_made:
                updated += 1

        processed += 1
        if processed % 500 == 0:
            session.commit()
            print(f"  Processed {processed}/{total_hands} hands ({updated} records updated)...")

    session.commit()
    print(f"  Completed: {processed} hands processed, {updated} records updated")


def main():
    """Run migration"""
    print("=" * 60)
    print("FACING 4-BET TRACKING MIGRATION")
    print("=" * 60)

    # Create engine and session
    db_url = get_db_url()
    print(f"\nConnecting to database: {db_url.split('@')[1] if '@' in db_url else 'localhost'}")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Step 1: Add columns
        add_columns_if_not_exists(engine)

        # Step 2: Recalculate flags
        recalculate_flags(session)

        print("\n" + "=" * 60)
        print("MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nNew columns added and flags recalculated:")
        print("  - raiser_position: Position of opener")
        print("  - faced_four_bet: True if faced a 4-bet")
        print("  - folded_to_four_bet: Response to 4-bet")
        print("  - called_four_bet: Response to 4-bet")
        print("  - five_bet: True if made a 5-bet")
        print("\nPosition-specific defense and facing 4-bet analysis now available!")

    except Exception as e:
        print(f"\nError during migration: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
