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

from .pregame_tools import PREGAME_TOOLS, execute_tool

logger = logging.getLogger(__name__)

def get_population_stats_from_db(db: Session, stake_level: str, hero_nicknames: List[str]) -> Dict[str, Any]:
    """
    Calculate actual population averages from database for a stake level.
    Uses WEIGHTED averages (same as UI) - players with more hands count more.
    Excludes hero nicknames from the calculation.
    """
    stake = stake_level.upper() if stake_level else "NL4"
    hero_lower = [n.lower() for n in hero_nicknames] if hero_nicknames else []

    # Build hero exclusion clause dynamically to avoid array parameter issues
    hero_exclusion = ""
    params = {"stake_level": stake}
    if hero_lower:
        placeholders = ", ".join([f":hero_{i}" for i in range(len(hero_lower))])
        hero_exclusion = f"AND LOWER(phs.player_name) NOT IN ({placeholders})"
        for i, name in enumerate(hero_lower):
            params[f"hero_{i}"] = name

    # Use same weighted average calculation as UI (pools_endpoints.py)
    query = f"""
        WITH player_stake_hands AS (
            SELECT
                phs.player_name,
                COUNT(*) as hands_at_stake
            FROM player_hand_summary phs
            JOIN raw_hands rh ON phs.hand_id = rh.hand_id
            WHERE rh.stake_level = :stake_level
            {hero_exclusion}
            GROUP BY phs.player_name
        ),
        player_with_stats AS (
            SELECT
                psh.player_name,
                psh.hands_at_stake,
                ps.vpip_pct,
                ps.pfr_pct,
                ps.three_bet_pct,
                ps.fold_to_three_bet_pct
            FROM player_stake_hands psh
            JOIN player_stats ps ON psh.player_name = ps.player_name
        )
        SELECT
            COUNT(*) as player_count,
            SUM(hands_at_stake) as total_hands,
            SUM(vpip_pct * hands_at_stake) as weighted_vpip,
            SUM(pfr_pct * hands_at_stake) as weighted_pfr,
            SUM(three_bet_pct * hands_at_stake) as weighted_3bet,
            SUM(fold_to_three_bet_pct * hands_at_stake) as weighted_f3b
        FROM player_with_stats
    """

    try:
        result = db.execute(text(query), params).fetchone()

        if result and result.player_count and result.player_count > 5 and result.total_hands > 0:
            avg_vpip = float(result.weighted_vpip) / float(result.total_hands) if result.weighted_vpip else 25.0
            avg_pfr = float(result.weighted_pfr) / float(result.total_hands) if result.weighted_pfr else 18.0
            avg_3bet = float(result.weighted_3bet) / float(result.total_hands) if result.weighted_3bet else 6.0
            avg_f3b = float(result.weighted_f3b) / float(result.total_hands) if result.weighted_f3b else 55.0

            logger.info(f"Pool stats for {stake}: {result.player_count} players, {result.total_hands} hands, VPIP={avg_vpip:.1f}%, PFR={avg_pfr:.1f}%")
            return {
                "vpip": round(avg_vpip, 1),
                "pfr": round(avg_pfr, 1),
                "three_bet": round(avg_3bet, 1),
                "fold_to_3bet": round(avg_f3b, 1),
                "player_count": result.player_count,
                "total_hands": result.total_hands,
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
    db: Session,
    stake_level: str,
    hero_position: str,
    opponent_profiles: List[Dict[str, Any]],
    table_softness: float,
    table_classification: str,
    hero_nicknames: List[str]
) -> Dict[str, Any]:
    """
    Use Claude with tool calling to generate exploitation strategy.
    Claude can query the database to gather whatever information it needs.
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Build initial opponent info for Claude
    opponent_summaries = []
    for p in opponent_profiles:
        stats = p.get("stats", {})
        stats_str = f"VPIP {stats.get('vpip', 'N/A')}% | PFR {stats.get('pfr', 'N/A')}% | 3bet {stats.get('three_bet', 'N/A')}% | F3B {stats.get('fold_to_3bet', 'N/A')}%"

        if p["data_source"].startswith("POOL_AVERAGE"):
            source_note = f"[UNKNOWN - using pool average - use tools to check if in database]"
        else:
            source_note = f"[{p['sample_size']} hands - {p['confidence']} confidence]"

        opponent_summaries.append(f"{p['seat']}. {p['name']} ({p['position']}) - {p['classification']} {source_note}\n   Basic Stats: {stats_str}")

    opponents_text = "\n".join(opponent_summaries)

    # Initial system prompt
    system_prompt = """You are a professional poker coach generating a preflop exploitation strategy for a 6-max No Limit Hold'em cash game.

