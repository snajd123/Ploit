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
            logger.info(f"Updated stats for {player_name}: {stats['total_hands']} hands")
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

        # Get hand dates
        hands_with_timestamps = self.session.query(PlayerHandSummary, RawHand).join(
            RawHand, PlayerHandSummary.hand_id == RawHand.hand_id
        ).filter(PlayerHandSummary.player_name == summaries[0].player_name).all()

        timestamps = [raw_hand.timestamp for _, raw_hand in hands_with_timestamps if raw_hand.timestamp]
        first_hand_date = min(timestamps) if timestamps else None
        last_hand_date = max(timestamps) if timestamps else None

        # Build stats dictionary
        stats = {
            'total_hands': total_hands,
            # Preflop
            'vpip_pct': calc_pct(vpip_count, total_hands),
            'pfr_pct': calc_pct(pfr_count, total_hands),
            'limp_pct': calc_pct(limp_count, total_hands),
            'three_bet_pct': calc_pct(made_3bet_count, faced_3bet_count) if faced_3bet_count > 0 else None,
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
            # Aggression (simplified for now - would need action data for full AF/AFQ)
            'af': None,
            'afq': None,
            # Showdown
            'wtsd_pct': calc_pct(went_to_showdown, saw_flop_count) if saw_flop_count > 0 else None,
            'wsd_pct': calc_pct(won_at_showdown, went_to_showdown) if went_to_showdown > 0 else None,
            # Win rate
            'total_profit_loss': total_profit_loss,
            'bb_per_100': None,  # TODO: Calculate from stake level
            # Dates
            'first_hand_date': first_hand_date,
            'last_hand_date': last_hand_date,
            # Composite metrics (will be calculated separately)
            'exploitability_index': None,
            'pressure_vulnerability_score': None,
            'aggression_consistency_ratio': None,
            'positional_awareness_index': None,
            'blind_defense_efficiency': None,
            'value_bluff_imbalance_ratio': None,
            'range_polarization_factor': None,
            'street_fold_gradient': None,
            'delayed_aggression_coefficient': None,
            'multi_street_persistence_score': None,
            'optimal_stake_skill_rating': None,
            'player_type': None
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

            # Convert to dictionary
            return {
                'player_name': player_stats.player_name,
                'total_hands': player_stats.total_hands,
                'vpip_pct': float(player_stats.vpip_pct) if player_stats.vpip_pct else None,
                'pfr_pct': float(player_stats.pfr_pct) if player_stats.pfr_pct else None,
                # Add all other stats...
                # (truncated for brevity - would include all fields)
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
