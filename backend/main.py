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
from backend.services.database_service import DatabaseConnectionError
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
    except DatabaseConnectionError as e:
        logger.error(f"Database connection error for player profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again."
        )
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
    except DatabaseConnectionError as e:
        logger.error(f"Database connection error for player leaks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again."
        )
    except Exception as e:
        logger.error(f"Error getting player leaks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving player leak analysis"
        )


@app.get(
    "/api/improvement-advice",
    response_model=Dict[str, Any],
    tags=["Analysis"],
    summary="Get improvement advice for a leak",
    description="Get tiered improvement advice (quick fix, detailed, study resources) for a specific leak"
)
async def get_improvement_advice_endpoint(
    leak_category: str = Query(..., description="Leak category: opening, defense, facing_3bet, facing_4bet"),
    leak_direction: str = Query(..., description="Leak direction: too_tight or too_loose"),
    position: str = Query(..., description="Player position: UTG, MP, CO, BTN, SB, BB"),
    vs_position: Optional[str] = Query(None, description="Opponent position for defense/facing scenarios"),
    player_value: float = Query(..., description="Player's frequency for this action"),
    gto_value: float = Query(..., description="GTO frequency for this action"),
    sample_size: int = Query(100, description="Number of hands in sample"),
    db: Session = Depends(get_db)
):
    """
    Get tiered improvement advice for a specific leak.

    Returns:
    - Tier 1: Quick fix (2-3 hands to add/remove, simple heuristic)
    - Tier 2: Detailed explanation (range construction, hand categories)
    - Tier 3: Study resources (concepts, solver scenarios, exercises)
    """
    from backend.services.improvement_advice import get_improvement_advice, advice_to_dict

    try:
        # Validate inputs
        valid_categories = ["opening", "defense", "facing_3bet", "facing_4bet"]
        valid_directions = ["too_tight", "too_loose"]
        valid_positions = ["UTG", "MP", "HJ", "CO", "BTN", "SB", "BB"]

        if leak_category not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid leak_category. Must be one of: {valid_categories}"
            )

        if leak_direction not in valid_directions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid leak_direction. Must be one of: {valid_directions}"
            )

        position = position.upper()
        if position not in valid_positions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid position. Must be one of: {valid_positions}"
            )

        # Get the advice
        advice = get_improvement_advice(
            leak_category=leak_category,
            leak_direction=leak_direction,
            position=position,
            vs_position=vs_position.upper() if vs_position else None,
            player_value=player_value,
            gto_value=gto_value,
            sample_size=sample_size
        )

        return advice_to_dict(advice)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting improvement advice: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating improvement advice"
        )


