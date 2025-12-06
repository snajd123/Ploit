"""
Pre-Game Strategy Service

Generates AI-powered preflop exploitation strategies for tables.
When user sends a single hand via email, this service:
1. Extracts all opponents from the hand
2. Looks up their stats in the database
3. Uses Claude to generate exploitation strategy
4. Saves strategy and emails it back
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import logging
import re
import anthropic
import os

logger = logging.getLogger(__name__)

def get_population_stats_from_db(db: Session, stake_level: str, hero_nicknames: List[str]) -> Dict[str, Any]:
    """
    Calculate actual population averages from database for a stake level.
    Excludes hero nicknames from the calculation.
    """
    stake = stake_level.upper() if stake_level else "NL4"
    hero_lower = [n.lower() for n in hero_nicknames] if hero_nicknames else []

    # Build hero exclusion clause dynamically to avoid array parameter issues
    hero_exclusion = ""
    params = {"stake_level": stake}
    if hero_lower:
        placeholders = ", ".join([f":hero_{i}" for i in range(len(hero_lower))])
        hero_exclusion = f"AND LOWER(ps.player_name) NOT IN ({placeholders})"
        for i, name in enumerate(hero_lower):
            params[f"hero_{i}"] = name

    query = f"""
        WITH player_stakes AS (
            SELECT DISTINCT phs.player_name, rh.stake_level
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE rh.stake_level = :stake_level
        )
        SELECT
            COUNT(*) as player_count,
            AVG(ps.vpip_pct) as avg_vpip,
            AVG(ps.pfr_pct) as avg_pfr,
            AVG(ps.three_bet_pct) as avg_3bet,
            AVG(ps.fold_to_three_bet_pct) as avg_f3b,
            AVG(ps.total_hands) as avg_hands
        FROM player_stats ps
        JOIN player_stakes pst ON ps.player_name = pst.player_name
        WHERE ps.total_hands >= 10
        {hero_exclusion}
    """

    try:
        result = db.execute(text(query), params).fetchone()

        if result and result.player_count and result.player_count > 5:
            logger.info(f"Pool stats for {stake}: {result.player_count} players, VPIP={result.avg_vpip:.1f}%, PFR={result.avg_pfr:.1f}%")
            return {
                "vpip": float(result.avg_vpip) if result.avg_vpip else 25.0,
                "pfr": float(result.avg_pfr) if result.avg_pfr else 18.0,
                "three_bet": float(result.avg_3bet) if result.avg_3bet else 6.0,
                "fold_to_3bet": float(result.avg_f3b) if result.avg_f3b else 55.0,
                "player_count": result.player_count,
                "source": "database"
            }
    except Exception as e:
        logger.error(f"Error querying pool stats: {e}")
        # Rollback to clear failed transaction state
        try:
            db.rollback()
        except:
            pass

    # Stake-specific fallback defaults based on typical population tendencies
    # NL2 is loosest/most passive, gets tighter as stakes increase
    STAKE_DEFAULTS = {
        "NL2": {"vpip": 30.0, "pfr": 17.0, "three_bet": 5.5, "fold_to_3bet": 60.0},
        "NL4": {"vpip": 29.0, "pfr": 17.0, "three_bet": 5.5, "fold_to_3bet": 59.0},
        "NL5": {"vpip": 28.0, "pfr": 17.0, "three_bet": 6.0, "fold_to_3bet": 58.0},
        "NL10": {"vpip": 26.0, "pfr": 18.0, "three_bet": 6.5, "fold_to_3bet": 56.0},
        "NL25": {"vpip": 24.0, "pfr": 19.0, "three_bet": 7.0, "fold_to_3bet": 54.0},
        "NL50": {"vpip": 22.0, "pfr": 18.0, "three_bet": 7.5, "fold_to_3bet": 52.0},
    }

    defaults = STAKE_DEFAULTS.get(stake, {"vpip": 28.0, "pfr": 17.0, "three_bet": 6.0, "fold_to_3bet": 58.0})

    logger.warning(f"No pool data for {stake}, using stake-specific defaults")
    return {
        "vpip": defaults["vpip"],
        "pfr": defaults["pfr"],
        "three_bet": defaults["three_bet"],
        "fold_to_3bet": defaults["fold_to_3bet"],
        "player_count": 0,
        "source": f"default_{stake}"
    }


def get_gto_baselines(db: Session) -> Dict[str, Any]:
    """
    Get key GTO baseline frequencies for the AI prompt.
    These are aggregate frequencies from GTOWizard data.
    """
    try:
        result = db.execute(text("""
            SELECT scenario_name, gto_aggregate_freq
            FROM gto_scenarios
            WHERE gto_aggregate_freq IS NOT NULL
            ORDER BY scenario_name
        """)).fetchall()

        baselines = {}
        for row in result:
            baselines[row[0]] = float(row[1]) if row[1] else None

        # Organize into useful categories
        gto_data = {
            "opening": {},
            "defense": {},
            "three_bet": {},
            "fold_to_3bet": {}
        }

        for name, freq in baselines.items():
            if freq is None:
                continue
            # Opening ranges
            if "_open" in name:
                pos = name.replace("_open", "")
                gto_data["opening"][pos] = round(freq * 100, 1)
            # Defense (calls)
            elif "_call" in name and "vs_" in name:
                gto_data["defense"][name] = round(freq * 100, 1)
            # 3-bet frequencies
            elif "_3bet" in name and "vs_" in name:
                gto_data["three_bet"][name] = round(freq * 100, 1)
            # Fold to 3-bet
            elif "_fold" in name and "4bet" not in name:
                gto_data["fold_to_3bet"][name] = round(freq * 100, 1)

        return gto_data
    except Exception as e:
        logger.error(f"Error fetching GTO baselines: {e}")
        return {}


def classify_player(stats: Dict[str, Any], sample_size: int) -> str:
    """Classify player type based on stats."""
    vpip = stats.get("vpip", 0) or 0
    pfr = stats.get("pfr", 0) or 0
    gap = vpip - pfr
    three_bet = stats.get("three_bet", 0) or 0

    if sample_size < 30:
        return "UNKNOWN"

    if vpip > 45 and pfr > 35:
        return "MANIAC"
    elif vpip > 40 and gap > 15:
        return "CALLING_STATION"
    elif vpip > 35 and gap > 12:
        return "LOOSE_PASSIVE"
    elif vpip < 18 and pfr < 15:
        return "NIT"
    elif 18 <= vpip <= 26 and 14 <= pfr <= 22 and gap < 8:
        return "TAG"
    elif vpip > 26 and pfr > 20 and gap < 10:
        return "LAG"
    elif vpip > 30:
        return "LOOSE"
    elif vpip < 22:
        return "TIGHT"
    else:
        return "REGULAR"


def calculate_confidence(sample_size: int) -> Tuple[str, float]:
    """Calculate confidence level based on sample size."""
    if sample_size >= 500:
        return "VERY_HIGH", 1.0
    elif sample_size >= 200:
        return "HIGH", 0.85
    elif sample_size >= 100:
        return "MEDIUM", 0.7
    elif sample_size >= 50:
        return "LOW", 0.5
    elif sample_size >= 20:
        return "VERY_LOW", 0.3
    else:
        return "NONE", 0.0


def extract_opponents_from_hand(hand_text: str, hero_nicknames: List[str]) -> List[Dict[str, Any]]:
    """
    Extract opponent information from a single hand history.

    Returns list of opponents with their seat, position, and actions in this hand.
    """
    opponents = []
    hero_names_lower = [n.lower() for n in hero_nicknames]

    # Extract seat info: "Seat 1: PlayerName ($5.00 in chips)"
    seat_pattern = re.compile(r"Seat (\d+): ([^\s(]+)")
    seats = {}
    for match in seat_pattern.finditer(hand_text):
        seat_num = int(match.group(1))
        player_name = match.group(2).strip()
        seats[player_name] = seat_num

    # Extract position info from action lines
    # Look for patterns like "PlayerName: posts small blind" or "PlayerName: raises"
    positions = {}

    # SB/BB detection
    sb_match = re.search(r"([^\s:]+): posts small blind", hand_text)
    bb_match = re.search(r"([^\s:]+): posts big blind", hand_text)
    if sb_match:
        positions[sb_match.group(1)] = "SB"
    if bb_match:
        positions[bb_match.group(1)] = "BB"

    # Button detection
    btn_match = re.search(r"Seat #(\d+) is the button", hand_text)
    if btn_match:
        btn_seat = int(btn_match.group(1))
        for player, seat in seats.items():
            if seat == btn_seat:
                positions[player] = "BTN"

    # For players without position, try to infer from action order
    # This is a simplified version - real implementation would need full position logic

    # Extract actions for each player in this hand
    player_actions = {}
    action_pattern = re.compile(r"([^\s:]+): (folds|calls|raises|checks|bets|posts)")
    for match in action_pattern.finditer(hand_text):
        player = match.group(1)
        action = match.group(2)
        if player not in player_actions:
            player_actions[player] = []
        player_actions[player].append(action)

    # Build opponent list (excluding hero)
    for player_name, seat in seats.items():
        if player_name.lower() not in hero_names_lower:
            opponents.append({
                "name": player_name,
                "seat": seat,
                "position": positions.get(player_name, "UNKNOWN"),
                "actions_in_hand": player_actions.get(player_name, [])
            })

    return opponents


def get_opponent_stats(db: Session, player_name: str) -> Optional[Dict[str, Any]]:
    """Look up opponent stats from database."""
    result = db.execute(text("""
        SELECT
            total_hands,
            vpip_pct,
            pfr_pct,
            three_bet_pct,
            fold_to_three_bet_pct,
            four_bet_pct,
            cold_call_pct,
            limp_pct,
            steal_attempt_pct,
            fold_to_steal_pct,
            player_type
        FROM player_stats
        WHERE player_name = :player_name
    """), {"player_name": player_name})

    row = result.fetchone()
    if row:
        return {
            "total_hands": row[0] or 0,
            "vpip": float(row[1]) if row[1] else None,
            "pfr": float(row[2]) if row[2] else None,
            "three_bet": float(row[3]) if row[3] else None,
            "fold_to_3bet": float(row[4]) if row[4] else None,
            "four_bet": float(row[5]) if row[5] else None,
            "cold_call": float(row[6]) if row[6] else None,
            "limp": float(row[7]) if row[7] else None,
            "steal_attempt": float(row[8]) if row[8] else None,
            "fold_to_steal": float(row[9]) if row[9] else None,
            "player_type": row[10]
        }
    return None


def build_opponent_profiles(
    db: Session,
    opponents: List[Dict[str, Any]],
    stake_level: str,
    hero_nicknames: List[str]
) -> List[Dict[str, Any]]:
    """
    Build complete profiles for each opponent.
    Uses database stats if available, otherwise pool averages from database.
    """
    # Get actual pool stats from database
    pool_stats = get_population_stats_from_db(db, stake_level, hero_nicknames)
    profiles = []

    for opp in opponents:
        stats = get_opponent_stats(db, opp["name"])

        if stats and stats["total_hands"] >= 20:
            # Have enough data - use actual stats
            sample_size = stats["total_hands"]
            confidence_label, confidence_score = calculate_confidence(sample_size)
            classification = classify_player(stats, sample_size)

            profile = {
                "name": opp["name"],
                "seat": opp["seat"],
                "position": opp["position"],
                "sample_size": sample_size,
                "confidence": confidence_label,
                "confidence_score": confidence_score,
                "data_source": "DATABASE",
                "stats": {
                    "vpip": stats["vpip"],
                    "pfr": stats["pfr"],
                    "three_bet": stats["three_bet"],
                    "fold_to_3bet": stats["fold_to_3bet"],
                    "cold_call": stats["cold_call"],
                    "limp": stats["limp"],
                    "steal_attempt": stats["steal_attempt"],
                    "fold_to_steal": stats["fold_to_steal"]
                },
                "classification": classification
            }
        else:
            # No data or insufficient - use pool averages from database
            profile = {
                "name": opp["name"],
                "seat": opp["seat"],
                "position": opp["position"],
                "sample_size": stats["total_hands"] if stats else 0,
                "confidence": "NONE",
                "confidence_score": 0.0,
                "data_source": f"POOL_AVERAGE_{stake_level.upper()}",
                "stats": {
                    "vpip": pool_stats["vpip"],
                    "pfr": pool_stats["pfr"],
                    "three_bet": pool_stats["three_bet"],
                    "fold_to_3bet": pool_stats["fold_to_3bet"]
                },
                "classification": "UNKNOWN"
            }

        profiles.append(profile)

    return profiles


def calculate_table_softness(profiles: List[Dict[str, Any]]) -> Tuple[float, str]:
    """
    Calculate overall table softness score (1-5).
    Higher = softer/more profitable.
    """
    if not profiles:
        return 3.0, "UNKNOWN"

    softness_scores = []
    for p in profiles:
        classification = p.get("classification", "UNKNOWN")
        confidence = p.get("confidence_score", 0)

        # Base score by player type
        type_scores = {
            "CALLING_STATION": 5.0,
            "LOOSE_PASSIVE": 4.5,
            "MANIAC": 4.0,
            "LOOSE": 3.8,
            "NIT": 3.5,
            "UNKNOWN": 3.0,
            "REGULAR": 2.5,
            "TIGHT": 2.5,
            "TAG": 2.0,
            "LAG": 1.8
        }
        base_score = type_scores.get(classification, 3.0)

        # Weight by confidence
        # Unknown players regress toward 3.0 (neutral)
        weighted_score = base_score * confidence + 3.0 * (1 - confidence)
        softness_scores.append(weighted_score)

    avg_softness = sum(softness_scores) / len(softness_scores)

    # Classify table
    if avg_softness >= 4.0:
        classification = "VERY_SOFT"
    elif avg_softness >= 3.5:
        classification = "SOFT"
    elif avg_softness >= 2.8:
        classification = "MIXED"
    elif avg_softness >= 2.2:
        classification = "TOUGH"
    else:
        classification = "VERY_TOUGH"

    return round(avg_softness, 1), classification


def generate_strategy_with_claude(
    stake_level: str,
    hero_position: str,
    opponent_profiles: List[Dict[str, Any]],
    table_softness: float,
    table_classification: str,
    pool_stats: Dict[str, Any],
    gto_baselines: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Use Claude to generate exploitation strategy.
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Build opponent summary for prompt with GTO deviation analysis
    opponent_summaries = []
    for p in opponent_profiles:
        stats = p.get("stats", {})
        stats_str = f"VPIP {stats.get('vpip', 'N/A')}% | PFR {stats.get('pfr', 'N/A')}% | 3bet {stats.get('three_bet', 'N/A')}% | F3B {stats.get('fold_to_3bet', 'N/A')}%"

        if p["data_source"].startswith("POOL_AVERAGE"):
            source_note = f"[UNKNOWN - using {stake_level} pool average]"
        else:
            source_note = f"[{p['sample_size']} hands - {p['confidence']} confidence]"

        opponent_summaries.append(f"""
{p['seat']}. {p['name']} ({p['position']}) - {p['classification']} {source_note}
   Stats: {stats_str}""")

    opponents_text = "\n".join(opponent_summaries)

    # Pool stats info
    pool_info = f"Pool Average ({pool_stats.get('player_count', 0)} players): VPIP {pool_stats['vpip']:.1f}% | PFR {pool_stats['pfr']:.1f}% | 3bet {pool_stats['three_bet']:.1f}% | F3B {pool_stats['fold_to_3bet']:.1f}%"

    # Format GTO baselines for the prompt
    gto_section = ""
    pool_vs_gto_section = ""

    if gto_baselines:
        gto_lines = ["GTO REFERENCE (from GTOWizard solver data):"]

        # Opening frequencies
        if gto_baselines.get("opening"):
            opens = gto_baselines["opening"]
            gto_lines.append(f"  Opening frequencies: UTG {opens.get('UTG', 'N/A')}% | MP {opens.get('MP', 'N/A')}% | CO {opens.get('CO', 'N/A')}% | BTN {opens.get('BTN', 'N/A')}% | SB {opens.get('SB_raise', 'N/A')}%")

        # Key 3-bet frequencies
        if gto_baselines.get("three_bet"):
            three_bets = gto_baselines["three_bet"]
            key_3bets = []
            for scenario, freq in sorted(three_bets.items())[:6]:
                clean = scenario.replace("_3bet", "").replace("_vs_", " vs ")
                key_3bets.append(f"{clean}: {freq}%")
            if key_3bets:
                gto_lines.append(f"  3-bet frequencies: {' | '.join(key_3bets)}")

        # Key defense frequencies
        if gto_baselines.get("defense"):
            defense = gto_baselines["defense"]
            key_defense = []
            for scenario, freq in sorted(defense.items())[:6]:
                clean = scenario.replace("_call", " call").replace("_vs_", " vs ")
                key_defense.append(f"{clean}: {freq}%")
            if key_defense:
                gto_lines.append(f"  Defense (call) frequencies: {' | '.join(key_defense)}")

        gto_section = "\n".join(gto_lines)

        # Calculate GTO averages for pool comparison
        gto_avg_open = 0
        gto_avg_3bet = 0
        gto_avg_f3b = 0

        if gto_baselines.get("opening"):
            open_freqs = [v for k, v in gto_baselines["opening"].items() if isinstance(v, (int, float)) and "limp" not in k.lower()]
            if open_freqs:
                gto_avg_open = sum(open_freqs) / len(open_freqs)

        if gto_baselines.get("three_bet"):
            three_bet_freqs = list(gto_baselines["three_bet"].values())
            if three_bet_freqs:
                gto_avg_3bet = sum(three_bet_freqs) / len(three_bet_freqs)

        if gto_baselines.get("fold_to_3bet"):
            f3b_freqs = list(gto_baselines["fold_to_3bet"].values())
            if f3b_freqs:
                gto_avg_f3b = sum(f3b_freqs) / len(f3b_freqs)

        # Build pool vs GTO comparison
        pool_vs_gto_lines = [f"POOL vs GTO DEVIATION ANALYSIS ({stake_level}):"]

        # PFR vs GTO opening
        if gto_avg_open > 0:
            pfr_diff = pool_stats['pfr'] - gto_avg_open
            direction = "LOOSER" if pfr_diff > 0 else "TIGHTER"
            pool_vs_gto_lines.append(f"  PFR: Pool {pool_stats['pfr']:.1f}% vs GTO avg {gto_avg_open:.1f}% → Pool is {abs(pfr_diff):.1f}% {direction}")

        # 3-bet comparison
        if gto_avg_3bet > 0:
            three_bet_diff = pool_stats['three_bet'] - gto_avg_3bet
            direction = "MORE AGGRESSIVE" if three_bet_diff > 0 else "MORE PASSIVE"
            pool_vs_gto_lines.append(f"  3-bet: Pool {pool_stats['three_bet']:.1f}% vs GTO avg {gto_avg_3bet:.1f}% → Pool is {abs(three_bet_diff):.1f}% {direction}")

        # F3B comparison
        if gto_avg_f3b > 0:
            f3b_diff = pool_stats['fold_to_3bet'] - gto_avg_f3b
            direction = "OVERFOLDS" if f3b_diff > 0 else "UNDERFOLDS"
            pool_vs_gto_lines.append(f"  Fold to 3-bet: Pool {pool_stats['fold_to_3bet']:.1f}% vs GTO avg {gto_avg_f3b:.1f}% → Pool {direction} by {abs(f3b_diff):.1f}%")

        # VPIP-PFR gap analysis (key indicator of passive play)
        vpip_pfr_gap = pool_stats['vpip'] - pool_stats['pfr']
        gto_gap = 5.0  # GTO players have small gap ~5%
        gap_diff = vpip_pfr_gap - gto_gap
        pool_vs_gto_lines.append(f"  VPIP-PFR Gap: Pool {vpip_pfr_gap:.1f}% vs GTO ~{gto_gap}% → Pool is {gap_diff:.1f}% MORE PASSIVE (cold-calling/limping)")

        pool_vs_gto_section = "\n".join(pool_vs_gto_lines)

    prompt = f"""You are a professional poker coach generating a preflop exploitation strategy for a 6-max No Limit Hold'em cash game.

