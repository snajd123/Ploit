# Development Rules for Poker Analysis App

## Critical Rules - Must Follow

### 1. NO UNAUTHORIZED CHANGES
**RULE**: You MUST ask for approval before making ANY of the following changes:
- Adding new features not in POKER_APP_PROJECT_PLAN.md
- Removing planned features from the project plan
- Changing the database schema (adding/removing tables or columns)
- Modifying the 12 composite metric formulas
- Changing the technology stack (switching frameworks, databases, etc.)
- Altering the API endpoint structure
- Adding new third-party dependencies not listed in the plan

**Why**: The project plan is the single source of truth. Deviations must be approved.

**If you think a change is needed**: 
1. Stop immediately
2. Explain why the change is necessary
3. Wait for explicit approval before proceeding

---

### 2. STRUCTURED STEP-BY-STEP DEVELOPMENT
**RULE**: Follow the development phases EXACTLY as outlined in the project plan.

**Required Order**:
1. Phase 1: Database Setup (complete before moving on)
2. Phase 2: Hand History Parser (complete and tested)
3. Phase 3: Database Service (complete and tested)
4. Phase 4: Statistical Calculator (complete and tested)
5. Phase 5: FastAPI Backend (complete and tested)
6. Phase 6: Claude Integration (complete and tested)
7. Phase 7: Frontend Development (complete and tested)
8. Phase 8: Integration & Testing
9. Phase 9: Deployment
10. Phase 10: Documentation

**At the end of each phase**:
- Report what was completed
- Confirm all tests pass
- Ask for approval to proceed to next phase
- **DO NOT** skip ahead or work on multiple phases simultaneously

**Why**: This ensures each component is solid before building on top of it.

---

### 3. NO MOCK DATA OR TEMPORARY SETUPS
**RULE**: Build everything for production from day one. No placeholders, no mock data, no temporary solutions.

**Forbidden practices**:
❌ Mock data generators or fake hand histories
❌ Hardcoded test values in production code
❌ "TODO: implement this later" comments
❌ Temporary database structures that need migration
❌ Dev-only endpoints or features
❌ Placeholder UI components
❌ Commented-out code "for future use"

**Required practices**:
✅ Real PostgreSQL database from start (cloud-hosted)
✅ Proper error handling from day one
✅ Production-ready code quality
✅ Complete implementations only
✅ Environment variables for all configuration
✅ Secure practices (no hardcoded secrets, SQL injection prevention)

**Why**: Rebuilding "temporary" solutions wastes time. Build it right the first time.

---

### 4. VERSION CONTROL REQUIREMENTS
**RULE**: Use Git with proper commit discipline throughout development.

**Git workflow**:
1. Initialize git repository at project start
2. Create `.gitignore` immediately (exclude .env, node_modules, __pycache__, etc.)
3. Commit after completing each logical unit of work
4. Write clear, descriptive commit messages

**Commit message format**:
```
[Component] Brief description of what was done

- Detailed point 1
- Detailed point 2

Related to: Phase X of project plan
```

**Examples of good commits**:
```
[Database] Create all 5 database tables with indexes

- Added raw_hands table with hand_id primary key
- Added hand_actions table with foreign key to raw_hands
- Added player_hand_summary with boolean flags
- Added player_stats with traditional + composite metrics
- Added upload_sessions for tracking imports
- Created indexes for performance

Related to: Phase 1 (Database Setup)
```

```
[Parser] Implement PokerStars preflop action parsing

- Extract raises, calls, folds from preflop section
- Calculate pot sizes after each action
- Identify preflop aggressor for cbet tracking
- Handle edge cases: limps, multiple raises, all-ins
- Added unit tests for 10 different hand scenarios

Related to: Phase 2 (Hand History Parser)
```

**Branch strategy**:
- `main` branch: Always working, production-ready code
- `develop` branch: Integration branch for completed features
- Feature branches: `feature/parser`, `feature/stats-calculator`, etc.
- Merge to develop only when feature is complete and tested
- Merge to main only at the end of each phase