You have access to a comprehensive database of player statistics and GTO reference data. Use the provided tools to:
1. Look up detailed stats for each opponent (especially those with DATABASE data)
2. Query GTO frequencies for relevant scenarios
3. Get pool statistics for comparison
4. Compare players to GTO to identify their biggest leaks

IMPORTANT WORKFLOW:
1. First, get the pool statistics for this stake level
2. Look up GTO scenarios for key spots (opening, 3-betting, defending)
3. For each opponent with DATABASE data, get their full stats and compare to GTO
4. Use this data to generate specific, actionable exploits

When you have gathered enough information, generate your final strategy as a JSON object."""

    # Initial user message
    initial_message = f"""Generate a preflop exploitation strategy for this table:

TABLE INFO:
- Stakes: {stake_level}
- Table Softness: {table_softness}/5.0 ({table_classification})
- Hero Position: {hero_position or "Unknown"}

OPPONENTS AT TABLE:
{opponents_text}

Use the tools to gather detailed information about:
1. Pool statistics for {stake_level}
2. GTO reference frequencies
3. Full stats for opponents with database data
4. Compare each known opponent to GTO to find their leaks

After gathering data, return a JSON strategy with this structure:
{{
  "general_strategy": {{
    "overview": "2-3 sentence summary referencing specific GTO deviations you found",
    "opening_adjustments": ["2-4 specific adjustments with hand examples"],
    "three_bet_adjustments": ["2-4 specific adjustments with hand examples"],
    "defense_adjustments": ["2-3 blind defense adjustments"],
    "key_principle": "One sentence - most important thing to remember"
  }},
  "opponent_exploits": [
    {{
      "name": "PlayerName",
      "exploit": "1-2 sentence specific exploit referencing their exact stats vs GTO"
    }}
  ],
  "priority_actions": ["Top 3 highest-EV actions for this session"]
}}

