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
    Stores metadata for each GTO scenario (preflop).

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

    # Metadata
    data_source = Column(String(50), default='gtowizard')
    description = Column(Text)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp())

    # Aggregate GTO frequency for this scenario
    gto_aggregate_freq = Column(DECIMAL(10, 4))

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
            'data_source': self.data_source,
            'description': self.description,
            'gto_aggregate_freq': float(self.gto_aggregate_freq) if self.gto_aggregate_freq else None
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


    # Note: PlayerAction, PlayerGTOStat, HandType models removed - tables no longer exist
