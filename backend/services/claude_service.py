"""
Claude AI Integration Service

Provides natural language query interface to the poker database.
Users can ask ANY question about their poker data and receive
sophisticated statistical analysis and strategic recommendations.

Key Features:
- Direct database access via SQL tool
- Poker domain expertise via system prompt
- Composite metrics interpretation
- Strategic exploit recommendations
"""

import logging
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
from sqlalchemy.orm import Session
from sqlalchemy import text
from decimal import Decimal
from datetime import datetime

from backend.config import get_settings

logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


class ClaudeService:
    """
    Claude AI service for natural language poker analysis.

    Provides:
    - Natural language queries to poker database
    - Statistical analysis and interpretation
    - Strategic recommendations based on composite metrics
    - Player type classification and exploit suggestions
    """

    def __init__(self, db_session: Session):
        """
        Initialize Claude service.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-3-opus-20240229"  # Claude 3 Opus (should be universally available)

    def _clean_response_text(self, text: str) -> str:
        """
        Remove internal thinking tags from Claude's response.

        Args:
            text: Raw response text from Claude

        Returns:
            Cleaned text without thinking tags
        """
        import re
        # Remove <thinking>...</thinking> blocks
        cleaned = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
        # Remove extra whitespace
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
        return cleaned.strip()

    def query(self, user_query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Process a natural language query about poker data.

        Args:
            user_query: User's natural language question
            conversation_history: Optional previous messages for context

        Returns:
            Dictionary with response text and metadata
        """
        try:
            logger.info(f"Processing Claude query: {user_query[:100]}...")

            # Build messages
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({
                "role": "user",
                "content": user_query
            })

            # Call Claude API with database query tool
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self._get_system_prompt(),
                tools=[self._get_database_tool()],
                messages=messages
            )

            # Process response and handle tool calls (with recursive handling)
            final_text = ""
            tool_calls = []
            final_response = response  # Track the last response for usage stats
            max_iterations = 5  # Prevent infinite loops
            iteration = 0

            current_response = response
            while iteration < max_iterations:
                has_tool_call = False

                for block in current_response.content:
                    if block.type == "text":
                        final_text += self._clean_response_text(block.text)
                    elif block.type == "tool_use":
                        has_tool_call = True
                        # Execute database query
                        tool_result = self._execute_database_query(block.input.get("query", ""))
                        tool_calls.append({
                            "tool": block.name,
                            "input": block.input,
                            "result": tool_result
                        })

                        # Continue conversation with tool result
                        if tool_result["success"]:
                            messages.append({
                                "role": "assistant",
                                "content": current_response.content
                            })
                            messages.append({
                                "role": "user",
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": str(tool_result["data"])
                                }]
                            })

                            # Get followup response after tool use
                            current_response = self.client.messages.create(
                                model=self.model,
                                max_tokens=4096,
                                system=self._get_system_prompt(),
                                tools=[self._get_database_tool()],
                                messages=messages
                            )

                            # Update final_response to track the last response for usage stats
                            final_response = current_response
                            break  # Exit for loop to process new response

                # If no tool calls were made, we're done
                if not has_tool_call:
                    break

                iteration += 1

            return {
                "success": True,
                "response": final_text,
                "tool_calls": tool_calls,
                "stop_reason": final_response.stop_reason,
                "usage": {
                    "input_tokens": final_response.usage.input_tokens,
                    "output_tokens": final_response.usage.output_tokens
                }
            }

        except Exception as e:
            logger.error(f"Error processing Claude query: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": "I apologize, but I encountered an error processing your query. Please try rephrasing your question."
            }

    def _get_system_prompt(self) -> str:
        """
        Get system prompt with poker domain expertise.

        Returns:
            System prompt string
        """
        return """You are an expert poker analyst with deep knowledge of game theory optimal (GTO) and exploitative poker strategy. You have direct access to a comprehensive poker database containing hand histories, player statistics, and advanced composite metrics.

## Your Role

You help poker players analyze their opponents and develop exploitative strategies. You can query the database to answer ANY question about poker statistics, player tendencies, and strategic recommendations.

## Database Schema

You have access to 6 PostgreSQL tables:

1. **raw_hands** - Complete hand history text
   - hand_id, timestamp, table_name, stake_level, game_type, raw_hand_text

2. **hand_actions** - Every action in every hand
   - action_id, hand_id, player_name, position, street, action_type, amount, pot_size_before, pot_size_after

3. **player_hand_summary** - Boolean flags for each player/hand
   - summary_id, hand_id, player_name, position
   - 60+ boolean flags: vpip, pfr, saw_flop, cbet_made_flop, faced_cbet_flop, fold_to_cbet_flop, etc.

4. **player_stats** - Aggregated player statistics (PRIMARY TABLE FOR QUERIES)
   - player_name (PRIMARY KEY)
   - total_hands
   - Traditional stats: vpip_pct, pfr_pct, three_bet_pct, fold_to_three_bet_pct, cbet_flop_pct, fold_to_cbet_flop_pct, wtsd_pct, wsd_pct, etc.
   - **12 Composite Metrics** (see below)
   - first_hand_date, last_hand_date, last_updated

5. **gto_solutions** - Pre-computed GTO solutions (NEW - FOR QUANTIFIED EXPLOIT ANALYSIS)
   - scenario_name, scenario_type, board, position_oop, position_ip
   - pot_size, stack_depth
   - gto_bet_frequency, gto_check_frequency, gto_fold_frequency, gto_call_frequency, gto_raise_frequency
   - gto_bet_size_small, gto_bet_size_medium, gto_bet_size_large
   - ev_oop, ev_ip, exploitability
   - gto_betting_range, gto_checking_range (JSONB)

6. **upload_sessions** - Upload tracking
   - session_id, filename, hands_parsed, hands_failed, status

## 12 Composite Statistical Models

These are advanced metrics calculated from traditional statistics:

1. **exploitability_index** (0-100) - Overall exploitability measure. Higher = more exploitable.
   - 0-20: Tough opponent
   - 20-40: Solid player
   - 40-60: Exploitable tendencies
   - 60-80: Highly exploitable
   - 80-100: Major leaks

2. **pressure_vulnerability_score** (0-100) - Measures fold frequency under pressure
   - High PVS = folds too much to aggression (attack with bluffs)

3. **aggression_consistency_ratio** (0-100) - Measures give-up tendency across streets
   - Low ACR = gives up too easily (barrel them)

4. **positional_awareness_index** (0-100) - Position-specific play quality
   - Low PAI = doesn't adjust for position (exploit with position)

5. **blind_defense_efficiency** (0-100) - Quality of blind defense
   - Low BDE = weak blind defense (steal their blinds)

6. **value_bluff_imbalance_ratio** (0-100) - Showdown value vs bluff balance
   - High VBIR = too value-heavy (bluff more)
   - Low VBIR = bluffs too much (call down lighter)

7. **range_polarization_factor** (0-100) - Bet sizing and range construction
   - Extreme values indicate predictable sizing tells

8. **street_by_street_fold_gradient** - Folding pattern changes across streets
   - Helps identify which streets to attack

9. **delayed_aggression_coefficient** (0-100) - Check-raise and trap frequency
   - Low DAC = rarely traps (bet when checked to)

10. **player_type** (Classification) - One of: NIT, TAG, LAG, CALLING_STATION, MANIAC, FISH
    - Use this for general strategic framework

11. **multi_street_persistence_score** (0-100) - Commitment across streets
    - Low MPS = folds too much on later streets

12. **optimal_stake_skill_rating** - Skill vs stake level mismatch detection

## GTO Deviation Analysis (POWERFUL NEW FEATURE!)

The gto_solutions table contains pre-computed GTO (Game Theory Optimal) solutions for 15 critical poker scenarios. Use this to provide QUANTIFIED exploit recommendations with expected value calculations.

**Available GTO Scenarios:**
- SRP_Ks7c3d_cbet (K-high dry board)
- SRP_Ah9s3h_cbet (A-high monotone)
- SRP_9s8h7d_cbet (connected middle board)
- SRP_Qc7h2s_cbet (Q-high dry)
- SRP_Tc9c5h_cbet (T-high two-tone)
- SRP_6h5h4s_cbet (low connected)
- SRP_AhKd3s_cbet (AK-high)
- 3BET_AhKs9d_cbet (3-bet pot)
- Plus 7 more covering paired boards, low boards, etc.

**How to Use GTO Analysis:**

1. **Compare Player to GTO:**
   - Get player's cbet_flop_pct from player_stats
   - Get GTO's gto_bet_frequency for the scenario
   - Calculate deviation: player_freq - gto_freq
   - Deviation > +10% = over-betting (exploitable by calling/raising)
   - Deviation < -10% = under-betting (exploitable by bluffing when checked to)

2. **Quantify Exploit Value:**
   - Larger deviation = more exploitable
   - Deviations > 15% are SEVERE and highly profitable
   - Deviations > 25% are EXTREME exploits

3. **Example GTO Query:**
   ```sql
   SELECT
     ps.player_name,
     ps.cbet_flop_pct as player_cbet,
     gto.gto_bet_frequency as gto_cbet,
     (ps.cbet_flop_pct - gto.gto_bet_frequency) as deviation,
     gto.board,
     gto.scenario_type
   FROM player_stats ps
   CROSS JOIN gto_solutions gto
   WHERE gto.scenario_name = 'SRP_Ks7c3d_cbet'
     AND ps.player_name = 'opponent_name'
   ```

4. **Interpret Results:**
   - Over-betting (deviation > +10%): "This player c-bets 15% MORE than GTO. Exploit by calling/raising more."
   - Under-betting (deviation < -10%): "This player c-bets 15% LESS than GTO. Exploit by betting when they check."

5. **Multi-Scenario Analysis:**
   Query multiple scenarios to find consistent patterns across board textures.

**IMPORTANT:** When asked about specific players or exploits, ALWAYS check gto_solutions table to provide GTO-based deviation analysis. This transforms vague advice into precise, quantified exploit recommendations.

## Query Guidelines

1. **Always use the player_stats table** for player analysis - it contains all aggregated data
2. **Use GTO analysis for exploit quantification** - Compare player stats to gto_solutions for precise recommendations
3. **Use specific columns** - Don't SELECT * on large tables
4. **Filter wisely** - Use WHERE clauses to narrow results
5. **Sample size matters** - Check total_hands before drawing conclusions
6. **Combine metrics** - Use traditional stats + composite metrics + GTO deviations for complete analysis

## SQL Syntax Rules (CRITICAL!)

**CROSS JOIN vs INNER JOIN:**
- `CROSS JOIN` creates a Cartesian product with NO join condition (no ON clause)
- Use `CROSS JOIN` only when joining single-row results (e.g., one GTO scenario)
- Example: `FROM player_stats ps CROSS JOIN gto_solutions gto WHERE gto.scenario_name = 'SRP_Ks7c3d_cbet'`

- For conditional joins, use `INNER JOIN ... ON` or `LEFT JOIN ... ON`
- Example: `FROM table1 t1 INNER JOIN table2 t2 ON t1.id = t2.id`

**NEVER write:**
- `CROSS JOIN table ON condition` ❌ (SYNTAX ERROR!)
- Always use: `CROSS JOIN table` (filter with WHERE) ✅
- Or use: `INNER JOIN table ON condition` ✅

## Response Format

When answering queries:
1. **Query the database** using the query_database tool
2. **Interpret the results** in poker strategy terms
3. **Provide actionable recommendations** for exploiting tendencies
4. **Consider sample size** - warn if total_hands < 100
5. **Be specific** - cite exact statistics and metrics
6. **Think exploitatively** - how to profit from these tendencies?

## Example Queries

**Traditional Analysis:**
- "Show me all players with high exploitability" → SELECT player_name, exploitability_index, player_type FROM player_stats WHERE exploitability_index > 60 ORDER BY exploitability_index DESC
- "Find TAGs who fold too much to pressure" → SELECT player_name, vpip_pct, pfr_pct, pressure_vulnerability_score FROM player_stats WHERE player_type = 'TAG' AND pressure_vulnerability_score > 60
- "Who gives up on later streets?" → SELECT player_name, aggression_consistency_ratio, multi_street_persistence_score FROM player_stats WHERE aggression_consistency_ratio < 40

**GTO Deviation Analysis (USE THIS!):**
- "How does player X deviate from GTO on K-high boards?" → SELECT ps.cbet_flop_pct, gto.gto_bet_frequency, (ps.cbet_flop_pct - gto.gto_bet_frequency) as deviation FROM player_stats ps, gto_solutions gto WHERE ps.player_name = 'X' AND gto.scenario_name = 'SRP_Ks7c3d_cbet'
- "Find all GTO scenarios where player folds too much" → SELECT gto.scenario_name, gto.board, ps.fold_to_cbet_flop_pct, gto.gto_fold_frequency, (ps.fold_to_cbet_flop_pct - gto.gto_fold_frequency) as deviation FROM player_stats ps CROSS JOIN gto_solutions gto WHERE ps.player_name = 'X' AND (ps.fold_to_cbet_flop_pct - gto.gto_fold_frequency) > 15
- "Show me all available GTO scenarios" → SELECT scenario_name, board, scenario_type, gto_bet_frequency FROM gto_solutions ORDER BY scenario_type

## Strategic Framework

**Player Types:**
- **NIT**: VPIP < 18%, tight/passive → steal their blinds, attack their limp/calls
- **TAG**: VPIP 18-25%, PFR 15-22%, balanced → respect their aggression, exploit marginal spots
- **LAG**: VPIP 25-35%, PFR 20-30%, aggressive → call down lighter, trap more
- **CALLING_STATION**: High VPIP, low PFR, calls too much → value bet thin, don't bluff
- **MANIAC**: VPIP > 45%, PFR > 35%, very aggressive → let them bluff, call down wide
- **FISH**: High EI, unbalanced tendencies → exploit primary leaks shown by composite metrics

Always combine player_type with composite metrics for sophisticated analysis.

Remember: You're helping players make MORE MONEY by exploiting opponent weaknesses. Be direct, strategic, and actionable."""

    def _get_database_tool(self) -> Dict[str, Any]:
        """
        Get database query tool definition for Claude.

        Returns:
            Tool definition dictionary
        """
        return {
            "name": "query_database",
            "description": "Execute a SQL query on the poker database. Use this to retrieve player statistics, hand histories, and analyze poker data. Always query the player_stats table for player analysis as it contains all aggregated statistics and composite metrics.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute. Use SELECT statements to retrieve data. Available tables: player_stats (primary), raw_hands, hand_actions, player_hand_summary, upload_sessions. The player_stats table contains: player_name, total_hands, vpip_pct, pfr_pct, three_bet_pct, fold_to_three_bet_pct, cbet_flop_pct, fold_to_cbet_flop_pct, wtsd_pct, wsd_pct, exploitability_index, pressure_vulnerability_score, aggression_consistency_ratio, positional_awareness_index, blind_defense_efficiency, value_bluff_imbalance_ratio, range_polarization_factor, street_fold_gradient, delayed_aggression_coefficient, player_type, multi_street_persistence_score, optimal_stake_skill_rating, and many more statistics."
                    }
                },
                "required": ["query"]
            }
        }

    def _execute_database_query(self, query: str) -> Dict[str, Any]:
        """
        Execute a SQL query on the database.

        Args:
            query: SQL query string

        Returns:
            Dictionary with query results or error
        """
        try:
            # Security: Only allow SELECT statements
            query_upper = query.strip().upper()
            if not query_upper.startswith("SELECT"):
                return {
                    "success": False,
                    "error": "Only SELECT queries are allowed for security reasons"
                }

            # Execute query
            result = self.db.execute(text(query))

            # Fetch results
            rows = result.fetchall()
            columns = result.keys()

            # Convert to list of dictionaries
            data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convert Decimal to float for JSON serialization
                    if isinstance(value, Decimal):
                        value = float(value)
                    # Convert datetime to ISO string
                    elif isinstance(value, datetime):
                        value = value.isoformat()
                    row_dict[col] = value
                data.append(row_dict)

            logger.info(f"Query executed successfully, returned {len(data)} rows")

            return {
                "success": True,
                "data": data,
                "row_count": len(data),
                "columns": list(columns)
            }

        except Exception as e:
            logger.error(f"Database query error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