TABLE INFO:
- Stakes: {stake_level}
- Table Softness: {table_softness}/5.0 ({table_classification})
- Hero Position: {hero_position or "Unknown"}
- {pool_info}

{gto_section}

{pool_vs_gto_section}

OPPONENTS:
{opponents_text}

Generate a comprehensive PREFLOP exploitation strategy. Use the GTO reference data above as your baseline - identify how opponents deviate from GTO and exploit those deviations.

IMPORTANT GUIDELINES:
- Only generate specific exploits for players with 30+ hands of data
- For UNKNOWN players, do NOT include them in opponent_exploits
- Compare player stats to GTO baselines to identify exploitable tendencies
- When a player folds more than GTO, increase bluff frequency
- When a player calls more than GTO, value bet wider and bluff less
- When a player 3-bets less than GTO, open wider; when more, tighten opens

Return a JSON object with this exact structure:
{{
  "general_strategy": {{
    "overview": "2-3 sentence summary of how to approach this table, referencing key GTO deviations",
    "opening_adjustments": ["List of 2-4 specific opening range adjustments based on GTO deviations"],
    "three_bet_adjustments": ["List of 2-4 specific 3-bet range adjustments based on GTO deviations"],
    "defense_adjustments": ["List of 2-3 blind defense adjustments based on GTO deviations"],
    "key_principle": "One sentence - the most important thing to remember"
  }},
  "opponent_exploits": [
    {{
      "name": "PlayerName",
      "exploit": "1-2 sentence specific exploit referencing their GTO deviation"
    }}
  ],
  "priority_actions": [
    "Top 3 highest-EV actions to focus on this session"
  ]
}}

