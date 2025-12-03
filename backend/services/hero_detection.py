"""
Hero Detection Service

Utility functions for identifying hero players based on configured nicknames.
Used to distinguish "My Game" (hero with hole cards) from "Pools" (opponents).
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Set, Optional, Tuple
import re


# Cache for hero nicknames (refreshed on each request for now)
_hero_nicknames_cache: Optional[Set[str]] = None


def get_hero_nicknames(db: Session) -> Set[str]:
    """
    Get all hero nicknames as a lowercase set for efficient matching.
    """
    result = db.execute(text("""
        SELECT LOWER(nickname) as nickname
        FROM hero_nicknames
    """))
    return {row.nickname for row in result.fetchall()}


def is_hero(player_name: str, db: Session) -> bool:
    """
    Check if a player name matches any configured hero nickname.
    Case-insensitive matching.
    """
    hero_nicknames = get_hero_nicknames(db)
    return player_name.lower() in hero_nicknames


def filter_heroes(player_names: List[str], db: Session) -> Tuple[List[str], List[str]]:
    """
    Separate player names into heroes and opponents.

    Returns:
        Tuple of (heroes, opponents)
    """
    hero_nicknames = get_hero_nicknames(db)

    heroes = []
    opponents = []

    for name in player_names:
        if name.lower() in hero_nicknames:
            heroes.append(name)
        else:
            opponents.append(name)

    return heroes, opponents


def detect_site_from_hand_text(raw_hand_text: str) -> str:
    """
    Detect the poker site from raw hand history text.

    Returns site name or 'Unknown'.
    """
    if not raw_hand_text:
        return 'Unknown'

    text_lower = raw_hand_text.lower()
    first_line = raw_hand_text.split('\n')[0] if raw_hand_text else ''

    # PokerStars
    if 'pokerstars' in text_lower or first_line.startswith('PokerStars'):
        return 'PokerStars'

    # GGPoker
    if 'ggpoker' in text_lower or 'gg poker' in text_lower:
        return 'GGPoker'

    # PartyPoker
    if 'partypoker' in text_lower or 'party poker' in text_lower:
        return 'PartyPoker'

    # 888poker
    if '888poker' in text_lower or '888 poker' in text_lower:
        return '888poker'

    # iPoker
    if 'ipoker' in text_lower:
        return 'iPoker'

    # Winamax
    if 'winamax' in text_lower:
        return 'Winamax'

    return 'Unknown'


def parse_stake_level(stake_level_str: Optional[str]) -> Tuple[float, float, str]:
    """
    Parse stake level string (e.g., "5NL", "€0.02/€0.04") into
    small blind, big blind, and standardized format.

    Returns:
        Tuple of (small_blind, big_blind, standardized_name like "5NL")
    """
    if not stake_level_str:
        return 0, 0, 'Unknown'

    # Handle "NL" format like "5NL", "10NL", "25NL"
    nl_match = re.match(r'(\d+)NL', stake_level_str.upper())
    if nl_match:
        bb = float(nl_match.group(1)) / 100  # Convert cents to dollars
        sb = bb / 2
        return sb, bb, stake_level_str.upper()

    # Handle currency format like "€0.02/€0.04" or "$0.25/$0.50"
    currency_match = re.search(r'[\$€£]?([\d.]+)/[\$€£]?([\d.]+)', stake_level_str)
    if currency_match:
        sb = float(currency_match.group(1))
        bb = float(currency_match.group(2))
        # Convert to NL format
        nl_value = int(bb * 100)
        return sb, bb, f"{nl_value}NL"

    return 0, 0, stake_level_str


def get_pool_id(site: str, stake_level: str) -> str:
    """
    Generate a unique pool identifier from site and stake level.

    Example: "PokerStars_5NL", "GGPoker_25NL"
    """
    _, _, standardized_stake = parse_stake_level(stake_level)
    return f"{site}_{standardized_stake}"


def get_pool_display_name(site: str, stake_level: str) -> str:
    """
    Generate a human-readable pool name.

    Example: "PokerStars 5NL", "GGPoker 25NL"
    """
    _, _, standardized_stake = parse_stake_level(stake_level)
    return f"{site} {standardized_stake}"