**Why**: Version control provides safety, enables rollback, and tracks progress.

---

### 5. CODE QUALITY STANDARDS
**RULE**: All code must meet production quality standards.

**Required practices**:
✅ **Type hints**: All Python functions must have type hints
✅ **Docstrings**: Every function/class must have clear docstring
✅ **Error handling**: Try/except blocks with specific exception handling
✅ **Logging**: Use proper logging (not print statements) with appropriate levels
✅ **Validation**: Input validation on all API endpoints
✅ **SQL injection prevention**: Use parameterized queries only
✅ **Constants**: Magic numbers/strings extracted to named constants
✅ **DRY principle**: No code duplication
✅ **Single responsibility**: Each function does one thing

**Example of acceptable code**:
```python
from typing import Optional, List
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def calculate_exploitability_index(
    vpip: Decimal, 
    pfr: Decimal, 
    fold_to_3bet: Decimal,
    cbet_flop: Decimal,
    cbet_turn: Decimal,
    wtsd: Decimal,
    wsd: Decimal
) -> Optional[Decimal]:
    """
    Calculate Exploitability Index from player statistics.
    
    Formula: EI = (Preflop_Score × 0.35) + (Postflop_Score × 0.40) + (Showdown_Score × 0.25)
    
    Args:
        vpip: Voluntarily Put In Pot percentage (0-100)
        pfr: Preflop Raise percentage (0-100)
        fold_to_3bet: Fold to 3-bet percentage (0-100)
        cbet_flop: Continuation bet flop percentage (0-100)
        cbet_turn: Continuation bet turn percentage (0-100)
        wtsd: Went to showdown percentage (0-100)
        wsd: Won at showdown percentage (0-100)
        
    Returns:
        Exploitability Index (0-100) or None if insufficient data
        
    Raises:
        ValueError: If any percentage is outside 0-100 range
    """
    try:
        # Input validation
        stats = [vpip, pfr, fold_to_3bet, cbet_flop, cbet_turn, wtsd, wsd]
        if any(s < 0 or s > 100 for s in stats if s is not None):
            raise ValueError("All percentages must be between 0 and 100")
        
        # Check for None values (insufficient data)
        if any(s is None for s in stats):
            logger.warning("Insufficient data to calculate EI - None values present")
            return None
            
        # Calculate components
        vpip_pfr_gap = abs(vpip - pfr - 3)
        fold_3bet_dev = abs(fold_to_3bet - 55)
        
        preflop_score = (vpip_pfr_gap * 2) + (fold_3bet_dev * 0.5)
        
        cbet_consistency = abs(cbet_flop - cbet_turn)
        postflop_score = cbet_consistency * 1.5
        
        wtsd_dev = abs(wtsd - 27)
        wsd_dev = abs(wsd - 51)
        showdown_score = (wtsd_dev * 1.2) + (wsd_dev * 0.8)
        
        # Final calculation
        ei = (preflop_score * 0.35) + (postflop_score * 0.40) + (showdown_score * 0.25)
        
        # Clamp to 0-100 range
        ei = max(Decimal(0), min(Decimal(100), ei))
        
        logger.info(f"Calculated EI: {ei}")
        return ei
        
    except Exception as e:
        logger.error(f"Error calculating EI: {str(e)}")
        raise
```

**Why**: Production code must be maintainable, debuggable, and reliable.

---

### 6. TESTING REQUIREMENTS
**RULE**: Write tests as you build features, not after.

**Required tests**:
- **Unit tests**: For every parser function, stat calculator, database operation
- **Integration tests**: For API endpoints, database workflows
- **Test coverage**: Minimum 80% coverage for critical components

**Testing workflow**:
1. Write test file alongside implementation file
2. Test file naming: `test_[module_name].py`
3. Run tests before committing
4. All tests must pass before moving to next feature

