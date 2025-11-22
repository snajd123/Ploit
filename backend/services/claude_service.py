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
        # Claude 4.5 Haiku - Fastest and cheapest ($1/1M input, $5/1M output)
        # Alternative: "claude-sonnet-4-5-20250929" for maximum intelligence
        self.model = "claude-haiku-4-5-20251001"

    def _is_pool_analysis_query(self, query: str) -> bool:
        """
        Detect if a query is requesting comprehensive pool analysis.

        Args:
            query: SQL query string

        Returns:
            True if this is a pool analysis query
        """
        import re
        query_lower = query.lower()

        # Check for pool analysis indicators
        pool_indicators = [
            'pool_analysis_comprehensive',
            'analyze.*pool',
            'pool.*overview',
            'comprehensive.*pool',
            'player_stats.*avg.*exploitability',
            'count.*player.*group by player_type',
            'select.*from.*player_stats.*where.*total_hands'
        ]

        # Check if query is trying to get overall pool statistics
        if ('avg(' in query_lower or 'count(' in query_lower) and 'player' in query_lower:
            # Multiple aggregations on player_stats usually means pool analysis
            if query_lower.count('avg(') >= 3 or query_lower.count('from player_stats') > 0:
                if 'group by player_name' not in query_lower:  # Not individual player analysis
                    return True

        # Check for explicit pool analysis patterns
        for pattern in pool_indicators:
            if re.search(pattern, query_lower):
                return True

        return False

    def _get_pool_analysis_data(self) -> Dict[str, Any]:
        """
        Get comprehensive pool analysis data using the optimized endpoint.

        Returns:
            Pool analysis data formatted as query results
        """
        try:
            # Import the pool analysis function
            from backend.api.pool_analysis_endpoints import get_comprehensive_pool_analysis

            # Get the comprehensive analysis
            analysis_data = get_comprehensive_pool_analysis(min_hands=100, db=self.db)

            # Format as query result for Claude
            # Create a flat structure that looks like query results
            formatted_results = []

            # Add pool overview as first row
            formatted_results.append({
                "analysis_type": "pool_overview",
                "total_players": analysis_data["pool_overview"]["total_players"],
                "avg_exploitability": analysis_data["pool_overview"]["average_composite_metrics"]["exploitability"],
                "avg_vpip": analysis_data["pool_overview"]["average_stats"]["vpip"],
                "avg_pfr": analysis_data["pool_overview"]["average_stats"]["pfr"],
                "avg_3bet": analysis_data["pool_overview"]["average_stats"]["3bet"],
                "pool_classification": analysis_data["summary"]["pool_classification"],
                "overall_skill_level": analysis_data["summary"]["overall_skill_level"],
                "best_exploit_angle": analysis_data["summary"]["best_exploit_angle"]
            })

            # Add player type distribution
            for player_type, count in analysis_data["player_type_distribution"].items():
                formatted_results.append({
                    "analysis_type": "player_type_distribution",
                    "player_type": player_type,
                    "count": count
                })

            # Add top exploitable players
            for player in analysis_data["top_exploitable_players"][:5]:
                formatted_results.append({
                    "analysis_type": "exploitable_player",
                    "player_name": player["player_name"],
                    "player_type": player["player_type"],
                    "exploitability_index": player["exploitability_index"],
                    "primary_weakness": player["primary_weakness"],
                    "vpip": player["key_stats"]["vpip"],
                    "pfr": player["key_stats"]["pfr"]
                })

            # Add common leaks
            for leak in analysis_data["common_gto_leaks"][:5]:
                formatted_results.append({
                    "analysis_type": "common_leak",
                    "scenario": leak["scenario"],
                    "position": leak["position"],
                    "pool_frequency": leak["pool_frequency"],
                    "gto_frequency": leak["gto_frequency"],
                    "deviation_percentage": leak["deviation_percentage"],
                    "exploit_recommendation": leak["exploit_recommendation"]
                })

            # Add recommended exploits
            for exploit in analysis_data["recommended_pool_exploits"]:
                formatted_results.append({
                    "analysis_type": "recommended_exploit",
                    "weakness": exploit["weakness"],
                    "exploit": exploit["exploit"],
                    "expected_profit": exploit["expected_profit"]
                })

            logger.info(f"Pool analysis data prepared with {len(formatted_results)} result rows")

            return {
                "success": True,
                "data": formatted_results,
                "row_count": len(formatted_results),
                "columns": list(formatted_results[0].keys()) if formatted_results else [],
                "note": "Comprehensive pool analysis data (optimized query)"
            }

        except Exception as e:
            logger.error(f"Error getting pool analysis data: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get pool analysis data: {str(e)}"
            }

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
            # Use prompt caching to save 90% on system prompt costs
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,  # Increased to allow complete analysis responses
                system=[
                    {
                        "type": "text",
                        "text": self._get_system_prompt(),
                        "cache_control": {"type": "ephemeral"}
                    }
                ],
                tools=[self._get_database_tool()],
                messages=messages
            )

            # Process response and handle tool calls (with recursive handling)
            final_text = ""
            tool_calls = []
            final_response = response  # Track the last response for usage stats
            max_iterations = 10  # Increased from 5 to allow complex analyses
            iteration = 0

            current_response = response
            while iteration < max_iterations:
                has_tool_call = False

                # Process all blocks in current response
                for block in current_response.content:
                    if block.type == "text":
                        # Add text to final output
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

                        # Always send tool result back to Claude (even on error)
                        messages.append({
                            "role": "assistant",
                            "content": current_response.content
                        })

                        # Format tool result content
                        if tool_result["success"]:
                            result_content = str(tool_result["data"])
                        else:
                            result_content = f"Error: {tool_result.get('error', 'Unknown error')}"

                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_content
                            }]
                        })

                        # Get followup response after tool use
                        current_response = self.client.messages.create(
                            model=self.model,
                            max_tokens=4096,
                            system=[
                                {
                                    "type": "text",
                                    "text": self._get_system_prompt(),
                                    "cache_control": {"type": "ephemeral"}
                                }
                            ],
                            tools=[self._get_database_tool()],
                            messages=messages
                        )

                        # Log what Claude responded with after receiving tool results
                        logger.info(f"Followup response has {len(current_response.content)} blocks")
                        for idx, block in enumerate(current_response.content):
                            if block.type == "text":
                                logger.info(f"Block {idx}: Text with {len(block.text)} chars")
                            elif block.type == "tool_use":
                                logger.info(f"Block {idx}: Tool use ({block.name})")

                        # Update final_response to track the last response for usage stats
                        final_response = current_response
                        break  # Exit for loop to process new response

                # If no tool calls were made, we're done
                if not has_tool_call:
                    break

                iteration += 1

            # After all iterations, make sure we captured any remaining text
            # This handles the case where Claude outputs analysis after all tool calls
            if current_response != response:  # If we have a different response than initial
                for block in current_response.content:
                    if block.type == "text" and block.text not in final_text:
                        # Add any text we haven't captured yet
                        final_text += self._clean_response_text(block.text)
                        logger.info(f"Added final text block: {len(block.text)} chars")

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

