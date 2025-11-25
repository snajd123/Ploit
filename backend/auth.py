"""
Authentication and Authorization Module for Poker Analysis App.

Provides:
- API Key authentication for sensitive endpoints
- Rate limiting helpers
- Input validation utilities
"""

import os
import re
import logging
from typing import Optional
from fastapi import HTTPException, Security, Depends, Request, status
from fastapi.security import APIKeyHeader
from functools import wraps

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# API Key header configuration
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def get_api_key() -> Optional[str]:
    """Get API key from environment variable."""
    return os.environ.get("API_KEY", os.environ.get("PLOIT_API_KEY"))


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify the API key provided in the request header.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        The validated API key

    Raises:
        HTTPException: If API key is invalid or missing
    """
    expected_key = get_api_key()

    # If no API key is configured, allow access (for development)
    if not expected_key:
        logger.warning("No API_KEY configured - authentication disabled")
        return "dev-mode"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != expected_key:
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key


async def optional_api_key(api_key: str = Security(api_key_header)) -> Optional[str]:
    """
    Optional API key verification - doesn't fail if missing.
    Used for endpoints that work with or without auth.
    """
    expected_key = get_api_key()

    if not expected_key or not api_key:
        return None

    if api_key == expected_key:
        return api_key

    return None


# Input validation utilities
class InputValidator:
    """Utilities for validating user input."""

    # Maximum lengths for various inputs
    MAX_PLAYER_NAME_LENGTH = 100
    MAX_QUERY_LENGTH = 10000
    MAX_CONVERSATION_HISTORY = 50
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

    # Allowed characters in player names
    PLAYER_NAME_PATTERN = re.compile(r'^[\w\s\.\-_@#]+$', re.UNICODE)

    @staticmethod
    def validate_player_name(player_name: str) -> str:
        """
        Validate and sanitize a player name.

        Args:
            player_name: Raw player name input

        Returns:
            Sanitized player name

        Raises:
            HTTPException: If player name is invalid
        """
        if not player_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Player name is required"
            )

        if len(player_name) > InputValidator.MAX_PLAYER_NAME_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Player name too long (max {InputValidator.MAX_PLAYER_NAME_LENGTH} chars)"
            )

        # Allow most characters but prevent obvious injection attempts
        if not InputValidator.PLAYER_NAME_PATTERN.match(player_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Player name contains invalid characters"
            )

        return player_name.strip()

    @staticmethod
    def validate_query(query: str) -> str:
        """
        Validate a Claude query.

        Args:
            query: User's query string

        Returns:
            Validated query

        Raises:
            HTTPException: If query is invalid
        """
        if not query or not query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query is required"
            )

        if len(query) > InputValidator.MAX_QUERY_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query too long (max {InputValidator.MAX_QUERY_LENGTH} chars)"
            )

        return query.strip()

    @staticmethod
    def validate_file_size(content: bytes, filename: str) -> None:
        """
        Validate uploaded file size.

        Args:
            content: File content bytes
            filename: Original filename

        Raises:
            HTTPException: If file is too large
        """
        if len(content) > InputValidator.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{filename}' too large (max {InputValidator.MAX_FILE_SIZE // (1024*1024)}MB)"
            )


class SQLValidator:
    """
    SQL query validation for Claude service.

    Provides strict validation to prevent SQL injection while
    still allowing legitimate SELECT queries.
    """

    # Dangerous SQL keywords that should never appear
    FORBIDDEN_KEYWORDS = [
        'DROP', 'DELETE', 'TRUNCATE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE',
        'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'SHUTDOWN', 'KILL',
        'xp_', 'sp_', 'LOAD_FILE', 'INTO OUTFILE', 'INTO DUMPFILE',
        'INFORMATION_SCHEMA', 'pg_', 'mysql.', 'master..', 'sysobjects',
        'syscolumns', 'UNION ALL SELECT', 'DECLARE', 'WAITFOR', 'BENCHMARK'
    ]

    # Allowed tables that can be queried
    ALLOWED_TABLES = [
        'player_stats', 'raw_hands', 'hand_actions', 'player_hand_summary',
        'upload_sessions', 'gto_solutions', 'gto_scenarios', 'gto_frequencies',
        'player_gto_stats', 'sessions', 'hero_gto_mistakes', 'opponent_session_stats',
        'player_board_stats', 'gto_category_aggregates', 'hand_types',
        'preflop_combos', 'player_actions'
    ]

    # Patterns that indicate SQL injection attempts
    INJECTION_PATTERNS = [
        r';\s*--',           # SQL comment after semicolon
        r'/\*.*\*/',         # Block comments
        r'CHAR\s*\(',        # CHAR function (often used for obfuscation)
        r'CONCAT\s*\(',      # CONCAT (can be used for obfuscation)
        r'0x[0-9a-fA-F]+',   # Hex encoding
        r'\\x[0-9a-fA-F]+',  # Escaped hex
        r"'.*'.*'",          # Multiple quotes (potential injection)
        r'OR\s+1\s*=\s*1',   # Classic OR injection
        r'OR\s+\'1\'\s*=\s*\'1\'',
        r'SLEEP\s*\(',       # Time-based injection
        r'BENCHMARK\s*\(',   # MySQL benchmark
        r'pg_sleep\s*\(',    # PostgreSQL sleep
    ]

    @classmethod
    def validate_query(cls, query: str) -> tuple[bool, str]:
        """
        Validate a SQL query for safety.

        Args:
            query: The SQL query to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query:
            return False, "Empty query"

        # Normalize query for checking
        query_upper = query.upper().strip()
        query_normalized = re.sub(r'\s+', ' ', query_upper)

        # Must start with SELECT
        if not query_normalized.startswith('SELECT'):
            return False, "Only SELECT queries are allowed"

        # Check for forbidden keywords
        for keyword in cls.FORBIDDEN_KEYWORDS:
            # Use word boundary matching to avoid false positives
            pattern = r'\b' + keyword.replace('_', r'\_') + r'\b'
            if re.search(pattern, query_upper, re.IGNORECASE):
                return False, f"Forbidden keyword detected: {keyword}"

        # Check for injection patterns
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return False, "Potential SQL injection pattern detected"

        # Check for multiple statements (semicolon not at end)
        # Allow trailing semicolon but not mid-query
        query_without_trailing = query.rstrip().rstrip(';')
        if ';' in query_without_trailing:
            return False, "Multiple statements not allowed"

        # Check for subqueries that modify data
        subquery_danger_patterns = [
            r'\(\s*DELETE\b',
            r'\(\s*UPDATE\b',
            r'\(\s*INSERT\b',
            r'\(\s*DROP\b',
        ]
        for pattern in subquery_danger_patterns:
            if re.search(pattern, query_upper):
                return False, "Dangerous subquery detected"

        return True, ""

    @classmethod
    def sanitize_query(cls, query: str) -> str:
        """
        Sanitize a query by removing dangerous elements.

        Args:
            query: Raw query string

        Returns:
            Sanitized query
        """
        # Remove transaction control statements
        query = re.sub(
            r';\s*(COMMIT|BEGIN|ROLLBACK|START\s+TRANSACTION)\s*;?\s*$',
            '', query, flags=re.IGNORECASE
        )

        # Remove trailing semicolon
        query = query.strip().rstrip(';').strip()

        # Remove SQL comments
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)

        return query.strip()