**Test structure**:
```python
# tests/test_stats_calculator.py
import pytest
from backend.services.stats_calculator import calculate_exploitability_index
from decimal import Decimal

def test_exploitability_index_balanced_player():
    """Test EI calculation for a balanced TAG player"""
    ei = calculate_exploitability_index(
        vpip=Decimal(22),
        pfr=Decimal(20),
        fold_to_3bet=Decimal(55),
        cbet_flop=Decimal(65),
        cbet_turn=Decimal(50),
        wtsd=Decimal(27),
        wsd=Decimal(51)
    )
    assert ei is not None
    assert 0 <= ei <= 40, "Balanced player should have low EI"

def test_exploitability_index_calling_station():
    """Test EI calculation for calling station (high VPIP, low PFR)"""
    ei = calculate_exploitability_index(
        vpip=Decimal(45),
        pfr=Decimal(10),
        fold_to_3bet=Decimal(20),
        cbet_flop=Decimal(30),
        cbet_turn=Decimal(15),
        wtsd=Decimal(40),
        wsd=Decimal(45)
    )
    assert ei is not None
    assert ei > 60, "Calling station should have high EI"

def test_exploitability_index_insufficient_data():
    """Test that None values return None"""
    ei = calculate_exploitability_index(
        vpip=Decimal(22),
        pfr=None,  # Missing data
        fold_to_3bet=Decimal(55),
        cbet_flop=Decimal(65),
        cbet_turn=Decimal(50),
        wtsd=Decimal(27),
        wsd=Decimal(51)
    )
    assert ei is None

def test_exploitability_index_invalid_input():
    """Test that invalid inputs raise ValueError"""
    with pytest.raises(ValueError):
        calculate_exploitability_index(
            vpip=Decimal(150),  # Invalid: > 100
            pfr=Decimal(20),
            fold_to_3bet=Decimal(55),
            cbet_flop=Decimal(65),
            cbet_turn=Decimal(50),
            wtsd=Decimal(27),
            wsd=Decimal(51)
        )
```

**Why**: Tests catch bugs early and ensure code works as expected.

---

### 7. CONFIGURATION MANAGEMENT
**RULE**: All environment-specific values go in .env files, never hardcoded.

**Required .env structure**:
```env
# Database
DATABASE_URL=postgresql://user:password@host:5432/poker_db
DATABASE_POOL_SIZE=10
DATABASE_POOL_MAX_OVERFLOW=20

# Claude API
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Backend
BACKEND_PORT=8000
BACKEND_HOST=0.0.0.0
BACKEND_WORKERS=4

# Frontend
FRONTEND_URL=http://localhost:3000

# Environment
ENVIRONMENT=development  # or production
LOG_LEVEL=INFO  # or DEBUG, WARNING, ERROR

# Security
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

**Loading configuration**:
```python
# backend/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    database_url: str
    database_pool_size: int = 10
    anthropic_api_key: str
    backend_port: int = 8000
    environment: str = "development"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
```

**Never commit**:
- `.env` files with actual secrets
- API keys
- Database passwords
- Any credentials

**Always commit**:
- `.env.example` with placeholder values
- Configuration class definitions

**Why**: Keeps secrets secure and makes deployment to different environments easy.

---

### 8. DATABASE PRACTICES
**RULE**: Follow database best practices from the start.

**Required practices**:
✅ **Migrations**: Use Alembic for all schema changes
✅ **Transactions**: Wrap related operations in transactions
✅ **Indexes**: Add indexes as defined in project plan
✅ **Constraints**: Use foreign keys, not null, unique constraints
✅ **Parameterized queries**: NEVER string concatenation for SQL
✅ **Connection pooling**: Use SQLAlchemy connection pool
✅ **Error handling**: Handle database errors gracefully

**Example of proper database operation**:
```python
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