The gto_solutions table contains 40+ pre-computed GTO (Game Theory Optimal) solutions with **multi-level board categorization** for finding relevant scenarios. Use this to provide QUANTIFIED exploit recommendations with expected value calculations.

**Board Categorization System:**

Every GTO solution is categorized using a 3-level hierarchical system:

1. **Level 1 (board_category_l1)** - Broad categories (7 types):
   - "Ace-high", "King-high", "Queen-high", "Jack-or-Ten-high", "Nine-or-lower", "Paired", "Broadway"

2. **Level 2 (board_category_l2)** - Medium specificity (~20 types):
   - Adds texture: "Ace-high-rainbow", "Ace-high-two-tone", "King-high-connected", etc.

3. **Level 3 (board_category_l3)** - Fine-grained (~100 types):
   - Adds wetness: "Ace-high-rainbow-dry", "King-high-two-tone-wet", etc.

**Board Texture Properties (Boolean columns):**
- `is_paired` - Board has a pair (e.g., 77x, KK3)
- `is_rainbow` - Three different suits
- `is_two_tone` - Two cards same suit
- `is_monotone` - All same suit
- `is_connected` - At least one gap ≤1 rank
- `is_highly_connected` - Max gap ≤2 ranks
- `has_broadway` - Contains T, J, Q, K, or A
- `is_dry` - Low connectivity (max gap ≥3)
- `is_wet` - High connectivity (gaps ≤1)
- `high_card_rank`, `middle_card_rank`, `low_card_rank` - Individual card ranks

