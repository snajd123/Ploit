"""
FastAPI backend for Poker Analysis App.

Provides REST API endpoints for:
- Uploading hand history files
- Querying player statistics
- Database overview
- Claude AI integration for natural language queries
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import tempfile
import os
import time
import logging

from backend.database import get_db, check_db_connection
from backend.services import DatabaseService, ClaudeService
from backend.services.stats_calculator import StatsCalculator
from backend.parser import PokerStarsParser
from backend.config import get_settings
from backend.verification_endpoint import router as verification_router
from backend.api.gto_endpoints import router as gto_router
from backend.api.gto_browser_endpoints import router as gto_browser_router
from backend.api.session_endpoints import router as session_router
from backend.api.strategy_endpoints import router as strategy_router
from backend.api.conversation_endpoints import router as conversation_router
from backend.api.pool_analysis_endpoints import router as pool_analysis_router
from backend.models.conversation_models import ClaudeConversation, ClaudeMessage
from backend.auth import verify_api_key, InputValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Poker Analysis API",
    description="Cloud-based poker analysis platform with Claude AI integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS - restrict to specific methods and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "Accept"],
)

# Include verification router
app.include_router(verification_router)

# Include GTO router
app.include_router(gto_router)

# Include GTO Browser router
app.include_router(gto_browser_router)

# Include Session router
app.include_router(session_router)

# Include Strategy router
app.include_router(strategy_router)

# Include Conversation router
app.include_router(conversation_router)

# Include Pool Analysis router
app.include_router(pool_analysis_router)

# ========================================
# Pydantic Models
# ========================================

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response model for file upload"""
    session_id: int
    hands_parsed: int
    hands_failed: int
    players_updated: int
    stake_level: Optional[str] = None
    processing_time: float
    message: str


class PlayerListItem(BaseModel):
    """List item for players"""
    player_name: str
    total_hands: int
    vpip_pct: Optional[float] = None
    pfr_pct: Optional[float] = None
    player_type: Optional[str] = None
    exploitability_index: Optional[float] = None


class DatabaseStatsResponse(BaseModel):
    """Response model for database statistics"""
    total_hands: int
    total_players: int
    first_hand_date: Optional[datetime] = None
    last_hand_date: Optional[datetime] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    database: str
    timestamp: datetime


class ClaudeQueryRequest(BaseModel):
    """Request model for Claude AI query"""
    query: str = Field(..., description="Natural language question about poker data", min_length=1)
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="Optional conversation history for context")
    conversation_id: Optional[int] = Field(None, description="Optional conversation ID to continue existing conversation")


class ClaudeToolCall(BaseModel):
    """Tool call information"""
    tool: str
    input: Dict[str, Any]
    result: Dict[str, Any]


class ClaudeQueryResponse(BaseModel):
    """Response model for Claude AI query"""
    success: bool
    response: str
    tool_calls: Optional[List[ClaudeToolCall]] = None
    usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None
    conversation_id: Optional[int] = None


# ========================================
# API Endpoints
# ========================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Poker Analysis API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
    description="Check API and database health status"
)
async def health_check():
    """
    Health check endpoint.

    Returns API status. DB status checked on actual requests to avoid
    unnecessary connection creation with NullPool.
    """
    # Don't check DB connection on health checks to avoid creating connections
    # The app will handle DB errors on actual API requests
    return HealthResponse(
        status="healthy",
        database="available",  # Assume available, actual requests will validate
        timestamp=datetime.now()
    )


@app.post(
    "/api/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Upload"],
    summary="Upload hand history file",
    description="Upload and parse a PokerStars .txt hand history file"
)
async def upload_hand_history(
    file: UploadFile = File(..., description="PokerStars hand history .txt file"),
    db: Session = Depends(get_db)
):
    """
    Upload and parse a PokerStars hand history file.

    Process:
    1. Save uploaded file temporarily
    2. Parse all hands using PokerStars parser
    3. Insert hands into database
    4. Update player statistics
    5. Create upload session record

    Args:
        file: Uploaded .txt file
        db: Database session (injected)

    Returns:
        Upload summary with parsing and insertion results
    """
    start_time = time.time()

    try:
        # Validate file type
        if not file.filename.endswith('.txt'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .txt files are supported"
            )

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as tmp_file:
            content = await file.read()

            # Validate file size
            InputValidator.validate_file_size(content, file.filename)

            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # Parse hands
            logger.info(f"Parsing file: {file.filename}")
            parser = PokerStarsParser()
            parse_result = parser.parse_file(tmp_path)

            if parse_result.total_hands == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid hands found in file"
                )

            # Insert hands into database
            logger.info(f"Inserting {len(parse_result.hands)} hands into database")
            service = DatabaseService(db)
            insert_result = service.insert_hand_batch(parse_result.hands)

            # Update player statistics
            affected_players = set()
            for hand in parse_result.hands:
                affected_players.update(hand.player_flags.keys())

            logger.info(f"Updating stats for {len(affected_players)} players")
            for player in affected_players:
                service.update_player_stats(player)

            # Determine stake level (from first hand)
            stake_level = parse_result.hands[0].stake_level if parse_result.hands else None

            # Calculate processing time
            processing_time = time.time() - start_time

            # Create upload session
            session_id = service.create_upload_session(
                filename=file.filename,
                hands_parsed=insert_result['hands_inserted'],
                hands_failed=insert_result['hands_failed'],
                players_updated=len(affected_players),
                stake_level=stake_level,
                processing_time=int(processing_time)
            )

            logger.info(f"Upload complete: session_id={session_id}, hands={insert_result['hands_inserted']}")

            return UploadResponse(
                session_id=session_id,
                hands_parsed=insert_result['hands_inserted'],
                hands_failed=insert_result['hands_failed'],
                players_updated=len(affected_players),
                stake_level=stake_level,
                processing_time=round(processing_time, 2),
                message=f"Successfully processed {insert_result['hands_inserted']} hands"
            )

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )


