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

    # Board cards
    flop_card_1 = Column(String(2))
    flop_card_2 = Column(String(2))
    flop_card_3 = Column(String(2))
    turn_card = Column(String(2))
    river_card = Column(String(2))

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
    Per-player per-hand preflop flags for statistical tracking.

    Table: player_hand_summary
    """
    __tablename__ = 'player_hand_summary'
    __table_args__ = {'extend_existing': True}

    summary_id = Column(Integer, primary_key=True, autoincrement=True)
    hand_id = Column(BigInteger, nullable=False)
    player_name = Column(String(100), nullable=False)
    position = Column(String(10))

    # Preflop flags
    vpip = Column(Boolean, default=False)
    pfr = Column(Boolean, default=False)
    limp = Column(Boolean, default=False)
    faced_raise = Column(Boolean, default=False)
    three_bet_opportunity = Column(Boolean, default=False)
    faced_three_bet = Column(Boolean, default=False)
    folded_to_three_bet = Column(Boolean, default=False)
    called_three_bet = Column(Boolean, default=False)
    made_three_bet = Column(Boolean, default=False)
    four_bet = Column(Boolean, default=False)
    cold_call = Column(Boolean, default=False)
    squeeze = Column(Boolean, default=False)

    # Position-specific tracking
    raiser_position = Column(String(10))  # Position of the first raiser (opener)
    three_bettor_position = Column(String(10))  # Position of the 3-bettor

    # Facing 4-bet tracking
    faced_four_bet = Column(Boolean, default=False)
    folded_to_four_bet = Column(Boolean, default=False)
    called_four_bet = Column(Boolean, default=False)
    five_bet = Column(Boolean, default=False)

    # Steal and blind defense (preflop)
    steal_attempt = Column(Boolean, default=False)
    faced_steal = Column(Boolean, default=False)
    fold_to_steal = Column(Boolean, default=False)
    call_steal = Column(Boolean, default=False)
    three_bet_vs_steal = Column(Boolean, default=False)

    # Basic outcome
    went_to_showdown = Column(Boolean, default=False)
    won_hand = Column(Boolean, default=False)
    profit_loss = Column(DECIMAL(10, 2))

    created_at = Column(TIMESTAMP, default=func.current_timestamp())

    def __repr__(self) -> str:
        return f"<PlayerHandSummary(hand_id={self.hand_id}, player={self.player_name}, vpip={self.vpip})>"


class GTOScenario(Base):
    """
    GTO preflop scenario definitions from GTOWizard.

    Table: gto_scenarios

    For villain analysis (without hole cards), use gto_aggregate_freq.
    For hero analysis (with hole cards), lookup combo-level freq in gto_frequencies.
    """
    __tablename__ = 'gto_scenarios'

    scenario_id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_name = Column(String(100), nullable=False, unique=True)
    street = Column(String(20), nullable=False, default='preflop')
    category = Column(String(50), nullable=False)  # opening, defense, facing_3bet, facing_4bet
    position = Column(String(10))  # UTG, MP, CO, BTN, SB, BB
    action = Column(String(20))  # open, fold, call, 3bet, 4bet, allin
    opponent_position = Column(String(20))  # Position of the opponent (for vs scenarios)
    gto_aggregate_freq = Column(DECIMAL(10, 8))  # Average freq across all combos (for villain analysis)
    data_source = Column(String(50), default='gtowizard')
    description = Column(Text)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp())

    def __repr__(self) -> str:
        return f"<GTOScenario(id={self.scenario_id}, name={self.scenario_name}, category={self.category})>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'scenario_id': self.scenario_id,
            'scenario_name': self.scenario_name,
            'street': self.street,
            'category': self.category,
            'position': self.position,
            'action': self.action,
            'opponent_position': self.opponent_position,
            'data_source': self.data_source,
            'description': self.description,
            'gto_aggregate_freq': float(self.gto_aggregate_freq) if self.gto_aggregate_freq else None
        }


class GTOFrequency(Base):
    """
    Combo-level GTO frequencies for each scenario.

    Table: gto_frequencies

    Used for HERO analysis when hole cards are known.
    """
    __tablename__ = 'gto_frequencies'

    frequency_id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(Integer, ForeignKey('gto_scenarios.scenario_id', ondelete='CASCADE'), nullable=False)
    hand = Column(String(4), nullable=False)  # e.g., "AhKd"
    position = Column(String(10), nullable=False)  # Position for this frequency
    frequency = Column(DECIMAL(10, 8), nullable=False)  # 0.0 to 1.0

    __table_args__ = (
        UniqueConstraint('scenario_id', 'hand', 'position', name='unique_scenario_hand_position'),
    )

    def __repr__(self) -> str:
        return f"<GTOFrequency(scenario={self.scenario_id}, hand={self.hand}, freq={self.frequency})>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'frequency_id': self.frequency_id,
            'scenario_id': self.scenario_id,
            'hand': self.hand,
            'position': self.position,
            'frequency': float(self.frequency) if self.frequency else 0.0,
            'percentage': float(self.frequency * 100) if self.frequency else 0.0
        }


class PlayerStats(Base):
    """
    Pre-calculated preflop statistics and composite metrics.
    Updated after each hand upload batch.

    Table: player_stats (preflop-only version)
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

    # Win rate
    total_profit_loss = Column(DECIMAL(12, 2))
    bb_per_100 = Column(DECIMAL(8, 2))

    # Composite Metrics (preflop-focused)
    exploitability_index = Column(DECIMAL(5, 2))
    positional_awareness_index = Column(DECIMAL(5, 2))
    blind_defense_efficiency = Column(DECIMAL(5, 2))
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


class UserSettings(Base):
    """
    User settings including hero nicknames for identifying 'My Game' hands.

    Table: user_settings

    Stores key-value pairs where:
    - 'hero_nicknames': JSON array of hero nicknames across different poker sites
    - Additional settings can be added as needed
    """
    __tablename__ = 'user_settings'

    setting_id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(100), nullable=False, unique=True)
    setting_value = Column(Text)  # JSON for complex values like arrays
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp())

    def __repr__(self) -> str:
        return f"<UserSettings(key={self.setting_key})>"


class HeroNickname(Base):
    """
    Individual hero nickname entries for easy querying.

    Table: hero_nicknames

    Each row represents one nickname the user plays under on a specific site.
    """
    __tablename__ = 'hero_nicknames'

    nickname_id = Column(Integer, primary_key=True, autoincrement=True)
    nickname = Column(String(100), nullable=False)
    site = Column(String(50))  # e.g., 'PokerStars', 'GGPoker', 'PartyPoker'
    created_at = Column(TIMESTAMP, default=func.current_timestamp())

    __table_args__ = (
        UniqueConstraint('nickname', 'site', name='unique_nickname_site'),
    )

    def __repr__(self) -> str:
        return f"<HeroNickname(nickname={self.nickname}, site={self.site})>"