**Available GTO Scenarios (40+ solutions):**
- SRP (Single Raised Pot): K-high, A-high, Q-high, connected, dry, wet boards
- 3BP (3-Bet Pot): Various textures
- Multiple position contexts (IP/OOP)
- Various action sequences (cbet, check, raise)

**GTO Frequency Columns (All Solutions Have Complete Data):**
- `gto_check_frequency` - % of range that checks
- `gto_bet_frequency` - % of range that bets (all bet sizes combined)
- `gto_raise_frequency` - % of range that raises
- `gto_fold_frequency` - % of range that folds (when facing aggression)
- `gto_call_frequency` - % of range that calls

**How to Use GTO Analysis:**

1. **Find Relevant GTO Solutions by Board Type:**

   ```sql
   -- Find GTO frequencies for Ace-high rainbow boards
   SELECT scenario_name, board,
          gto_check_frequency, gto_bet_frequency,
          board_category_l3
   FROM gto_solutions
   WHERE board_category_l1 = 'Ace-high' AND is_rainbow = true
   ```

   **Real Example Output:**
   - A94r (Ace-high-rainbow-dry): check=90.80%, bet=9.20%
   - A62r (Ace-high-rainbow-dry): check=92.31%, bet=7.69%
   - AT3r (Ace-high-rainbow-dry): check=90.09%, bet=9.91%

2. **Compare Player Stats to GTO Frequencies:**

   ```sql
   -- Compare player's c-bet frequency to GTO on King-high boards
   SELECT
     ps.player_name,
     ps.cbet_flop_pct as player_cbet,
     AVG(gto.gto_bet_frequency) as gto_avg_bet,
     (ps.cbet_flop_pct - AVG(gto.gto_bet_frequency)) as deviation
   FROM player_stats ps
   CROSS JOIN gto_solutions gto
   WHERE ps.player_name = 'opponent'
     AND gto.board_category_l1 = 'King-high'
     AND gto.is_rainbow = true
   GROUP BY ps.player_name, ps.cbet_flop_pct
   ```

   **Example Result:**
   - Player c-bets: 78% on K-high boards
   - GTO average: 24% (based on K94r=26%, KT3r=22%, K62r=21%)
   - Deviation: +54% = **SEVERE OVERBET** (massively exploitable)

3. **Quantified Exploit Recommendations:**

   Based on deviations from GTO frequencies:
   - **Deviation +10 to +20%**: Moderate over-betting → Call lighter
   - **Deviation +20 to +40%**: Heavy over-betting → Raise as bluff-catch
   - **Deviation +40%+**: **SEVERE over-betting → Check-raise frequently**
   - **Deviation -10 to -20%**: Moderate under-betting → Barrel when checked to
   - **Deviation -20%+**: **SEVERE under-betting → Auto-barrel turn/river**
   - Deviations > 25% are EXTREME exploits

4. **Board-Specific Exploits:**
   ```sql
   -- Find which board textures player over-c-bets the most
   SELECT
     gto.board_category_l2,
     gto.board,
     ps.cbet_flop_pct,
     gto.gto_bet_frequency,
     (ps.cbet_flop_pct - gto.gto_bet_frequency) as deviation
   FROM player_stats ps
   CROSS JOIN gto_solutions gto
   WHERE ps.player_name = 'opponent'
   ORDER BY deviation DESC
   LIMIT 5
   ```

5. **Multi-Texture Pattern Analysis:**
   Use categorization to identify if player struggles with specific textures:
   - Paired vs Unpaired boards
   - Wet vs Dry boards
   - Rainbow vs Monotone boards
   - High-card vs Low-card boards

**IMPORTANT:** When asked about specific players or exploits, ALWAYS check gto_solutions table to provide GTO-based deviation analysis. This transforms vague advice into precise, quantified exploit recommendations.

## IMPORTANT: Pool Analysis Optimization