@app.post(
    "/api/upload/batch",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Upload"],
    summary="Upload multiple hand history files",
    description="Upload and parse multiple PokerStars .txt hand history files at once"
)
async def upload_hand_history_batch(
    files: List[UploadFile] = File(..., description="Multiple PokerStars hand history .txt files"),
    db: Session = Depends(get_db)
):
    """
    Upload and parse multiple PokerStars hand history files at once.

    Processes all files and combines results into a single upload session.

    Args:
        files: List of uploaded .txt files
        db: Database session (injected)

    Returns:
        Combined upload summary for all files
    """
    start_time = time.time()
    total_hands_parsed = 0
    total_hands_failed = 0
    all_affected_players = set()
    stake_level = None

    try:
        parser = PokerStarsParser()
        service = DatabaseService(db)

        for file in files:
            # Validate file type
            if not file.filename.endswith('.txt'):
                logger.warning(f"Skipping non-.txt file: {file.filename}")
                continue

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as tmp_file:
                content = await file.read()

                # Validate file size
                InputValidator.validate_file_size(content, file.filename)

                tmp_file.write(content)
                tmp_path = tmp_file.name

            try:
                # Parse hands
                logger.info(f"Parsing file: {file.filename}")
                parse_result = parser.parse_file(tmp_path)

                if parse_result.total_hands == 0:
                    logger.warning(f"No valid hands found in {file.filename}")
                    continue

                # Insert hands into database
                logger.info(f"Inserting {len(parse_result.hands)} hands from {file.filename}")
                insert_result = service.insert_hand_batch(parse_result.hands)

                total_hands_parsed += insert_result['hands_inserted']
                total_hands_failed += insert_result['hands_failed']

                # Track affected players
                for hand in parse_result.hands:
                    all_affected_players.update(hand.player_flags.keys())

                # Get stake level from first file's first hand
                if not stake_level and parse_result.hands:
                    stake_level = parse_result.hands[0].stake_level

            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        # Update player statistics for all affected players
        logger.info(f"Updating stats for {len(all_affected_players)} players")
        for player in all_affected_players:
            service.update_player_stats(player)

        # Calculate processing time
        processing_time = time.time() - start_time

        # Create upload session
        session_id = service.create_upload_session(
            filename=f"{len(files)} files",
            hands_parsed=total_hands_parsed,
            hands_failed=total_hands_failed,
            players_updated=len(all_affected_players),
            stake_level=stake_level,
            processing_time=int(processing_time)
        )

        logger.info(f"Batch upload complete: session_id={session_id}, files={len(files)}, hands={total_hands_parsed}")

        return UploadResponse(
            session_id=session_id,
            hands_parsed=total_hands_parsed,
            hands_failed=total_hands_failed,
            players_updated=len(all_affected_players),
            stake_level=stake_level,
            processing_time=round(processing_time, 2),
            message=f"Successfully processed {total_hands_parsed} hands from {len(files)} files"
        )

    except Exception as e:
        logger.error(f"Error processing batch upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing files: {str(e)}"
        )


@app.get(
    "/api/players",
    response_model=List[PlayerListItem],
    tags=["Players"],
    summary="Get all players",
    description="Retrieve list of all players with optional filtering"
)
async def get_all_players(
    min_hands: int = 0,
    stake_level: Optional[str] = None,
    sort_by: str = 'player_name',
    limit: int = 10000,
    db: Session = Depends(get_db)
):
    """
    Get all players with optional filtering.

    Args:
        min_hands: Minimum number of hands (default: 100)
        stake_level: Filter by stake level (optional)
        sort_by: Column to sort by (default: total_hands)
        limit: Maximum results to return (default: 100)
        db: Database session (injected)

    Returns:
        List of players matching criteria
    """
    try:
        service = DatabaseService(db)
        players = service.get_all_players(
            min_hands=min_hands,
            stake_level=stake_level,
            order_by=sort_by,
            limit=limit
        )

        # Note: get_all_players returns simplified data, would need to expand for full response
        # For now, returning basic data
        return players

    except Exception as e:
        logger.error(f"Error getting players: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving players"
        )


@app.get(
    "/api/players/{player_name}",
    response_model=Dict[str, Any],
    tags=["Players"],
    summary="Get player profile",
    description="Retrieve complete player statistics and metrics"
)
async def get_player_profile(
    player_name: str,
    db: Session = Depends(get_db)
):
    """
    Get complete player profile with all statistics.

    Args:
        player_name: Name of player
        db: Database session (injected)

    Returns:
        Complete player statistics including traditional stats and composite metrics
    """
    try:
        # Validate player name input
        validated_name = InputValidator.validate_player_name(player_name)

        service = DatabaseService(db)
        stats = service.get_player_stats(validated_name)

        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player '{player_name}' not found"
            )

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting player profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving player profile"
        )