Be specific with hand examples (e.g., "3-bet A5s-A2s, K9s+" rather than "3-bet wider").
Reference GTO deviations where possible (e.g., "Player folds 72% vs GTO 56%, so 3-bet bluff wider").
Respond with ONLY the JSON object, no other text."""

    response_text = ""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON response
        response_text = response.content[0].text.strip()

        # Handle potential markdown code blocks
        clean_response = response_text
        if clean_response.startswith("```"):
            clean_response = re.sub(r"^```(?:json)?\n?", "", clean_response)
            clean_response = re.sub(r"\n?```$", "", clean_response)

        strategy = json.loads(clean_response)
        return {
            "strategy": strategy,
            "prompt": prompt,
            "response": response_text
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        logger.error(f"Response was: {response_text[:500]}")
        # Return a basic fallback strategy - only exploit players with 30+ hands
        return {
            "strategy": {
                "general_strategy": {
                    "overview": f"Table is {table_classification.lower()}. Adjust accordingly.",
                    "opening_adjustments": ["Play standard opening ranges"],
                    "three_bet_adjustments": ["3-bet value hands"],
                    "defense_adjustments": ["Defend standard ranges"],
                    "key_principle": "Focus on value betting against loose players"
                },
                "opponent_exploits": [
                    {"name": p["name"], "exploit": f"{p['classification']} - adjust accordingly"}
                    for p in opponent_profiles
                    if p.get("sample_size", 0) >= 30
                ],
                "priority_actions": ["Play solid preflop poker", "Observe opponent tendencies"]
            },
            "prompt": prompt,
            "response": response_text or "JSON parse error"
        }
    except Exception as e:
        logger.error(f"Error calling Claude API: {e}")
        raise


def save_pregame_strategy(
    db: Session,
    hero_nickname: str,
    stake_level: str,
    hand_id: Optional[int],
    hand_number: Optional[str],
    softness_score: float,
    table_classification: str,
    strategy: Dict[str, Any],
    opponents: List[Dict[str, Any]],
    sender_email: Optional[str] = None,
    ai_prompt: Optional[str] = None,
    ai_response: Optional[str] = None
) -> int:
    """Save strategy to database and return ID."""
    result = db.execute(text("""
        INSERT INTO pregame_strategies (
            hero_nickname, stake_level, hand_id, hand_number,
            softness_score, table_classification,
            strategy, opponents, sender_email,
            ai_prompt, ai_response
        ) VALUES (
            :hero_nickname, :stake_level, :hand_id, :hand_number,
            :softness_score, :table_classification,
            :strategy, :opponents, :sender_email,
            :ai_prompt, :ai_response
        )
        RETURNING id
    """), {
        "hero_nickname": hero_nickname,
        "stake_level": stake_level,
        "hand_id": hand_id,
        "hand_number": hand_number,
        "softness_score": softness_score,
        "table_classification": table_classification,
        "strategy": json.dumps(strategy),
        "opponents": json.dumps(opponents),
        "sender_email": sender_email,
        "ai_prompt": ai_prompt,
        "ai_response": ai_response
    })

    strategy_id = result.fetchone()[0]
    db.commit()
    return strategy_id


def format_strategy_email(
    stake_level: str,
    softness_score: float,
    table_classification: str,
    strategy: Dict[str, Any],
    opponents: List[Dict[str, Any]],
    strategy_id: int
) -> str:
    """Format strategy as email text."""
    general = strategy.get("general_strategy", {})

    lines = [
        f"Subject: Pre-Game Strategy: {stake_level} Table",
        "",
        "━" * 45,
        f"TABLE ASSESSMENT: {table_classification} ({softness_score}/5.0)",
        "━" * 45,
        "",
        "GENERAL STRATEGY",
        "─" * 20,
        general.get("overview", ""),
        "",
        f"Key principle: {general.get('key_principle', '')}",
        "",
        "OPENING ADJUSTMENTS:",
    ]

    for adj in general.get("opening_adjustments", []):
        lines.append(f"• {adj}")

    lines.append("")
    lines.append("3-BET ADJUSTMENTS:")
    for adj in general.get("three_bet_adjustments", []):
        lines.append(f"• {adj}")

    lines.append("")
    lines.append("DEFENSE ADJUSTMENTS:")
    for adj in general.get("defense_adjustments", []):
        lines.append(f"• {adj}")

    lines.append("")
    lines.append("━" * 45)
    lines.append("OPPONENT EXPLOITS")
    lines.append("━" * 45)
    lines.append("")

    for opp in opponents:
        stats = opp.get("stats", {})
        source = "UNKNOWN" if opp["data_source"].startswith("POOL_AVERAGE") else f"{opp['sample_size']} hands"
        stats_str = f"VPIP {stats.get('vpip', 'N/A')}% | PFR {stats.get('pfr', 'N/A')}%"

        lines.append(f"{opp['seat']}. {opp['name']} ({opp['position']}) - {opp['classification']} [{source}]")
        lines.append(f"   {stats_str}")

        # Find exploit for this opponent
        for exp in strategy.get("opponent_exploits", []):
            if exp["name"] == opp["name"]:
                lines.append(f"   → {exp['exploit']}")
                break
        lines.append("")

    lines.append("━" * 45)
    lines.append("PRIORITY ACTIONS")
    lines.append("━" * 45)
    lines.append("")

    for i, action in enumerate(strategy.get("priority_actions", []), 1):
        lines.append(f"{i}. {action}")

    lines.append("")
    lines.append("━" * 45)
    lines.append("")
    lines.append(f"View in app: https://ploit.app/pregame/{strategy_id}")
    lines.append("")
    lines.append("Good luck at the tables!")

    return "\n".join(lines)


async def process_pregame_analysis(
    db: Session,
    hand_text: str,
    stake_level: str,
    hero_nicknames: List[str],
    sender_email: Optional[str] = None,
    hand_id: Optional[int] = None,
    hand_number: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main entry point for pre-game analysis.

    1. Extract opponents from hand
    2. Look up stats
    3. Generate strategy with Claude
    4. Save to database
    5. Return strategy (for email sending)
    """
    logger.info(f"Processing pre-game analysis for {stake_level} hand")

    # Extract opponents
    opponents = extract_opponents_from_hand(hand_text, hero_nicknames)
    if not opponents:
        raise ValueError("No opponents found in hand")

    logger.info(f"Found {len(opponents)} opponents")

    # Get pool stats from database
    pool_stats = get_population_stats_from_db(db, stake_level, hero_nicknames)

    # Build profiles with stats (uses actual pool data from database)
    profiles = build_opponent_profiles(db, opponents, stake_level, hero_nicknames)

    # Calculate table softness
    softness_score, table_classification = calculate_table_softness(profiles)
    logger.info(f"Table softness: {softness_score} ({table_classification})")

    # Detect hero position (if in hand)
    hero_position = None
    for hero in hero_nicknames:
        if hero.lower() in hand_text.lower():
            # Try to find hero's position
            sb_match = re.search(rf"{re.escape(hero)}: posts small blind", hand_text, re.I)
            bb_match = re.search(rf"{re.escape(hero)}: posts big blind", hand_text, re.I)
            if sb_match:
                hero_position = "SB"
            elif bb_match:
                hero_position = "BB"
            break

    # Get GTO baselines from database
    gto_baselines = get_gto_baselines(db)
    logger.info(f"Loaded GTO baselines: {len(gto_baselines.get('opening', {}))} opening, {len(gto_baselines.get('three_bet', {}))} 3bet scenarios")

    # Generate strategy with Claude
    ai_result = generate_strategy_with_claude(
        stake_level=stake_level,
        hero_position=hero_position,
        opponent_profiles=profiles,
        table_softness=softness_score,
        table_classification=table_classification,
        pool_stats=pool_stats,
        gto_baselines=gto_baselines
    )
    strategy = ai_result["strategy"]
    ai_prompt = ai_result["prompt"]
    ai_response = ai_result["response"]

    # Save to database
    strategy_id = save_pregame_strategy(
        db=db,
        hero_nickname=hero_nicknames[0] if hero_nicknames else "unknown",
        stake_level=stake_level,
        hand_id=hand_id,
        hand_number=hand_number,
        softness_score=softness_score,
        table_classification=table_classification,
        strategy=strategy,
        opponents=profiles,
        sender_email=sender_email,
        ai_prompt=ai_prompt,
        ai_response=ai_response
    )

    logger.info(f"Saved pre-game strategy with ID {strategy_id}")

    # Format email
    email_text = format_strategy_email(
        stake_level=stake_level,
        softness_score=softness_score,
        table_classification=table_classification,
        strategy=strategy,
        opponents=profiles,
        strategy_id=strategy_id
    )

    return {
        "strategy_id": strategy_id,
        "softness_score": softness_score,
        "table_classification": table_classification,
        "strategy": strategy,
        "opponents": profiles,
        "email_text": email_text
    }
