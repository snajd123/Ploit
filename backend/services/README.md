# Database Service Layer

Service layer for all database operations in the poker analysis app.

## Overview

The `DatabaseService` class provides a clean interface for:
- Inserting parsed hands into the database
- Calculating and updating player statistics
- Querying player data
- Tracking upload sessions

## Architecture

```
Parser → Database Service → PostgreSQL
  ↓           ↓                  ↓
Hand     Insert/Update      raw_hands
objects  Calculate Stats    hand_actions
                           player_hand_summary
                           player_stats
                           upload_sessions
```

## Usage

### Initialize Service

```python
from backend.database import get_db
from backend.services import DatabaseService

# Get database session
db = next(get_db())

# Create service instance
service = DatabaseService(db)
```

### Insert Hands

```python
from backend.parser import PokerStarsParser

# Parse hands
parser = PokerStarsParser()
result = parser.parse_file("hands.txt")

# Insert into database
insert_result = service.insert_hand_batch(result.hands)

print(f"Inserted: {insert_result['hands_inserted']}")
print(f"Failed: {insert_result['hands_failed']}")
```

### Update Player Statistics

```python
# Update single player
service.update_player_stats("Player1")

# Update all players
result = service.update_all_player_stats()
print(f"Updated {result['players_updated']} players")
```

### Query Player Data

```python
# Get specific player
stats = service.get_player_stats("Player1")
if stats:
    print(f"VPIP: {stats['vpip_pct']}%")
    print(f"PFR: {stats['pfr_pct']}%")
    print(f"Hands: {stats['total_hands']}")

# Get all players
players = service.get_all_players(
    min_hands=100,
    order_by='total_hands',
    limit=50
)
```

### Database Overview

```python
stats = service.get_database_stats()
print(f"Total hands: {stats['total_hands']}")
print(f"Total players: {stats['total_players']}")
print(f"Date range: {stats['first_hand_date']} to {stats['last_hand_date']}")
```

## Core Methods

### Hand Insertion

#### `insert_hand(hand: Hand) -> bool`
Insert a single parsed hand.

Inserts into:
- `raw_hands`: Complete hand history text
- `hand_actions`: All player actions
- `player_hand_summary`: Boolean flags for each player

Returns `True` if successful, `False` if hand already exists.

#### `insert_hand_batch(hands: List[Hand]) -> Dict`
Insert multiple hands atomically.

Returns dictionary with:
- `hands_inserted`: Number successfully inserted
- `hands_failed`: Number that failed
- `error_details`: List of error messages

### Statistics Calculation

#### `update_player_stats(player_name: str) -> bool`
Recalculate all statistics for a single player.

Process:
1. Query all `player_hand_summary` records for player
2. Calculate traditional statistics (VPIP%, PFR%, etc.)
3. Calculate positional statistics
4. Calculate postflop statistics
5. Update or create `player_stats` record
6. (Composite metrics calculated in Phase 4)

#### `_calculate_traditional_stats(summaries: List) -> Dict`
Internal method that converts boolean flags to percentages.

Calculates:
- **Preflop**: VPIP%, PFR%, 3-bet%, 4-bet%, limp%, etc.
- **Positional**: VPIP by position (UTG, HJ, MP, CO, BTN, SB, BB)
- **Postflop**: Cbet%, fold to cbet%, check-raise%, etc.
- **Showdown**: WTSD%, W$SD%
- **Results**: Total profit/loss

#### `update_all_player_stats() -> Dict`
Update statistics for all players in the database.

Returns:
- `players_updated`: Number of players updated

### Query Functions

#### `get_player_stats(player_name: str) -> Optional[Dict]`
Retrieve complete player statistics.

Returns dictionary with all stats or `None` if player not found.

#### `get_all_players(...) -> List[Dict]`
Get all players matching criteria.

Parameters:
- `min_hands`: Minimum number of hands (default: 100)
- `stake_level`: Filter by stakes (optional)
- `order_by`: Sort column (default: 'total_hands')
- `limit`: Max results (default: 100)

#### `get_database_stats() -> Dict`
Get database overview statistics.

Returns:
- `total_hands`: Total hands in database
- `total_players`: Total players tracked
- `first_hand_date`: Oldest hand date
- `last_hand_date`: Newest hand date

### Upload Session Tracking

#### `create_upload_session(...) -> int`
Create an upload session record for audit trail.

Parameters:
- `filename`: Original filename
- `hands_parsed`: Number successfully parsed
- `hands_failed`: Number that failed
- `players_updated`: Number of players updated
- `stake_level`: Stakes of hands (optional)
- `processing_time`: Time in seconds (optional)
- `error_message`: Error details (optional)

Returns session ID.

## Statistics Calculated