ONLY include opponent_exploits for players with 30+ hands of data.
Be specific with hand examples (e.g., "3-bet A5s-A2s, K9s+" not "3-bet wider").
Reference exact numbers from your tool queries (e.g., "Player folds 72% vs GTO 56%")."""

    messages = [{"role": "user", "content": initial_message}]
    full_prompt = f"System: {system_prompt}\n\nUser: {initial_message}"
    full_response = ""

    # Tool calling loop
    max_iterations = 15
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        logger.info(f"Claude strategy generation iteration {iteration}")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system_prompt,
            tools=PREGAME_TOOLS,
            messages=messages
        )

        # Check stop reason
        if response.stop_reason == "end_turn":
            # Claude is done - extract final response
            for block in response.content:
                if hasattr(block, 'text'):
                    full_response += block.text
            break

        elif response.stop_reason == "tool_use":
            # Process tool calls
            tool_results = []
            assistant_content = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_id = block.id

                    logger.info(f"Claude calling tool: {tool_name} with {tool_input}")
                    full_prompt += f"\n\n[Tool Call: {tool_name}({json.dumps(tool_input)})]"

                    # Execute the tool
                    result = execute_tool(db, tool_name, tool_input, hero_nicknames)
                    full_response += f"\n[Tool: {tool_name}] {result[:200]}..."

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result
                    })
                    assistant_content.append(block)
                elif hasattr(block, 'text'):
                    assistant_content.append(block)
                    full_response += block.text

            # Add assistant message with tool calls
            messages.append({"role": "assistant", "content": assistant_content})
            # Add tool results
            messages.append({"role": "user", "content": tool_results})
        else:
            # Unexpected stop reason
            logger.warning(f"Unexpected stop reason: {response.stop_reason}")
            for block in response.content:
                if hasattr(block, 'text'):
                    full_response += block.text
            break

    logger.info(f"Strategy generation completed after {iteration} iterations")

    # Parse the final JSON response
    try:
        clean_response = full_response.strip()

        # First, try to extract JSON from markdown code blocks (most reliable)
        code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?"general_strategy"[\s\S]*?\})\s*```', clean_response)
        if code_block_match:
            clean_response = code_block_match.group(1)
        else:
            # Fallback: Find the last JSON object containing "general_strategy"
            # This handles cases where Claude outputs JSON without code blocks
            all_matches = list(re.finditer(r'\{[^{}]*"general_strategy"[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', clean_response))
            if all_matches:
                clean_response = all_matches[-1].group(0)
            else:
                # Last resort: greedy match but take the last occurrence
                json_match = re.search(r'(\{[\s\S]*"general_strategy"[\s\S]*"priority_actions"[\s\S]*\})\s*$', clean_response)
                if json_match:
                    clean_response = json_match.group(1)

        # Clean any remaining markdown artifacts
        clean_response = re.sub(r'^```(?:json)?\s*', '', clean_response)
        clean_response = re.sub(r'\s*```$', '', clean_response)

        strategy = json.loads(clean_response)
        logger.info(f"Successfully parsed strategy JSON with {len(strategy.get('opponent_exploits', []))} exploits")
        return {
            "strategy": strategy,
            "prompt": full_prompt,
            "response": full_response
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        logger.error(f"Response was: {full_response[:1000]}")

        # Return fallback strategy
        return {
            "strategy": {
                "general_strategy": {
                    "overview": f"Table is {table_classification.lower()}. Adjust accordingly based on opponent tendencies.",
                    "opening_adjustments": ["Play standard opening ranges", "Adjust based on player types"],
                    "three_bet_adjustments": ["3-bet value hands", "Add bluffs vs tight folders"],
                    "defense_adjustments": ["Defend standard ranges in blinds"],
                    "key_principle": "Focus on value betting against loose players"
                },
                "opponent_exploits": [
                    {"name": p["name"], "exploit": f"{p['classification']} player - adjust accordingly"}
                    for p in opponent_profiles
                    if p.get("sample_size", 0) >= 30
                ],
                "priority_actions": ["Play solid preflop poker", "Observe and adapt to opponent tendencies", "Value bet relentlessly vs calling stations"]
            },
            "prompt": full_prompt,
            "response": full_response or "JSON parse error"
        }
    except Exception as e:
        logger.error(f"Error in strategy generation: {e}")
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


def get_classification_color(classification: str) -> tuple:
    """Get color scheme for table classification."""
    colors = {
        "VERY_SOFT": ("#10b981", "#d1fae5"),  # green
        "SOFT": ("#22c55e", "#dcfce7"),  # light green
        "MIXED": ("#f59e0b", "#fef3c7"),  # amber
        "TOUGH": ("#f97316", "#ffedd5"),  # orange
        "VERY_TOUGH": ("#ef4444", "#fee2e2"),  # red
    }
    return colors.get(classification, ("#6b7280", "#f3f4f6"))


def get_player_type_color(player_type: str) -> tuple:
    """Get color scheme for player type."""
    colors = {
        "CALLING_STATION": ("#eab308", "#fef9c3"),  # yellow
        "LOOSE_PASSIVE": ("#f97316", "#ffedd5"),  # orange
        "MANIAC": ("#a855f7", "#f3e8ff"),  # purple
        "LOOSE": ("#f59e0b", "#fef3c7"),  # amber
        "NIT": ("#3b82f6", "#dbeafe"),  # blue
        "TAG": ("#22c55e", "#dcfce7"),  # green
        "LAG": ("#f97316", "#ffedd5"),  # orange
        "TIGHT": ("#6366f1", "#e0e7ff"),  # indigo
        "REGULAR": ("#6b7280", "#f3f4f6"),  # gray
        "UNKNOWN": ("#9ca3af", "#f9fafb"),  # light gray
    }
    return colors.get(player_type, ("#6b7280", "#f3f4f6"))


def format_strategy_html_email(
    stake_level: str,
    softness_score: float,
    table_classification: str,
    strategy: Dict[str, Any],
    opponents: List[Dict[str, Any]],
    strategy_id: int
) -> str:
    """Format strategy as professional HTML email."""
    general = strategy.get("general_strategy", {})
    class_color, class_bg = get_classification_color(table_classification)

    # Build opponent rows
    opponent_rows = ""
    for opp in opponents:
        stats = opp.get("stats", {})
        source = "Unknown" if opp["data_source"].startswith("POOL_AVERAGE") else f"{opp['sample_size']} hands"
        type_color, type_bg = get_player_type_color(opp.get("classification", "UNKNOWN"))

        # Find exploit for this opponent
        exploit_text = ""
        for exp in strategy.get("opponent_exploits", []):
            if exp["name"] == opp["name"]:
                exploit_text = exp["exploit"]
                break

        opponent_rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">
                <div style="font-weight: 600; color: #111827;">{opp['name']}</div>
                <div style="font-size: 12px; color: #6b7280;">{opp['position']} • {source}</div>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: center;">
                <span style="display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 500; background-color: {type_bg}; color: {type_color};">
                    {opp.get('classification', 'UNKNOWN')}
                </span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: center; font-family: monospace; font-size: 13px;">
                {stats.get('vpip', 'N/A')}%
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: center; font-family: monospace; font-size: 13px;">
                {stats.get('pfr', 'N/A')}%
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: center; font-family: monospace; font-size: 13px;">
                {stats.get('three_bet', 'N/A')}%
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; font-size: 13px; color: #374151;">
                {exploit_text if exploit_text else '<span style="color: #9ca3af;">Insufficient data</span>'}
            </td>
        </tr>
        """

    # Build priority actions
    priority_items = ""
    for i, action in enumerate(strategy.get("priority_actions", []), 1):
        priority_items += f"""
        <div style="display: flex; align-items: flex-start; margin-bottom: 12px;">
            <div style="width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 14px; flex-shrink: 0;">{i}</div>
            <div style="margin-left: 12px; color: #374151; line-height: 1.5;">{action}</div>
        </div>
        """

    # Build adjustment lists
    def build_list(items):
        if not items:
            return "<li style='color: #9ca3af;'>No specific adjustments</li>"
        return "".join([f"<li style='margin-bottom: 8px; color: #374151;'>{item}</li>" for item in items])

    opening_list = build_list(general.get("opening_adjustments", []))
    three_bet_list = build_list(general.get("three_bet_adjustments", []))
    defense_list = build_list(general.get("defense_adjustments", []))

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6;">
    <div style="max-width: 700px; margin: 0 auto; padding: 20px;">

        <!-- Header -->
        <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); border-radius: 16px 16px 0 0; padding: 32px; text-align: center;">
            <h1 style="margin: 0; color: white; font-size: 28px; font-weight: 700;">Pre-Game Strategy</h1>
            <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 16px;">{stake_level} Table Analysis</p>
        </div>

        <!-- Table Assessment Card -->
        <div style="background: white; padding: 24px; border-left: 1px solid #e5e7eb; border-right: 1px solid #e5e7eb;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                <div>
                    <div style="font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Table Classification</div>
                    <span style="display: inline-block; padding: 8px 20px; border-radius: 9999px; font-size: 16px; font-weight: 600; background-color: {class_bg}; color: {class_color};">
                        {table_classification.replace('_', ' ')}
                    </span>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Softness Score</div>
                    <div style="font-size: 32px; font-weight: 700; color: {class_color};">{softness_score}<span style="font-size: 18px; color: #9ca3af;">/5.0</span></div>
                </div>
            </div>
        </div>

        <!-- Overview Card -->
        <div style="background: #f8fafc; padding: 24px; border-left: 1px solid #e5e7eb; border-right: 1px solid #e5e7eb; border-top: 1px solid #e5e7eb;">
            <div style="font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px;">Strategy Overview</div>
            <p style="margin: 0; color: #1f2937; font-size: 16px; line-height: 1.6;">{general.get("overview", "No overview available.")}</p>
            <div style="margin-top: 16px; padding: 16px; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 12px; border-left: 4px solid #f59e0b;">
                <div style="font-size: 12px; color: #92400e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Key Principle</div>
                <div style="color: #78350f; font-weight: 500;">{general.get("key_principle", "Play solid poker.")}</div>
            </div>
        </div>

        <!-- Adjustments Section -->
        <div style="background: white; padding: 24px; border: 1px solid #e5e7eb;">
            <h2 style="margin: 0 0 20px 0; font-size: 18px; color: #111827;">Strategy Adjustments</h2>

            <div style="display: grid; gap: 20px;">
                <!-- Opening -->
                <div style="background: #f0fdf4; border-radius: 12px; padding: 16px;">
                    <div style="font-size: 14px; font-weight: 600; color: #166534; margin-bottom: 12px;">Opening Range</div>
                    <ul style="margin: 0; padding-left: 20px; list-style-type: disc;">
                        {opening_list}
                    </ul>
                </div>

                <!-- 3-Bet -->
                <div style="background: #fef3c7; border-radius: 12px; padding: 16px;">
                    <div style="font-size: 14px; font-weight: 600; color: #92400e; margin-bottom: 12px;">3-Bet Strategy</div>
                    <ul style="margin: 0; padding-left: 20px; list-style-type: disc;">
                        {three_bet_list}
                    </ul>
                </div>

                <!-- Defense -->
                <div style="background: #ede9fe; border-radius: 12px; padding: 16px;">
                    <div style="font-size: 14px; font-weight: 600; color: #5b21b6; margin-bottom: 12px;">Blind Defense</div>
                    <ul style="margin: 0; padding-left: 20px; list-style-type: disc;">
                        {defense_list}
                    </ul>
                </div>
            </div>
        </div>

        <!-- Opponents Table -->
        <div style="background: white; padding: 24px; border: 1px solid #e5e7eb; border-top: none; overflow-x: auto;">
            <h2 style="margin: 0 0 20px 0; font-size: 18px; color: #111827;">Opponent Analysis</h2>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <thead>
                    <tr style="background: #f9fafb;">
                        <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151; border-bottom: 2px solid #e5e7eb;">Player</th>
                        <th style="padding: 12px; text-align: center; font-weight: 600; color: #374151; border-bottom: 2px solid #e5e7eb;">Type</th>
                        <th style="padding: 12px; text-align: center; font-weight: 600; color: #374151; border-bottom: 2px solid #e5e7eb;">VPIP</th>
                        <th style="padding: 12px; text-align: center; font-weight: 600; color: #374151; border-bottom: 2px solid #e5e7eb;">PFR</th>
                        <th style="padding: 12px; text-align: center; font-weight: 600; color: #374151; border-bottom: 2px solid #e5e7eb;">3bet</th>
                        <th style="padding: 12px; text-align: left; font-weight: 600; color: #374151; border-bottom: 2px solid #e5e7eb;">Exploit</th>
                    </tr>
                </thead>
                <tbody>
                    {opponent_rows}
                </tbody>
            </table>
        </div>

        <!-- Priority Actions -->
        <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); padding: 24px; border-radius: 0 0 16px 16px;">
            <h2 style="margin: 0 0 20px 0; font-size: 18px; color: white;">Priority Actions</h2>
            {priority_items}
        </div>

        <!-- Footer -->
        <div style="text-align: center; padding: 24px;">
            <a href="https://ploit.app/pregame/{strategy_id}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; text-decoration: none; border-radius: 12px; font-weight: 600; font-size: 16px;">
                View Full Strategy in App
            </a>
            <p style="margin: 20px 0 0 0; color: #6b7280; font-size: 14px;">Good luck at the tables! 🎰</p>
        </div>

    </div>
