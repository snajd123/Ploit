"""
Database service layer for poker analysis app.

Handles all database operations including:
- Inserting parsed hands
- Updating player statistics
- Querying player data
- Aggregating statistics from boolean flags
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func, and_, or_, text
from typing import List, Dict, Optional, Any
from datetime import datetime
from decimal import Decimal
import logging

from backend.models.database_models import (
    RawHand, HandAction, PlayerHandSummary, PlayerStats, UploadSession
)
from backend.parser.data_structures import Hand, Action, PlayerHandSummaryFlags
from backend.database import get_db
from backend.services.stats_calculator import StatsCalculator

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Service class for database operations.

    Provides methods for inserting hands, updating statistics,
    and querying player data.
    """

    def __init__(self, session: Session):
        """
        Initialize database service.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    # ========================================
    # Hand Insertion
    # ========================================

    def insert_hand(self, hand: Hand) -> bool:
        """
        Insert a single parsed hand into the database.

        Inserts into:
        - raw_hands: Complete hand history
        - hand_actions: All actions
        - player_hand_summary: Boolean flags for each player

        Args:
            hand: Parsed Hand object

        Returns:
            True if successful, False otherwise

        Raises:
            IntegrityError: If hand_id already exists
            SQLAlchemyError: For other database errors
        """
        try:
            # Insert raw hand
            raw_hand = RawHand(
                hand_id=hand.hand_id,
                timestamp=hand.timestamp,
                table_name=hand.table_name,
                stake_level=hand.stake_level,
                game_type=hand.game_type,
                raw_hand_text=hand.raw_text
            )
            self.session.add(raw_hand)
            # Flush to catch duplicate hand_id errors before inserting actions
            self.session.flush()

            # Insert hand actions
            for action in hand.actions:
                hand_action = HandAction(
                    hand_id=hand.hand_id,
                    player_name=action.player_name,
                    position=next((p.position for p in hand.players if p.name == action.player_name), None),
                    street=action.street.value,
                    action_type=action.action_type.value,
                    amount=action.amount,
                    pot_size_before=action.pot_size_before,
                    pot_size_after=action.pot_size_after,
                    is_aggressive=action.is_aggressive,
                    facing_bet=action.facing_bet,
                    stack_size=action.stack_size
                )
                self.session.add(hand_action)

            # Insert player hand summaries
            for player_name, flags in hand.player_flags.items():
                summary = self._flags_to_summary(hand.hand_id, flags)
                self.session.add(summary)

            self.session.commit()
            logger.info(f"Successfully inserted hand {hand.hand_id}")
            return True

        except IntegrityError as e:
            self.session.rollback()
            logger.warning(f"Hand {hand.hand_id} already exists: {str(e)}")
            return False

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error inserting hand {hand.hand_id}: {str(e)}")
            raise

    def insert_hand_batch(self, hands: List[Hand]) -> Dict[str, Any]:
        """
        Insert multiple hands atomically.

        Args:
            hands: List of parsed Hand objects

        Returns:
            Dictionary with:
            - hands_inserted: Number successfully inserted
            - hands_failed: Number that failed
            - error_details: List of error messages
        """
        result = {
            'hands_inserted': 0,
            'hands_failed': 0,
            'error_details': []
        }

        for hand in hands:
            try:
                if self.insert_hand(hand):
                    result['hands_inserted'] += 1
                else:
                    result['hands_failed'] += 1
                    result['error_details'].append(f"Hand {hand.hand_id} already exists")

            except Exception as e:
                result['hands_failed'] += 1
                error_msg = f"Hand {hand.hand_id} failed: {str(e)}"
                result['error_details'].append(error_msg)
                logger.error(error_msg)

        logger.info(f"Batch insert complete: {result['hands_inserted']} inserted, {result['hands_failed']} failed")
        return result

    def _flags_to_summary(self, hand_id: int, flags: PlayerHandSummaryFlags) -> PlayerHandSummary:
        """
        Convert PlayerHandSummaryFlags to PlayerHandSummary database model.

        Args:
            hand_id: Hand ID
            flags: PlayerHandSummaryFlags object

        Returns:
            PlayerHandSummary ORM object
        """
        return PlayerHandSummary(
            hand_id=hand_id,
            player_name=flags.player_name,
            position=flags.position,
            # Preflop
            vpip=flags.vpip,
            pfr=flags.pfr,
            limp=flags.limp,
            faced_raise=flags.faced_raise,
            faced_three_bet=flags.faced_three_bet,
            folded_to_three_bet=flags.folded_to_three_bet,
            called_three_bet=flags.called_three_bet,
            made_three_bet=flags.made_three_bet,
            four_bet=flags.four_bet,
            cold_call=flags.cold_call,
            squeeze=flags.squeeze,
            # Street visibility
            saw_flop=flags.saw_flop,
            saw_turn=flags.saw_turn,
            saw_river=flags.saw_river,
            # Cbet opportunities
            cbet_opportunity_flop=flags.cbet_opportunity_flop,
            cbet_made_flop=flags.cbet_made_flop,
            cbet_opportunity_turn=flags.cbet_opportunity_turn,
            cbet_made_turn=flags.cbet_made_turn,
            cbet_opportunity_river=flags.cbet_opportunity_river,
            cbet_made_river=flags.cbet_made_river,
            # Facing cbets
            faced_cbet_flop=flags.faced_cbet_flop,
            folded_to_cbet_flop=flags.folded_to_cbet_flop,
            called_cbet_flop=flags.called_cbet_flop,
            raised_cbet_flop=flags.raised_cbet_flop,
            faced_cbet_turn=flags.faced_cbet_turn,
            folded_to_cbet_turn=flags.folded_to_cbet_turn,
            called_cbet_turn=flags.called_cbet_turn,
            raised_cbet_turn=flags.raised_cbet_turn,
            faced_cbet_river=flags.faced_cbet_river,
            folded_to_cbet_river=flags.folded_to_cbet_river,
            called_cbet_river=flags.called_cbet_river,
            raised_cbet_river=flags.raised_cbet_river,
            # Check-raise
            check_raise_opportunity_flop=flags.check_raise_opportunity_flop,
            check_raised_flop=flags.check_raised_flop,
            check_raise_opportunity_turn=flags.check_raise_opportunity_turn,
            check_raised_turn=flags.check_raised_turn,
            check_raise_opportunity_river=flags.check_raise_opportunity_river,
            check_raised_river=flags.check_raised_river,
            # Donk bets
            donk_bet_flop=flags.donk_bet_flop,
            donk_bet_turn=flags.donk_bet_turn,
            donk_bet_river=flags.donk_bet_river,
            # Float
            float_flop=flags.float_flop,
            # Steal and defense
            steal_attempt=flags.steal_attempt,
            faced_steal=flags.faced_steal,
            fold_to_steal=flags.fold_to_steal,
            call_steal=flags.call_steal,
            three_bet_vs_steal=flags.three_bet_vs_steal,
            # Showdown
            went_to_showdown=flags.went_to_showdown,
            won_at_showdown=flags.won_at_showdown,
            showed_bluff=flags.showed_bluff,
            # Result
            won_hand=flags.won_hand,
            profit_loss=flags.profit_loss
        )

    # ========================================
    # Statistics Calculation
    # ========================================

    def recalculate_hand_flags(self, hand_id: int) -> bool:
        """
        Recalculate flags for a single hand using the latest flag calculation logic.

        This method:
        1. Gets the raw hand text from raw_hands
        2. Re-parses it to create a Hand object with actions
        3. Recalculates flags using FlagCalculator
        4. Updates player_hand_summary records

        Args:
            hand_id: Hand ID to recalculate

        Returns:
            True if successful, False otherwise
        """
        try:
            from backend.parser.pokerstars_parser import PokerStarsParser

            # Get raw hand
            raw_hand = self.session.query(RawHand).filter(
                RawHand.hand_id == hand_id
            ).first()

            if not raw_hand:
                logger.warning(f"Hand {hand_id} not found in raw_hands")
                return False

            # Parse the hand
            parser = PokerStarsParser()
            hand = parser.parse_single_hand(raw_hand.raw_hand_text)

            if not hand or not hand.player_flags:
                logger.warning(f"Failed to parse hand {hand_id}")
                return False

            # Update player_hand_summary for each player
            for player_name, flags in hand.player_flags.items():
                summary = self.session.query(PlayerHandSummary).filter(
                    PlayerHandSummary.hand_id == hand_id,
                    PlayerHandSummary.player_name == player_name
                ).first()

                if summary:
                    # Update flags
                    summary.vpip = flags.vpip
                    summary.pfr = flags.pfr
                    summary.limp = flags.limp
                    summary.faced_raise = flags.faced_raise
                    summary.faced_three_bet = flags.faced_three_bet
                    summary.folded_to_three_bet = flags.folded_to_three_bet
                    summary.called_three_bet = flags.called_three_bet
                    summary.made_three_bet = flags.made_three_bet
                    summary.four_bet = flags.four_bet
                    summary.cold_call = flags.cold_call
                    summary.squeeze = flags.squeeze
                    summary.saw_flop = flags.saw_flop
                    summary.saw_turn = flags.saw_turn
                    summary.saw_river = flags.saw_river
                    summary.cbet_opportunity_flop = flags.cbet_opportunity_flop
                    summary.cbet_made_flop = flags.cbet_made_flop
                    summary.cbet_opportunity_turn = flags.cbet_opportunity_turn
                    summary.cbet_made_turn = flags.cbet_made_turn
                    summary.cbet_opportunity_river = flags.cbet_opportunity_river
                    summary.cbet_made_river = flags.cbet_made_river
                    summary.faced_cbet_flop = flags.faced_cbet_flop
                    summary.folded_to_cbet_flop = flags.folded_to_cbet_flop
                    summary.called_cbet_flop = flags.called_cbet_flop
                    summary.raised_cbet_flop = flags.raised_cbet_flop
                    summary.faced_cbet_turn = flags.faced_cbet_turn
                    summary.folded_to_cbet_turn = flags.folded_to_cbet_turn
                    summary.called_cbet_turn = flags.called_cbet_turn
                    summary.raised_cbet_turn = flags.raised_cbet_turn
                    summary.faced_cbet_river = flags.faced_cbet_river
                    summary.folded_to_cbet_river = flags.folded_to_cbet_river
                    summary.called_cbet_river = flags.called_cbet_river
                    summary.raised_cbet_river = flags.raised_cbet_river
                    summary.went_to_showdown = flags.went_to_showdown
                    summary.won_at_showdown = flags.won_at_showdown
                    # Add other flags as needed

            self.session.commit()
            return True

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error recalculating flags for hand {hand_id}: {str(e)}")
            return False

    def update_player_stats(self, player_name: str) -> bool:
        """
        Recalculate aggregated stats for a single player.

        Process:
        1. Calculate traditional statistics from player_hand_summary
        2. Calculate composite metrics using stats_calculator
        3. Update player_stats table

        Args:
            player_name: Name of player to update

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all hands for this player
            summaries = self.session.query(PlayerHandSummary).filter(
                PlayerHandSummary.player_name == player_name
            ).all()

            if not summaries:
                logger.warning(f"No hands found for player {player_name}")
                return False

            # Calculate traditional stats
            stats = self._calculate_traditional_stats(summaries)

            # Calculate composite metrics
            calculator = StatsCalculator(stats)
            composite_metrics = calculator.calculate_all_metrics()

            # Merge composite metrics into stats
            stats.update(composite_metrics)

            # Check if player exists in player_stats
            player_stats = self.session.query(PlayerStats).filter(
                PlayerStats.player_name == player_name
            ).first()

            if player_stats:
                # Update existing
                for key, value in stats.items():
                    setattr(player_stats, key, value)
                player_stats.last_updated = datetime.now()
            else:
                # Create new
                player_stats = PlayerStats(player_name=player_name, **stats)
                self.session.add(player_stats)

            self.session.commit()
            logger.info(f"Updated stats for {player_name}: {stats['total_hands']} hands, type={stats.get('player_type')}")
            return True

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error updating stats for {player_name}: {str(e)}")
            return False

    def _calculate_traditional_stats(self, summaries: List[PlayerHandSummary]) -> Dict[str, Any]:
        """
        Calculate traditional statistics from player hand summaries.

        Args:
            summaries: List of PlayerHandSummary objects

        Returns:
            Dictionary of calculated statistics
        """
        total_hands = len(summaries)

        def calc_pct(true_count: int, total: int) -> Optional[Decimal]:
            """Calculate percentage, return None if total is 0"""
            if total == 0:
                return None
            return Decimal(str(round((true_count / total) * 100, 2)))

        def count_true(attr: str) -> int:
            """Count how many summaries have attribute set to True"""
            return sum(1 for s in summaries if getattr(s, attr, False))

        # Preflop statistics
        vpip_count = count_true('vpip')
        pfr_count = count_true('pfr')
        limp_count = count_true('limp')

        faced_raise_count = count_true('faced_raise')
        faced_3bet_count = count_true('faced_three_bet')
        folded_to_3bet_count = count_true('folded_to_three_bet')
        made_3bet_count = count_true('made_three_bet')
        four_bet_count = count_true('four_bet')
        cold_call_count = count_true('cold_call')
        squeeze_count = count_true('squeeze')

        # Positional VPIP
        positions = {}
        for pos in ['utg', 'hj', 'mp', 'co', 'btn', 'sb', 'bb']:
            pos_summaries = [s for s in summaries if s.position and s.position.upper() == pos.upper()]
            pos_vpip = sum(1 for s in pos_summaries if s.vpip)
            positions[f'vpip_{pos}'] = calc_pct(pos_vpip, len(pos_summaries)) if pos_summaries else None

        # Steal and blind defense
        steal_attempt_count = count_true('steal_attempt')
        faced_steal_count = count_true('faced_steal')
        fold_to_steal_count = count_true('fold_to_steal')
        three_bet_vs_steal_count = count_true('three_bet_vs_steal')

        # Continuation betting
        cbet_opp_flop = count_true('cbet_opportunity_flop')
        cbet_made_flop = count_true('cbet_made_flop')
        cbet_opp_turn = count_true('cbet_opportunity_turn')
        cbet_made_turn = count_true('cbet_made_turn')
        cbet_opp_river = count_true('cbet_opportunity_river')
        cbet_made_river = count_true('cbet_made_river')

        # Facing cbets
        faced_cbet_flop = count_true('faced_cbet_flop')
        folded_to_cbet_flop = count_true('folded_to_cbet_flop')
        called_cbet_flop = count_true('called_cbet_flop')
        raised_cbet_flop = count_true('raised_cbet_flop')

        faced_cbet_turn = count_true('faced_cbet_turn')
        folded_to_cbet_turn = count_true('folded_to_cbet_turn')
        called_cbet_turn = count_true('called_cbet_turn')
        raised_cbet_turn = count_true('raised_cbet_turn')

        faced_cbet_river = count_true('faced_cbet_river')
        folded_to_cbet_river = count_true('folded_to_cbet_river')
        called_cbet_river = count_true('called_cbet_river')
        raised_cbet_river = count_true('raised_cbet_river')

        # Check-raise
        cr_opp_flop = count_true('check_raise_opportunity_flop')
        cr_flop = count_true('check_raised_flop')
        cr_opp_turn = count_true('check_raise_opportunity_turn')
        cr_turn = count_true('check_raised_turn')
        cr_opp_river = count_true('check_raise_opportunity_river')
        cr_river = count_true('check_raised_river')

        # Donk bets
        donk_flop = count_true('donk_bet_flop')
        donk_turn = count_true('donk_bet_turn')
        donk_river = count_true('donk_bet_river')
        saw_flop_count = count_true('saw_flop')

        # Float
        float_flop = count_true('float_flop')

        # Showdown
        saw_flop_count = count_true('saw_flop')
        went_to_showdown = count_true('went_to_showdown')
        won_at_showdown = count_true('won_at_showdown')

        # Profit/loss
        total_profit_loss = sum(s.profit_loss or Decimal("0") for s in summaries)

        # Aggression metrics (AF and AFQ) - query hand_actions table
        player_name = summaries[0].player_name if summaries else None
        af_value = None
        afq_value = None

        if player_name:
            from sqlalchemy import func
            from ..models.database_models import HandAction

            # Get action counts for this player (postflop only - exclude preflop)
            action_counts = self.session.query(
                HandAction.action_type,
                func.count(HandAction.action_id).label('count')
            ).filter(
                HandAction.player_name == player_name,
                HandAction.street.in_(['flop', 'turn', 'river'])  # Postflop only
            ).group_by(HandAction.action_type).all()

            action_dict = {action_type: count for action_type, count in action_counts}

            # Count aggressive actions (bet, raise) and passive actions (call, check, fold)
            bets = action_dict.get('bet', 0) + action_dict.get('BET', 0)
            raises = action_dict.get('raise', 0) + action_dict.get('RAISE', 0) + action_dict.get('raises', 0)
            calls = action_dict.get('call', 0) + action_dict.get('CALL', 0) + action_dict.get('calls', 0)
            checks = action_dict.get('check', 0) + action_dict.get('CHECK', 0) + action_dict.get('checks', 0)

            aggressive_actions = bets + raises

            # Calculate AF = (bets + raises) / calls
            if calls > 0:
                af_value = Decimal(str(round(aggressive_actions / calls, 2)))

            # Calculate AFQ = (bets + raises) / (bets + raises + calls + checks)
            total_voluntary_actions = aggressive_actions + calls + checks
            if total_voluntary_actions > 0:
                afq_value = Decimal(str(round((aggressive_actions / total_voluntary_actions) * 100, 2)))

        # Get hand dates and stake levels
        hands_with_timestamps = self.session.query(PlayerHandSummary, RawHand).join(
            RawHand, PlayerHandSummary.hand_id == RawHand.hand_id
        ).filter(PlayerHandSummary.player_name == summaries[0].player_name).all()

        timestamps = [raw_hand.timestamp for _, raw_hand in hands_with_timestamps if raw_hand.timestamp]
        first_hand_date = min(timestamps) if timestamps else None
        last_hand_date = max(timestamps) if timestamps else None

        # Calculate bb/100 hands
        bb_per_100_value = None
        if hands_with_timestamps and total_hands > 0:
            # Get the most common stake level for this player
            stake_levels = [raw_hand.stake_level for _, raw_hand in hands_with_timestamps if raw_hand.stake_level]
            if stake_levels:
                # Use the most common stake level
                from collections import Counter
                most_common_stake = Counter(stake_levels).most_common(1)[0][0]

                # Extract big blind from stake level (e.g., "$0.25/$0.50" -> 0.50, "NL100" -> 1.00)
                big_blind = None
                if '/' in most_common_stake:
                    # Format: "$0.25/$0.50" or "0.25/0.50"
                    parts = most_common_stake.replace('$', '').split('/')
                    if len(parts) == 2:
                        try:
                            big_blind = Decimal(parts[1].strip())
                        except:
                            pass
                elif 'NL' in most_common_stake.upper():
                    # Format: "NL100" means $100 buy-in, typically 1/2 game (BB=$2)
                    # Or "NL50" means $50 buy-in, typically 0.25/0.50 game (BB=$0.50)
                    try:
                        buyin = Decimal(most_common_stake.upper().replace('NL', '').replace('$', ''))
                        big_blind = buyin / 50  # Standard 100bb buy-in
                    except:
                        pass

                if big_blind and big_blind > 0:
                    # bb/100 = (total_profit_loss / (total_hands * big_blind)) * 100
                    bb_per_100_value = Decimal(str(round((total_profit_loss / (Decimal(total_hands) * big_blind)) * 100, 2)))

        # Build stats dictionary
        stats = {
            'total_hands': total_hands,
            # Preflop
            'vpip_pct': calc_pct(vpip_count, total_hands),
            'pfr_pct': calc_pct(pfr_count, total_hands),
            'limp_pct': calc_pct(limp_count, total_hands),
            'three_bet_pct': calc_pct(made_3bet_count, faced_raise_count) if faced_raise_count > 0 else None,
            'fold_to_three_bet_pct': calc_pct(folded_to_3bet_count, faced_3bet_count) if faced_3bet_count > 0 else None,
            'four_bet_pct': calc_pct(four_bet_count, made_3bet_count) if made_3bet_count > 0 else None,
            'cold_call_pct': calc_pct(cold_call_count, total_hands),
            'squeeze_pct': calc_pct(squeeze_count, total_hands),
            # Positional VPIP
            **positions,
            # Steal and defense
            'steal_attempt_pct': calc_pct(steal_attempt_count, total_hands),
            'fold_to_steal_pct': calc_pct(fold_to_steal_count, faced_steal_count) if faced_steal_count > 0 else None,
            'three_bet_vs_steal_pct': calc_pct(three_bet_vs_steal_count, faced_steal_count) if faced_steal_count > 0 else None,
            # Cbets
            'cbet_flop_pct': calc_pct(cbet_made_flop, cbet_opp_flop) if cbet_opp_flop > 0 else None,
            'cbet_turn_pct': calc_pct(cbet_made_turn, cbet_opp_turn) if cbet_opp_turn > 0 else None,
            'cbet_river_pct': calc_pct(cbet_made_river, cbet_opp_river) if cbet_opp_river > 0 else None,
            # Facing cbets
            'fold_to_cbet_flop_pct': calc_pct(folded_to_cbet_flop, faced_cbet_flop) if faced_cbet_flop > 0 else None,
            'fold_to_cbet_turn_pct': calc_pct(folded_to_cbet_turn, faced_cbet_turn) if faced_cbet_turn > 0 else None,
            'fold_to_cbet_river_pct': calc_pct(folded_to_cbet_river, faced_cbet_river) if faced_cbet_river > 0 else None,
            'call_cbet_flop_pct': calc_pct(called_cbet_flop, faced_cbet_flop) if faced_cbet_flop > 0 else None,
            'call_cbet_turn_pct': calc_pct(called_cbet_turn, faced_cbet_turn) if faced_cbet_turn > 0 else None,
            'call_cbet_river_pct': calc_pct(called_cbet_river, faced_cbet_river) if faced_cbet_river > 0 else None,
            'raise_cbet_flop_pct': calc_pct(raised_cbet_flop, faced_cbet_flop) if faced_cbet_flop > 0 else None,
            'raise_cbet_turn_pct': calc_pct(raised_cbet_turn, faced_cbet_turn) if faced_cbet_turn > 0 else None,
            'raise_cbet_river_pct': calc_pct(raised_cbet_river, faced_cbet_river) if faced_cbet_river > 0 else None,
            # Check-raise
            'check_raise_flop_pct': calc_pct(cr_flop, cr_opp_flop) if cr_opp_flop > 0 else None,
            'check_raise_turn_pct': calc_pct(cr_turn, cr_opp_turn) if cr_opp_turn > 0 else None,
            'check_raise_river_pct': calc_pct(cr_river, cr_opp_river) if cr_opp_river > 0 else None,
            # Donk bets
            'donk_bet_flop_pct': calc_pct(donk_flop, saw_flop_count) if saw_flop_count > 0 else None,
            'donk_bet_turn_pct': calc_pct(donk_turn, saw_flop_count) if saw_flop_count > 0 else None,
            'donk_bet_river_pct': calc_pct(donk_river, saw_flop_count) if saw_flop_count > 0 else None,
            # Float
            'float_flop_pct': calc_pct(float_flop, saw_flop_count) if saw_flop_count > 0 else None,
            # Aggression metrics
            'af': af_value,
            'afq': afq_value,
            # Showdown
            'wtsd_pct': calc_pct(went_to_showdown, saw_flop_count) if saw_flop_count > 0 else None,
            'wsd_pct': calc_pct(won_at_showdown, went_to_showdown) if went_to_showdown > 0 else None,
            # Win rate
            'total_profit_loss': total_profit_loss,
            'bb_per_100': bb_per_100_value,
            # Dates
            'first_hand_date': first_hand_date,
            'last_hand_date': last_hand_date
            # Note: Composite metrics calculated by StatsCalculator and merged separately
        }

        return stats

    def update_all_player_stats(self) -> Dict[str, int]:
        """
        Recalculate stats for all players.

        Returns:
            Dictionary with 'players_updated' count
        """
        try:
            # Get all unique player names
            player_names = self.session.query(PlayerHandSummary.player_name).distinct().all()
            player_names = [name[0] for name in player_names]

            count = 0
            for player_name in player_names:
                if self.update_player_stats(player_name):
                    count += 1

            logger.info(f"Updated stats for {count} players")
            return {'players_updated': count}

        except Exception as e:
            logger.error(f"Error updating all player stats: {str(e)}")
            return {'players_updated': 0}

    # ========================================
    # Query Functions
    # ========================================

    def get_player_stats(self, player_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve all statistics for a player.

        Args:
            player_name: Name of player

        Returns:
            Dictionary with all stats, or None if not found
        """
        try:
            player_stats = self.session.query(PlayerStats).filter(
                PlayerStats.player_name == player_name
            ).first()

            if not player_stats:
                return None

            # Helper to convert Decimal to float
            def to_float(value):
                return float(value) if value is not None else None

            # Convert to dictionary with ALL stats
            return {
                'player_name': player_stats.player_name,
                'total_hands': player_stats.total_hands,
                # Preflop statistics
                'vpip_pct': to_float(player_stats.vpip_pct),
                'pfr_pct': to_float(player_stats.pfr_pct),
                'limp_pct': to_float(player_stats.limp_pct),
                'three_bet_pct': to_float(player_stats.three_bet_pct),
                'fold_to_three_bet_pct': to_float(player_stats.fold_to_three_bet_pct),
                'four_bet_pct': to_float(player_stats.four_bet_pct),
                'cold_call_pct': to_float(player_stats.cold_call_pct),
                'squeeze_pct': to_float(player_stats.squeeze_pct),
                # Positional VPIP
                'vpip_utg': to_float(player_stats.vpip_utg),
                'vpip_hj': to_float(player_stats.vpip_hj),
                'vpip_mp': to_float(player_stats.vpip_mp),
                'vpip_co': to_float(player_stats.vpip_co),
                'vpip_btn': to_float(player_stats.vpip_btn),
                'vpip_sb': to_float(player_stats.vpip_sb),
                'vpip_bb': to_float(player_stats.vpip_bb),
                # Steal and blind defense
                'steal_attempt_pct': to_float(player_stats.steal_attempt_pct),
                'fold_to_steal_pct': to_float(player_stats.fold_to_steal_pct),
                'three_bet_vs_steal_pct': to_float(player_stats.three_bet_vs_steal_pct),
                # Continuation betting
                'cbet_flop_pct': to_float(player_stats.cbet_flop_pct),
                'cbet_turn_pct': to_float(player_stats.cbet_turn_pct),
                'cbet_river_pct': to_float(player_stats.cbet_river_pct),
                # Facing cbets
                'fold_to_cbet_flop_pct': to_float(player_stats.fold_to_cbet_flop_pct),
                'fold_to_cbet_turn_pct': to_float(player_stats.fold_to_cbet_turn_pct),
                'fold_to_cbet_river_pct': to_float(player_stats.fold_to_cbet_river_pct),
                'call_cbet_flop_pct': to_float(player_stats.call_cbet_flop_pct),
                'call_cbet_turn_pct': to_float(player_stats.call_cbet_turn_pct),
                'call_cbet_river_pct': to_float(player_stats.call_cbet_river_pct),
                'raise_cbet_flop_pct': to_float(player_stats.raise_cbet_flop_pct),
                'raise_cbet_turn_pct': to_float(player_stats.raise_cbet_turn_pct),
                'raise_cbet_river_pct': to_float(player_stats.raise_cbet_river_pct),
                # Check-raise
                'check_raise_flop_pct': to_float(player_stats.check_raise_flop_pct),
                'check_raise_turn_pct': to_float(player_stats.check_raise_turn_pct),
                'check_raise_river_pct': to_float(player_stats.check_raise_river_pct),
                # Donk betting
                'donk_bet_flop_pct': to_float(player_stats.donk_bet_flop_pct),
                'donk_bet_turn_pct': to_float(player_stats.donk_bet_turn_pct),
                'donk_bet_river_pct': to_float(player_stats.donk_bet_river_pct),
                # Float
                'float_flop_pct': to_float(player_stats.float_flop_pct),
                # Aggression
                'af': to_float(player_stats.af),
                'afq': to_float(player_stats.afq),
                # Showdown
                'wtsd_pct': to_float(player_stats.wtsd_pct),
                'wsd_pct': to_float(player_stats.wsd_pct),
                # Win rate
                'total_profit_loss': to_float(player_stats.total_profit_loss),
                'bb_per_100': to_float(player_stats.bb_per_100),
                # Composite metrics
                'exploitability_index': to_float(player_stats.exploitability_index),
                'pressure_vulnerability_score': to_float(player_stats.pressure_vulnerability_score),
                'aggression_consistency_ratio': to_float(player_stats.aggression_consistency_ratio),
                'positional_awareness_index': to_float(player_stats.positional_awareness_index),
                'blind_defense_efficiency': to_float(player_stats.blind_defense_efficiency),
                'value_bluff_imbalance_ratio': to_float(player_stats.value_bluff_imbalance_ratio),
                'range_polarization_factor': to_float(player_stats.range_polarization_factor),
                'street_fold_gradient': to_float(player_stats.street_fold_gradient),
                'delayed_aggression_coefficient': to_float(player_stats.delayed_aggression_coefficient),
                'multi_street_persistence_score': to_float(player_stats.multi_street_persistence_score),
                'optimal_stake_skill_rating': to_float(player_stats.optimal_stake_skill_rating),
                'player_type': player_stats.player_type,
                # Metadata
                'last_updated': player_stats.last_updated,
                'first_hand_date': player_stats.first_hand_date,
                'last_hand_date': player_stats.last_hand_date
            }

        except SQLAlchemyError as e:
            logger.error(f"Error getting stats for {player_name}: {str(e)}")
            return None

    def get_all_players(
        self,
        min_hands: int = 100,
        stake_level: Optional[str] = None,
        order_by: str = 'total_hands',
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all players matching criteria.

        Args:
            min_hands: Minimum number of hands
            stake_level: Filter by stake level
            order_by: Column to sort by
            limit: Maximum number of players to return

        Returns:
            List of player dictionaries
        """
        try:
            query = self.session.query(PlayerStats).filter(
                PlayerStats.total_hands >= min_hands
            )

            # Apply stake filter if specified
            # TODO: Implement stake filtering (requires joining with raw_hands)

            # Order results
            if hasattr(PlayerStats, order_by):
                query = query.order_by(getattr(PlayerStats, order_by).desc())

            # Limit results
            query = query.limit(limit)

            players = query.all()

            return [{'player_name': p.player_name, 'total_hands': p.total_hands} for p in players]

        except SQLAlchemyError as e:
            logger.error(f"Error getting all players: {str(e)}")
            return []

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get overview statistics about the database.

        Returns:
            Dictionary with database statistics
        """
        try:
            total_hands = self.session.query(func.count(RawHand.hand_id)).scalar() or 0
            total_players = self.session.query(func.count(PlayerStats.player_name)).scalar() or 0

            # Get date range
            if total_hands > 0:
                first_hand = self.session.query(func.min(RawHand.timestamp)).scalar()
                last_hand = self.session.query(func.max(RawHand.timestamp)).scalar()
            else:
                first_hand = None
                last_hand = None

            return {
                'total_hands': total_hands,
                'total_players': total_players,
                'first_hand_date': first_hand,
                'last_hand_date': last_hand
            }

        except SQLAlchemyError as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {}

    # ========================================
    # Upload Session Tracking
    # ========================================

    def create_upload_session(
        self,
        filename: str,
        hands_parsed: int,
        hands_failed: int,
        players_updated: int,
        stake_level: Optional[str] = None,
        processing_time: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> int:
        """
        Create an upload session record.

        Args:
            filename: Name of uploaded file
            hands_parsed: Number of hands successfully parsed
            hands_failed: Number of hands that failed
            players_updated: Number of players updated
            stake_level: Stake level of hands
            processing_time: Processing time in seconds
            error_message: Error message if failed

        Returns:
            Session ID
        """
        try:
            status = 'completed' if hands_failed == 0 else 'partial' if hands_parsed > 0 else 'failed'

            session = UploadSession(
                filename=filename,
                hands_parsed=hands_parsed,
                hands_failed=hands_failed,
                players_updated=players_updated,
                stake_level=stake_level,
                status=status,
                processing_time_seconds=processing_time,
                error_message=error_message
            )

            self.session.add(session)
            self.session.commit()

            logger.info(f"Created upload session {session.session_id} for {filename}")
            return session.session_id

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error creating upload session: {str(e)}")
            return -1
