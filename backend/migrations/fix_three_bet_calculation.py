"""
Migration script to fix 3-bet calculation

This script:
1. Adds three_bet_opportunity column to player_hand_summary table
2. Recalculates three_bet_opportunity for all existing hands
3. Recalculates three_bet_pct for all players using correct denominator

Usage:
    python -m backend.migrations.fix_three_bet_calculation
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database_models import PlayerHandSummary, PlayerStats, RawHand, HandAction
from parser.flag_calculator import FlagCalculator
from parser.data_structures import Hand, Action, Street, ActionType
from decimal import Decimal


def get_db_url():
    """Get database URL from environment or use default"""
    return os.getenv('DATABASE_URL', 'postgresql://ploit_user:ploit123@localhost:5432/ploit_db')


def add_column_if_not_exists(engine):
    """Add three_bet_opportunity column if it doesn't exist"""
    print("Step 1: Adding three_bet_opportunity column...")

    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='player_hand_summary'
            AND column_name='three_bet_opportunity'
        """))

        if result.fetchone():
            print("  ✓ Column already exists")
        else:
            # Add column
            conn.execute(text("""
                ALTER TABLE player_hand_summary
                ADD COLUMN three_bet_opportunity BOOLEAN DEFAULT FALSE
            """))
            conn.commit()
            print("  ✓ Column added successfully")


def recalculate_three_bet_opportunities(session):
    """Recalculate three_bet_opportunity for all existing hands"""
    print("\nStep 2: Recalculating three_bet_opportunity flags...")

    # Get all unique hand IDs
    hand_ids = session.query(RawHand.hand_id).all()
    total_hands = len(hand_ids)
    print(f"  Processing {total_hands} hands...")

    processed = 0
    updated = 0

    for (hand_id,) in hand_ids:
        # Get raw hand data
        raw_hand = session.query(RawHand).filter_by(hand_id=hand_id).first()
        if not raw_hand:
            continue

        # Get all actions for this hand
        actions = session.query(HandAction).filter_by(hand_id=hand_id).order_by(HandAction.action_id).all()

        # Convert to parser format
        hand_actions = []
        for action in actions:
            hand_actions.append(Action(
                player_name=action.player_name,
                action_type=ActionType(action.action_type.lower()) if action.action_type else ActionType.FOLD,
                amount=float(action.amount) if action.amount else 0.0,
                street=Street(action.street.lower()) if action.street else Street.PREFLOP,
                facing_bet=action.facing_bet or False,
                is_aggressive=action.is_aggressive or False,
                position=action.position
            ))

        hand = Hand(
            hand_id=hand_id,
            actions=hand_actions
        )

        calculator = FlagCalculator(hand)

        # Get all summaries for this hand
        summaries = session.query(PlayerHandSummary).filter_by(hand_id=hand_id).all()

        for summary in summaries:
            # Count preflop raises
            preflop_actions = [a for a in hand.actions if a.street == Street.PREFLOP]
            raises = [a for a in preflop_actions
                     if a.action_type == ActionType.RAISE and a.is_aggressive]
            raise_count = len(raises)

            if raise_count >= 1:
                # Check if player made first raise
                made_first_raise = (raises[0].player_name == summary.player_name if raises else False)

                # Check if player faced first raise
                if raises:
                    first_raise_idx = preflop_actions.index(raises[0])
                    player_actions_after = [a for a in preflop_actions[first_raise_idx + 1:]
                                          if a.player_name == summary.player_name]
                    faced_first_raise = len(player_actions_after) > 0
                else:
                    faced_first_raise = False

                # Set three_bet_opportunity
                old_value = summary.three_bet_opportunity
                new_value = faced_first_raise and not made_first_raise
                summary.three_bet_opportunity = new_value

                if old_value != new_value:
                    updated += 1

        processed += 1
        if processed % 100 == 0:
            session.commit()
            print(f"  Processed {processed}/{total_hands} hands ({updated} flags updated)...")

    session.commit()
    print(f"  ✓ Completed: {processed} hands processed, {updated} flags updated")


def recalculate_player_stats(session):
    """Recalculate three_bet_pct for all players"""
    print("\nStep 3: Recalculating three_bet_pct for all players...")

    players = session.query(PlayerStats).all()
    total_players = len(players)
    print(f"  Processing {total_players} players...")

    for player in players:
        # Get all summaries for this player
        summaries = session.query(PlayerHandSummary).filter_by(player_name=player.player_name).all()

        if not summaries:
            continue

        # Count opportunities and 3-bets
        three_bet_opportunity_count = sum(1 for s in summaries if s.three_bet_opportunity)
        made_3bet_count = sum(1 for s in summaries if s.made_three_bet)

        # Calculate percentage
        if three_bet_opportunity_count > 0:
            old_value = player.three_bet_pct
            player.three_bet_pct = Decimal(str(round(made_3bet_count / three_bet_opportunity_count * 100, 2)))

            if old_value != player.three_bet_pct:
                print(f"    {player.player_name}: {old_value}% → {player.three_bet_pct}% "
                      f"({made_3bet_count}/{three_bet_opportunity_count} opportunities)")
        else:
            player.three_bet_pct = None

    session.commit()
    print(f"  ✓ Completed: {total_players} players updated")


def main():
    """Run migration"""
    print("=" * 60)
    print("3-BET CALCULATION FIX MIGRATION")
    print("=" * 60)

    # Create engine and session
    db_url = get_db_url()
    print(f"\nConnecting to database: {db_url.split('@')[1] if '@' in db_url else 'localhost'}")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Step 1: Add column
        add_column_if_not_exists(engine)

        # Step 2: Recalculate flags
        recalculate_three_bet_opportunities(session)

        # Step 3: Recalculate stats
        recalculate_player_stats(session)

        print("\n" + "=" * 60)
        print("MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\n3-bet calculations are now fixed!")
        print("- three_bet_opportunity column added")
        print("- All hand flags recalculated")
        print("- All player stats updated")

    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