**For Pool Analysis, use this optimized workflow:**

Instead of making multiple individual queries, use ONE comprehensive query to get all pool data:

```sql
-- OPTIMAL: Get complete pool analysis in one query
SELECT 'Use the pool_analysis_comprehensive endpoint instead!' as recommendation;
-- This would normally require 6-10 separate queries
```

**Better approach - Query this special view that aggregates everything:**
```sql
-- Pool Analysis Super Query (contains all needed data)
SELECT * FROM (
    -- This represents the /pool-analysis/comprehensive endpoint data
    -- Returns: pool_overview, player_type_distribution, top_exploitable_players,
    -- common_gto_leaks, aggression_patterns, positional_tendencies, profit_distribution
    VALUES ('See pool_analysis_comprehensive endpoint for complete data')
) AS pool_data;
```

**When user asks for pool analysis, prioritize using:**
1. Query multiple related tables in ONE joined query when possible
2. Use CTEs (WITH clauses) to structure complex analysis
3. Get all needed data upfront rather than iterative queries

## Query Guidelines

1. **Always use the player_stats table** for player analysis - it contains all aggregated data
2. **Use GTO analysis for exploit quantification** - Compare player stats to gto_solutions for precise recommendations
3. **Use specific columns** - Don't SELECT * on large tables
4. **Filter wisely** - Use WHERE clauses to narrow results
5. **Sample size matters** - Check total_hands before drawing conclusions
6. **Combine metrics** - Use traditional stats + composite metrics + GTO deviations for complete analysis
7. **For Pool Analysis** - Try to get all data in minimal queries using JOINs and aggregations

## SQL Syntax Rules (CRITICAL!)

**Transaction Control:**
- **NEVER use COMMIT, BEGIN, ROLLBACK, or any transaction control statements** ❌
- Only use SELECT queries for reading data ✅
- The database connection handles transactions automatically
- Example: `SELECT ... FROM ...` (NO COMMIT at the end!)

**CROSS JOIN vs INNER JOIN:**
- `CROSS JOIN` creates a Cartesian product with NO join condition (no ON clause)
- Use `CROSS JOIN` only when joining single-row results (e.g., one GTO scenario)
- Example: `FROM player_stats ps CROSS JOIN gto_solutions gto WHERE gto.scenario_name = 'SRP_Ks7c3d_cbet'`

- For conditional joins, use `INNER JOIN ... ON` or `LEFT JOIN ... ON`
- Example: `FROM table1 t1 INNER JOIN table2 t2 ON t1.id = t2.id`

**NEVER write:**
- `CROSS JOIN table ON condition` ❌ (SYNTAX ERROR!)
- `SELECT ... ; COMMIT;` ❌ (NO TRANSACTION CONTROL!)
- Always use: `CROSS JOIN table` (filter with WHERE) ✅
- Or use: `INNER JOIN table ON condition` ✅
- Just: `SELECT ...` (no COMMIT/BEGIN/ROLLBACK) ✅

## Response Format

**CRITICAL: Always format your responses using Markdown for better readability!**

**MANDATORY RULES - NEVER VIOLATE THESE:**
1. **ALWAYS show query results** - If you say "Let me analyze..." you MUST show the actual data
2. **Never leave analysis incomplete** - If you start, you MUST finish with results
3. **If a query fails, state it explicitly** - Say "Query failed: [error]" don't pretend you have data
4. **If no data found, say so** - "No data found for X" - don't continue without data
5. **Show concrete numbers first** - Display actual statistics before interpreting them

**AFTER EACH QUERY COMPLETES:**
- IMMEDIATELY display the key findings from that query
- Show actual numbers, counts, percentages
- Use tables or lists to organize the data
- ONLY THEN move to the next query
- Never say "Now let me..." without first showing results from the previous query

When answering queries:
1. **Query the database** using the query_database tool
2. **IMMEDIATELY show key findings** - Display the data/numbers you found
3. **Then interpret the results** in poker strategy terms - **DO NOT include raw function results in your response**
4. **Format your response with Markdown**:
   - Use **## Headers** for main sections (e.g., "## Player Analysis", "## Key Statistics")
   - Use **### Subheaders** for subsections (e.g., "### Exploitable Weaknesses")
   - Use **tables** for statistical comparisons (player vs GTO)
   - Use **bullet lists** for recommendations and key points
   - Use **bold** for important stats and player names
   - Use `inline code` for specific stat names and values