@app.get(
    "/api/players/{player_name}/leaks",
    response_model=Dict[str, Any],
    tags=["Players"],
    summary="Get player leak analysis",
    description="Analyze player leaks with confidence intervals and exploit recommendations"
)
async def get_player_leaks(
    player_name: str,
    db: Session = Depends(get_db)
):
    """
    Get player leak analysis with confidence intervals and exploit recommendations.

    Returns prioritized leaks sorted by severity and EV impact.
    """
    try:
        validated_name = InputValidator.validate_player_name(player_name)
        service = DatabaseService(db)
        stats = service.get_player_stats(validated_name)

        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player '{player_name}' not found"
            )

        # Create StatsCalculator and get leak analysis
        calculator = StatsCalculator(stats)
        leak_analysis = calculator.get_leak_analysis()
        core_metrics = calculator.get_core_metrics()
        player_type_info = calculator.get_player_type_details()

        # Extract the leaks list from the analysis result
        leaks_list = leak_analysis.get("leaks", [])

        return {
            "player_name": stats.get("player_name"),
            "total_hands": stats.get("total_hands"),
            "player_type": player_type_info,
            "core_metrics": core_metrics,
            "leaks": leaks_list,
            "leak_summary": {
                "total_leaks": leak_analysis.get("total_leaks", 0),
                "critical_leaks": leak_analysis.get("critical_leaks", 0),
                "major_leaks": leak_analysis.get("major_leaks", 0),
                "total_ev_opportunity": leak_analysis.get("total_ev_opportunity_bb_100", 0),
                "reliability": leak_analysis.get("reliability", "low")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting player leaks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving player leak analysis"
        )


@app.get(
    "/api/players/{player_name}/gto-analysis",
    response_model=Dict[str, Any],
    tags=["Players"],
    summary="Get comprehensive player GTO analysis",
    description="Compare player preflop frequencies to GTO optimal frequencies across all scenarios"
)
async def get_player_gto_analysis(
    player_name: str,
    db: Session = Depends(get_db)
):
    """
    Calculate comprehensive GTO comparison for a player on-the-fly.

    Covers all preflop GTO scenario categories:
    - Opening ranges (RFI by position)
    - Defense vs opens (call/3bet/fold when facing a raise)
    - Facing 3-bet responses (call/4bet/fold after opening)
    - Blind defense (vs steals from CO/BTN/SB)
    """
    from sqlalchemy import text

    try:
        validated_name = InputValidator.validate_player_name(player_name)

        # ============================================
        # 1. OPENING RANGES (RFI - Raise First In)
        # ============================================
        opening_query = text("""
            SELECT
                position,
                COUNT(*) as total_hands,
                COUNT(*) FILTER (WHERE faced_raise = false) as rfi_opportunities,
                COUNT(*) FILTER (WHERE pfr = true AND faced_raise = false) as opened,
                ROUND(100.0 * COUNT(*) FILTER (WHERE pfr = true AND faced_raise = false) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_raise = false), 0), 1) as player_open_pct
            FROM player_hand_summary
            WHERE player_name = :player_name
            AND position IS NOT NULL
            AND position NOT IN ('BB')
            GROUP BY position
            HAVING COUNT(*) FILTER (WHERE faced_raise = false) >= 10
            ORDER BY CASE position
                WHEN 'UTG' THEN 1 WHEN 'MP' THEN 2 WHEN 'HJ' THEN 3
                WHEN 'CO' THEN 4 WHEN 'BTN' THEN 5 WHEN 'SB' THEN 6
            END
        """)
        opening_result = db.execute(opening_query, {"player_name": validated_name})
        opening_rows = [dict(row._mapping) for row in opening_result]

        # Get GTO opening frequencies
        gto_opening_result = db.execute(text("""
            SELECT position, gto_aggregate_freq
            FROM gto_scenarios WHERE category = 'opening'
        """))
        gto_opening = {row[0]: float(row[1]) * 100 if row[1] else 0 for row in gto_opening_result}

        opening_ranges = []
        for row in opening_rows:
            pos = row['position']
            player_freq = float(row['player_open_pct']) if row['player_open_pct'] else 0
            gto_freq = gto_opening.get(pos, 0)
            diff = player_freq - gto_freq
            severity = 'minor' if abs(diff) < 5 else 'moderate' if abs(diff) < 15 else 'major'
            opening_ranges.append({
                'position': pos,
                'total_hands': row['rfi_opportunities'],
                'player_frequency': player_freq,
                'gto_frequency': round(gto_freq, 1),
                'frequency_diff': round(diff, 1),
                'leak_severity': severity,
                'leak_type': 'Too Loose' if diff > 5 else 'Too Tight' if diff < -5 else None
            })

        # ============================================
        # 2. DEFENSE VS OPENS (call/3bet/fold)
        # ============================================
        defense_query = text("""
            SELECT
                position,
                COUNT(*) FILTER (WHERE faced_raise = true) as faced_open,
                COUNT(*) FILTER (WHERE faced_raise = true AND vpip = false) as folded,
                COUNT(*) FILTER (WHERE faced_raise = true AND vpip = true AND pfr = false) as called,
                COUNT(*) FILTER (WHERE faced_raise = true AND made_three_bet = true) as three_bets,
                ROUND(100.0 * COUNT(*) FILTER (WHERE faced_raise = true AND vpip = false) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_raise = true), 0), 1) as fold_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE faced_raise = true AND vpip = true AND pfr = false) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_raise = true), 0), 1) as call_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE faced_raise = true AND made_three_bet = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_raise = true), 0), 1) as three_bet_pct
            FROM player_hand_summary
            WHERE player_name = :player_name
            AND position IS NOT NULL
            GROUP BY position
            HAVING COUNT(*) FILTER (WHERE faced_raise = true) >= 5
            ORDER BY position
        """)
        defense_result = db.execute(defense_query, {"player_name": validated_name})
        defense_rows = [dict(row._mapping) for row in defense_result]

        # Get GTO defense frequencies (call and 3bet)
        gto_defense_result = db.execute(text("""
            SELECT position, action, AVG(gto_aggregate_freq) * 100 as avg_freq
            FROM gto_scenarios
            WHERE category = 'defense'
            AND action IN ('call', '3bet')
            GROUP BY position, action
        """))
        gto_defense = {}
        for row in gto_defense_result:
            pos, action, freq = row[0], row[1], float(row[2]) if row[2] else 0
            if pos not in gto_defense:
                gto_defense[pos] = {}
            gto_defense[pos][action] = freq

        defense_vs_open = []
        for row in defense_rows:
            pos = row['position']
            fold_freq = float(row['fold_pct']) if row['fold_pct'] else 0
            call_freq = float(row['call_pct']) if row['call_pct'] else 0
            threebet_freq = float(row['three_bet_pct']) if row['three_bet_pct'] else 0

            gto_call = gto_defense.get(pos, {}).get('call', 15)
            gto_3bet = gto_defense.get(pos, {}).get('3bet', 8)
            gto_fold = 100 - gto_call - gto_3bet

            defense_vs_open.append({
                'position': pos,
                'sample_size': row['faced_open'],
                'player_fold': round(fold_freq, 1),
                'player_call': round(call_freq, 1),
                'player_3bet': round(threebet_freq, 1),
                'gto_fold': round(gto_fold, 1),
                'gto_call': round(gto_call, 1),
                'gto_3bet': round(gto_3bet, 1),
                'fold_diff': round(fold_freq - gto_fold, 1),
                'call_diff': round(call_freq - gto_call, 1),
                '3bet_diff': round(threebet_freq - gto_3bet, 1),
            })

        # ============================================
        # 3. FACING 3-BET (after opening)
        # ============================================
        facing_3bet_query = text("""
            SELECT
                position,
                COUNT(*) FILTER (WHERE faced_three_bet = true) as faced_3bet,
                COUNT(*) FILTER (WHERE folded_to_three_bet = true) as folded,
                COUNT(*) FILTER (WHERE called_three_bet = true) as called,
                COUNT(*) FILTER (WHERE four_bet = true) as four_bet,
                ROUND(100.0 * COUNT(*) FILTER (WHERE folded_to_three_bet = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true), 0), 1) as fold_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE called_three_bet = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true), 0), 1) as call_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE four_bet = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true), 0), 1) as four_bet_pct
            FROM player_hand_summary
            WHERE player_name = :player_name
            AND position IS NOT NULL
            GROUP BY position
            HAVING COUNT(*) FILTER (WHERE faced_three_bet = true) >= 5
            ORDER BY position
        """)
        facing_3bet_result = db.execute(facing_3bet_query, {"player_name": validated_name})
        facing_3bet_rows = [dict(row._mapping) for row in facing_3bet_result]

        # Get GTO facing 3-bet frequencies
        gto_f3bet_result = db.execute(text("""
            SELECT position, action, AVG(gto_aggregate_freq) * 100 as avg_freq
            FROM gto_scenarios
            WHERE category = 'facing_3bet'
            AND action IN ('fold', 'call', '4bet')
            GROUP BY position, action
        """))
        gto_f3bet = {}
        for row in gto_f3bet_result:
            pos, action, freq = row[0], row[1], float(row[2]) if row[2] else 0
            if pos not in gto_f3bet:
                gto_f3bet[pos] = {}
            gto_f3bet[pos][action] = freq

        facing_3bet = []
        for row in facing_3bet_rows:
            pos = row['position']
            fold = float(row['fold_pct']) if row['fold_pct'] else 0
            call = float(row['call_pct']) if row['call_pct'] else 0
            four_bet = float(row['four_bet_pct']) if row['four_bet_pct'] else 0

            gto_fold = gto_f3bet.get(pos, {}).get('fold', 55)
            gto_call = gto_f3bet.get(pos, {}).get('call', 35)
            gto_4bet = gto_f3bet.get(pos, {}).get('4bet', 10)

            facing_3bet.append({
                'position': pos,
                'sample_size': row['faced_3bet'],
                'player_fold': round(fold, 1),
                'player_call': round(call, 1),
                'player_4bet': round(four_bet, 1),
                'gto_fold': round(gto_fold, 1),
                'gto_call': round(gto_call, 1),
                'gto_4bet': round(gto_4bet, 1),
                'fold_diff': round(fold - gto_fold, 1),
                'call_diff': round(call - gto_call, 1),
                '4bet_diff': round(four_bet - gto_4bet, 1),
            })

        # ============================================
        # 4. BLIND DEFENSE (vs steals) - Using actual GTO from database
        # ============================================
        blind_defense_query = text("""
            SELECT
                position,
                COUNT(*) FILTER (WHERE faced_steal = true) as faced_steal,
                COUNT(*) FILTER (WHERE fold_to_steal = true) as folded,
                COUNT(*) FILTER (WHERE call_steal = true) as called,
                COUNT(*) FILTER (WHERE three_bet_vs_steal = true) as three_bet,
                ROUND(100.0 * COUNT(*) FILTER (WHERE fold_to_steal = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_steal = true), 0), 1) as fold_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE call_steal = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_steal = true), 0), 1) as call_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE three_bet_vs_steal = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_steal = true), 0), 1) as three_bet_pct
            FROM player_hand_summary
            WHERE player_name = :player_name
            AND position IN ('BB', 'SB')
            GROUP BY position
            HAVING COUNT(*) FILTER (WHERE faced_steal = true) >= 5
            ORDER BY position
        """)
        blind_result = db.execute(blind_defense_query, {"player_name": validated_name})
        blind_rows = [dict(row._mapping) for row in blind_result]

        # Get GTO blind defense frequencies from database (vs BTN which is typical steal)
        gto_blind_result = db.execute(text("""
            SELECT position, action, gto_aggregate_freq * 100 as freq
            FROM gto_scenarios
            WHERE category = 'defense'
            AND position IN ('BB', 'SB')
            AND opponent_position = 'BTN'
        """))
        gto_blind = {}
        for row in gto_blind_result:
            pos, action, freq = row[0], row[1], float(row[2]) if row[2] else 0
            if pos not in gto_blind:
                gto_blind[pos] = {}
            gto_blind[pos][action] = freq

        blind_defense = []
        for row in blind_rows:
            pos = row['position']
            fold = float(row['fold_pct']) if row['fold_pct'] else 0
            call = float(row['call_pct']) if row['call_pct'] else 0
            three_bet = float(row['three_bet_pct']) if row['three_bet_pct'] else 0

            gto_call = gto_blind.get(pos, {}).get('call', 30)
            gto_3bet = gto_blind.get(pos, {}).get('3bet', 15)
            gto_fold = gto_blind.get(pos, {}).get('fold', 55)

            blind_defense.append({
                'position': pos,
                'sample_size': row['faced_steal'],
                'player_fold': round(fold, 1),
                'player_call': round(call, 1),
                'player_3bet': round(three_bet, 1),
                'gto_fold': round(gto_fold, 1),
                'gto_call': round(gto_call, 1),
                'gto_3bet': round(gto_3bet, 1),
                'fold_diff': round(fold - gto_fold, 1),
                'call_diff': round(call - gto_call, 1),
                '3bet_diff': round(three_bet - gto_3bet, 1),
            })

        # ============================================
        # 5. STEAL ATTEMPTS - Using actual GTO from database
        # ============================================
        steal_query = text("""
            SELECT
                position,
                COUNT(*) FILTER (WHERE faced_raise = false) as opportunities,
                COUNT(*) FILTER (WHERE steal_attempt = true) as steals,
                ROUND(100.0 * COUNT(*) FILTER (WHERE steal_attempt = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_raise = false), 0), 1) as steal_pct
            FROM player_hand_summary
            WHERE player_name = :player_name
            AND position IN ('CO', 'BTN', 'SB')
            GROUP BY position
            HAVING COUNT(*) FILTER (WHERE faced_raise = false) >= 10
            ORDER BY position
        """)
        steal_result = db.execute(steal_query, {"player_name": validated_name})
        steal_rows = [dict(row._mapping) for row in steal_result]

        # Get GTO opening frequencies from database for steal positions
        gto_steal_result = db.execute(text("""
            SELECT position, gto_aggregate_freq * 100 as freq
            FROM gto_scenarios
            WHERE category = 'opening'
            AND position IN ('CO', 'BTN', 'SB')
        """))
        gto_steal = {row[0]: float(row[1]) if row[1] else 0 for row in gto_steal_result}

        steal_attempts = []
        for row in steal_rows:
            pos = row['position']
            player_freq = float(row['steal_pct']) if row['steal_pct'] else 0
            gto_freq = gto_steal.get(pos, 35)
            diff = player_freq - gto_freq

            steal_attempts.append({
                'position': pos,
                'sample_size': row['opportunities'],
                'player_frequency': round(player_freq, 1),
                'gto_frequency': round(gto_freq, 1),
                'frequency_diff': round(diff, 1),
                'leak_type': 'Over-stealing' if diff > 10 else 'Under-stealing' if diff < -10 else None
            })

        # ============================================
        # 6. POSITION-SPECIFIC DEFENSE (BB vs BTN, BB vs CO, etc.)
        # ============================================
        # Get all position-specific GTO defense scenarios
        gto_matchups_result = db.execute(text("""
            SELECT position, opponent_position, action, gto_aggregate_freq * 100 as freq
            FROM gto_scenarios
            WHERE category = 'defense'
            ORDER BY position, opponent_position, action
        """))
        gto_matchups = {}
        for row in gto_matchups_result:
            pos, opp, action, freq = row[0], row[1], row[2], float(row[3]) if row[3] else 0
            key = f"{pos}_vs_{opp}"
            if key not in gto_matchups:
                gto_matchups[key] = {}
            gto_matchups[key][action] = freq

        # Format as list for frontend
        position_matchups = []
        for key, actions in sorted(gto_matchups.items()):
            pos, opp = key.split('_vs_')
            position_matchups.append({
                'position': pos,
                'vs_position': opp,
                'gto_fold': round(actions.get('fold', 0), 1),
                'gto_call': round(actions.get('call', 0), 1),
                'gto_3bet': round(actions.get('3bet', 0), 1),
            })

        # ============================================
        # 7. FACING 4-BET GTO Reference
        # ============================================
        gto_f4bet_result = db.execute(text("""
            SELECT position, opponent_position, action, gto_aggregate_freq * 100 as freq
            FROM gto_scenarios
            WHERE category = 'facing_4bet'
            ORDER BY position, opponent_position, action
        """))
        gto_facing_4bet = {}
        for row in gto_f4bet_result:
            pos, opp, action, freq = row[0], row[1], row[2], float(row[3]) if row[3] else 0
            key = f"{pos}_vs_{opp}"
            if key not in gto_facing_4bet:
                gto_facing_4bet[key] = {}
            gto_facing_4bet[key][action] = freq

        # Format facing 4-bet reference for frontend
        facing_4bet_reference = []
        for key, actions in sorted(gto_facing_4bet.items()):
            pos, opp = key.split('_vs_')
            facing_4bet_reference.append({
                'position': pos,
                'vs_position': opp,
                'gto_fold': round(actions.get('fold', 0), 1),
                'gto_call': round(actions.get('call', 0), 1),
                'gto_5bet': round(actions.get('5bet', 0) + actions.get('allin', 0), 1),
            })

        # ============================================
        # CALCULATE OVERALL ADHERENCE SCORE
        # ============================================
        all_deviations = []

        for r in opening_ranges:
            all_deviations.append(abs(r['frequency_diff']))
        for r in defense_vs_open:
            all_deviations.append(abs(r['call_diff']))
            all_deviations.append(abs(r['3bet_diff']))
        for r in facing_3bet:
            all_deviations.append(abs(r['fold_diff']))
            all_deviations.append(abs(r['call_diff']))
        for r in blind_defense:
            all_deviations.append(abs(r['fold_diff']))
            all_deviations.append(abs(r['3bet_diff']))
        for r in steal_attempts:
            all_deviations.append(abs(r['frequency_diff']))

        avg_deviation = sum(all_deviations) / len(all_deviations) if all_deviations else 0
        adherence_score = max(0, 100 - avg_deviation * 1.5)

        # Count leaks
        major_leaks = sum(1 for d in all_deviations if d > 15)
        moderate_leaks = sum(1 for d in all_deviations if 8 < d <= 15)

        # Get total hands
        total_hands_result = db.execute(text("""
            SELECT COUNT(*) FROM player_hand_summary WHERE player_name = :player_name
        """), {"player_name": validated_name})
        total_hands = total_hands_result.scalar() or 0

        return {
            'player': validated_name,
            'adherence': {
                'gto_adherence_score': round(adherence_score, 1),
                'avg_deviation': round(avg_deviation, 1),
                'major_leaks_count': major_leaks,
                'moderate_leaks_count': moderate_leaks,
                'total_hands': total_hands
            },
            'opening_ranges': opening_ranges,
            'defense_vs_open': defense_vs_open,
            'facing_3bet': facing_3bet,
            'blind_defense': blind_defense,
            'steal_attempts': steal_attempts,
            'position_matchups': position_matchups,
            'facing_4bet_reference': facing_4bet_reference
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting player GTO analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving GTO analysis: {str(e)}"
        )


@app.get(
    "/api/database/stats",
    response_model=DatabaseStatsResponse,
    tags=["Database"],
    summary="Get database statistics",
    description="Retrieve overview statistics about the database"
)
async def get_database_stats(db: Session = Depends(get_db)):
    """
    Get database overview statistics.

    Returns:
        Database statistics including total hands, players, and date range
    """
    try:
        service = DatabaseService(db)
        stats = service.get_database_stats()

        return DatabaseStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving database statistics"
        )


