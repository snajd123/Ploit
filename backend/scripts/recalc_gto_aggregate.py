"""
Recalculate gto_aggregate_freq from actual gto_frequencies data.

This fixes any incorrectly calculated aggregate frequencies.
"""

import os
import sys
import re
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use transaction mode (port 6543) to avoid session pool limits
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres.lyvnuiuatuggtirdxiht:SourBeer2027@aws-1-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require')


def combo_to_hand_type(combo: str) -> str:
    """Convert combo like 'AhKs' to hand type like 'AKs'"""
    if len(combo) == 4:
        r1, s1, r2, s2 = combo[0], combo[1], combo[2], combo[3]
        if r1 == r2:
            return r1 + r2  # Pair
        elif s1 == s2:
            return r1 + r2 + 's'  # Suited
        else:
            return r1 + r2 + 'o'  # Offsuit
    return combo


def recalc_aggregate():
    """Recalculate aggregate frequencies from gto_frequencies."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get all scenarios
        scenarios = session.execute(text("""
            SELECT scenario_id, scenario_name FROM gto_scenarios
        """)).fetchall()

        logger.info(f"Recalculating {len(scenarios)} scenarios...")

        for scenario_id, scenario_name in scenarios:
            # Get all frequencies for this scenario
            freqs = session.execute(text("""
                SELECT hand, frequency FROM gto_frequencies
                WHERE scenario_id = :scenario_id
            """), {'scenario_id': scenario_id}).fetchall()

            if not freqs:
                # No frequency data - set to 0
                session.execute(text("""
                    UPDATE gto_scenarios SET gto_aggregate_freq = 0
                    WHERE scenario_id = :scenario_id
                """), {'scenario_id': scenario_id})
                continue

            # Group by hand type and calculate weighted average
            hand_type_freqs = {}
            for hand, freq in freqs:
                ht = combo_to_hand_type(hand)
                if ht not in hand_type_freqs:
                    hand_type_freqs[ht] = []
                hand_type_freqs[ht].append(Decimal(str(freq)))

            total_weighted_freq = Decimal('0')
            for ht, freq_list in hand_type_freqs.items():
                avg_freq = sum(freq_list) / len(freq_list)
                # Determine combo count
                if len(ht) == 2:  # Pairs like "AA"
                    combo_count = 6
                elif ht.endswith('s'):  # Suited like "AKs"
                    combo_count = 4
                else:  # Offsuit like "AKo"
                    combo_count = 12
                total_weighted_freq += avg_freq * combo_count

            # Calculate aggregate as percentage of 1326 total combos
            aggregate_freq = total_weighted_freq / Decimal('1326')

            session.execute(text("""
                UPDATE gto_scenarios SET gto_aggregate_freq = :agg_freq
                WHERE scenario_id = :scenario_id
            """), {'scenario_id': scenario_id, 'agg_freq': aggregate_freq})

            if 'open' in scenario_name.lower():
                logger.info(f"  {scenario_name}: {float(aggregate_freq)*100:.1f}%")

        session.commit()
        logger.info("Done!")

        # Show opening frequencies
        result = session.execute(text("""
            SELECT scenario_name, position, gto_aggregate_freq * 100 as pct
            FROM gto_scenarios WHERE category = 'opening'
            ORDER BY position
        """))
        logger.info("\nOpening frequencies:")
        for row in result:
            logger.info(f"  {row[0]}: {row[2]:.1f}%")

    except Exception as e:
        session.rollback()
        logger.error(f"Failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    recalc_aggregate()
