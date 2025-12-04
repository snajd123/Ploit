"""
DEPRECATED: This module is deprecated. Use database_models instead.

This file exists only for backward compatibility.
All GTO models are now consolidated in database_models.py.
"""

# Re-export from database_models for backward compatibility
from backend.models.database_models import GTOScenario, GTOFrequency, Base

__all__ = ['GTOScenario', 'GTOFrequency', 'Base']
