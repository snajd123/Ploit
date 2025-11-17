# Claude AI Integration

This document describes the Claude AI integration for natural language poker analysis.

## Overview

The Claude integration provides a natural language interface to the poker database, allowing users to ask ANY question about their poker data and receive sophisticated statistical analysis and strategic recommendations.

## Architecture

### ClaudeService (`claude_service.py`)

The core service that:
- Connects to Anthropic's Claude API
- Provides database query tool for Claude
- Manages conversation flow and tool execution
- Returns analyzed results with strategic insights

### Key Components

1. **Database Query Tool**
   - Claude can execute SELECT queries on the database
   - Security: Only SELECT statements allowed
   - Returns formatted results for Claude to analyze

2. **System Prompt**
   - Provides poker domain expertise
   - Describes all database tables and schemas
   - Explains the 12 composite metrics and interpretations
   - Defines player type classifications (NIT, TAG, LAG, etc.)
   - Establishes strategic framework for exploit recommendations

3. **Query Handler**
   - Processes natural language user queries
   - Handles tool calling workflow
   - Manages conversation history for context
   - Returns formatted responses

## API Endpoint

### POST /api/query/claude

Ask natural language questions about poker data.

**Request Body:**
```json
{
  "query": "Who are the most exploitable players at NL50?",
  "conversation_history": [
    {
      "role": "user",
      "content": "Previous question..."
    },
    {
      "role": "assistant",
      "content": "Previous response..."
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "response": "Based on the database analysis, here are the most exploitable players at NL50:\n\n1. **Player123** (EI: 78.5)\n   - Type: CALLING_STATION\n   - Pressure Vulnerability Score: 82.3\n   - **Exploit**: This player folds too much under pressure. Triple barrel bluff frequently...\n\n2. **FishyMcFish** (EI: 85.2)\n   - Type: FISH\n   - Value-Bluff Imbalance: High value bias\n   - **Exploit**: This player rarely bluffs. You can fold confidently to their aggression...",
  "tool_calls": [
    {
      "tool": "query_database",
      "input": {
        "query": "SELECT player_name, exploitability_index, player_type, pressure_vulnerability_score FROM player_stats WHERE stake_level = 'NL50' AND exploitability_index > 60 ORDER BY exploitability_index DESC LIMIT 10"
      },
      "result": {
        "success": true,
        "data": [...],
        "row_count": 10
      }
    }
  ],
  "usage": {
    "input_tokens": 1250,
    "output_tokens": 450
  }
}
```

## Example Queries

### Finding Exploitable Players

**Query:** "Who are the most exploitable players with at least 500 hands?"

Claude will:
1. Query player_stats table filtering by total_hands and exploitability_index
2. Analyze composite metrics (PVS, ACR, VBIR, etc.)
3. Provide specific exploit recommendations for each player

### Player Type Analysis

**Query:** "Show me all LAG players who give up too easily on later streets"

Claude will:
1. Filter by player_type = 'LAG'
2. Look at multi_street_persistence_score and aggression_consistency_ratio
3. Recommend barreling strategy

### Positional Exploitation

**Query:** "Which players don't adjust for position and can be exploited from the button?"

Claude will:
1. Analyze positional_awareness_index
2. Look at blind_defense_efficiency for blind play
3. Recommend stealing and 3-bet bluffing strategies

### Head-to-Head Analysis

**Query:** "Analyze the playing style of PlayerName and tell me how to beat them"

Claude will:
1. Get complete stats for the specific player
2. Interpret all composite metrics
3. Classify player type
4. Provide comprehensive exploit strategy

## Database Schema Access

Claude has complete knowledge of:

### player_stats table (Primary)
- **Traditional Stats**: vpip_pct, pfr_pct, three_bet_pct, fold_to_three_bet_pct, cbet_flop_pct, fold_to_cbet_flop_pct, wtsd_pct, wsd_pct, etc.
- **Composite Metrics**: All 12 metrics with interpretations
- **Classification**: player_type (NIT, TAG, LAG, CALLING_STATION, MANIAC, FISH)

### Other tables
- **raw_hands**: Complete hand history text
- **hand_actions**: Every action with pot sizes
- **player_hand_summary**: 60+ boolean flags per hand
- **upload_sessions**: Upload tracking

## 12 Composite Metrics Interpretation

Claude understands the strategic implications of each metric:

1. **Exploitability Index (0-100)**: Overall exploitability
   - 0-20: Tough opponent
   - 60-80: Highly exploitable
   - 80-100: Major leaks

2. **Pressure Vulnerability Score**: Fold frequency under pressure
   - High = attack with bluffs

3. **Aggression Consistency Ratio**: Give-up tendency
   - Low = barrel them on later streets

4. **Positional Awareness Index**: Position adjustment quality
   - Low = exploit with position

5. **Blind Defense Efficiency**: Blind defense quality
   - Low = steal their blinds

6. **Value-Bluff Imbalance Ratio**: Range balance
   - High = too value-heavy, bluff more
   - Low = bluffs too much, call down

7. **Range Polarization Factor**: Bet sizing tells
   - Extreme values = predictable sizing

8. **Street-by-Street Fold Gradient**: Folding patterns
   - Identifies which streets to attack

9. **Delayed Aggression Coefficient**: Trapping frequency
   - Low = bet when checked to

10. **Player Type**: General framework
    - Strategic approach per type

11. **Multi-Street Persistence Score**: Commitment across streets
    - Low = folds too much on later streets

12. **Optimal Stake Skill Rating**: Skill vs stake mismatch
    - Identifies players at wrong stakes

## Player Type Classifications

Claude uses these classifications as strategic frameworks:

- **NIT**: VPIP < 18%, tight/passive → Steal blinds, attack limp/calls
- **TAG**: VPIP 18-25%, PFR 15-22%, balanced → Respect aggression, exploit marginal spots
- **LAG**: VPIP 25-35%, PFR 20-30%, aggressive → Call down lighter, trap more
- **CALLING_STATION**: High VPIP, low PFR → Value bet thin, don't bluff
- **MANIAC**: VPIP > 45%, PFR > 35% → Let them bluff, call down wide
- **FISH**: High EI, unbalanced → Exploit primary leaks

## Security

- Only SELECT queries allowed (no INSERT, UPDATE, DELETE)
- SQL injection protection via parameterized queries
- Rate limiting recommended for production
- API key required for Anthropic access

## Configuration

Set in `.env`:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Usage in Code

```python
from backend.services import ClaudeService
from backend.database import get_db

db = next(get_db())
claude = ClaudeService(db)

result = claude.query("Who are the most exploitable TAGs?")
print(result["response"])
```

## Error Handling

The service handles:
- Invalid SQL queries
- Database connection errors
- API rate limits
- Malformed requests
- Tool execution failures

All errors return user-friendly messages while logging technical details.

## Performance Considerations

- Database queries are executed by Claude as needed
- Results cached within conversation context
- Token usage tracked and returned
- Recommend limiting query complexity for large databases

## Future Enhancements

Potential improvements:
- Conversation memory/session management
- Query result caching
- Advanced filtering and aggregation helpers
- Multi-player comparison tools
- Hand replay analysis with Claude commentary
- Automated exploit report generation