### Preflop Statistics
- **VPIP%**: Voluntarily Put money In Pot
- **PFR%**: Preflop Raise frequency
- **Limp%**: Limp frequency
- **3-bet%**: 3-bet frequency (when facing raise)
- **Fold to 3-bet%**: Fold frequency when facing 3-bet
- **4-bet%**: 4-bet frequency (when facing 3-bet)
- **Cold call%**: Cold call frequency
- **Squeeze%**: Squeeze play frequency

### Positional VPIP
- VPIP% for each position: UTG, HJ, MP, CO, BTN, SB, BB

### Steal & Blind Defense
- **Steal attempt%**: Steal attempt frequency from late position
- **Fold to steal%**: Fold frequency in blinds vs steal
- **3-bet vs steal%**: 3-bet frequency vs steal

### Continuation Betting
- **Cbet flop%**: Flop cbet frequency (when opportunity)
- **Cbet turn%**: Turn cbet frequency
- **Cbet river%**: River cbet frequency

### Facing Continuation Bets
- **Fold to cbet [street]%**: Fold frequency vs cbet
- **Call cbet [street]%**: Call frequency vs cbet
- **Raise cbet [street]%**: Raise frequency vs cbet

### Check-Raise
- **Check-raise [street]%**: Check-raise frequency by street

### Other Actions
- **Donk bet [street]%**: Donk bet frequency
- **Float flop%**: Float play frequency

### Showdown
- **WTSD%**: Went To ShowDown (% of hands that saw flop)
- **W$SD%**: Won $ at ShowDown (% of showdowns won)

### Results
- **Total profit/loss**: Total winnings/losses
- **BB/100**: Big blinds per 100 hands (calculated from stakes)

## Stat Calculation Logic

### Percentage Calculation

```python
# Example: VPIP%
vpip_count = count_hands_where(vpip=True)
total_hands = count_all_hands()
vpip_pct = (vpip_count / total_hands) * 100
```

### Conditional Percentages

```python
# Example: Cbet%
cbet_opportunities = count_hands_where(cbet_opportunity_flop=True)
cbets_made = count_hands_where(cbet_made_flop=True)
cbet_pct = (cbets_made / cbet_opportunities) * 100 if cbet_opportunities > 0 else None
```

### Positional Stats

```python
# Example: VPIP by position
utg_hands = get_hands_where(position='UTG')
utg_vpip_hands = count_where(position='UTG' AND vpip=True)
vpip_utg = (utg_vpip_hands / len(utg_hands)) * 100 if utg_hands else None
```

## Error Handling

The service includes comprehensive error handling:

- **Duplicate hands**: Returns `False` from `insert_hand()`, logs warning
- **Database errors**: Rolls back transaction, raises `SQLAlchemyError`
- **Missing data**: Returns `None` for stats, logs warning
- **Invalid queries**: Returns empty list/dict, logs error

## Transaction Management

All mutations use proper transaction handling:

```python
try:
    # Database operations
    self.session.add(record)
    self.session.commit()
    return True
except SQLAlchemyError as e:
    self.session.rollback()
    logger.error(f"Error: {e}")
    raise
```

## Performance Considerations

### Batch Operations
- Use `insert_hand_batch()` for multiple hands (more efficient than loops)
- Batch size recommendation: 100-1000 hands per batch

### Stat Updates
- Update stats after each upload session, not per-hand
- Use `update_all_player_stats()` sparingly (expensive for large databases)
- Consider updating only affected players

### Query Optimization
- Use `limit` parameter to avoid loading entire table
- Add indexes on frequently queried columns (already in schema)
- Consider pagination for large result sets

## Integration with Parser

Complete workflow:

```python
from backend.parser import PokerStarsParser
from backend.services import DatabaseService
from backend.database import get_db

# 1. Parse hands
parser = PokerStarsParser()
parse_result = parser.parse_file("hands.txt")

# 2. Insert into database
db = next(get_db())
service = DatabaseService(db)
insert_result = service.insert_hand_batch(parse_result.hands)

# 3. Update player stats
affected_players = set()
for hand in parse_result.hands:
    affected_players.update(hand.player_flags.keys())

for player in affected_players:
    service.update_player_stats(player)

# 4. Create upload session
session_id = service.create_upload_session(
    filename="hands.txt",
    hands_parsed=insert_result['hands_inserted'],
    hands_failed=insert_result['hands_failed'],
    players_updated=len(affected_players)
)

print(f"Upload complete. Session ID: {session_id}")
```

## Future Enhancements

- [ ] Implement AF (Aggression Factor) calculation
- [ ] Implement AFQ (Aggression Frequency) calculation
- [ ] Add BB/100 calculation based on stake level
- [ ] Implement stake-level filtering in `get_all_players()`
- [ ] Add pagination support for large queries
- [ ] Optimize batch insert performance
- [ ] Add caching layer for frequently accessed stats

## Testing

Tests will be created in Phase 8 (Integration & Testing).

For now, the service can be validated by:
1. Parsing sample hands
2. Inserting into test database
3. Verifying records created
4. Checking stat calculations manually