4. **Structure your responses** with clear sections:
   - Start with a brief summary
   - Show key statistics in a table format when comparing multiple values
   - List exploits as bullet points with clear action items
   - End with tactical recommendations
5. **Consider sample size** - warn if total_hands < 100
6. **Be specific** - cite exact statistics and metrics
7. **Think exploitatively** - how to profit from these tendencies?

**Example Response Format:**

```markdown
## Player Analysis: [PlayerName]

**Player Type:** TAG | **Sample Size:** 500 hands ✅

### Key Statistics

| Stat | Player | Optimal | Deviation |
|------|--------|---------|-----------|
| VPIP | 32% | 20-25% | +10% 🔴 |
| PFR | 24% | 15-20% | +6% 🟡 |

### Exploitable Weaknesses

1. **Over-aggressive preflop** - VPIP 10% above optimal
   - *Exploit:* Call their opens wider, trap with premium hands

2. **High fold to 3-bet** (68%)
   - *Exploit:* 3-bet them liberally with wide range

### GTO Deviations

**K-high board (Ks7c3d):**
- Player c-bets: `78%` vs GTO: `58%` = **+20% deviation** 🔴
- *Exploit:* Call and raise their c-bets more often

### Tactical Recommendations

- ✅ 3-bet them frequently from late position
- ✅ Call down lighter against their c-bets
- ✅ Trap with strong hands rather than fast-playing
```

**IMPORTANT:** Never include raw function results or SQL query outputs in your response. Extract the relevant data and present it in formatted Markdown tables and lists.