@app.get(
    "/api/database/schema",
    tags=["Database"],
    summary="Get database schema",
    description="Retrieve database schema information (for Claude integration)"
)
async def get_database_schema():
    """
    Get database schema information.

    This endpoint provides schema details for Claude AI integration
    in Phase 6.

    Returns:
        Database schema information
    """
    return {
        "tables": {
            "raw_hands": {
                "description": "Complete hand history text",
                "columns": ["hand_id", "timestamp", "table_name", "stake_level", "game_type", "raw_hand_text"]
            },
            "hand_actions": {
                "description": "Every action in every hand",
                "columns": ["action_id", "hand_id", "player_name", "position", "street", "action_type", "amount", "pot_size_before", "pot_size_after"]
            },
            "player_hand_summary": {
                "description": "Boolean flags for each player per hand",
                "columns": ["summary_id", "hand_id", "player_name", "position", "vpip", "pfr", "saw_flop", "cbet_made_flop", "...60+ more flags"]
            },
            "player_stats": {
                "description": "Aggregated player statistics and composite metrics",
                "columns": ["player_name", "total_hands", "vpip_pct", "pfr_pct", "exploitability_index", "player_type", "...100+ stats"]
            },
            "upload_sessions": {
                "description": "Upload tracking and audit trail",
                "columns": ["session_id", "filename", "hands_parsed", "hands_failed", "status"]
            }
        }
    }