</body>
</html>
    """

    return html


def format_strategy_email(
    stake_level: str,
    softness_score: float,
    table_classification: str,
    strategy: Dict[str, Any],
    opponents: List[Dict[str, Any]],
    strategy_id: int
) -> str:
    """Format strategy as plain text email (fallback)."""
    general = strategy.get("general_strategy", {})

    lines = [
        f"PRE-GAME STRATEGY: {stake_level} Table",
        "",
        f"TABLE: {table_classification} ({softness_score}/5.0)",
        "",
        "OVERVIEW:",
        general.get("overview", ""),
        "",
        f"KEY PRINCIPLE: {general.get('key_principle', '')}",
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
    lines.append("OPPONENTS:")
    lines.append("")

    for opp in opponents:
        stats = opp.get("stats", {})
        source = "Unknown" if opp["data_source"].startswith("POOL_AVERAGE") else f"{opp['sample_size']} hands"
        lines.append(f"{opp['name']} ({opp['position']}) - {opp['classification']} [{source}]")
        lines.append(f"  VPIP {stats.get('vpip', 'N/A')}% | PFR {stats.get('pfr', 'N/A')}% | 3bet {stats.get('three_bet', 'N/A')}%")

        for exp in strategy.get("opponent_exploits", []):
            if exp["name"] == opp["name"]:
                lines.append(f"  → {exp['exploit']}")
                break
        lines.append("")

    lines.append("PRIORITY ACTIONS:")
    for i, action in enumerate(strategy.get("priority_actions", []), 1):
        lines.append(f"{i}. {action}")

    lines.append("")
    lines.append(f"View in app: https://ploit.app/pregame/{strategy_id}")

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

    # Build profiles with stats (uses pool averages for unknown players)
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

    # Generate strategy with Claude (tool-based approach)
    # Claude will query pool stats, GTO baselines, and detailed opponent info itself
    logger.info("Starting tool-based strategy generation with Claude")
    ai_result = generate_strategy_with_claude(
        db=db,
        stake_level=stake_level,
        hero_position=hero_position,
        opponent_profiles=profiles,
        table_softness=softness_score,
        table_classification=table_classification,
        hero_nicknames=hero_nicknames
    )
    strategy = ai_result["strategy"]
    ai_prompt = ai_result["prompt"]
    ai_response = ai_result["response"]

    # Ensure clean transaction state before saving (tool queries may have left it dirty)
    try:
        db.rollback()
    except:
        pass

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

    # Format emails (HTML and plain text fallback)
    email_html = format_strategy_html_email(
        stake_level=stake_level,
        softness_score=softness_score,
        table_classification=table_classification,
        strategy=strategy,
        opponents=profiles,
        strategy_id=strategy_id
    )
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
        "email_text": email_text,
        "email_html": email_html
    }
