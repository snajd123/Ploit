"""
SQLAlchemy ORM models for new GTO architecture (GTOWizard-based).

These models support preflop GTO scenarios with extensibility for postflop.
"""

from sqlalchemy import (
    Column, Integer, String, Text, TIMESTAMP, DECIMAL, Boolean, ForeignKey, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from typing import Dict, Optional
from decimal import Decimal

Base = declarative_base()


class GTOScenario(Base):
    """
    Stores metadata for each GTO scenario (preflop or postflop).

    Table: gto_scenarios
    """
    __tablename__ = 'gto_scenarios'

    scenario_id = Column(Integer, primary_key=True, autoincrement=True)

    # Scenario identification
    scenario_name = Column(String(100), unique=True, nullable=False)

    # Scenario classification
    street = Column(String(10), nullable=False)  # 'preflop', 'flop', 'turn', 'river'
    category = Column(String(50), nullable=False)  # 'opening', 'defense', 'facing_3bet', etc.

    # Preflop specific
    position = Column(String(10))  # 'UTG', 'BB', 'BTN', etc.
    action = Column(String(20))  # 'open', 'call', 'fold', '3bet', '4bet', 'allin'
    opponent_position = Column(String(10))  # 'UTG', NULL for opens

    # Postflop specific (for future use)
    board = Column(String(20))  # e.g., 'AsKsQs', 'PREFLOP'
    board_texture = Column(String(50))  # e.g., 'monotone', 'dry', 'wet'
    position_context = Column(String(20))  # 'IP', 'OOP'
    action_node = Column(String(50))  # 'facing_cbet', 'facing_raise'

    # Metadata
    data_source = Column(String(50), default='gtowizard')
    description = Column(Text)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp())

    def __repr__(self) -> str:
        return f"<GTOScenario(id={self.scenario_id}, name={self.scenario_name}, street={self.street})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'scenario_id': self.scenario_id,
            'scenario_name': self.scenario_name,
            'street': self.street,
            'category': self.category,
            'position': self.position,
            'action': self.action,
            'opponent_position': self.opponent_position,
            'board': self.board,
            'board_texture': self.board_texture,
            'position_context': self.position_context,
            'action_node': self.action_node,
            'data_source': self.data_source,
            'description': self.description
        }


class GTOFrequency(Base):
    """
    Stores GTO frequencies for each hand in each scenario.

    Table: gto_frequencies
    """
    __tablename__ = 'gto_frequencies'

    frequency_id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(Integer, ForeignKey('gto_scenarios.scenario_id', ondelete='CASCADE'), nullable=False)

    # Hand identification
    hand = Column(String(4), nullable=False)  # 'AKo', 'JTs', '22', 'AhKd'

    # Position (whose strategy is this?)
    position = Column(String(10), nullable=False)  # 'BB', 'UTG', 'IP', 'OOP', etc.

    # Frequency data
    frequency = Column(DECIMAL(10, 8), nullable=False)  # 0.0 to 1.0

    __table_args__ = (
        UniqueConstraint('scenario_id', 'hand', 'position', name='unique_scenario_hand_position'),
    )

    def __repr__(self) -> str:
        return f"<GTOFrequency(scenario={self.scenario_id}, hand={self.hand}, pos={self.position}, freq={self.frequency})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'frequency_id': self.frequency_id,
            'scenario_id': self.scenario_id,
            'hand': self.hand,
            'position': self.position,
            'frequency': float(self.frequency) if self.frequency else 0.0,
            'percentage': float(self.frequency * 100) if self.frequency else 0.0
        }


class PlayerAction(Base):
    """
    Stores actual player actions from hand histories for leak detection.

    Table: player_actions
    """
    __tablename__ = 'player_actions'

    action_id = Column(Integer, primary_key=True, autoincrement=True)

    # Player identification
    player_name = Column(String(100), nullable=False)
    hand_id = Column(String(100), nullable=False)

    # Action context
    timestamp = Column(TIMESTAMP, nullable=False)
    scenario_id = Column(Integer, ForeignKey('gto_scenarios.scenario_id'), nullable=False)

    # Hole cards
    hole_cards = Column(String(4), nullable=False)  # 'AKo', 'JTs', etc.

    # Action taken
    action_taken = Column(String(20), nullable=False)  # 'fold', 'call', 'raise', '3bet', etc.

    # GTO analysis (cached)
    gto_frequency = Column(DECIMAL(10, 8))
    ev_loss_bb = Column(DECIMAL(10, 4))
    is_mistake = Column(Boolean)
    mistake_severity = Column(String(20))  # 'minor', 'moderate', 'major', 'critical'

    # Metadata
    created_at = Column(TIMESTAMP, default=func.current_timestamp())

    def __repr__(self) -> str:
        return f"<PlayerAction(player={self.player_name}, hand={self.hole_cards}, action={self.action_taken})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'action_id': self.action_id,
            'player_name': self.player_name,
            'hand_id': self.hand_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'scenario_id': self.scenario_id,
            'hole_cards': self.hole_cards,
            'action_taken': self.action_taken,
            'gto_frequency': float(self.gto_frequency) if self.gto_frequency else None,
            'ev_loss_bb': float(self.ev_loss_bb) if self.ev_loss_bb else None,
            'is_mistake': self.is_mistake,
            'mistake_severity': self.mistake_severity
        }


