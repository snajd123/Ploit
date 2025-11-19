"""
SQLAlchemy ORM models for GTO Solutions database tables.

These models support multi-level board categorization and scalable GTO solution storage,
designed to work efficiently with both 79 solutions today and 20,000+ in the future.
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, TIMESTAMP,
    DECIMAL, Boolean, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, Dict, List
from decimal import Decimal

Base = declarative_base()


class GTOSolution(Base):
    """
    Stores individual GTO solver solutions with multi-level board categorization.

    Table: gto_solutions

    The multi-level categorization system:
    - Level 1: 7 broad categories (Ace-high, King-high, etc.)
    - Level 2: ~20 medium categories (Ace-high-rainbow, King-high-2tone, etc.)
    - Level 3: ~100+ fine categories (Ace-high-rainbow-dry, etc.)
    """
    __tablename__ = 'gto_solutions'

    solution_id = Column(Integer, primary_key=True, autoincrement=True)

    # Scenario identification
    scenario_name = Column(String(100), nullable=False, unique=True)
    config_file = Column(String(255))
    output_file = Column(String(255))

    # Board information
    board = Column(String(20), nullable=False)
    flop_card_1 = Column(String(2))
    flop_card_2 = Column(String(2))
    flop_card_3 = Column(String(2))

    # Multi-level board categorization
    board_category_l1 = Column(String(30), nullable=False)
    board_category_l2 = Column(String(50), nullable=False)
    board_category_l3 = Column(String(100), nullable=False)

    # Board texture properties
    is_paired = Column(Boolean, default=False)
    is_rainbow = Column(Boolean, default=False)
    is_two_tone = Column(Boolean, default=False)
    is_monotone = Column(Boolean, default=False)
    is_connected = Column(Boolean, default=False)
    is_highly_connected = Column(Boolean, default=False)
    has_broadway = Column(Boolean, default=False)
    is_dry = Column(Boolean, default=False)
    is_wet = Column(Boolean, default=False)
    high_card_rank = Column(String(2))
    middle_card_rank = Column(String(2))
    low_card_rank = Column(String(2))

    # Scenario context
    scenario_type = Column(String(50))
    position_context = Column(String(50))
    action_sequence = Column(String(100))
    pot_size = Column(DECIMAL(8, 2))
    effective_stack = Column(DECIMAL(8, 2))

    # Range information
    ip_range = Column(Text)
    oop_range = Column(Text)

    # Solution metadata
    accuracy = Column(DECIMAL(5, 3))
    iterations = Column(Integer)
    solving_time_seconds = Column(Integer)
    file_size_bytes = Column(BigInteger)

    # Timestamps
    solved_at = Column(TIMESTAMP)
    imported_at = Column(TIMESTAMP, default=func.current_timestamp())
    last_accessed = Column(TIMESTAMP)

    def __repr__(self) -> str:
        return f"<GTOSolution(scenario={self.scenario_name}, board={self.board}, cat_l1={self.board_category_l1})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'solution_id': self.solution_id,
            'scenario_name': self.scenario_name,
            'board': self.board,
            'board_category_l1': self.board_category_l1,
            'board_category_l2': self.board_category_l2,
            'board_category_l3': self.board_category_l3,
            'scenario_type': self.scenario_type,
            'position_context': self.position_context,
            'action_sequence': self.action_sequence,
            'pot_size': float(self.pot_size) if self.pot_size else None,
            'effective_stack': float(self.effective_stack) if self.effective_stack else None,
            'is_paired': self.is_paired,
            'is_rainbow': self.is_rainbow,
            'is_two_tone': self.is_two_tone,
            'is_monotone': self.is_monotone,
            'is_connected': self.is_connected,
            'has_broadway': self.has_broadway,
            'is_dry': self.is_dry,
            'is_wet': self.is_wet
        }


class GTOCategoryAggregate(Base):
    """
    Pre-computed aggregates for each board category.

    Table: gto_category_aggregates

    Stores aggregated statistics across all solutions in a category,
    enabling fast lookups without scanning individual solutions.
    """
    __tablename__ = 'gto_category_aggregates'

    aggregate_id = Column(Integer, primary_key=True, autoincrement=True)

    # Category information
    category_level = Column(Integer, nullable=False)
    category_name = Column(String(100), nullable=False)

    # Aggregate statistics
    solution_count = Column(Integer, default=0)
    total_scenarios = Column(Integer)
    coverage_pct = Column(DECIMAL(5, 2))

    # Representative solution
    representative_board = Column(String(20))
    representative_solution_id = Column(Integer, ForeignKey('gto_solutions.solution_id'))

    # Category characteristics
    avg_pot_size = Column(DECIMAL(8, 2))
    avg_stack_size = Column(DECIMAL(8, 2))

    # Strategy patterns (stored as JSONB for flexibility)
    common_actions = Column(JSONB)

    # Aggregated frequencies
    avg_cbet_freq = Column(DECIMAL(5, 2))
    avg_check_freq = Column(DECIMAL(5, 2))
    avg_fold_to_cbet_freq = Column(DECIMAL(5, 2))

    # Metadata
    last_updated = Column(TIMESTAMP, default=func.current_timestamp())

    __table_args__ = (
        UniqueConstraint('category_level', 'category_name', name='unique_category'),
    )

    def __repr__(self) -> str:
        return f"<GTOCategoryAggregate(level={self.category_level}, name={self.category_name}, count={self.solution_count})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'aggregate_id': self.aggregate_id,
            'category_level': self.category_level,
            'category_name': self.category_name,
            'solution_count': self.solution_count,
            'coverage_pct': float(self.coverage_pct) if self.coverage_pct else None,
            'representative_board': self.representative_board,
            'avg_pot_size': float(self.avg_pot_size) if self.avg_pot_size else None,
            'avg_stack_size': float(self.avg_stack_size) if self.avg_stack_size else None,
            'common_actions': self.common_actions,
            'avg_cbet_freq': float(self.avg_cbet_freq) if self.avg_cbet_freq else None,
            'avg_check_freq': float(self.avg_check_freq) if self.avg_check_freq else None,
            'avg_fold_to_cbet_freq': float(self.avg_fold_to_cbet_freq) if self.avg_fold_to_cbet_freq else None
        }


class GTOStrategyCache(Base):
    """
    Cached strategy data for quick lookup of specific hands.

    Table: gto_strategy_cache

    Stores pre-computed strategy frequencies for individual hands,
    enabling instant lookups without parsing full solution JSON.
    """
    __tablename__ = 'gto_strategy_cache'

    cache_id = Column(Integer, primary_key=True, autoincrement=True)
    solution_id = Column(Integer, ForeignKey('gto_solutions.solution_id', ondelete='CASCADE'), nullable=False)

    # Hand-specific data
    hand = Column(String(4), nullable=False)
    position = Column(String(10), nullable=False)
    street = Column(String(10), default='flop')
    action_node = Column(String(50))

    # Strategy data
    strategy_json = Column(JSONB, nullable=False)

    # Most common action
    primary_action = Column(String(50))
    primary_action_freq = Column(DECIMAL(5, 2))

    # Metadata
    created_at = Column(TIMESTAMP, default=func.current_timestamp())

    __table_args__ = (
        UniqueConstraint('solution_id', 'hand', 'position', 'street', 'action_node',
                        name='unique_cache_entry'),
    )

    def __repr__(self) -> str:
        return f"<GTOStrategyCache(solution={self.solution_id}, hand={self.hand}, action={self.primary_action})>"

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'cache_id': self.cache_id,
            'solution_id': self.solution_id,
            'hand': self.hand,
            'position': self.position,
            'street': self.street,
            'action_node': self.action_node,
            'strategy_json': self.strategy_json,
            'primary_action': self.primary_action,
            'primary_action_freq': float(self.primary_action_freq) if self.primary_action_freq else None
        }