@app.post(
    "/api/database/recalculate-stats",
    tags=["Database"],
    summary="Recalculate all player statistics",
    description="Recalculate statistics for all players using the latest flag calculation logic. Requires API key."
)
async def recalculate_all_stats(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Recalculate statistics for all players.

    This endpoint:
    1. Gets all unique player names from player_hand_summary
    2. Recalculates their statistics using the current flag calculation logic
    3. Updates the player_stats table

    Use this after fixing flag calculation bugs to update existing data.

    Returns:
        Summary of recalculation including number of players updated
    """
    try:
        service = DatabaseService(db)

        # Step 1: Recalculate flags for all hands
        from backend.models.database_models import RawHand, PlayerHandSummary

        hand_ids = db.query(RawHand.hand_id).all()
        hand_ids = [hand_id[0] for hand_id in hand_ids]

        logger.info(f"Starting flag recalculation for {len(hand_ids)} hands")

        hands_updated = 0
        hands_failed = 0

        for i, hand_id in enumerate(hand_ids):
            try:
                if service.recalculate_hand_flags(hand_id):
                    hands_updated += 1
                else:
                    hands_failed += 1

                if (i + 1) % 100 == 0:
                    logger.info(f"Recalculated flags for {i + 1}/{len(hand_ids)} hands")
            except Exception as e:
                hands_failed += 1
                logger.error(f"Failed to recalculate hand {hand_id}: {str(e)}")

        logger.info(f"Flag recalculation complete: {hands_updated} updated, {hands_failed} failed")

        # Step 2: Recalculate player stats from updated flags
        player_names = db.query(PlayerHandSummary.player_name).distinct().all()
        player_names = [name[0] for name in player_names]

        logger.info(f"Starting stats recalculation for {len(player_names)} players")

        players_updated = 0
        players_failed = 0

        for player_name in player_names:
            try:
                service.update_player_stats(player_name)
                players_updated += 1
                logger.info(f"Updated stats for {player_name} ({players_updated}/{len(player_names)})")
            except Exception as e:
                players_failed += 1
                logger.error(f"Failed to update stats for {player_name}: {str(e)}")

        logger.info(f"Stats recalculation complete: {players_updated} updated, {players_failed} failed")

        return {
            "message": "Statistics recalculated successfully",
            "hands_recalculated": hands_updated,
            "hands_failed": hands_failed,
            "players_processed": len(player_names),
            "players_updated": players_updated,
            "players_failed": players_failed
        }

    except Exception as e:
        logger.error(f"Error recalculating stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recalculating statistics: {str(e)}"
        )


@app.get(
    "/api/database/debug/{player_name}",
    tags=["Database"],
    summary="Debug player flags",
    description="Get sample hand flags for debugging"
)
async def debug_player_flags(player_name: str, db: Session = Depends(get_db)):
    """
    Get sample hand flags for a player to debug statistics.

    Returns 5 sample hands with their calculated flags.
    """
    try:
        from backend.models.database_models import PlayerHandSummary

        summaries = db.query(PlayerHandSummary).filter(
            PlayerHandSummary.player_name == player_name
        ).limit(10).all()

        if not summaries:
            return {"error": f"No hands found for player {player_name}"}

        result = []
        for s in summaries:
            result.append({
                "hand_id": s.hand_id,
                "position": s.position,
                "vpip": s.vpip,
                "pfr": s.pfr,
                "limp": s.limp,
                "faced_raise": s.faced_raise,
                "made_three_bet": s.made_three_bet,
                "faced_three_bet": s.faced_three_bet,
                "folded_to_three_bet": s.folded_to_three_bet,
                "saw_flop": s.saw_flop,
                "saw_turn": s.saw_turn,
                "saw_river": s.saw_river,
                "cbet_opportunity_flop": s.cbet_opportunity_flop,
                "cbet_made_flop": s.cbet_made_flop,
                "faced_cbet_flop": s.faced_cbet_flop,
                "folded_to_cbet_flop": s.folded_to_cbet_flop,
                "called_cbet_flop": s.called_cbet_flop,
                "raised_cbet_flop": s.raised_cbet_flop,
                "went_to_showdown": s.went_to_showdown,
                "won_at_showdown": s.won_at_showdown
            })

        return {
            "player_name": player_name,
            "total_hands": len(summaries),
            "sample_hands": result
        }

    except Exception as e:
        logger.error(f"Error debugging player {player_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@app.get(
    "/api/database/stats-debug/{player_name}",
    tags=["Database"],
    summary="Debug player stats calculation",
    description="Show raw counts used for statistics calculation"
)
async def debug_player_stats(player_name: str, db: Session = Depends(get_db)):
    """
    Get raw counts used for calculating player statistics.

    Shows the numerator and denominator for each stat to debug N/A values.
    """
    try:
        from backend.models.database_models import PlayerHandSummary

        summaries = db.query(PlayerHandSummary).filter(
            PlayerHandSummary.player_name == player_name
        ).all()

        if not summaries:
            return {"error": f"No hands found for player {player_name}"}

        def count_true(attr: str) -> int:
            return sum(1 for s in summaries if getattr(s, attr, False))

        total_hands = len(summaries)
        vpip_count = count_true('vpip')
        pfr_count = count_true('pfr')
        faced_raise_count = count_true('faced_raise')
        three_bet_opportunity_count = count_true('three_bet_opportunity')
        made_3bet_count = count_true('made_three_bet')
        faced_3bet_count = count_true('faced_three_bet')
        saw_flop_count = count_true('saw_flop')
        saw_turn_count = count_true('saw_turn')
        saw_river_count = count_true('saw_river')
        cbet_opp_flop = count_true('cbet_opportunity_flop')
        cbet_made_flop = count_true('cbet_made_flop')
        faced_cbet_flop = count_true('faced_cbet_flop')
        folded_to_cbet_flop = count_true('folded_to_cbet_flop')
        went_to_showdown = count_true('went_to_showdown')
        won_at_showdown = count_true('won_at_showdown')

        return {
            "player_name": player_name,
            "total_hands": total_hands,
            "counts": {
                "vpip": f"{vpip_count}/{total_hands} = {round(vpip_count/total_hands*100, 1)}%" if total_hands > 0 else "0/0",
                "pfr": f"{pfr_count}/{total_hands} = {round(pfr_count/total_hands*100, 1)}%" if total_hands > 0 else "0/0",
                "three_bet": f"{made_3bet_count}/{three_bet_opportunity_count} = {round(made_3bet_count/three_bet_opportunity_count*100, 1) if three_bet_opportunity_count > 0 else 'N/A'}",
                "fold_to_three_bet": f"{count_true('folded_to_three_bet')}/{faced_3bet_count} = {round(count_true('folded_to_three_bet')/faced_3bet_count*100, 1) if faced_3bet_count > 0 else 'N/A'}",
                "cbet_flop": f"{cbet_made_flop}/{cbet_opp_flop} = {round(cbet_made_flop/cbet_opp_flop*100, 1) if cbet_opp_flop > 0 else 'N/A'}",
                "fold_to_cbet_flop": f"{folded_to_cbet_flop}/{faced_cbet_flop} = {round(folded_to_cbet_flop/faced_cbet_flop*100, 1) if faced_cbet_flop > 0 else 'N/A'}",
                "wtsd": f"{went_to_showdown}/{saw_flop_count} = {round(went_to_showdown/saw_flop_count*100, 1) if saw_flop_count > 0 else 'N/A'}",
                "wsd": f"{won_at_showdown}/{went_to_showdown} = {round(won_at_showdown/went_to_showdown*100, 1) if went_to_showdown > 0 else 'N/A'}"
            },
            "raw_counts": {
                "total_hands": total_hands,
                "vpip_count": vpip_count,
                "pfr_count": pfr_count,
                "faced_raise_count": faced_raise_count,
                "made_3bet_count": made_3bet_count,
                "faced_3bet_count": faced_3bet_count,
                "saw_flop_count": saw_flop_count,
                "saw_turn_count": saw_turn_count,
                "saw_river_count": saw_river_count,
                "cbet_opp_flop": cbet_opp_flop,
                "cbet_made_flop": cbet_made_flop,
                "faced_cbet_flop": faced_cbet_flop,
                "folded_to_cbet_flop": folded_to_cbet_flop,
                "went_to_showdown": went_to_showdown,
                "won_at_showdown": won_at_showdown
            }
        }

    except Exception as e:
        logger.error(f"Error debugging stats for {player_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@app.get(
    "/api/database/test-calculation/{player_name}",
    tags=["Database"],
    summary="Test stats calculation",
    description="Calculate stats without saving to database"
)
async def test_stats_calculation(player_name: str, db: Session = Depends(get_db)):
    """
    Test what stats would be calculated for a player without saving.
    """
    try:
        from backend.services.database_service import DatabaseService
        from backend.models.database_models import PlayerHandSummary

        service = DatabaseService(db)

        summaries = db.query(PlayerHandSummary).filter(
            PlayerHandSummary.player_name == player_name
        ).all()

        if not summaries:
            return {"error": f"No hands found for player {player_name}"}

        # Calculate stats
        stats = service._calculate_traditional_stats(summaries)

        return {
            "player_name": player_name,
            "calculated_stats": stats,
            "note": "These are the stats that WOULD be saved to player_stats table"
        }

    except Exception as e:
        logger.error(f"Error testing calculation for {player_name}: {str(e)}")
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@app.delete(
    "/api/database/clear",
    tags=["Database"],
    summary="Clear all player data (preserves GTO data)",
    description="Delete all player/hand data but preserve GTO reference data."
)
async def clear_database(
    db: Session = Depends(get_db)
):
    """
    Clear all player data from the database while preserving GTO reference data.

    WARNING: This is a destructive operation that cannot be undone.

    Deletes all data from:
    - hand_actions
    - player_preflop_actions
    - player_scenario_stats
    - raw_hands
    - player_stats
    - upload_sessions

    Preserves:
    - gto_scenarios (188 preflop scenarios)
    - gto_frequencies (53,532 combo-level frequencies)

    Returns:
        Confirmation message with counts of deleted records
    """
    try:
        from sqlalchemy import text

        # Count records before deletion
        counts_before = {}
        # Order matters - delete child tables before parent tables (foreign keys)
        tables_to_clear = [
            'hero_gto_mistakes',      # FK to raw_hands
            'missed_exploits',        # FK to sessions/players
            'session_gto_summary',    # FK to sessions
            'opponent_session_stats', # FK to sessions
            'sessions',               # FK to player_stats
            'hand_actions',           # FK to raw_hands
            'player_preflop_actions',
            'player_scenario_stats',
            'raw_hands',
            'player_stats',
            'upload_sessions',
            'claude_messages',        # FK to claude_conversations
            'claude_conversations',
        ]

        for table in tables_to_clear:
            try:
                result = db.execute(text(f'SELECT COUNT(*) FROM {table}'))
                counts_before[table] = result.scalar()
            except:
                counts_before[table] = 0

        # Get preserved counts
        gto_scenarios = db.execute(text('SELECT COUNT(*) FROM gto_scenarios')).scalar()
        gto_frequencies = db.execute(text('SELECT COUNT(*) FROM gto_frequencies')).scalar()

        logger.warning("Starting database reset operation (preserving GTO data)")

        # Use TRUNCATE CASCADE to handle all foreign key dependencies automatically
        # This is faster and handles circular/complex FK relationships
        tables_str = ', '.join(tables_to_clear)
        try:
            db.execute(text(f'TRUNCATE TABLE {tables_str} CASCADE'))
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"TRUNCATE failed: {e}, trying individual deletes...")
            # Fallback: delete with CASCADE on each table
            for table in tables_to_clear:
                try:
                    db.execute(text(f'TRUNCATE TABLE {table} CASCADE'))
                except Exception as e2:
                    logger.warning(f"Could not clear {table}: {e2}")
            db.commit()

        total_deleted = sum(counts_before.values())
        logger.warning(f"Database reset complete: {total_deleted} total rows deleted, GTO data preserved")

        return {
            "message": "Database reset successfully (GTO data preserved)",
            "deleted": counts_before,
            "total_deleted": total_deleted,
            "preserved": {
                "gto_scenarios": gto_scenarios,
                "gto_frequencies": gto_frequencies
            }
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error resetting database: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting database: {str(e)}"
        )


@app.get(
    "/api/database/reset-preview",
    tags=["Database"],
    summary="Preview what would be deleted in a reset",
    description="Shows counts of data that would be deleted vs preserved"
)
async def reset_preview(db: Session = Depends(get_db)):
    """
    Preview what data would be deleted in a reset operation.

    Returns counts for both data that would be deleted and data that would be preserved.
    """
    try:
        from sqlalchemy import text

        # Tables to delete (all player/session data)
        tables_to_delete = [
            ('raw_hands', 'Hand histories'),
            ('hand_actions', 'Hand actions'),
            ('hero_gto_mistakes', 'Hero GTO mistakes'),
            ('missed_exploits', 'Missed exploits'),
            ('sessions', 'Sessions'),
            ('session_gto_summary', 'Session GTO summaries'),
            ('opponent_session_stats', 'Opponent session stats'),
            ('player_preflop_actions', 'Player preflop actions'),
            ('player_scenario_stats', 'Player scenario stats'),
            ('player_stats', 'Player stats'),
            ('upload_sessions', 'Upload sessions'),
            ('claude_conversations', 'Claude conversations'),
            ('claude_messages', 'Claude messages'),
        ]

        to_delete = {}
        for table, description in tables_to_delete:
            try:
                count = db.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
                to_delete[table] = count
            except:
                to_delete[table] = 0

        # Tables to preserve
        gto_scenarios = db.execute(text('SELECT COUNT(*) FROM gto_scenarios')).scalar()
        gto_frequencies = db.execute(text('SELECT COUNT(*) FROM gto_frequencies')).scalar()

        return {
            "to_delete": to_delete,
            "to_preserve": {
                "gto_scenarios": gto_scenarios,
                "gto_frequencies": gto_frequencies
            }
        }

    except Exception as e:
        logger.error(f"Error getting reset preview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting reset preview: {str(e)}"
        )


@app.get(
    "/api/uploads",
    tags=["Database"],
    summary="Get upload history",
    description="Returns list of all upload sessions with details"
)
async def get_upload_sessions(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of uploads to return"),
    offset: int = Query(0, ge=0, description="Number of uploads to skip")
):
    """
    Get upload history showing all hand history file uploads.

    Returns list of uploads with filename, date, hands parsed, and status.
    """
    try:
        from sqlalchemy import text

        # Get upload sessions ordered by most recent first
        result = db.execute(text('''
            SELECT
                session_id,
                filename,
                upload_timestamp,
                hands_parsed,
                hands_failed,
                players_updated,
                stake_level,
                status,
                error_message,
                processing_time_seconds
            FROM upload_sessions
            ORDER BY upload_timestamp DESC
            LIMIT :limit OFFSET :offset
        '''), {"limit": limit, "offset": offset})

        uploads = []
        for row in result:
            uploads.append({
                "session_id": row[0],
                "filename": row[1],
                "upload_timestamp": row[2].isoformat() if row[2] else None,
                "hands_parsed": row[3],
                "hands_failed": row[4],
                "players_updated": row[5],
                "stake_level": row[6],
                "status": row[7],
                "error_message": row[8],
                "processing_time_seconds": row[9]
            })

        # Get total count
        total = db.execute(text('SELECT COUNT(*) FROM upload_sessions')).scalar()

        return {
            "uploads": uploads,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error getting upload sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting upload sessions: {str(e)}"
        )


@app.post(
    "/api/query/claude",
    response_model=ClaudeQueryResponse,
    tags=["Claude AI"],
    summary="Query Claude AI",
    description="Ask natural language questions about poker data and receive strategic analysis"
)
async def query_claude(
    request: ClaudeQueryRequest,
    db: Session = Depends(get_db)
):
    """
    Query Claude AI with natural language.

    Users can ask ANY question about their poker database and receive:
    - Sophisticated statistical analysis
    - Strategic recommendations
    - Player type classifications
    - Exploit suggestions based on composite metrics

    Example queries:
    - "Who are the most exploitable players at NL50?"
    - "Show me all TAGs with high pressure vulnerability"
    - "Which players fold too much to 3-bets from the button?"
    - "Analyze my performance against LAG players"

    Args:
        request: ClaudeQueryRequest with query and optional conversation history
        db: Database session (injected)

    Returns:
        ClaudeQueryResponse with analysis and recommendations
    """
    try:
        logger.info(f"Processing Claude query: {request.query[:100]}...")

        # Get or create conversation
        conversation_id = request.conversation_id
        if conversation_id:
            # Load existing conversation
            conversation = db.query(ClaudeConversation).filter(
                ClaudeConversation.conversation_id == conversation_id
            ).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # Create new conversation with auto-generated title from first query
            title = request.query[:100] + ("..." if len(request.query) > 100 else "")
            conversation = ClaudeConversation(title=title)
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            conversation_id = conversation.conversation_id

        # Save user message
        user_message = ClaudeMessage(
            conversation_id=conversation_id,
            role="user",
            content=request.query
        )
        db.add(user_message)
        db.commit()

        # Initialize Claude service
        claude_service = ClaudeService(db)

        # Process query
        try:
            result = claude_service.query(
                user_query=request.query,
                conversation_history=request.conversation_history
            )
        except Exception as query_error:
            # If query processing fails, rollback and re-raise
            logger.error(f"Claude query processing failed: {str(query_error)}")
            db.rollback()
            raise

        # Convert tool calls to Pydantic models if present
        tool_calls = None
        tool_calls_json = None
        if result.get("tool_calls"):
            tool_calls = [
                ClaudeToolCall(**tc) for tc in result["tool_calls"]
            ]
            tool_calls_json = result.get("tool_calls")

        # Save assistant message
        try:
            assistant_message = ClaudeMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=result.get("response", ""),
                tool_calls=tool_calls_json,
                usage=result.get("usage")
            )
            db.add(assistant_message)
            db.commit()
        except Exception as save_error:
            logger.error(f"Failed to save assistant message: {str(save_error)}")
            db.rollback()
            # Still return the response even if we couldn't save it
            logger.warning("Continuing with response despite save failure")

        return ClaudeQueryResponse(
            success=result["success"],
            response=result.get("response", ""),
            tool_calls=tool_calls,
            usage=result.get("usage"),
            error=result.get("error"),
            conversation_id=conversation_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Claude query: {str(e)}", exc_info=True)
        return ClaudeQueryResponse(
            success=False,
            response="I apologize, but I encountered an error processing your query. Please try rephrasing your question.",
            error=str(e)
        )

@app.post(
    "/api/admin/run-migration",
    tags=["Admin"],
    summary="Run pending database migrations",
    description="Runs the conversation tables migration. Safe to call multiple times. Requires API key."
)
async def run_migration(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Run database migrations for conversation tables.

    This endpoint is safe to call multiple times - it will only create tables if they don't exist.
    """
    try:
        from pathlib import Path
        from sqlalchemy import text

        migration_file = Path(__file__).parent / "migrations" / "005_add_claude_conversations.sql"

        if not migration_file.exists():
            raise HTTPException(status_code=500, detail="Migration file not found")

        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        # Execute migration
        db.execute(text(migration_sql))
        db.commit()

        # Verify tables exist
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name IN ('claude_conversations', 'claude_messages')
        """))
        table_count = result.scalar()

        return {
            "success": True,
            "message": "Migration completed successfully",
            "tables_created": table_count
        }

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}"
        )


# ========================================
# Error Handlers
# ========================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "timestamp": datetime.now().isoformat()
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.now().isoformat()
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


# ========================================
# Startup/Shutdown Events
# ========================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("Starting Poker Analysis API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"CORS origins: {settings.allowed_origins_list}")

    # Check database connection (non-blocking, just log result)
    # Don't fail startup if DB check fails - let requests handle it
    try:
        if check_db_connection():
            logger.info("Database connection successful")
        else:
            logger.warning("Database connection check returned False - connections may be available later")
    except Exception as e:
        logger.warning(f"Database connection check failed with error: {e} - will retry on requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("Shutting down Poker Analysis API")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.environment == "development"
    )