**BAD EXAMPLE (What you're doing wrong):**
"Let me analyze the player pool..."
"Now let me check exploitability..."
"Let me identify patterns..."
[Never shows any actual results]

**GOOD EXAMPLE (What you should do):**
"Let me analyze the player pool..."
[Query executes]

## Player Pool Analysis

**Total players analyzed:** 47
**Average exploitability:** 62.3
**Most common player type:** LAG (18 players)

### Top 3 Most Exploitable Players:
1. **Villain1** - Exploitability: 89.2 (FISH)
2. **Hero2** - Exploitability: 84.7 (MANIAC)
3. **Player3** - Exploitability: 78.9 (CALLING_STATION)

[Then continues with interpretation and recommendations]

## Example Queries

**Traditional Analysis:**
- "Show me all players with high exploitability" → SELECT player_name, exploitability_index, player_type FROM player_stats WHERE exploitability_index > 60 ORDER BY exploitability_index DESC
- "Find TAGs who fold too much to pressure" → SELECT player_name, vpip_pct, pfr_pct, pressure_vulnerability_score FROM player_stats WHERE player_type = 'TAG' AND pressure_vulnerability_score > 60
- "Who gives up on later streets?" → SELECT player_name, aggression_consistency_ratio, multi_street_persistence_score FROM player_stats WHERE aggression_consistency_ratio < 40

**GTO Deviation Analysis with Board Categorization (USE THIS!):**
- "How does player X play on Ace-high boards?" → SELECT gto.board, gto.board_category_l3, ps.cbet_flop_pct, gto.gto_bet_frequency, (ps.cbet_flop_pct - gto.gto_bet_frequency) as deviation FROM player_stats ps CROSS JOIN gto_solutions gto WHERE ps.player_name = 'X' AND gto.board_category_l1 = 'Ace-high'
- "Find board textures where player over-c-bets" → SELECT gto.board_category_l2, gto.is_wet, gto.is_paired, AVG(ps.cbet_flop_pct - gto.gto_bet_frequency) as avg_deviation FROM player_stats ps CROSS JOIN gto_solutions gto WHERE ps.player_name = 'X' GROUP BY gto.board_category_l2, gto.is_wet, gto.is_paired HAVING AVG(ps.cbet_flop_pct - gto.gto_bet_frequency) > 10
- "Does player struggle more on wet or dry boards?" → SELECT CASE WHEN is_wet THEN 'Wet' WHEN is_dry THEN 'Dry' ELSE 'Medium' END as texture, AVG(ps.cbet_flop_pct - gto.gto_bet_frequency) as avg_deviation FROM player_stats ps CROSS JOIN gto_solutions gto WHERE ps.player_name = 'X' GROUP BY is_wet, is_dry
- "Show all GTO scenarios by board category" → SELECT board_category_l1, board_category_l2, COUNT(*) as count FROM gto_solutions GROUP BY board_category_l1, board_category_l2 ORDER BY board_category_l1

## GTO Preflop Analysis (NEW - GTOWizard Data!)

You now have access to **127 preflop GTO scenarios** from GTOWizard, covering complete preflop strategy across all positions.

**Available Data:**
- Opening ranges (UTG, MP, CO, BTN, SB)
- BB/SB defense vs all positions (fold/call/3bet frequencies)
- IP cold calls (CO, BTN facing opens)
- Facing 3bets (fold/call/4bet/allin) - all positions
- Facing 4bets (fold/call/5bet/allin)
- Multiway scenarios (squeezes, overcalls)

**New Tables for Preflop GTO:**

7. **gto_scenarios** - Preflop scenario metadata
   - scenario_id, scenario_name, street, category, position, action, opponent_position
   - Example rows: 'BB_vs_UTG_call', 'UTG_open', 'CO_vs_BTN_3bet_4bet'

8. **gto_frequencies** - Hand-level GTO frequencies
   - frequency_id, scenario_id, hand, position, frequency
   - Example: (BB_vs_UTG_call, AKo, BB, 0.395) = call AKo 39.5% in BB vs UTG

9. **player_gto_stats** - Aggregated preflop leak statistics per player ⭐ PRIMARY TABLE FOR PREFLOP ANALYSIS
   - player_name, scenario_id, total_hands, player_frequency, gto_frequency, frequency_diff
   - leak_type, leak_severity, total_ev_loss_bb, avg_ev_loss_bb
   - **IMPORTANT**: This is the MAIN table for finding preflop leaks. Always JOIN with gto_scenarios to get scenario details.

**Preflop GTO Query Examples:**

1. **Get GTO frequency for specific hand/scenario:**
   ```sql
   -- How often should I call with AKo in BB vs UTG?
   SELECT gf.frequency, gf.frequency * 100 as percentage
   FROM gto_frequencies gf
   JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
   WHERE gs.scenario_name = 'BB_vs_UTG_call' AND gf.hand = 'AKo' AND gf.position = 'BB';
   ```
   **Result:** 0.395 (39.5% call, 60.5% 3bet or fold)

2. **Get full action breakdown for a hand:**
   ```sql
   -- What should I do with AKo in BB vs UTG?
   SELECT gs.action, gf.frequency * 100 as percentage
   FROM gto_frequencies gf
   JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
   WHERE gs.position = 'BB' AND gs.opponent_position = 'UTG'
     AND gf.hand = 'AKo' AND gf.position = 'BB'
   ORDER BY gf.frequency DESC;
   ```
   **Result:** call=39.5%, 3bet=60.5%, fold=0%

3. **Get opening range for position:**
   ```sql
   -- Show UTG opening range (hands opened >50%)
   SELECT gf.hand, gf.frequency * 100 as open_pct
   FROM gto_frequencies gf
   JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
   WHERE gs.scenario_name = 'UTG_open' AND gf.frequency >= 0.5
   ORDER BY gf.frequency DESC;
   ```

4. **Find player's preflop leaks (MOST COMMON QUERY):**
   ```sql
   -- What are player's biggest preflop leaks?
   SELECT gs.scenario_name, gs.position, gs.action, gs.opponent_position,
          pgs.total_hands,
          pgs.player_frequency * 100 as player_pct,
          pgs.gto_frequency * 100 as gto_pct,
          pgs.frequency_diff * 100 as diff_pct,
          pgs.total_ev_loss_bb,
          pgs.leak_type,
          pgs.leak_severity
   FROM player_gto_stats pgs
   JOIN gto_scenarios gs ON pgs.scenario_id = gs.scenario_id
   WHERE pgs.player_name = 'snajd' AND pgs.total_hands >= 10
   ORDER BY pgs.total_ev_loss_bb DESC
   LIMIT 10;
   ```

   **Note:** Multiply frequency values by 100 to get percentages for display.

5. **Calculate preflop GTO adherence:**
   ```sql
   -- How well does player follow GTO preflop?
   SELECT
     pgs.player_name,
     COUNT(*) as scenarios_analyzed,
     SUM(pgs.total_hands) as total_hands,
     AVG(pgs.avg_ev_loss_bb) as avg_ev_loss_per_hand,
     SUM(pgs.total_ev_loss_bb) as total_bb_lost,
     COUNT(CASE WHEN pgs.leak_severity IN ('major', 'critical') THEN 1 END) as major_leaks
   FROM player_gto_stats pgs
   JOIN gto_scenarios gs ON pgs.scenario_id = gs.scenario_id
   WHERE pgs.player_name = 'Hero' AND gs.street = 'preflop'
   GROUP BY pgs.player_name;
   ```

6. **Find exploitable patterns:**
   ```sql
   -- Find scenarios where player deviates significantly from GTO
   SELECT gs.scenario_name,
          pgs.frequency_diff * 100 as deviation_pct,
          pgs.leak_type,
          pgs.leak_severity,
          pgs.total_ev_loss_bb,
          pgs.total_hands
   FROM player_gto_stats pgs
   JOIN gto_scenarios gs ON pgs.scenario_id = gs.scenario_id
   WHERE pgs.player_name = 'snajd'
     AND ABS(pgs.frequency_diff) > 0.10  -- Deviation >10%
     AND pgs.total_hands >= 10  -- Sufficient sample size
   ORDER BY ABS(pgs.frequency_diff) DESC
   LIMIT 10;
   ```

**Interpreting Preflop GTO Frequencies:**
- **Frequency = 0.0:** Never take this action (GTO always folds/calls/3bets instead)
- **Frequency = 1.0:** Always take this action (GTO pure strategy)
- **Frequency 0.0-1.0:** Mixed strategy (randomize to remain unexploitable)

**Leak Types:**
- **undercall:** Player doesn't call enough (e.g., folds too much in BB) → Open wider vs them
- **overcall:** Player calls too much → Bluff more on later streets
- **under3bet:** Player doesn't 3bet enough → Open wider, flat more vs their 3bets
- **over3bet:** Player 3bets too much → Call down lighter, 4bet bluff
- **overfold:** Player folds too much to aggression → Bet/raise more
- **underfold:** Player doesn't fold enough → Value bet thinner

**Exploit Recommendations Based on Frequency Deviations:**
- **Deviation +10 to +20%:** Moderate leak → Adjust moderately
- **Deviation +20 to +40%:** Major leak → Exploit aggressively
- **Deviation +40%+:** Critical leak → Extreme exploitation (massive EV)
- Deviations >10% are significant, >25% are extreme exploits

**When analyzing preflop play, ALWAYS:**
1. Query gto_frequencies to show what GTO recommends
2. If player data exists in player_gto_stats, compare to identify leaks
3. Translate frequency deviations into specific exploits
4. Calculate expected value of exploits (exploit_value_bb_100)

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
            # Clean the query: remove transaction control statements
            import re
            # Remove COMMIT, BEGIN, ROLLBACK statements (case-insensitive)
            cleaned_query = re.sub(r';\s*(COMMIT|BEGIN|ROLLBACK|START\s+TRANSACTION)\s*;?\s*$', '', query, flags=re.IGNORECASE)
            cleaned_query = cleaned_query.strip()

            # Security: Only allow SELECT statements
            query_upper = cleaned_query.upper()
            if not query_upper.startswith("SELECT"):
                return {
                    "success": False,
                    "error": "Only SELECT queries are allowed for security reasons. Do not use COMMIT, BEGIN, ROLLBACK, or other transaction control statements."
                }

            # Special handling for pool analysis queries
            # Detect if this is a comprehensive pool analysis request
            if self._is_pool_analysis_query(cleaned_query):
                logger.info("Detected pool analysis query, using optimized endpoint")
                return self._get_pool_analysis_data()

            # Execute query
            result = self.db.execute(text(cleaned_query))

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
            # Rollback the session to clear the failed transaction state
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