async def insert_hand(
    session: Session, 
    hand_id: int, 
    timestamp: datetime,
    raw_text: str
) -> bool:
    """
    Insert a poker hand into the database.
    
    Args:
        session: SQLAlchemy session
        hand_id: Unique hand identifier
        timestamp: When hand was played
        raw_text: Complete hand history text
        
    Returns:
        True if inserted successfully, False otherwise
        
    Raises:
        IntegrityError: If hand_id already exists
        SQLAlchemyError: For other database errors
    """
    try:
        # Create hand record
        hand = RawHand(
            hand_id=hand_id,
            timestamp=timestamp,
            raw_hand_text=raw_text
        )
        
        # Insert within transaction
        session.add(hand)
        session.commit()
        
        logger.info(f"Successfully inserted hand {hand_id}")
        return True
        
    except IntegrityError as e:
        session.rollback()
        logger.warning(f"Hand {hand_id} already exists: {str(e)}")
        return False
        
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error inserting hand {hand_id}: {str(e)}")
        raise
```

**Why**: Proper database practices prevent data corruption and ensure reliability.

---

### 9. API DEVELOPMENT STANDARDS
**RULE**: All API endpoints must follow REST conventions and include proper validation.

**Required for each endpoint**:
✅ **Request validation**: Use Pydantic models
✅ **Response models**: Define expected response structure
✅ **Error handling**: Return appropriate HTTP status codes
✅ **Documentation**: FastAPI auto-generates docs, but add descriptions
✅ **CORS**: Configure properly for frontend
✅ **Rate limiting**: Add if needed for production

**Example of proper endpoint**:
```python
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field, validator
from typing import Optional
from decimal import Decimal

router = APIRouter(prefix="/api/players", tags=["players"])

class PlayerStatsResponse(BaseModel):
    """Response model for player statistics"""
    player_name: str
    total_hands: int
    vpip_pct: Optional[Decimal] = None
    pfr_pct: Optional[Decimal] = None
    exploitability_index: Optional[Decimal] = None
    player_type: Optional[str] = None
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v else None
        }

@router.get(
    "/{player_name}",
    response_model=PlayerStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get player statistics",
    description="Retrieve complete player profile including traditional stats and composite metrics"
)
async def get_player_stats(
    player_name: str,
    db: Session = Depends(get_db)
) -> PlayerStatsResponse:
    """
    Get complete statistics for a specific player.
    
    Args:
        player_name: Name of the player to lookup
        db: Database session (injected)
        
    Returns:
        PlayerStatsResponse with all statistics
        
    Raises:
        HTTPException 404: If player not found
        HTTPException 500: For database errors
    """
    try:
        # Query database
        player = db.query(PlayerStats).filter(
            PlayerStats.player_name == player_name
        ).first()
        
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player '{player_name}' not found"
            )
        
        return PlayerStatsResponse.from_orm(player)
        
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching player {player_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
```

**Why**: Consistent API design makes the backend predictable and reliable.

---

### 10. FRONTEND DEVELOPMENT STANDARDS
**RULE**: Build reusable, maintainable React components.

**Required practices**:
✅ **Component structure**: One component per file
✅ **Props validation**: Use PropTypes or TypeScript
✅ **Error boundaries**: Catch and display errors gracefully
✅ **Loading states**: Show spinners/skeletons during data fetch
✅ **Responsive design**: Mobile-first with Tailwind
✅ **Accessibility**: Proper ARIA labels, keyboard navigation
✅ **API error handling**: Display user-friendly error messages

**Example of proper React component**:
```jsx
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { api } from '../services/api';

/**
 * PlayerProfile component displays complete player statistics
 * and composite metrics in an organized card layout.
 * 
 * @param {string} playerName - Name of player to display
 */
const PlayerProfile = ({ playerName }) => {
  const [player, setPlayer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPlayerData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await api.getPlayerProfile(playerName);
        setPlayer(response.data);
      } catch (err) {
        console.error('Error fetching player:', err);
        setError(
          err.response?.status === 404 
            ? 'Player not found' 
            : 'Failed to load player data. Please try again.'
        );
      } finally {
        setLoading(false);
      }
    };

    if (playerName) {
      fetchPlayerData();
    }
  }, [playerName]);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 m-4">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  if (!player) {
    return null;
  }

  return (
    <div className="max-w-4xl mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">{player.player_name}</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Traditional Stats Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Traditional Stats</h2>
          <dl className="space-y-2">
            <div className="flex justify-between">
              <dt className="text-gray-600">VPIP:</dt>
              <dd className="font-medium">{player.vpip_pct}%</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-600">PFR:</dt>
              <dd className="font-medium">{player.pfr_pct}%</dd>
            </div>
            {/* More stats... */}
          </dl>
        </div>

        {/* Composite Metrics Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Exploitability</h2>
          <dl className="space-y-2">
            <div className="flex justify-between">
              <dt className="text-gray-600">EI:</dt>
              <dd className="font-medium">{player.exploitability_index}/100</dd>
            </div>
            {/* More metrics... */}
          </dl>
        </div>
      </div>
    </div>
  );
};

