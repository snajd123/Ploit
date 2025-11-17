"""
SQLAlchemy ORM models for Poker Analysis App database.

These models map to the PostgreSQL tables defined in database_schema.sql.
All models follow the exact schema specified in the project plan.
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, TIMESTAMP,
    DECIMAL, Boolean, ForeignKey, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
from decimal import Decimal

Base = declarative_base()


class RawHand(Base):
    """
    Stores complete hand history text for reference and audit trail.

    Table: raw_hands
    """
    __tablename__ = 'raw_hands'

    hand_id = Column(BigInteger, primary_key=True)
    timestamp = Column(TIMESTAMP, nullable=False)
    table_name = Column(String(255))
    stake_level = Column(String(50))
    game_type = Column(String(50))
    raw_hand_text = Column(Text)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())

    def __repr__(self) -> str:
        return f"<RawHand(hand_id={self.hand_id}, stake={self.stake_level}, timestamp={self.timestamp})>"


class HandAction(Base):
    """
    Every single action in every hand for granular analysis.

    Table: hand_actions
    """
    __tablename__ = 'hand_actions'

    action_id = Column(Integer, primary_key=True, autoincrement=True)
    hand_id = Column(BigInteger, ForeignKey('raw_hands.hand_id', ondelete='CASCADE'), nullable=False)
    player_name = Column(String(100), nullable=False)
    position = Column(String(10))
    street = Column(String(10))
    action_type = Column(String(20))
    amount = Column(DECIMAL(10, 2))
    pot_size_before = Column(DECIMAL(10, 2))
    pot_size_after = Column(DECIMAL(10, 2))
    is_aggressive = Column(Boolean)
    facing_bet = Column(Boolean)
    stack_size = Column(DECIMAL(10, 2))
    created_at = Column(TIMESTAMP, default=func.current_timestamp())

    def __repr__(self) -> str:
        return f"<HandAction(hand_id={self.hand_id}, player={self.player_name}, action={self.action_type})>"


class PlayerHandSummary(Base):
    """
    Per-player per-hand boolean flags for efficient stat calculation.

    Table: player_hand_summary
    """
    __tablename__ = 'player_hand_summary'

    summary_id = Column(Integer, primary_key=True, autoincrement=True)
    hand_id = Column(BigInteger, ForeignKey('raw_hands.hand_id', ondelete='CASCADE'), nullable=False)
    player_name = Column(String(100), nullable=False)
    position = Column(String(10))

    # Preflop flags
    vpip = Column(Boolean, default=False)
    pfr = Column(Boolean, default=False)
    limp = Column(Boolean, default=False)
    faced_raise = Column(Boolean, default=False)
    faced_three_bet = Column(Boolean, default=False)
    folded_to_three_bet = Column(Boolean, default=False)
    called_three_bet = Column(Boolean, default=False)
    made_three_bet = Column(Boolean, default=False)
    four_bet = Column(Boolean, default=False)
    cold_call = Column(Boolean, default=False)
    squeeze = Column(Boolean, default=False)

    # Street visibility
    saw_flop = Column(Boolean, default=False)
    saw_turn = Column(Boolean, default=False)
    saw_river = Column(Boolean, default=False)

    # Continuation bet opportunities and actions (as aggressor)
    cbet_opportunity_flop = Column(Boolean, default=False)
    cbet_made_flop = Column(Boolean, default=False)
    cbet_opportunity_turn = Column(Boolean, default=False)
    cbet_made_turn = Column(Boolean, default=False)
    cbet_opportunity_river = Column(Boolean, default=False)
    cbet_made_river = Column(Boolean, default=False)

    # Facing continuation bets
    faced_cbet_flop = Column(Boolean, default=False)
    folded_to_cbet_flop = Column(Boolean, default=False)
    called_cbet_flop = Column(Boolean, default=False)
    raised_cbet_flop = Column(Boolean, default=False)

    faced_cbet_turn = Column(Boolean, default=False)
    folded_to_cbet_turn = Column(Boolean, default=False)
    called_cbet_turn = Column(Boolean, default=False)
    raised_cbet_turn = Column(Boolean, default=False)

    faced_cbet_river = Column(Boolean, default=False)
    folded_to_cbet_river = Column(Boolean, default=False)
    called_cbet_river = Column(Boolean, default=False)
    raised_cbet_river = Column(Boolean, default=False)

    # Check-raise flags
    check_raise_opportunity_flop = Column(Boolean, default=False)
    check_raised_flop = Column(Boolean, default=False)
    check_raise_opportunity_turn = Column(Boolean, default=False)
    check_raised_turn = Column(Boolean, default=False)
    check_raise_opportunity_river = Column(Boolean, default=False)
    check_raised_river = Column(Boolean, default=False)

    # Donk bets (betting into aggressor)
    donk_bet_flop = Column(Boolean, default=False)
    donk_bet_turn = Column(Boolean, default=False)
    donk_bet_river = Column(Boolean, default=False)

    # Float plays (call flop, bet/raise later when checked to)
    float_flop = Column(Boolean, default=False)

    # Steal and blind defense
    steal_attempt = Column(Boolean, default=False)
    faced_steal = Column(Boolean, default=False)
    fold_to_steal = Column(Boolean, default=False)
    call_steal = Column(Boolean, default=False)
    three_bet_vs_steal = Column(Boolean, default=False)

    # Showdown
    went_to_showdown = Column(Boolean, default=False)
    won_at_showdown = Column(Boolean, default=False)
    showed_bluff = Column(Boolean, default=False)

    # Hand result
    won_hand = Column(Boolean, default=False)
    profit_loss = Column(DECIMAL(10, 2))

    created_at = Column(TIMESTAMP, default=func.current_timestamp())

    __table_args__ = (
        UniqueConstraint('hand_id', 'player_name', name='uq_hand_player'),
    )

    def __repr__(self) -> str:
        return f"<PlayerHandSummary(hand_id={self.hand_id}, player={self.player_name}, vpip={self.vpip})>"


class PlayerStats(Base):
    """
    Pre-calculated traditional statistics and composite metrics.
    Updated after each hand upload batch.

    Table: player_stats
    """
    __tablename__ = 'player_stats'

    player_name = Column(String(100), primary_key=True)
    total_hands = Column(Integer, default=0)

    # Preflop statistics (percentages 0-100)
    vpip_pct = Column(DECIMAL(5, 2))
    pfr_pct = Column(DECIMAL(5, 2))
    limp_pct = Column(DECIMAL(5, 2))
    three_bet_pct = Column(DECIMAL(5, 2))
    fold_to_three_bet_pct = Column(DECIMAL(5, 2))
    four_bet_pct = Column(DECIMAL(5, 2))
    cold_call_pct = Column(DECIMAL(5, 2))
    squeeze_pct = Column(DECIMAL(5, 2))

    # Positional VPIP (for positional awareness analysis)
    vpip_utg = Column(DECIMAL(5, 2))
    vpip_hj = Column(DECIMAL(5, 2))
    vpip_mp = Column(DECIMAL(5, 2))
    vpip_co = Column(DECIMAL(5, 2))
    vpip_btn = Column(DECIMAL(5, 2))
    vpip_sb = Column(DECIMAL(5, 2))
    vpip_bb = Column(DECIMAL(5, 2))

    # Steal and blind defense
    steal_attempt_pct = Column(DECIMAL(5, 2))
    fold_to_steal_pct = Column(DECIMAL(5, 2))
    three_bet_vs_steal_pct = Column(DECIMAL(5, 2))

    # Postflop aggression (continuation betting)
    cbet_flop_pct = Column(DECIMAL(5, 2))
    cbet_turn_pct = Column(DECIMAL(5, 2))
    cbet_river_pct = Column(DECIMAL(5, 2))

    # Postflop defense (facing cbets)
    fold_to_cbet_flop_pct = Column(DECIMAL(5, 2))
    fold_to_cbet_turn_pct = Column(DECIMAL(5, 2))
    fold_to_cbet_river_pct = Column(DECIMAL(5, 2))

    call_cbet_flop_pct = Column(DECIMAL(5, 2))
    call_cbet_turn_pct = Column(DECIMAL(5, 2))
    call_cbet_river_pct = Column(DECIMAL(5, 2))

    raise_cbet_flop_pct = Column(DECIMAL(5, 2))
    raise_cbet_turn_pct = Column(DECIMAL(5, 2))
    raise_cbet_river_pct = Column(DECIMAL(5, 2))

    # Check-raise frequency
    check_raise_flop_pct = Column(DECIMAL(5, 2))
    check_raise_turn_pct = Column(DECIMAL(5, 2))
    check_raise_river_pct = Column(DECIMAL(5, 2))

    # Donk betting
    donk_bet_flop_pct = Column(DECIMAL(5, 2))
    donk_bet_turn_pct = Column(DECIMAL(5, 2))
    donk_bet_river_pct = Column(DECIMAL(5, 2))

    # Float frequency
    float_flop_pct = Column(DECIMAL(5, 2))

    # Aggression metrics
    af = Column(DECIMAL(5, 2))
    afq = Column(DECIMAL(5, 2))

    # Showdown metrics
    wtsd_pct = Column(DECIMAL(5, 2))
    wsd_pct = Column(DECIMAL(5, 2))

    # Win rate
    total_profit_loss = Column(DECIMAL(12, 2))
    bb_per_100 = Column(DECIMAL(8, 2))

    # Composite Metrics (calculated and stored for query performance)
    exploitability_index = Column(DECIMAL(5, 2))
    pressure_vulnerability_score = Column(DECIMAL(5, 2))
    aggression_consistency_ratio = Column(DECIMAL(5, 2))
    positional_awareness_index = Column(DECIMAL(5, 2))
    blind_defense_efficiency = Column(DECIMAL(5, 2))
    value_bluff_imbalance_ratio = Column(DECIMAL(5, 2))
    range_polarization_factor = Column(DECIMAL(5, 2))
    street_fold_gradient = Column(DECIMAL(5, 2))
    delayed_aggression_coefficient = Column(DECIMAL(5, 2))
    multi_street_persistence_score = Column(DECIMAL(5, 2))
    optimal_stake_skill_rating = Column(DECIMAL(5, 2))
    player_type = Column(String(20))

    # Metadata
    last_updated = Column(TIMESTAMP, default=func.current_timestamp())
    first_hand_date = Column(TIMESTAMP)
    last_hand_date = Column(TIMESTAMP)

    def __repr__(self) -> str:
        return f"<PlayerStats(player={self.player_name}, hands={self.total_hands}, vpip={self.vpip_pct}, type={self.player_type})>"


class UploadSession(Base):
    """
    Track hand history file uploads for audit and debugging.

    Table: upload_sessions
    """
    __tablename__ = 'upload_sessions'

    session_id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255))
    upload_timestamp = Column(TIMESTAMP, default=func.current_timestamp())
    hands_parsed = Column(Integer, default=0)
    hands_failed = Column(Integer, default=0)
    players_updated = Column(Integer, default=0)
    stake_level = Column(String(50))
    status = Column(String(50), default='processing')
    error_message = Column(Text)
    processing_time_seconds = Column(Integer)

    def __repr__(self) -> str:
        return f"<UploadSession(session_id={self.session_id}, filename={self.filename}, status={self.status})>"