class PlayerGTOStat(Base):
    """
    Aggregated leak statistics per player per scenario.

    Table: player_gto_stats
    """
    __tablename__ = 'player_gto_stats'

    stat_id = Column(Integer, primary_key=True, autoincrement=True)

    # Player and scenario
    player_name = Column(String(100), nullable=False)
    scenario_id = Column(Integer, ForeignKey('gto_scenarios.scenario_id'), nullable=False)

    # Sample size
    total_hands = Column(Integer, nullable=False, default=0)
    last_updated = Column(TIMESTAMP, default=func.current_timestamp())

    # Frequency comparison
    player_frequency = Column(DECIMAL(10, 8))
    gto_frequency = Column(DECIMAL(10, 8))
    frequency_diff = Column(DECIMAL(10, 8))

    # EV metrics
    total_ev_loss_bb = Column(DECIMAL(10, 4))
    avg_ev_loss_bb = Column(DECIMAL(10, 4))

    # Leak classification
    leak_type = Column(String(50))  # 'overfold', 'underfold', 'overcall', 'under3bet', etc.
    leak_severity = Column(String(20))  # 'minor', 'moderate', 'major', 'critical'

    # Exploit recommendation
    exploit_description = Column(Text)
    exploit_value_bb_100 = Column(DECIMAL(10, 4))
    exploit_confidence = Column(DECIMAL(5, 2))

    __table_args__ = (
        UniqueConstraint('player_name', 'scenario_id', name='unique_player_scenario'),
    )

    def __repr__(self) -> str:
        return f"<PlayerGTOStat(player={self.player_name}, scenario={self.scenario_id}, leak={self.leak_type})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'stat_id': self.stat_id,
            'player_name': self.player_name,
            'scenario_id': self.scenario_id,
            'total_hands': self.total_hands,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'player_frequency': float(self.player_frequency) if self.player_frequency else None,
            'gto_frequency': float(self.gto_frequency) if self.gto_frequency else None,
            'frequency_diff': float(self.frequency_diff) if self.frequency_diff else None,
            'total_ev_loss_bb': float(self.total_ev_loss_bb) if self.total_ev_loss_bb else None,
            'avg_ev_loss_bb': float(self.avg_ev_loss_bb) if self.avg_ev_loss_bb else None,
            'leak_type': self.leak_type,
            'leak_severity': self.leak_severity,
            'exploit_description': self.exploit_description,
            'exploit_value_bb_100': float(self.exploit_value_bb_100) if self.exploit_value_bb_100 else None,
            'exploit_confidence': float(self.exploit_confidence) if self.exploit_confidence else None
        }


class HandType(Base):
    """
    Helper table mapping combos to hand types for preflop aggregation.

    Table: hand_types
    """
    __tablename__ = 'hand_types'

    combo = Column(String(4), primary_key=True)  # 'AhKd', '2c2d', etc.
    hand = Column(String(4), nullable=False)  # 'AKo', '22', 'JTs'
    rank1 = Column(String(1), nullable=False)
    rank2 = Column(String(1), nullable=False)
    suit1 = Column(String(1), nullable=False)
    suit2 = Column(String(1), nullable=False)
    is_pair = Column(Boolean, nullable=False)
    is_suited = Column(Boolean, nullable=False)

    def __repr__(self) -> str:
        return f"<HandType(combo={self.combo}, hand={self.hand})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'combo': self.combo,
            'hand': self.hand,
            'rank1': self.rank1,
            'rank2': self.rank2,
            'suit1': self.suit1,
            'suit2': self.suit2,
            'is_pair': self.is_pair,
            'is_suited': self.is_suited
        }