PlayerProfile.propTypes = {
  playerName: PropTypes.string.isRequired
};

export default PlayerProfile;
```

**Why**: Clean components are easier to maintain, test, and reuse.

---

### 11. PROGRESS REPORTING
**RULE**: Report progress at key milestones.

**Required reporting points**:
1. **After completing each phase**: Summary of what was built
2. **When tests pass**: Confirmation that all tests pass
3. **When encountering blockers**: Immediate notification
4. **Before making any non-trivial decision**: Ask for input

**Progress report format**:
```
✅ PHASE [X] COMPLETE: [Phase Name]

Completed:
- Item 1
- Item 2
- Item 3

Tests:
- Unit tests: X passing
- Integration tests: Y passing
- Coverage: Z%

Files created:
- path/to/file1.py
- path/to/file2.py

Git commits:
- [commit hash] Brief description

Next phase: [Phase X+1 Name]
Ready to proceed? (awaiting approval)
```

**Why**: Keeps development transparent and allows for course correction.

---

### 12. SECURITY REQUIREMENTS
**RULE**: Security must be built in from the start.

**Required security practices**:
✅ **SQL injection prevention**: Parameterized queries only
✅ **Environment variables**: Never hardcode secrets
✅ **CORS configuration**: Restrict to specific origins
✅ **Input validation**: Validate all user inputs
✅ **Error messages**: Don't expose system details to users
✅ **HTTPS**: Use SSL/TLS in production
✅ **Dependencies**: Keep all packages updated
✅ **API rate limiting**: Prevent abuse

**Example of secure code**:
```python
# ✅ CORRECT: Parameterized query
def get_player(player_name: str):
    query = "SELECT * FROM player_stats WHERE player_name = %s"
    return db.execute(query, (player_name,))

# ❌ WRONG: SQL injection vulnerable
def get_player_wrong(player_name: str):
    query = f"SELECT * FROM player_stats WHERE player_name = '{player_name}'"
    return db.execute(query)