@app.post(
    "/api/improvement-advice/ai",
    response_model=Dict[str, Any],
    tags=["Analysis"],
    summary="Get AI-enhanced improvement advice",
    description="Get personalized AI-generated improvement advice based on player's specific patterns"
)
async def get_ai_improvement_advice(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Get AI-enhanced improvement advice for a specific leak.

    Request body:
    - leak_category: opening, defense, facing_3bet, facing_4bet
    - leak_direction: too_tight or too_loose
    - position: Player position
    - vs_position: Opponent position (optional)
    - player_value: Player's frequency
    - gto_value: GTO frequency
    - sample_size: Number of hands
    - player_name: Optional player name for personalized analysis
    - additional_context: Optional additional context about the player

    Returns AI-generated personalized advice including:
    - Specific hand recommendations based on patterns
    - Personalized study plan
    - Common mistakes analysis
    """
    from backend.services.improvement_advice import get_improvement_advice, advice_to_dict
    from sqlalchemy import text

    try:
        # Extract parameters
        leak_category = request.get("leak_category")
        leak_direction = request.get("leak_direction")
        position = request.get("position", "").upper()
        vs_position = request.get("vs_position")
        player_value = request.get("player_value", 0)
        gto_value = request.get("gto_value", 0)
        sample_size = request.get("sample_size", 100)
        player_name = request.get("player_name")

        # First get the static advice
        static_advice = get_improvement_advice(
            leak_category=leak_category,
            leak_direction=leak_direction,
            position=position,
            vs_position=vs_position.upper() if vs_position else None,
            player_value=player_value,
            gto_value=gto_value,
            sample_size=sample_size
        )
        static_dict = advice_to_dict(static_advice)

        # Fetch REAL hand deviations data if player_name is provided
        real_deviations = []
        missing_hands = []
        hands_by_action_data = {}  # For sparse sample fallback
        if player_name:
            try:
                # Call the hand deviations logic inline (avoiding circular request)
                validated_name = InputValidator.validate_player_name(player_name)
                vs_pos_upper = vs_position.upper() if vs_position else None

                # Helper function to normalize hole cards
                def normalize_to_combo(hole_cards: str):
                    if not hole_cards:
                        return None
                    cards = hole_cards.strip().split()
                    if len(cards) != 2:
                        return None
                    rank_order = "23456789TJQKA"
                    card1, card2 = cards[0], cards[1]
                    r1, s1 = card1[0].upper(), card1[1].lower()
                    r2, s2 = card2[0].upper(), card2[1].lower()
                    if rank_order.index(r1) < rank_order.index(r2):
                        r1, r2 = r2, r1
                        s1, s2 = s2, s1
                    if r1 == r2:
                        return f"{r1}{r2}"
                    elif s1 == s2:
                        return f"{r1}{r2}s"
                    else:
                        return f"{r1}{r2}o"

                # Build scenario query
                if leak_category == 'opening':
                    hands_query = text("""
                        SELECT
                            (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                            CASE WHEN phs.pfr = true THEN 'open' WHEN phs.vpip = false THEN 'fold' ELSE 'limp' END as player_action
                        FROM player_hand_summary phs
                        JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                        WHERE phs.player_name = :player_name AND phs.position = :position AND phs.faced_raise = false
                    """)
                    params = {"player_name": validated_name, "position": position}
                elif leak_category == 'defense':
                    hands_query = text("""
                        SELECT
                            (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                            CASE WHEN phs.vpip = false THEN 'fold' WHEN phs.made_three_bet = true THEN '3bet' ELSE 'call' END as player_action
                        FROM player_hand_summary phs
                        JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                        WHERE phs.player_name = :player_name AND phs.position = :position
                        AND phs.faced_raise = true AND phs.faced_three_bet = false
                        AND (:vs_position IS NULL OR phs.raiser_position = :vs_position)
                    """)
                    params = {"player_name": validated_name, "position": position, "vs_position": vs_pos_upper}
                else:  # facing_3bet
                    hands_query = text("""
                        SELECT
                            (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                            CASE WHEN phs.folded_to_three_bet = true THEN 'fold' WHEN phs.four_bet = true THEN '4bet' ELSE 'call' END as player_action
                        FROM player_hand_summary phs
                        JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                        WHERE phs.player_name = :player_name AND phs.position = :position
                        AND phs.faced_three_bet = true AND phs.pfr = true
                    """)
                    params = {"player_name": validated_name, "position": position}

                result = db.execute(hands_query, params)
                rows = list(result)

                # Count player actions by combo
                hand_actions = {}
                for row in rows:
                    combo = normalize_to_combo(row[0])
                    if not combo:
                        continue
                    if combo not in hand_actions:
                        hand_actions[combo] = {}
                    action = row[1]
                    hand_actions[combo][action] = hand_actions[combo].get(action, 0) + 1

                # Get GTO frequencies
                # For defense/facing scenarios, we need to:
                # 1. Filter by opponent position if available
                # 2. Sum call + 3bet/4bet within each opponent position
                # 3. Average across opponent positions if no specific vs_position
                if leak_category == 'opening':
                    gto_query = text("""
                        SELECT gf.hand, gf.frequency * 100 FROM gto_frequencies gf
                        JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
                        WHERE gs.category = 'opening' AND gs.position = :position AND gs.action = 'open'
                    """)
                    gto_params = {"position": position}
                    gto_result = db.execute(gto_query, gto_params)
                    gto_freqs = {}
                    for row in gto_result:
                        hand = row[0].replace(' ', '')
                        if len(hand) >= 4:
                            r1, s1, r2, s2 = hand[0].upper(), hand[1].lower(), hand[2].upper(), hand[3].lower()
                            rank_order = "23456789TJQKA"
                            if rank_order.index(r1) < rank_order.index(r2):
                                r1, r2, s1, s2 = r2, r1, s2, s1
                            combo = f"{r1}{r2}" if r1 == r2 else (f"{r1}{r2}s" if s1 == s2 else f"{r1}{r2}o")
                        else:
                            combo = hand.upper()
                        gto_freqs[combo] = float(row[1]) if row[1] else 0
                else:
                    # For defense/facing scenarios: get defend frequency (call + 3bet/4bet)
                    # grouped by opponent position, then average across positions
                    if leak_category == 'defense':
                        action1, action2 = 'call', '3bet'
                    else:  # facing_3bet
                        action1, action2 = 'call', '4bet'

                    if vs_pos_upper:
                        # Specific opponent position - sum call + 3bet/4bet
                        gto_query = text("""
                            SELECT gf.hand, SUM(gf.frequency * 100) as total_freq
                            FROM gto_frequencies gf
                            JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
                            WHERE gs.category = :category AND gs.position = :position
                            AND gs.opponent_position = :vs_position
                            AND gs.action IN (:action1, :action2)
                            GROUP BY gf.hand
                        """)
                        gto_params = {"category": leak_category, "position": position,
                                     "vs_position": vs_pos_upper, "action1": action1, "action2": action2}
                    else:
                        # No specific opponent - average across all opponent positions
                        gto_query = text("""
                            SELECT hand, AVG(defend_freq) as avg_freq FROM (
                                SELECT gf.hand, gs.opponent_position, SUM(gf.frequency * 100) as defend_freq
                                FROM gto_frequencies gf
                                JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
                                WHERE gs.category = :category AND gs.position = :position
                                AND gs.action IN (:action1, :action2)
                                GROUP BY gf.hand, gs.opponent_position
                            ) sub
                            GROUP BY hand
                        """)
                        gto_params = {"category": leak_category, "position": position,
                                     "action1": action1, "action2": action2}

                    gto_result = db.execute(gto_query, gto_params)
                    gto_freqs = {}
                    for row in gto_result:
                        hand = row[0].replace(' ', '')
                        if len(hand) >= 4:
                            r1, s1, r2, s2 = hand[0].upper(), hand[1].lower(), hand[2].upper(), hand[3].lower()
                            rank_order = "23456789TJQKA"
                            if rank_order.index(r1) < rank_order.index(r2):
                                r1, r2, s1, s2 = r2, r1, s2, s1
                            combo = f"{r1}{r2}" if r1 == r2 else (f"{r1}{r2}s" if s1 == s2 else f"{r1}{r2}o")
                        else:
                            combo = hand.upper()
                        gto_freqs[combo] = float(row[1]) if row[1] else 0

                # Calculate player frequencies and actions for ALL hands
                player_data = {}  # combo -> {freq, actions, sample}
                for combo, actions in hand_actions.items():
                    total = sum(actions.values())
                    if leak_category == 'opening':
                        freq = (actions.get('open', 0) / total) * 100 if total > 0 else 0
                        player_action = 'open' if freq > 50 else 'fold'
                    else:
                        fold_count = actions.get('fold', 0)
                        freq = ((total - fold_count) / total) * 100 if total > 0 else 0
                        if actions.get('3bet', 0) > actions.get('call', 0):
                            player_action = '3bet'
                        elif actions.get('call', 0) > 0:
                            player_action = 'call'
                        else:
                            player_action = 'fold'
                    player_data[combo] = {"freq": freq, "action": player_action, "sample": total}

                # COMPREHENSIVE RANGE ANALYSIS: Categorize ALL hands
                # Categories: overfolds, overcalls, correct_defends, correct_folds
                overfolds = []      # GTO defends, player folds
                overcalls = []      # GTO folds, player defends
                correct_defends = []
                correct_folds = []
                no_data_should_defend = []  # GTO defends but no sample

                for combo, gto_freq in gto_freqs.items():
                    gto_defends = gto_freq >= 30  # GTO plays this hand
                    gto_folds = gto_freq < 15     # GTO folds this hand

                    if combo in player_data:
                        pd = player_data[combo]
                        player_defends = pd["freq"] >= 50

                        if gto_defends and not player_defends:
                            # LEAK: Overfolding - GTO defends but player folds
                            overfolds.append({"hand": combo, "gto": round(gto_freq), "action": pd["action"]})
                        elif gto_folds and player_defends:
                            # LEAK: Overcalling - GTO folds but player defends
                            overcalls.append({"hand": combo, "gto": round(gto_freq), "action": pd["action"]})
                        elif player_defends:
                            correct_defends.append(combo)
                        else:
                            correct_folds.append(combo)
                    else:
                        # No sample for this hand
                        if gto_freq >= 50:  # GTO strongly defends
                            no_data_should_defend.append({"hand": combo, "gto": round(gto_freq)})

                # Also check player hands NOT in GTO - these are overcalls (GTO folds 100%)
                for combo, pd in player_data.items():
                    if combo not in gto_freqs and pd["freq"] >= 50:
                        # Player defends a hand GTO doesn't play at all
                        overcalls.append({"hand": combo, "gto": 0, "action": pd["action"]})

                # Sort leaks by GTO frequency (biggest misses first)
                overfolds.sort(key=lambda x: x["gto"], reverse=True)
                overcalls.sort(key=lambda x: x["gto"])  # Lowest GTO first (worst overcalls)
                no_data_should_defend.sort(key=lambda x: x["gto"], reverse=True)

                # Helper to categorize hands for pattern analysis
                def categorize_hand(h):
                    if len(h) == 2:  # Pair like "AA", "77"
                        rank = h[0]
                        if rank in "AKQJ":
                            return "premium_pairs"
                        elif rank in "T98":
                            return "medium_pairs"
                        else:
                            return "small_pairs"
                    elif h.endswith('s'):  # Suited
                        if h[0] == 'A':
                            return "suited_aces"
                        elif h[0] in "KQJ" and h[1] in "AKQJT":
                            return "suited_broadways"
                        elif abs(ord(h[0]) - ord(h[1])) == 1:
                            return "suited_connectors"
                        else:
                            return "suited_other"
                    else:  # Offsuit
                        if h[0] in "AKQ" and h[1] in "AKQJT":
                            return "offsuit_broadways"
                        else:
                            return "offsuit_other"

                # Group leaks by category for pattern recognition
                overfold_groups = {}
                for h in overfolds:
                    cat = categorize_hand(h["hand"])
                    if cat not in overfold_groups:
                        overfold_groups[cat] = []
                    overfold_groups[cat].append(f"{h['hand']}({h['gto']}%)")

                overcall_groups = {}
                for h in overcalls:
                    cat = categorize_hand(h["hand"])
                    if cat not in overcall_groups:
                        overcall_groups[cat] = []
                    overcall_groups[cat].append(f"{h['hand']}({h['gto']}%)")

                # Store for prompt and response
                real_deviations = overfolds[:10]  # Top overfolds for UI
                missing_hands = [{"hand": h["hand"], "gto_freq": h["gto"]} for h in no_data_should_defend[:5]]

                # Build comprehensive analysis data
                hands_by_action_data = {
                    "overfolds": overfolds,
                    "overcalls": overcalls,
                    "overfold_groups": overfold_groups,
                    "overcall_groups": overcall_groups,
                    "correct_defends": correct_defends,
                    "correct_folds": correct_folds,
                    "no_data_should_defend": no_data_should_defend,
                    "total_gto_hands": len(gto_freqs),
                    "total_player_hands": len(player_data)
                }

            except Exception as e:
                logger.warning(f"Could not fetch hand deviations: {e}")

        # Build prompt for AI enhancement with REAL data
        # IMPORTANT: Frontend may pass FOLD rates for defense/facing scenarios
        # (e.g., gto_value=85% meaning GTO folds 85%). We need to convert to DEFEND rates.
        # Detection: if gto_value > 50% for defense scenarios, it's likely a fold rate
        if leak_category in ("defense", "facing_3bet", "facing_4bet") and gto_value > 50:
            # Convert fold rates to defend rates
            player_value = 100 - player_value
            gto_value = 100 - gto_value
            logger.info(f"Converted fold rates to defend rates: player={player_value:.1f}%, gto={gto_value:.1f}%")

        deviation = player_value - gto_value

        # Determine actual direction from the values
        # For all scenarios: player < GTO means too tight, player > GTO means too loose
        actual_direction = "too_tight" if player_value < gto_value else "too_loose"

        # Determine action context based on leak
        if leak_category == "opening":
            action_context = "opening/raising first in"
            if actual_direction == "too_tight":
                adjustment = "ADD more hands to your opening range"
            else:
                adjustment = "REMOVE marginal hands from your opening range"
        elif leak_category == "defense":
            action_context = "defending vs opens (calling or 3-betting)"
            if actual_direction == "too_tight":
                adjustment = "DEFEND more hands - you're folding too much"
            else:
                adjustment = "FOLD more hands - you're defending too wide"
        elif leak_category == "facing_3bet":
            action_context = "responding to 3-bets (calling or 4-betting)"
            if actual_direction == "too_tight":
                adjustment = "CONTINUE more vs 3-bets - add calls and 4-bet bluffs"
            else:
                adjustment = "FOLD more to 3-bets - you're continuing too wide"
        else:
            action_context = leak_category
            adjustment = "Adjust your frequency closer to GTO"

        # Build comprehensive range analysis for prompt using categorized format
        analysis_text = ""

        if hands_by_action_data:
            hba = hands_by_action_data

            # LEAKS SECTION - Overfolds (GTO defends but player folds)
            if hba.get('overfold_groups'):
                analysis_text += "\n\n=== SIGNIFICANT LEAKS: OVERFOLDING ===\n"
                analysis_text += "(GTO defends these hands but you folded - add to your range)\n"
                for category, hands in hba['overfold_groups'].items():
                    cat_name = category.replace('_', ' ').title()
                    analysis_text += f"\n{cat_name}: {', '.join(hands)}"

            # LEAKS SECTION - Overcalls (GTO folds but player defends)
            if hba.get('overcall_groups'):
                analysis_text += "\n\n=== SIGNIFICANT LEAKS: OVERCALLING ===\n"
                analysis_text += "(GTO folds these hands but you defended - remove from your range)\n"
                for category, hands in hba['overcall_groups'].items():
                    cat_name = category.replace('_', ' ').title()
                    analysis_text += f"\n{cat_name}: {', '.join(hands)}"

            # NOTE: We intentionally omit "hands missing from range" because no sample
            # doesn't mean folding - the player may never have been dealt those cards.
            # We can only analyze hands we actually observed.

            # CORRECT PLAYS - Summarized
            correct_d = hba.get('correct_defends', [])
            correct_f = hba.get('correct_folds', [])
            if correct_d or correct_f:
                analysis_text += "\n\n=== CORRECT PLAYS (no action needed) ===\n"
                if correct_d:
                    analysis_text += f"Correct defends ({len(correct_d)}): {', '.join(sorted(correct_d))}\n"
                if correct_f:
                    analysis_text += f"Correct folds ({len(correct_f)}): {', '.join(sorted(correct_f))}\n"

            # Summary stats
            total_overfolds = len(hba.get('overfolds', []))
            total_overcalls = len(hba.get('overcalls', []))
            analysis_text += f"\n\n=== SUMMARY ===\n"
            analysis_text += f"Total leaks: {total_overfolds} overfolds, {total_overcalls} overcalls\n"
            analysis_text += f"Hands analyzed: {hba.get('total_player_hands', 0)} player / {hba.get('total_gto_hands', 0)} GTO combos"

            # Flag contradictions between aggregate and hand analysis
            if actual_direction == "too_tight" and total_overfolds == 0:
                analysis_text += "\n\nNOTE: Aggregate stats suggest underdefending, but no specific overfolds found in sample. "
                analysis_text += "Player may be defending GTO hands correctly but at lower frequency than optimal, "
                analysis_text += "or sample size is too small to detect specific leaks."
            elif actual_direction == "too_loose" and total_overcalls == 0:
                analysis_text += "\n\nNOTE: Aggregate stats suggest overdefending, but no specific overcalls found in sample. "
                analysis_text += "Focus on tightening up borderline hands."

        # Fallback if no comprehensive data
        elif real_deviations:
            analysis_text = "\n\nRANGE DEVIATIONS:\n"
            for d in real_deviations:
                analysis_text += f"- {d['hand']}: GTO {d.get('gto', d.get('gto_freq', 0))}%\n"

        prompt = f"""You are an expert poker coach. Analyze this preflop leak and provide specific improvement advice.

LEAK DETAILS:
- Scenario: {leak_category.replace('_', ' ').title()} from {position}{f' vs {vs_position}' if vs_position else ''}
- Player's {action_context} frequency: {player_value:.1f}%
- GTO optimal frequency: {gto_value:.1f}%
- Deviation: {deviation:+.1f}% ({actual_direction.replace('_', ' ')})
- Sample size: {sample_size} hands

The player needs to {adjustment}.
{analysis_text}

Based on the COMPREHENSIVE RANGE ANALYSIS above, provide your response as valid JSON with this exact structure:
{{
  "hand_recommendations": [
    {{"hand": "AJs", "action": "add/remove", "reason": "brief reason"}},
    {{"hand": "KQo", "action": "add/remove", "reason": "brief reason"}}
  ],
  "pattern_analysis": "What this leak suggests about their overall game based on the specific hands shown",
  "study_plan": ["Exercise 1", "Exercise 2", "Exercise 3"],
  "quick_adjustment": "One simple rule to apply immediately"
}}

IMPORTANT:
- Focus on OVERFOLDING section (hands to ADD) and OVERCALLING section (hands to REMOVE)
- Look for PATTERNS in hand categories (e.g., "folding too many suited connectors")
- Hands in MISSING section are likely leaks too - player probably folds these
- Use standard poker notation (AKs, AKo, JJ, T9s, etc.)
Only respond with the JSON object, no additional text."""

        # Call Claude directly without database tools
        from anthropic import Anthropic
        from backend.config import get_settings
        import json
        import re

        settings = get_settings()
        client = Anthropic(api_key=settings.anthropic_api_key)

        ai_advice = {}
        raw_response_text = ""
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )

            raw_response_text = response.content[0].text if response.content else ""
            logger.info(f"AI advice response: {raw_response_text[:200]}...")

            # Try to parse JSON from response
            # First try direct parse
            try:
                ai_advice = json.loads(raw_response_text)
            except json.JSONDecodeError:
                # Try to find JSON block in response
                json_match = re.search(r'\{[\s\S]*\}', raw_response_text)
                if json_match:
                    try:
                        ai_advice = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        ai_advice = {"raw_advice": raw_response_text}
                else:
                    ai_advice = {"raw_advice": raw_response_text}

        except Exception as e:
            logger.error(f"Claude API error: {str(e)}")
            ai_advice = {"raw_advice": f"AI analysis unavailable: {str(e)}"}
            raw_response_text = str(e)

        # Combine static and AI advice with REAL data
        result = {
            **static_dict,
            "ai_enhanced": {
                "hand_recommendations": ai_advice.get("hand_recommendations", []),
                "pattern_analysis": ai_advice.get("pattern_analysis", ""),
                "study_plan": ai_advice.get("study_plan", []),
                "quick_adjustment": ai_advice.get("quick_adjustment", ""),
                "raw_response": ai_advice.get("raw_advice") if "raw_advice" in ai_advice else None
            },
            # Include the REAL deviations data from player's hands
            "real_data": {
                "deviations": [d for d in real_deviations if not d.get('_sparse_data')],  # Filter out sparse marker
                "missing_hands": missing_hands,
                "hands_by_action": hands_by_action_data if hands_by_action_data else None,
                "data_available": len(real_deviations) > 0 or len(missing_hands) > 0 or bool(hands_by_action_data)
            },
            # Debug info - prompt and raw response for transparency
            "debug": {
                "prompt": prompt,
                "raw_response": raw_response_text
            }
        }

        return result

    except Exception as e:
        logger.error(f"Error getting AI improvement advice: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating AI improvement advice"
        )


@app.get(
    "/api/players/{player_name}/hand-deviations",
    response_model=Dict[str, Any],
    tags=["Analysis"],
    summary="Get specific hand deviations from GTO",
    description="Compare player's actual hand frequencies to GTO frequencies for a specific scenario"
)
async def get_hand_deviations(
    player_name: str,
    scenario: str = Query(..., description="Scenario: opening, defense, facing_3bet"),
    position: str = Query(..., description="Player position: UTG, MP, CO, BTN, SB, BB"),
    vs_position: Optional[str] = Query(None, description="Opponent position for defense/facing scenarios"),
    db: Session = Depends(get_db)
):
    """
    Get detailed hand-by-hand comparison of player actions vs GTO.

    Returns:
    - List of hands where player deviates from GTO
    - Each hand shows: player frequency, GTO frequency, deviation, recommendation
    - Sorted by impact (biggest deviations first)
    """
    from sqlalchemy import text

    try:
        validated_name = InputValidator.validate_player_name(player_name)
        position = position.upper()
        if vs_position:
            vs_position = vs_position.upper()

        # Helper function to normalize hole cards to combo notation
        def normalize_to_combo(hole_cards: str) -> Optional[str]:
            if not hole_cards:
                return None
            cards = hole_cards.strip().split()
            if len(cards) != 2:
                return None

            rank_order = "23456789TJQKA"
            card1, card2 = cards[0], cards[1]
            r1, s1 = card1[0].upper(), card1[1].lower()
            r2, s2 = card2[0].upper(), card2[1].lower()

            # Ensure higher rank first
            if rank_order.index(r1) < rank_order.index(r2):
                r1, r2 = r2, r1
                s1, s2 = s2, s1

            if r1 == r2:
                return f"{r1}{r2}"
            elif s1 == s2:
                return f"{r1}{r2}s"
            else:
                return f"{r1}{r2}o"

        # Build scenario-specific query to get player hands with hole cards
        if scenario == 'opening':
            hands_query = text("""
                SELECT
                    (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                    CASE
                        WHEN phs.pfr = true THEN 'open'
                        WHEN phs.vpip = false THEN 'fold'
                        ELSE 'limp'
                    END as player_action
                FROM player_hand_summary phs
                JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                WHERE phs.player_name = :player_name
                AND phs.position = :position
                AND phs.faced_raise = false
            """)
            params = {"player_name": validated_name, "position": position}
            gto_action_key = 'open'

        elif scenario == 'defense':
            if vs_position:
                hands_query = text("""
                    SELECT
                        (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                        CASE
                            WHEN phs.vpip = false THEN 'fold'
                            WHEN phs.made_three_bet = true THEN '3bet'
                            ELSE 'call'
                        END as player_action
                    FROM player_hand_summary phs
                    JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                    WHERE phs.player_name = :player_name
                    AND phs.position = :position
                    AND phs.faced_raise = true
                    AND phs.faced_three_bet = false
                    AND phs.raiser_position = :vs_position
                """)
                params = {"player_name": validated_name, "position": position, "vs_position": vs_position}
            else:
                hands_query = text("""
                    SELECT
                        (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                        CASE
                            WHEN phs.vpip = false THEN 'fold'
                            WHEN phs.made_three_bet = true THEN '3bet'
                            ELSE 'call'
                        END as player_action
                    FROM player_hand_summary phs
                    JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                    WHERE phs.player_name = :player_name
                    AND phs.position = :position
                    AND phs.faced_raise = true
                    AND phs.faced_three_bet = false
                """)
                params = {"player_name": validated_name, "position": position}
            gto_action_key = 'call'  # For defense, we compare to continue frequency (call + 3bet)

        elif scenario == 'facing_3bet':
            hands_query = text("""
                SELECT
                    (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                    CASE
                        WHEN phs.folded_to_three_bet = true THEN 'fold'
                        WHEN phs.four_bet = true THEN '4bet'
                        ELSE 'call'
                    END as player_action
                FROM player_hand_summary phs
                JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                WHERE phs.player_name = :player_name
                AND phs.position = :position
                AND phs.faced_three_bet = true
                AND phs.pfr = true
            """)
            params = {"player_name": validated_name, "position": position}
            gto_action_key = 'call'
        else:
            raise HTTPException(status_code=400, detail="Invalid scenario")

        # Execute query
        result = db.execute(hands_query, params)
        rows = list(result)

        # Count player actions by hand combo
        hand_actions: Dict[str, Dict[str, int]] = {}  # combo -> {action -> count}
        for row in rows:
            hole_cards = row[0]
            action = row[1]
            combo = normalize_to_combo(hole_cards)
            if not combo:
                continue

            if combo not in hand_actions:
                hand_actions[combo] = {}
            if action not in hand_actions[combo]:
                hand_actions[combo][action] = 0
            hand_actions[combo][action] += 1

        # Get GTO frequencies for this scenario
        if scenario == 'opening':
            gto_query = text("""
                SELECT gf.hand, gf.frequency * 100 as freq
                FROM gto_frequencies gf
                JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
                WHERE gs.category = 'opening'
                AND gs.position = :position
                AND gs.action = 'open'
            """)
            gto_params = {"position": position}
        elif scenario == 'defense':
            # For defense, get call and 3bet frequencies
            gto_query = text("""
                SELECT gf.hand, gs.action, gf.frequency * 100 as freq
                FROM gto_frequencies gf
                JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
                WHERE gs.category = 'defense'
                AND gs.position = :position
                AND gs.action IN ('call', '3bet')
                AND (gs.opponent_position = :vs_position OR :vs_position IS NULL)
            """)
            gto_params = {"position": position, "vs_position": vs_position}
        else:  # facing_3bet
            gto_query = text("""
                SELECT gf.hand, gs.action, gf.frequency * 100 as freq
                FROM gto_frequencies gf
                JOIN gto_scenarios gs ON gf.scenario_id = gs.scenario_id
                WHERE gs.category = 'facing_3bet'
                AND gs.position = :position
                AND gs.action IN ('call', '4bet')
            """)
            gto_params = {"position": position}

        gto_result = db.execute(gto_query, gto_params)

        # Build GTO lookup - normalize hand notation
        gto_freqs: Dict[str, Dict[str, float]] = {}  # combo -> {action -> freq}
        for row in gto_result:
            if scenario == 'opening':
                hand, freq = row[0], float(row[1]) if row[1] else 0
                action = 'open'
            else:
                hand, action, freq = row[0], row[1], float(row[2]) if row[2] else 0

            # Normalize hand from DB format to combo
            hand = hand.replace(' ', '')
            if len(hand) >= 4:
                r1, s1 = hand[0].upper(), hand[1].lower()
                r2, s2 = hand[2].upper(), hand[3].lower()
                rank_order = "23456789TJQKA"
                if rank_order.index(r1) < rank_order.index(r2):
                    r1, r2 = r2, r1
                    s1, s2 = s2, s1
                if r1 == r2:
                    combo = f"{r1}{r2}"
                elif s1 == s2:
                    combo = f"{r1}{r2}s"
                else:
                    combo = f"{r1}{r2}o"
            elif len(hand) == 2 or len(hand) == 3:
                combo = hand.upper()
            else:
                continue

            if combo not in gto_freqs:
                gto_freqs[combo] = {}
            gto_freqs[combo][action] = freq

        # Calculate GTO continue frequency (sum of non-fold actions)
        gto_continue: Dict[str, float] = {}
        for combo, actions in gto_freqs.items():
            gto_continue[combo] = sum(actions.values())

        # Compare player vs GTO and find deviations
        deviations = []
        for combo, actions in hand_actions.items():
            total = sum(actions.values())
            if total < 2:  # Need at least 2 hands for meaningful comparison
                continue

            # Calculate player frequencies
            if scenario == 'opening':
                player_open_freq = (actions.get('open', 0) / total) * 100
                gto_open_freq = gto_continue.get(combo, 0)

                # Calculate deviation
                deviation = player_open_freq - gto_open_freq

                if abs(deviation) >= 20:  # Only show significant deviations
                    deviations.append({
                        "hand": combo,
                        "sample_size": total,
                        "player_freq": round(player_open_freq, 1),
                        "gto_freq": round(gto_open_freq, 1),
                        "deviation": round(deviation, 1),
                        "action": "open" if deviation > 0 else "fold",
                        "recommendation": "remove" if deviation > 0 else "add",
                        "player_actions": actions
                    })
            else:
                # For defense/facing_3bet, calculate continue frequency
                fold_count = actions.get('fold', 0)
                continue_count = total - fold_count
                player_continue_freq = (continue_count / total) * 100
                gto_cont_freq = gto_continue.get(combo, 0)

                deviation = player_continue_freq - gto_cont_freq

                if abs(deviation) >= 20:
                    deviations.append({
                        "hand": combo,
                        "sample_size": total,
                        "player_freq": round(player_continue_freq, 1),
                        "gto_freq": round(gto_cont_freq, 1),
                        "deviation": round(deviation, 1),
                        "action": "continue" if deviation > 0 else "fold",
                        "recommendation": "fold more" if deviation > 0 else "defend more",
                        "player_actions": actions,
                        "gto_breakdown": gto_freqs.get(combo, {})
                    })

        # Sort by absolute deviation (biggest leaks first)
        deviations.sort(key=lambda x: abs(x['deviation']), reverse=True)

        # Also find hands player NEVER plays that GTO opens/defends
        missing_hands = []
        for combo, gto_freq in gto_continue.items():
            if combo not in hand_actions and gto_freq >= 50:  # GTO plays this hand often but player never does
                missing_hands.append({
                    "hand": combo,
                    "gto_freq": round(gto_freq, 1),
                    "note": "GTO plays this hand but you never have in sample"
                })
        missing_hands.sort(key=lambda x: x['gto_freq'], reverse=True)

        return {
            "scenario": scenario,
            "position": position,
            "vs_position": vs_position,
            "total_hands_analyzed": len(rows),
            "unique_combos": len(hand_actions),
            "deviations": deviations[:20],  # Top 20 deviations
            "missing_hands": missing_hands[:10],  # Top 10 missing hands
            "summary": {
                "over_playing": len([d for d in deviations if d['deviation'] > 0]),
                "under_playing": len([d for d in deviations if d['deviation'] < 0]),
                "biggest_leak": deviations[0] if deviations else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting hand deviations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing hand deviations: {str(e)}"
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
        # Note: Only include positions that can actually defend against an open
        # UTG is first to act, so they can never "defend" - exclude them
        # Valid defense positions: BB, SB, BTN, CO, MP (can face opens from earlier positions)
        # IMPORTANT: Exclude hands where hero faced a 3-bet (squeeze) - those are different scenarios
        defense_query = text("""
            SELECT
                position,
                COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false) as faced_open,
                COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = false) as folded,
                COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = true AND pfr = false) as called,
                COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND made_three_bet = true) as three_bets,
                ROUND(100.0 * COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = false) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false), 0), 1) as fold_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND vpip = true AND pfr = false) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false), 0), 1) as call_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false AND made_three_bet = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false), 0), 1) as three_bet_pct
            FROM player_hand_summary
            WHERE player_name = :player_name
            AND position IN ('BB', 'SB', 'BTN', 'CO', 'MP')
            GROUP BY position
            HAVING COUNT(*) FILTER (WHERE faced_raise = true AND faced_three_bet = false) >= 5
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
        # Only include hands where player opened (pfr=true) and then faced a 3-bet
        # Excludes cold-call of 3-bet situations (someone else opened, someone 3-bet, player calls)
        facing_3bet_query = text("""
            SELECT
                position,
                COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true) as faced_3bet,
                COUNT(*) FILTER (WHERE folded_to_three_bet = true AND pfr = true) as folded,
                COUNT(*) FILTER (WHERE called_three_bet = true AND pfr = true) as called,
                COUNT(*) FILTER (WHERE four_bet = true AND pfr = true) as four_bet,
                ROUND(100.0 * COUNT(*) FILTER (WHERE folded_to_three_bet = true AND pfr = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true), 0), 1) as fold_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE called_three_bet = true AND pfr = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true), 0), 1) as call_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE four_bet = true AND pfr = true) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true), 0), 1) as four_bet_pct
            FROM player_hand_summary
            WHERE player_name = :player_name
            AND position IS NOT NULL
            GROUP BY position
            HAVING COUNT(*) FILTER (WHERE faced_three_bet = true AND pfr = true) >= 5
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
        # 3b. FACING 3-BET BY MATCHUP (position-specific)
        # ============================================
        # Get GTO facing 3-bet scenarios by position matchup
        gto_f3bet_matchups_result = db.execute(text("""
            SELECT position, opponent_position, action, gto_aggregate_freq * 100 as freq
            FROM gto_scenarios
            WHERE category = 'facing_3bet'
            AND opponent_position IS NOT NULL
            ORDER BY position, opponent_position, action
        """))
        gto_f3bet_matchups = {}
        for row in gto_f3bet_matchups_result:
            pos, opp, action, freq = row[0], row[1], row[2], float(row[3]) if row[3] else 0
            key = f"{pos}_vs_{opp}"
            if key not in gto_f3bet_matchups:
                gto_f3bet_matchups[key] = {}
            gto_f3bet_matchups[key][action] = freq

        # Get player's facing 3-bet by who 3-bet them
        # Only include hands where player opened (pfr=true) before facing the 3-bet
        player_f3bet_matchups_result = db.execute(text("""
            SELECT
                position,
                three_bettor_position,
                COUNT(*) as faced_3bet,
                COUNT(*) FILTER (WHERE folded_to_three_bet = true) as folded,
                COUNT(*) FILTER (WHERE called_three_bet = true) as called,
                COUNT(*) FILTER (WHERE four_bet = true) as four_bets
            FROM player_hand_summary
            WHERE player_name = :player_name
              AND faced_three_bet = true
              AND pfr = true
              AND three_bettor_position IS NOT NULL
              AND position IS NOT NULL
            GROUP BY position, three_bettor_position
            ORDER BY position, three_bettor_position
        """), {"player_name": validated_name})

        player_f3bet_stats = {}
        for row in player_f3bet_matchups_result.mappings():
            key = f"{row['position']}_vs_{row['three_bettor_position']}"
            total = row['faced_3bet'] or 0
            if total > 0:
                player_f3bet_stats[key] = {
                    'sample_size': total,
                    'fold_pct': (row['folded'] or 0) / total * 100,
                    'call_pct': (row['called'] or 0) / total * 100,
                    '4bet_pct': (row['four_bets'] or 0) / total * 100
                }

        # Format facing 3-bet matchups
        facing_3bet_matchups = []
        for key, actions in sorted(gto_f3bet_matchups.items()):
            pos, opp = key.split('_vs_')
            player_stats = player_f3bet_stats.get(key, {})

            gto_fold = actions.get('fold', 0)
            gto_call = actions.get('call', 0)
            gto_4bet = actions.get('4bet', 0)

            player_fold = player_stats.get('fold_pct')
            player_call = player_stats.get('call_pct')
            player_4bet = player_stats.get('4bet_pct')

            facing_3bet_matchups.append({
                'position': pos,
                'vs_position': opp,
                'sample_size': player_stats.get('sample_size', 0),
                'player_fold': round(player_fold, 1) if player_fold is not None else None,
                'player_call': round(player_call, 1) if player_call is not None else None,
                'player_4bet': round(player_4bet, 1) if player_4bet is not None else None,
                'gto_fold': round(gto_fold, 1),
                'gto_call': round(gto_call, 1),
                'gto_4bet': round(gto_4bet, 1),
                'fold_diff': round(player_fold - gto_fold, 1) if player_fold is not None else None,
                'call_diff': round(player_call - gto_call, 1) if player_call is not None else None,
                '4bet_diff': round(player_4bet - gto_4bet, 1) if player_4bet is not None else None,
            })

        # ============================================
        # 4. BLIND DEFENSE (vs steals) - Using actual GTO from database
        # IMPORTANT: Exclude hands where hero faced a 3-bet (squeeze) - those are different scenarios
        # ============================================
        blind_defense_query = text("""
            SELECT
                position,
                COUNT(*) FILTER (WHERE faced_steal = true AND faced_three_bet = false) as faced_steal,
                COUNT(*) FILTER (WHERE fold_to_steal = true AND faced_three_bet = false) as folded,
                COUNT(*) FILTER (WHERE call_steal = true AND faced_three_bet = false) as called,
                COUNT(*) FILTER (WHERE three_bet_vs_steal = true AND faced_three_bet = false) as three_bet,
                ROUND(100.0 * COUNT(*) FILTER (WHERE fold_to_steal = true AND faced_three_bet = false) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_steal = true AND faced_three_bet = false), 0), 1) as fold_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE call_steal = true AND faced_three_bet = false) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_steal = true AND faced_three_bet = false), 0), 1) as call_pct,
                ROUND(100.0 * COUNT(*) FILTER (WHERE three_bet_vs_steal = true AND faced_three_bet = false) /
                    NULLIF(COUNT(*) FILTER (WHERE faced_steal = true AND faced_three_bet = false), 0), 1) as three_bet_pct
            FROM player_hand_summary
            WHERE player_name = :player_name
            AND position IN ('BB', 'SB')
            GROUP BY position
            HAVING COUNT(*) FILTER (WHERE faced_steal = true AND faced_three_bet = false) >= 5
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

        # Get player's position-specific defense frequencies using raiser_position
        # IMPORTANT: Exclude hands where hero faced a 3-bet (squeeze) - those are different scenarios
        player_matchups_result = db.execute(text("""
            SELECT
                position,
                raiser_position,
                COUNT(*) as faced_open,
                COUNT(*) FILTER (WHERE vpip = false) as folded,
                COUNT(*) FILTER (WHERE vpip = true AND pfr = false) as called,
                COUNT(*) FILTER (WHERE made_three_bet = true) as three_bets
            FROM player_hand_summary
            WHERE player_name = :player_name
              AND faced_raise = true
              AND faced_three_bet = false
              AND raiser_position IS NOT NULL
              AND position IS NOT NULL
            GROUP BY position, raiser_position
            ORDER BY position, raiser_position
        """), {"player_name": validated_name})

        player_matchup_stats = {}
        for row in player_matchups_result.mappings():
            key = f"{row['position']}_vs_{row['raiser_position']}"
            total = row['faced_open'] or 0
            if total > 0:
                player_matchup_stats[key] = {
                    'sample_size': total,
                    'fold_pct': (row['folded'] or 0) / total * 100,
                    'call_pct': (row['called'] or 0) / total * 100,
                    '3bet_pct': (row['three_bets'] or 0) / total * 100
                }

        # Format as list for frontend with player frequencies
        position_matchups = []
        for key, actions in sorted(gto_matchups.items()):
            pos, opp = key.split('_vs_')
            player_stats = player_matchup_stats.get(key, {})

            gto_fold = actions.get('fold', 0)
            gto_call = actions.get('call', 0)
            gto_3bet = actions.get('3bet', 0)

            player_fold = player_stats.get('fold_pct')
            player_call = player_stats.get('call_pct')
            player_3bet = player_stats.get('3bet_pct')

            position_matchups.append({
                'position': pos,
                'vs_position': opp,
                'sample_size': player_stats.get('sample_size', 0),
                'player_fold': round(player_fold, 1) if player_fold is not None else None,
                'player_call': round(player_call, 1) if player_call is not None else None,
                'player_3bet': round(player_3bet, 1) if player_3bet is not None else None,
                'gto_fold': round(gto_fold, 1),
                'gto_call': round(gto_call, 1),
                'gto_3bet': round(gto_3bet, 1),
                'fold_diff': round(player_fold - gto_fold, 1) if player_fold is not None else None,
                'call_diff': round(player_call - gto_call, 1) if player_call is not None else None,
                '3bet_diff': round(player_3bet - gto_3bet, 1) if player_3bet is not None else None,
            })

        # ============================================
        # 7. FACING 4-BET Analysis
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

        # Get player's facing 4-bet frequencies
        # We need position and raiser_position to know who 4-bet us
        player_f4bet_result = db.execute(text("""
            SELECT
                position,
                raiser_position,
                COUNT(*) as faced_4bet,
                COUNT(*) FILTER (WHERE folded_to_four_bet = true) as folded,
                COUNT(*) FILTER (WHERE called_four_bet = true) as called,
                COUNT(*) FILTER (WHERE five_bet = true) as five_bets
            FROM player_hand_summary
            WHERE player_name = :player_name
              AND faced_four_bet = true
              AND raiser_position IS NOT NULL
              AND position IS NOT NULL
            GROUP BY position, raiser_position
            ORDER BY position, raiser_position
        """), {"player_name": validated_name})

        player_f4bet_stats = {}
        for row in player_f4bet_result.mappings():
            key = f"{row['position']}_vs_{row['raiser_position']}"
            total = row['faced_4bet'] or 0
            if total > 0:
                player_f4bet_stats[key] = {
                    'sample_size': total,
                    'fold_pct': (row['folded'] or 0) / total * 100,
                    'call_pct': (row['called'] or 0) / total * 100,
                    '5bet_pct': (row['five_bets'] or 0) / total * 100
                }

        # Format facing 4-bet with player frequencies
        facing_4bet_reference = []
        for key, actions in sorted(gto_facing_4bet.items()):
            pos, opp = key.split('_vs_')
            player_stats = player_f4bet_stats.get(key, {})

            gto_fold = actions.get('fold', 0)
            gto_call = actions.get('call', 0)
            gto_5bet = actions.get('5bet', 0) + actions.get('allin', 0)

            player_fold = player_stats.get('fold_pct')
            player_call = player_stats.get('call_pct')
            player_5bet = player_stats.get('5bet_pct')

            facing_4bet_reference.append({
                'position': pos,
                'vs_position': opp,
                'sample_size': player_stats.get('sample_size', 0),
                'player_fold': round(player_fold, 1) if player_fold is not None else None,
                'player_call': round(player_call, 1) if player_call is not None else None,
                'player_5bet': round(player_5bet, 1) if player_5bet is not None else None,
                'gto_fold': round(gto_fold, 1),
                'gto_call': round(gto_call, 1),
                'gto_5bet': round(gto_5bet, 1),
                'fold_diff': round(player_fold - gto_fold, 1) if player_fold is not None else None,
                'call_diff': round(player_call - gto_call, 1) if player_call is not None else None,
                '5bet_diff': round(player_5bet - gto_5bet, 1) if player_5bet is not None else None,
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
            'facing_3bet_matchups': facing_3bet_matchups,
            'blind_defense': blind_defense,
            'steal_attempts': steal_attempts,
            'position_matchups': position_matchups,
            'facing_4bet_reference': facing_4bet_reference
        }

    except HTTPException:
        raise
    except DatabaseConnectionError as e:
        logger.error(f"Database connection error for GTO analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again."
        )
    except Exception as e:
        error_msg = str(e).lower()
        # Check for connection-related errors in the generic exception
        if any(term in error_msg for term in ['ssl', 'connection', 'timeout', 'closed', 'refused']):
            logger.error(f"Database connection error for GTO analysis: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database temporarily unavailable. Please try again."
            )
        logger.error(f"Error getting player GTO analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving GTO analysis: {str(e)}"
        )


def categorize_hand(hole_cards: Optional[str]) -> Dict[str, Any]:
    """
    Categorize a hand into type, tier, and provide context.

    Tiers: 1 = Premium (top 5%), 2 = Strong (5-15%), 3 = Playable (15-30%),
           4 = Speculative (30-50%), 5 = Weak (50%+)
    """
    if not hole_cards:
        return {"category": "Unknown", "tier": None, "combo": None}

    # Parse hole cards like "5d Qc" or "Ah Ks"
    cards = hole_cards.strip().split()
    if len(cards) != 2:
        return {"category": "Unknown", "tier": None, "combo": hole_cards}

    # Extract ranks and suits
    rank_order = "23456789TJQKA"
    card1, card2 = cards[0], cards[1]
    rank1, suit1 = card1[0].upper(), card1[1].lower()
    rank2, suit2 = card2[0].upper(), card2[1].lower()

    # Normalize so higher rank is first
    if rank_order.index(rank1) < rank_order.index(rank2):
        rank1, rank2 = rank2, rank1
        suit1, suit2 = suit2, suit1

    is_suited = suit1 == suit2
    is_pair = rank1 == rank2

    # Build combo string
    if is_pair:
        combo = f"{rank1}{rank2}"
    elif is_suited:
        combo = f"{rank1}{rank2}s"
    else:
        combo = f"{rank1}{rank2}o"

    # Categorization logic
    premium_pairs = ["AA", "KK", "QQ"]
    strong_pairs = ["JJ", "TT"]
    medium_pairs = ["99", "88", "77"]
    small_pairs = ["66", "55", "44", "33", "22"]

    premium_broadways = ["AKs", "AKo"]
    strong_broadways = ["AQs", "AQo", "AJs", "KQs"]
    playable_broadways = ["ATs", "AJo", "KJs", "KQo", "QJs", "ATo", "KTs"]

    suited_connectors = ["JTs", "T9s", "98s", "87s", "76s", "65s", "54s"]
    suited_aces = ["A5s", "A4s", "A3s", "A2s", "A9s", "A8s", "A7s", "A6s"]

    # Determine category and tier
    if combo in premium_pairs:
        return {"category": "Premium Pair", "tier": 1, "combo": combo}
    elif combo in premium_broadways:
        return {"category": "Premium Broadway", "tier": 1, "combo": combo}
    elif combo in strong_pairs:
        return {"category": "Strong Pair", "tier": 2, "combo": combo}
    elif combo in strong_broadways:
        return {"category": "Strong Broadway", "tier": 2, "combo": combo}
    elif combo in medium_pairs:
        return {"category": "Medium Pair", "tier": 3, "combo": combo}
    elif combo in playable_broadways:
        return {"category": "Playable Broadway", "tier": 3, "combo": combo}
    elif combo in suited_connectors:
        return {"category": "Suited Connector", "tier": 3, "combo": combo}
    elif combo in suited_aces:
        return {"category": "Suited Ace", "tier": 3, "combo": combo}
    elif combo in small_pairs:
        return {"category": "Small Pair", "tier": 4, "combo": combo}
    elif is_suited and rank1 in "AKQJT":
        return {"category": "Suited Broadway", "tier": 3, "combo": combo}
    elif is_suited:
        return {"category": "Suited Speculative", "tier": 4, "combo": combo}
    elif rank1 in "AKQJT" and rank2 in "AKQJT":
        return {"category": "Offsuit Broadway", "tier": 4, "combo": combo}
    else:
        return {"category": "Weak/Trash", "tier": 5, "combo": combo}


def build_gto_lookup_table(
    db: Session,
    scenario: str,
    position: str
) -> Dict[tuple, Dict[str, float]]:
    """
    Pre-fetch ALL GTO frequencies for a scenario/position and build a lookup table.

    Returns a dict mapping (hand_combo, opponent_position) -> {action: frequency}
    This allows O(1) lookups instead of O(n) database queries.
    """
    from sqlalchemy import text

    # Fetch all frequencies for this scenario/position in ONE query
    all_freqs_query = text("""
        SELECT gs.action, gs.opponent_position, gf.hand, gf.frequency
        FROM gto_scenarios gs
        JOIN gto_frequencies gf ON gs.scenario_id = gf.scenario_id
        WHERE gs.category = :scenario
        AND gs.position = :position
    """)

    result = db.execute(all_freqs_query, {
        "scenario": scenario,
        "position": position
    })

    # Build lookup table: (hand_combo, opponent_pos) -> {action -> [frequencies]}
    temp_lookup: Dict[tuple, Dict[str, list]] = {}
    rank_order = "23456789TJQKA"

    for row in result:
        action, opp_pos, hand, freq = row[0], row[1], row[2], float(row[3]) if row[3] else 0

        # Normalize the hand from database (e.g., "QdTc" -> "QTs")
        hand = hand.replace(' ', '')
        if len(hand) < 4:
            continue

        r1, s1 = hand[0].upper(), hand[1].lower()
        r2, s2 = hand[2].upper(), hand[3].lower()

        # Ensure higher rank first
        if rank_order.index(r1) < rank_order.index(r2):
            r1, r2 = r2, r1
            s1, s2 = s2, s1

        # Build combo string
        if r1 == r2:
            normalized = f"{r1}{r2}"
        elif s1 == s2:
            normalized = f"{r1}{r2}s"
        else:
            normalized = f"{r1}{r2}o"

        key = (normalized, opp_pos)
        if key not in temp_lookup:
            temp_lookup[key] = {}
        if action not in temp_lookup[key]:
            temp_lookup[key][action] = []
        temp_lookup[key][action].append(freq * 100)  # Convert to percentage

    # Average and normalize frequencies
    lookup_table: Dict[tuple, Dict[str, float]] = {}
    for key, actions in temp_lookup.items():
        avg_freqs = {action: sum(freqs) / len(freqs) for action, freqs in actions.items()}

        # Normalize to sum to ~100%
        total = sum(avg_freqs.values())
        if total > 0 and abs(total - 100) > 1:
            for action in avg_freqs:
                avg_freqs[action] = avg_freqs[action] / total * 100

        lookup_table[key] = avg_freqs

    return lookup_table


def classify_deviation(player_action: str, action_gto_freq: float, gto_freqs: Dict[str, float]) -> Dict[str, Any]:
    """
    Classify a deviation from GTO as correct, suboptimal, mistake, or exploitative.

    Based on poker professor's recommendations:
    - Correct: action has GTO freq >= 40%
    - Suboptimal: action has GTO freq 15-40%
    - Mistake: action has GTO freq < 15%
    """
    if action_gto_freq >= 40:
        return {
            "type": "correct",
            "severity": None,
            "description": "Within GTO range"
        }
    elif action_gto_freq >= 15:
        # Find what GTO prefers
        best_action = max(gto_freqs.keys(), key=lambda k: gto_freqs[k]) if gto_freqs else None
        best_freq = gto_freqs.get(best_action, 0) if best_action else 0
        return {
            "type": "suboptimal",
            "severity": "minor",
            "description": f"GTO prefers {best_action} ({best_freq:.0f}%)"
        }
    else:
        best_action = max(gto_freqs.keys(), key=lambda k: gto_freqs[k]) if gto_freqs else None
        best_freq = gto_freqs.get(best_action, 0) if best_action else 0
        return {
            "type": "mistake",
            "severity": "major" if action_gto_freq < 5 else "moderate",
            "description": f"GTO strongly prefers {best_action} ({best_freq:.0f}%)"
        }


@app.get(
    "/api/players/{player_name}/scenario-hands",
    tags=["Players"],
    summary="Get hands for a specific GTO scenario",
    description="Drill down into hands for a specific position/scenario matchup with GTO comparison"
)
async def get_scenario_hands(
    player_name: str,
    scenario: str = Query(..., description="Scenario type: opening, defense, facing_3bet, facing_4bet"),
    position: str = Query(..., description="Player's position: UTG, MP, CO, BTN, SB, BB"),
    vs_position: Optional[str] = Query(None, description="Opponent position for matchup scenarios"),
    limit: int = Query(50, ge=1, le=200, description="Max hands to return"),
    db: Session = Depends(get_db)
):
    """
    Get individual hands for a specific scenario to analyze GTO deviations.

    Returns hands where the player was in the specified scenario, showing
    what action they took vs what GTO recommends, including:
    - Hole cards and hand category
    - Effective stack depth
    - Deviation classification (correct/suboptimal/mistake)
    """
    from sqlalchemy import text

    try:
        # Validate inputs
        validated_name = InputValidator.validate_player_name(player_name)
        valid_scenarios = ['opening', 'defense', 'facing_3bet', 'facing_4bet']
        if scenario not in valid_scenarios:
            raise HTTPException(status_code=400, detail=f"Invalid scenario. Must be one of: {valid_scenarios}")

        valid_positions = ['UTG', 'MP', 'HJ', 'CO', 'BTN', 'SB', 'BB']
        if position.upper() not in valid_positions:
            raise HTTPException(status_code=400, detail=f"Invalid position. Must be one of: {valid_positions}")

        position = position.upper()
        if vs_position:
            vs_position = vs_position.upper()

        # Get GTO frequencies for this scenario
        gto_query = text("""
            SELECT action, gto_aggregate_freq * 100 as freq
            FROM gto_scenarios
            WHERE category = :scenario
            AND position = :position
            AND (opponent_position = :vs_position OR (:vs_position IS NULL AND opponent_position IS NULL))
        """)
        gto_result = db.execute(gto_query, {
            "scenario": scenario,
            "position": position,
            "vs_position": vs_position
        })
        gto_freqs = {row[0]: float(row[1]) if row[1] else 0 for row in gto_result}

        # If no specific GTO found, get average for position
        if not gto_freqs:
            gto_avg_query = text("""
                SELECT action, AVG(gto_aggregate_freq) * 100 as freq
                FROM gto_scenarios
                WHERE category = :scenario
                AND position = :position
                GROUP BY action
            """)
            gto_avg_result = db.execute(gto_avg_query, {"scenario": scenario, "position": position})
            gto_freqs = {row[0]: float(row[1]) if row[1] else 0 for row in gto_avg_result}

        # Build the query based on scenario type
        # All queries now include:
        # - hole_cards extracted from raw_hand_text using regex
        # - effective_stack_bb from hand_actions
        if scenario == 'opening':
            # Opening: hands where player was first to act and could open
            hands_query = text("""
                SELECT
                    phs.hand_id,
                    rh.timestamp,
                    rh.stake_level,
                    phs.pfr as raised,
                    phs.vpip,
                    CASE
                        WHEN phs.pfr = true THEN 'open'
                        WHEN phs.vpip = false THEN 'fold'
                        ELSE 'limp'
                    END as player_action,
                    -- Extract hole cards from raw hand text (format: "Dealt to player [Ah Ks]")
                    (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                    -- Get effective stack in BB
                    ha.stack_size,
                    -- Extract BB from raw_hand_text (format: €0.02/€0.04 or $0.05/$0.10)
                    ha.stack_size / NULLIF(
                        (regexp_match(rh.raw_hand_text, '[€$][0-9.]+/[€$]([0-9.]+)'))[1]::numeric,
                        0
                    ) as effective_stack_bb
                FROM player_hand_summary phs
                JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                LEFT JOIN (
                    SELECT DISTINCT ON (hand_id, player_name) hand_id, player_name, stack_size
                    FROM hand_actions
                    WHERE street = 'preflop'
                    ORDER BY hand_id, player_name, action_id
                ) ha ON ha.hand_id = phs.hand_id AND ha.player_name = phs.player_name
                WHERE phs.player_name = :player_name
                AND phs.position = :position
                AND phs.faced_raise = false
                ORDER BY rh.timestamp DESC
                LIMIT :limit
            """)
            params = {"player_name": validated_name, "position": position, "limit": limit}

        elif scenario == 'defense':
            # Defense: hands where player faced an open (but NOT a subsequent 3-bet)
            # Hands where hero faced a 3-bet (squeeze) are excluded - those are different scenarios
            if vs_position:
                hands_query = text("""
                    SELECT
                        phs.hand_id,
                        rh.timestamp,
                        rh.stake_level,
                        phs.raiser_position as vs_pos,
                        CASE
                            WHEN phs.vpip = false THEN 'fold'
                            WHEN phs.made_three_bet = true THEN '3bet'
                            ELSE 'call'
                        END as player_action,
                        (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                        ha.stack_size,
                        -- Extract BB from raw_hand_text (format: €0.02/€0.04 or $0.05/$0.10)
                        ha.stack_size / NULLIF(
                            (regexp_match(rh.raw_hand_text, '[€$][0-9.]+/[€$]([0-9.]+)'))[1]::numeric,
                            0
                        ) as effective_stack_bb
                    FROM player_hand_summary phs
                    JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                    LEFT JOIN (
                        SELECT DISTINCT ON (hand_id, player_name) hand_id, player_name, stack_size
                        FROM hand_actions WHERE street = 'preflop'
                        ORDER BY hand_id, player_name, action_id
                    ) ha ON ha.hand_id = phs.hand_id AND ha.player_name = phs.player_name
                    WHERE phs.player_name = :player_name
                    AND phs.position = :position
                    AND phs.faced_raise = true
                    AND phs.faced_three_bet = false
                    AND phs.raiser_position = :vs_position
                    ORDER BY rh.timestamp DESC
                    LIMIT :limit
                """)
                params = {"player_name": validated_name, "position": position, "vs_position": vs_position, "limit": limit}
            else:
                hands_query = text("""
                    SELECT
                        phs.hand_id,
                        rh.timestamp,
                        rh.stake_level,
                        phs.raiser_position as vs_pos,
                        CASE
                            WHEN phs.vpip = false THEN 'fold'
                            WHEN phs.made_three_bet = true THEN '3bet'
                            ELSE 'call'
                        END as player_action,
                        (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                        ha.stack_size,
                        -- Extract BB from raw_hand_text (format: €0.02/€0.04 or $0.05/$0.10)
                        ha.stack_size / NULLIF(
                            (regexp_match(rh.raw_hand_text, '[€$][0-9.]+/[€$]([0-9.]+)'))[1]::numeric,
                            0
                        ) as effective_stack_bb
                    FROM player_hand_summary phs
                    JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                    LEFT JOIN (
                        SELECT DISTINCT ON (hand_id, player_name) hand_id, player_name, stack_size
                        FROM hand_actions WHERE street = 'preflop'
                        ORDER BY hand_id, player_name, action_id
                    ) ha ON ha.hand_id = phs.hand_id AND ha.player_name = phs.player_name
                    WHERE phs.player_name = :player_name
                    AND phs.position = :position
                    AND phs.faced_raise = true
                    AND phs.faced_three_bet = false
                    ORDER BY rh.timestamp DESC
                    LIMIT :limit
                """)
                params = {"player_name": validated_name, "position": position, "limit": limit}

        elif scenario == 'facing_3bet':
            # Facing 3-bet: hands where player opened (pfr=true) and faced a 3-bet
            # Excludes cold-call of 3-bet (someone else opened, villain 3-bet, hero calls)
            if vs_position:
                hands_query = text("""
                    SELECT
                        phs.hand_id,
                        rh.timestamp,
                        rh.stake_level,
                        phs.three_bettor_position as vs_pos,
                        CASE
                            WHEN phs.folded_to_three_bet = true THEN 'fold'
                            WHEN phs.four_bet = true THEN '4bet'
                            WHEN phs.called_three_bet = true THEN 'call'
                            ELSE 'unknown'
                        END as player_action,
                        (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                        ha.stack_size,
                        -- Extract BB from raw_hand_text (format: €0.02/€0.04 or $0.05/$0.10)
                        ha.stack_size / NULLIF(
                            (regexp_match(rh.raw_hand_text, '[€$][0-9.]+/[€$]([0-9.]+)'))[1]::numeric,
                            0
                        ) as effective_stack_bb
                    FROM player_hand_summary phs
                    JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                    LEFT JOIN (
                        SELECT DISTINCT ON (hand_id, player_name) hand_id, player_name, stack_size
                        FROM hand_actions WHERE street = 'preflop'
                        ORDER BY hand_id, player_name, action_id
                    ) ha ON ha.hand_id = phs.hand_id AND ha.player_name = phs.player_name
                    WHERE phs.player_name = :player_name
                    AND phs.position = :position
                    AND phs.faced_three_bet = true
                    AND phs.pfr = true
                    AND phs.three_bettor_position = :vs_position
                    ORDER BY rh.timestamp DESC
                    LIMIT :limit
                """)
                params = {"player_name": validated_name, "position": position, "vs_position": vs_position, "limit": limit}
            else:
                hands_query = text("""
                    SELECT
                        phs.hand_id,
                        rh.timestamp,
                        rh.stake_level,
                        phs.three_bettor_position as vs_pos,
                        CASE
                            WHEN phs.folded_to_three_bet = true THEN 'fold'
                            WHEN phs.four_bet = true THEN '4bet'
                            WHEN phs.called_three_bet = true THEN 'call'
                            ELSE 'unknown'
                        END as player_action,
                        (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                        ha.stack_size,
                        -- Extract BB from raw_hand_text (format: €0.02/€0.04 or $0.05/$0.10)
                        ha.stack_size / NULLIF(
                            (regexp_match(rh.raw_hand_text, '[€$][0-9.]+/[€$]([0-9.]+)'))[1]::numeric,
                            0
                        ) as effective_stack_bb
                    FROM player_hand_summary phs
                    JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                    LEFT JOIN (
                        SELECT DISTINCT ON (hand_id, player_name) hand_id, player_name, stack_size
                        FROM hand_actions WHERE street = 'preflop'
                        ORDER BY hand_id, player_name, action_id
                    ) ha ON ha.hand_id = phs.hand_id AND ha.player_name = phs.player_name
                    WHERE phs.player_name = :player_name
                    AND phs.position = :position
                    AND phs.faced_three_bet = true
                    AND phs.pfr = true
                    ORDER BY rh.timestamp DESC
                    LIMIT :limit
                """)
                params = {"player_name": validated_name, "position": position, "limit": limit}

        elif scenario == 'facing_4bet':
            # Facing 4-bet: hands where player 3-bet and faced a 4-bet
            if vs_position:
                hands_query = text("""
                    SELECT
                        phs.hand_id,
                        rh.timestamp,
                        rh.stake_level,
                        phs.raiser_position as vs_pos,
                        CASE
                            WHEN phs.folded_to_four_bet = true THEN 'fold'
                            WHEN phs.five_bet = true THEN '5bet'
                            WHEN phs.called_four_bet = true THEN 'call'
                            ELSE 'unknown'
                        END as player_action,
                        (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                        ha.stack_size,
                        -- Extract BB from raw_hand_text (format: €0.02/€0.04 or $0.05/$0.10)
                        ha.stack_size / NULLIF(
                            (regexp_match(rh.raw_hand_text, '[€$][0-9.]+/[€$]([0-9.]+)'))[1]::numeric,
                            0
                        ) as effective_stack_bb
                    FROM player_hand_summary phs
                    JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                    LEFT JOIN (
                        SELECT DISTINCT ON (hand_id, player_name) hand_id, player_name, stack_size
                        FROM hand_actions WHERE street = 'preflop'
                        ORDER BY hand_id, player_name, action_id
                    ) ha ON ha.hand_id = phs.hand_id AND ha.player_name = phs.player_name
                    WHERE phs.player_name = :player_name
                    AND phs.position = :position
                    AND phs.faced_four_bet = true
                    AND phs.raiser_position = :vs_position
                    ORDER BY rh.timestamp DESC
                    LIMIT :limit
                """)
                params = {"player_name": validated_name, "position": position, "vs_position": vs_position, "limit": limit}
            else:
                hands_query = text("""
                    SELECT
                        phs.hand_id,
                        rh.timestamp,
                        rh.stake_level,
                        phs.raiser_position as vs_pos,
                        CASE
                            WHEN phs.folded_to_four_bet = true THEN 'fold'
                            WHEN phs.five_bet = true THEN '5bet'
                            WHEN phs.called_four_bet = true THEN 'call'
                            ELSE 'unknown'
                        END as player_action,
                        (regexp_match(rh.raw_hand_text, 'Dealt to ' || phs.player_name || ' \\[([^\\]]+)\\]'))[1] as hole_cards,
                        ha.stack_size,
                        -- Extract BB from raw_hand_text (format: €0.02/€0.04 or $0.05/$0.10)
                        ha.stack_size / NULLIF(
                            (regexp_match(rh.raw_hand_text, '[€$][0-9.]+/[€$]([0-9.]+)'))[1]::numeric,
                            0
                        ) as effective_stack_bb
                    FROM player_hand_summary phs
                    JOIN raw_hands rh ON phs.hand_id = rh.hand_id
                    LEFT JOIN (
                        SELECT DISTINCT ON (hand_id, player_name) hand_id, player_name, stack_size
                        FROM hand_actions WHERE street = 'preflop'
                        ORDER BY hand_id, player_name, action_id
                    ) ha ON ha.hand_id = phs.hand_id AND ha.player_name = phs.player_name
                    WHERE phs.player_name = :player_name
                    AND phs.position = :position
                    AND phs.faced_four_bet = true
                    ORDER BY rh.timestamp DESC
                    LIMIT :limit
                """)
                params = {"player_name": validated_name, "position": position, "limit": limit}

        # Execute query
        result = db.execute(hands_query, params)
        hands = []

        # Pre-fetch ALL GTO frequencies for this scenario in ONE query
        # Returns dict mapping (hand_combo, opponent_pos) -> {action: frequency}
        gto_lookup = build_gto_lookup_table(db, scenario, position)

        for row in result.mappings():
            player_action = row['player_action']

            # Get hole cards and categorize them
            hole_cards = row.get('hole_cards')
            hand_info = categorize_hand(hole_cards)
            hand_combo = hand_info.get('combo')

            # Get the actual raiser position for THIS hand (may differ from filter)
            actual_vs_pos = row.get('vs_pos') or vs_position

            # Look up hand-specific GTO frequencies from pre-fetched data
            hand_specific_gto = None
            if hand_combo and hand_combo not in ['Unknown', None]:
                # O(1) lookup from pre-built table
                hand_specific_gto = gto_lookup.get((hand_combo, actual_vs_pos))

            # Determine effective GTO frequencies
            if hand_specific_gto:
                # Hand found in GTO data - use those frequencies
                # For opening scenarios, add implied fold frequency (100 - open - limp)
                if scenario == 'opening':
                    open_freq = hand_specific_gto.get('open', 0)
                    limp_freq = hand_specific_gto.get('limp', 0)
                    fold_freq = max(0, 100.0 - open_freq - limp_freq)
                    effective_gto_freqs = {'open': open_freq, 'fold': fold_freq, 'limp': limp_freq}
                else:
                    effective_gto_freqs = hand_specific_gto
            elif scenario == 'opening' and hand_combo and hand_combo not in ['Unknown', None]:
                # Opening scenario: hand NOT in GTO data means GTO never opens it
                # This is correct - GTO only stores hands it opens, absence = fold
                effective_gto_freqs = {'fold': 100.0, 'open': 0.0, 'limp': 0.0}
            else:
                # Other scenarios or unknown hand: fall back to aggregate
                effective_gto_freqs = gto_freqs

            # Get GTO frequency for the action taken
            action_freq = effective_gto_freqs.get(player_action, 0)

            # Find what GTO recommends most
            gto_recommended = max(effective_gto_freqs.keys(), key=lambda k: effective_gto_freqs[k]) if effective_gto_freqs else None

            # Enhanced deviation classification
            deviation = classify_deviation(player_action, action_freq, effective_gto_freqs)

            # Get effective stack
            effective_stack = row.get('effective_stack_bb')
            if effective_stack is not None:
                effective_stack = round(float(effective_stack), 1)

            hands.append({
                'hand_id': row['hand_id'],
                'timestamp': row['timestamp'].isoformat() if row['timestamp'] else None,
                'stake_level': row['stake_level'],
                'vs_position': row.get('vs_pos'),
                'player_action': player_action,
                # Enhanced: Hole card info
                'hole_cards': hole_cards,
                'hand_combo': hand_info['combo'],
                'hand_category': hand_info['category'],
                'hand_tier': hand_info['tier'],
                # Enhanced: Stack info
                'effective_stack_bb': effective_stack,
                # GTO comparison - use hand-specific frequencies when available
                'gto_frequencies': effective_gto_freqs,
                'gto_recommended': gto_recommended,
                'action_gto_freq': round(action_freq, 1),
                # Enhanced: Deviation classification
                'deviation_type': deviation['type'],
                'deviation_severity': deviation['severity'],
                'deviation_description': deviation['description'],
                # Legacy field for backwards compatibility
                'is_mistake': deviation['type'] == 'mistake'
            })

        # Calculate summary stats
        total_hands = len(hands)
        mistakes = sum(1 for h in hands if h['deviation_type'] == 'mistake')
        suboptimal = sum(1 for h in hands if h['deviation_type'] == 'suboptimal')
        correct = sum(1 for h in hands if h['deviation_type'] == 'correct')

        # Hands with hole cards (for hero only)
        hands_with_cards = sum(1 for h in hands if h['hole_cards'])

        return {
            'player': validated_name,
            'scenario': scenario,
            'position': position,
            'vs_position': vs_position,
            'gto_frequencies': gto_freqs,
            'total_hands': total_hands,
            'hands_with_hole_cards': hands_with_cards,
            # Enhanced summary
            'summary': {
                'correct': correct,
                'correct_pct': round(correct / total_hands * 100, 1) if total_hands > 0 else 0,
                'suboptimal': suboptimal,
                'suboptimal_pct': round(suboptimal / total_hands * 100, 1) if total_hands > 0 else 0,
                'mistakes': mistakes,
                'mistake_pct': round(mistakes / total_hands * 100, 1) if total_hands > 0 else 0,
            },
            # Legacy fields
            'mistakes': mistakes,
            'mistake_rate': round(mistakes / total_hands * 100, 1) if total_hands > 0 else 0,
            'hands': hands
        }

    except HTTPException:
        raise
    except DatabaseConnectionError as e:
        logger.error(f"Database connection error for scenario hands: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again."
        )
    except Exception as e:
        error_msg = str(e).lower()
        if any(term in error_msg for term in ['ssl', 'connection', 'timeout', 'closed', 'refused']):
            logger.error(f"Database connection error for scenario hands: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database temporarily unavailable. Please try again."
            )
        logger.error(f"Error getting scenario hands: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving scenario hands: {str(e)}"
        )


@app.get(
    "/api/hands/{hand_id}/replay",
    tags=["Hands"],
    summary="Get full hand history for replay",
    description="Retrieves complete hand data including street-by-street actions for visual replay"
)
async def get_hand_replay(
    hand_id: int,
    db: Session = Depends(get_db)
):
    """
    Get complete hand history for visual hand replay.

    Returns:
        - Game info (stakes, table, timestamp)
        - All players with positions and starting stacks
        - Hero hole cards
        - Street-by-street actions with pot sizes
        - Board cards for each street
        - Final result
    """
    from sqlalchemy import text
    from backend.parser.pokerstars_parser import PokerStarsParser

    try:
        # Get raw hand text
        raw_query = text("""
            SELECT hand_id, timestamp, table_name, stake_level, game_type, raw_hand_text
            FROM raw_hands
            WHERE hand_id = :hand_id
        """)
        raw_result = db.execute(raw_query, {"hand_id": hand_id}).fetchone()

        if not raw_result:
            raise HTTPException(status_code=404, detail=f"Hand {hand_id} not found")

        # Parse the hand
        parser = PokerStarsParser()
        hand = parser.parse_single_hand(raw_result.raw_hand_text)

        if not hand:
            raise HTTPException(status_code=500, detail="Failed to parse hand history")

        # Extract big blind from raw hand text (format: "€0.02/€0.04" or "$0.05/$0.10")
        import re
        raw_text = raw_result.raw_hand_text or ""
        bb_pattern = r'[€$]([\d.]+)/[€$]([\d.]+)'
        bb_match = re.search(bb_pattern, raw_text)
        big_blind = float(bb_match.group(2)) if bb_match else 1.0
        stake_level = raw_result.stake_level or ""

        # Build player list with positions
        players = []
        hero_name = None
        for player in hand.players:
            player_data = {
                'name': player.name,
                'position': player.position,
                'seat': player.seat_number,
                'stack': float(player.starting_stack),
                'stack_bb': round(float(player.starting_stack) / big_blind, 1) if big_blind else None,
                'hole_cards': player.hole_cards,
                'is_hero': player.hole_cards is not None
            }
            if player.hole_cards:
                hero_name = player.name
            players.append(player_data)

        # Build street-by-street actions
        streets_data = {}
        street_order = ['preflop', 'flop', 'turn', 'river']

        for street_name in street_order:
            from backend.parser.data_structures import Street
            street_enum = Street(street_name)
            street_actions = hand.get_actions_for_street(street_enum)

            if street_actions or (street_name in ['flop', 'turn', 'river'] and street_name in (hand.board_cards or {})):
                actions = []
                for action in street_actions:
                    actions.append({
                        'player': action.player_name,
                        'action': action.action_type.value,
                        'amount': float(action.amount) if action.amount else 0,
                        'amount_bb': round(float(action.amount) / big_blind, 1) if action.amount and big_blind else 0,
                        'pot_before': float(action.pot_size_before) if action.pot_size_before else 0,
                        'pot_after': float(action.pot_size_after) if action.pot_size_after else 0,
                        'pot_before_bb': round(float(action.pot_size_before) / big_blind, 1) if action.pot_size_before and big_blind else 0,
                        'pot_after_bb': round(float(action.pot_size_after) / big_blind, 1) if action.pot_size_after and big_blind else 0,
                        'stack': float(action.stack_size) if action.stack_size else 0,
                        'stack_bb': round(float(action.stack_size) / big_blind, 1) if action.stack_size and big_blind else 0,
                        'is_aggressive': action.is_aggressive,
                        'is_all_in': action.is_all_in,
                        'facing_bet': action.facing_bet
                    })

                # Get board cards for this street
                board = None
                if street_name == 'flop' and 'flop' in (hand.board_cards or {}):
                    board = hand.board_cards.get('flop', '').split()
                elif street_name == 'turn' and 'turn' in (hand.board_cards or {}):
                    board = [hand.board_cards.get('turn', '')]
                elif street_name == 'river' and 'river' in (hand.board_cards or {}):
                    board = [hand.board_cards.get('river', '')]

                streets_data[street_name] = {
                    'actions': actions,
                    'board': board
                }

        # Get result info from player_hand_summary
        result_query = text("""
            SELECT player_name, won_hand, profit_loss, went_to_showdown
            FROM player_hand_summary
            WHERE hand_id = :hand_id
        """)
        result_rows = db.execute(result_query, {"hand_id": hand_id}).fetchall()

        results = {}
        for row in result_rows:
            results[row.player_name] = {
                'won': row.won_hand,
                'profit_loss': float(row.profit_loss) if row.profit_loss else 0,
                'profit_loss_bb': round(float(row.profit_loss) / big_blind, 1) if row.profit_loss and big_blind else 0,
                'showdown': row.went_to_showdown
            }

        # Build full board
        full_board = []
        if hand.board_cards:
            if 'flop' in hand.board_cards:
                full_board.extend(hand.board_cards['flop'].split())
            if 'turn' in hand.board_cards:
                full_board.append(hand.board_cards['turn'])
            if 'river' in hand.board_cards:
                full_board.append(hand.board_cards['river'])

        # =========================================
        # GTO Analysis for Hero's Preflop Actions
        # =========================================
        hero_gto_analysis = None
        if hero_name and 'preflop' in streets_data:
            hero_player = next((p for p in players if p['name'] == hero_name), None)
            if hero_player and hero_player.get('position'):
                hero_position = hero_player['position']
                preflop_actions = streets_data['preflop']['actions']

                # Analyze the preflop action sequence to determine hero's scenario
                first_raiser_name = None
                first_raiser_pos = None
                three_bettor_name = None
                three_bettor_pos = None
                four_bettor_name = None
                four_bettor_pos = None
                hero_opened = False
                hero_3bet = False
                hero_final_action = None
                raise_count = 0

                # First pass: identify the action sequence
                for action in preflop_actions:
                    action_type = action['action']
                    player = action['player']

                    # Skip blinds
                    if action_type in ['post_sb', 'post_bb']:
                        continue

                    # Track raises
                    if action_type == 'raise':
                        raise_count += 1
                        if raise_count == 1:
                            first_raiser_name = player
                            first_raiser_pos = next((p['position'] for p in players if p['name'] == player), None)
                            if player == hero_name:
                                hero_opened = True
                        elif raise_count == 2:
                            three_bettor_name = player
                            three_bettor_pos = next((p['position'] for p in players if p['name'] == player), None)
                            if player == hero_name:
                                hero_3bet = True
                        elif raise_count == 3:
                            four_bettor_name = player
                            four_bettor_pos = next((p['position'] for p in players if p['name'] == player), None)

                    # Track hero's final preflop action (last action they take)
                    if player == hero_name and action_type not in ['post_sb', 'post_bb']:
                        hero_final_action = action_type

                # Determine the GTO scenario based on what hero did
                gto_scenario = None
                gto_vs_position = None
                hero_gto_action = None

                if hero_final_action:
                    if hero_3bet and raise_count >= 3:
                        # Hero 3-bet and faced a 4-bet
                        gto_scenario = 'facing_4bet'
                        gto_vs_position = four_bettor_pos
                        # Hero's response to the 4-bet
                        if hero_final_action == 'raise':
                            hero_gto_action = '5bet'
                        elif hero_final_action == 'call':
                            hero_gto_action = 'call'
                        else:
                            hero_gto_action = 'fold'
                    elif hero_opened and raise_count >= 2:
                        # Hero opened and faced a 3-bet
                        gto_scenario = 'facing_3bet'
                        gto_vs_position = three_bettor_pos
                        # Hero's response to the 3-bet
                        if hero_final_action == 'raise':
                            hero_gto_action = '4bet'
                        elif hero_final_action == 'call':
                            hero_gto_action = 'call'
                        else:
                            hero_gto_action = 'fold'
                    elif hero_opened and raise_count == 1:
                        # Hero opened and wasn't 3-bet (just opened)
                        gto_scenario = 'opening'
                        hero_gto_action = 'open'
                    elif not hero_opened and raise_count >= 2:
                        # Hero faced a squeeze/3-bet (someone opened, someone else 3-bet)
                        # This is different from simple defense - hero is facing the 3-bettor
                        gto_scenario = 'defense'  # Still defense but vs the 3-bettor
                        gto_vs_position = three_bettor_pos  # The 3-bettor, not original raiser
                        if hero_final_action == 'raise':
                            hero_gto_action = '3bet'  # Would be a cold 4-bet
                        elif hero_final_action == 'call':
                            hero_gto_action = 'call'
                        else:
                            hero_gto_action = 'fold'
                    elif not hero_opened and raise_count == 1:
                        # Hero faced a single open (simple defense scenario)
                        gto_scenario = 'defense'
                        gto_vs_position = first_raiser_pos
                        if hero_final_action == 'raise':
                            hero_gto_action = '3bet'
                        elif hero_final_action == 'call':
                            hero_gto_action = 'call'
                        else:
                            hero_gto_action = 'fold'

                    # Look up GTO frequencies
                    if gto_scenario:
                        # First get aggregate GTO frequencies as fallback
                        gto_query = text("""
                            SELECT action, gto_aggregate_freq * 100 as freq
                            FROM gto_scenarios
                            WHERE category = :category
                            AND position = :position
                            AND (opponent_position = :vs_position OR (:vs_position IS NULL AND opponent_position IS NULL))
                        """)
                        gto_result = db.execute(gto_query, {
                            "category": gto_scenario,
                            "position": hero_position,
                            "vs_position": gto_vs_position
                        })
                        aggregate_gto_freqs = {row[0]: round(float(row[1]), 1) for row in gto_result}

                        # Try to get hand-specific GTO frequencies if hero has hole cards
                        gto_freqs = aggregate_gto_freqs
                        hero_hole_cards = hero_player.get('hole_cards')
                        if hero_hole_cards:
                            hand_info = categorize_hand(hero_hole_cards)
                            hand_combo = hand_info.get('combo')
                            if hand_combo and hand_combo not in ['Unknown', None]:
                                # Use the same lookup table as scenario-hands for consistency
                                gto_lookup = build_gto_lookup_table(db, gto_scenario, hero_position)
                                hand_specific = gto_lookup.get((hand_combo, gto_vs_position))
                                if hand_specific:
                                    gto_freqs = {k: round(v, 1) for k, v in hand_specific.items()}

                        if gto_freqs:
                            # Get frequency for hero's action
                            action_freq = gto_freqs.get(hero_gto_action, 0)

                            # Find recommended action (highest frequency)
                            recommended = max(gto_freqs.keys(), key=lambda k: gto_freqs[k]) if gto_freqs else None
                            recommended_freq = gto_freqs.get(recommended, 0) if recommended else 0

                            # Determine deviation assessment (aligned with classify_deviation)
                            # - Correct: >= 40%
                            # - Suboptimal: 15-40%
                            # - Mistake: < 15%
                            if action_freq >= 40:
                                deviation_type = 'correct'
                                deviation_desc = 'Within GTO range'
                            elif action_freq >= 15:
                                deviation_type = 'suboptimal'
                                deviation_desc = f'GTO prefers {recommended} ({recommended_freq}%)'
                            else:
                                deviation_type = 'mistake'
                                severity = 'major' if action_freq < 5 else 'moderate'
                                deviation_desc = f'GTO strongly prefers {recommended} ({recommended_freq}%)'

                            hero_gto_analysis = {
                                'scenario': gto_scenario,
                                'vs_position': gto_vs_position,
                                'hero_action': hero_gto_action,
                                'action_frequency': action_freq,
                                'gto_frequencies': gto_freqs,
                                'recommended_action': recommended,
                                'deviation_type': deviation_type,
                                'deviation_description': deviation_desc
                            }

        return {
            'hand_id': hand_id,
            'timestamp': raw_result.timestamp.isoformat() if raw_result.timestamp else None,
            'table_name': raw_result.table_name,
            'stake_level': stake_level,
            'big_blind': big_blind,
            'game_type': raw_result.game_type,
            'button_seat': hand.button_seat,
            'pot_size': float(hand.pot_size) if hand.pot_size else 0,
            'pot_size_bb': round(float(hand.pot_size) / big_blind, 1) if hand.pot_size and big_blind else 0,
            'rake': float(hand.rake) if hand.rake else 0,
            'players': players,
            'hero': hero_name,
            'streets': streets_data,
            'board': full_board,
            'results': results,
            'hero_gto_analysis': hero_gto_analysis,
            'raw_hand_text': raw_result.raw_hand_text
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting hand replay for {hand_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving hand: {str(e)}"
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