```

**Why**: Security bugs are expensive to fix after launch. Build secure from day one.

---

### 13. DOCUMENTATION REQUIREMENTS
**RULE**: Document as you build, not after.

**Required documentation**:
✅ **Code comments**: Complex logic explained inline
✅ **Docstrings**: All functions/classes documented
✅ **README updates**: Keep main README current
✅ **API docs**: FastAPI auto-generates, but add descriptions
✅ **Setup instructions**: Complete local setup guide
✅ **Environment variables**: Document all env vars in .env.example

**When to document**:
- Write function docstring when writing the function
- Update README when project structure changes
- Document API endpoints as you create them
- Add setup instructions as you configure services

**Why**: Documentation helps future development and onboarding.

---

## Workflow Summary

### Starting Development
1. Read POKER_APP_PROJECT_PLAN.md completely
2. Initialize git repository
3. Create .gitignore
4. Set up .env and .env.example
5. Make initial commit: `[Setup] Initialize project structure`
6. Begin Phase 1

### During Each Phase
1. Create feature branch: `git checkout -b feature/phase-name`
2. Build according to project plan specifications
3. Write tests alongside implementation
4. Commit logical units of work with clear messages
5. Run all tests before committing
6. Complete entire phase before moving on
7. Merge to develop when phase complete
8. Report completion and request approval for next phase

### Before Committing
- [ ] All tests pass
- [ ] Code follows quality standards
- [ ] No TODOs or commented code
- [ ] Docstrings complete
- [ ] No hardcoded values
- [ ] Type hints added
- [ ] Error handling implemented
- [ ] Logging in place

### Before Moving to Next Phase
- [ ] All features in current phase complete
- [ ] All tests passing
- [ ] Code reviewed for quality
- [ ] Documentation updated
- [ ] Approval received to proceed

---

## What to Do When...

### You encounter ambiguity in the project plan
1. Stop work
2. Explain the ambiguity
3. Propose 2-3 solutions
4. Wait for guidance
5. Do NOT make assumptions

### You think a feature should be added
1. Stop work
2. Explain the feature and why it's needed
3. Explain where it would fit in the architecture
4. Wait for approval
5. Do NOT add features proactively

### You find a bug in the project plan
1. Continue with current task if possible
2. Document the issue clearly
3. Propose a fix
4. Wait for confirmation
5. Do NOT silently fix without approval

### You're blocked on something
1. Stop work on that item
2. Explain the blocker clearly
3. Suggest alternatives if any
4. Wait for help
5. Work on unblocked items if any

### Tests fail
1. Do NOT commit
2. Debug the issue
3. Fix the root cause
4. Re-run tests
5. Only commit when all tests pass

### You want to refactor something
1. Complete the feature first
2. Ensure tests pass
3. Propose the refactor with reasoning
4. Wait for approval
5. Refactor only if approved

---

## Forbidden Practices - Never Do These

❌ Committing broken code ("I'll fix it later")
❌ Skipping tests ("We'll test it later")
❌ Hardcoding values ("Just for now")
❌ Using mock data in production code
❌ Adding dependencies without approval
❌ Changing the database schema without approval
❌ Implementing features not in the plan
❌ Copying code from Stack Overflow without understanding it
❌ Ignoring errors or exceptions
❌ Using print() instead of proper logging
❌ Committing .env files with secrets
❌ Working on multiple phases at once
❌ Pushing to main branch directly

---

## Success Criteria

You're doing it right when:
✅ Each git commit is atomic and well-described
✅ All tests pass before committing
✅ Code is production-ready from the start
✅ You ask for approval before deviating from plan
✅ Progress is reported at key milestones
✅ Documentation stays current with code
✅ No temporary solutions or technical debt
✅ Security is built in from day one
✅ Each phase is complete before starting the next

---

## Remember

**This is NOT a prototype or MVP. This is production software being built correctly from the start.**

- Quality over speed
- Complete over quick
- Tested over assumed working
- Secure over convenient
- Documented over "self-explanatory"
- Approved over autonomous

**When in doubt: STOP and ASK.**

---

## Final Checklist Before Starting

Before you begin Phase 1, confirm:
- [ ] I have read POKER_APP_PROJECT_PLAN.md completely
- [ ] I have read this RULES.md completely
- [ ] I understand I must ask before making changes not in the plan
- [ ] I understand I must build for production from day one
- [ ] I understand I must follow the phases in order
- [ ] I understand I must write tests as I build
- [ ] I understand I must use version control properly
- [ ] I understand I must report progress at milestones
- [ ] I am ready to build production-quality software

**Ready to begin? Confirm and let's start Phase 1: Database Setup.**
