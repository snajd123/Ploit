"""
FastAPI backend for Poker Analysis App.

Provides REST API endpoints for:
- Uploading hand history files
- Querying player statistics
- Database overview
- Claude AI integration for natural language queries
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status
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
from backend.parser import PokerStarsParser
from backend.config import get_settings
from backend.verification_endpoint import router as verification_router
from backend.api.gto_endpoints import router as gto_router
from backend.api.strategy_endpoints import router as strategy_router
from backend.api.conversation_endpoints import router as conversation_router
from backend.models.conversation_models import ClaudeConversation, ClaudeMessage

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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include verification router
app.include_router(verification_router)

# Include GTO router
app.include_router(gto_router)

# Include Strategy router
app.include_router(strategy_router)

# Include Conversation router
app.include_router(conversation_router)

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


class PlayerStatsResponse(BaseModel):
    """Response model for player statistics"""
    player_name: str
    total_hands: int

    # Traditional stats
    vpip_pct: Optional[float] = None
    pfr_pct: Optional[float] = None
    three_bet_pct: Optional[float] = None
    cbet_flop_pct: Optional[float] = None
    wtsd_pct: Optional[float] = None
    wsd_pct: Optional[float] = None

    # Composite metrics
    exploitability_index: Optional[float] = None
    pressure_vulnerability_score: Optional[float] = None
    player_type: Optional[str] = None

    # Dates
    first_hand_date: Optional[datetime] = None
    last_hand_date: Optional[datetime] = None


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


class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str
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

    Returns API status and database connection status.
    """
    db_status = "connected" if check_db_connection() else "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        database=db_status,
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
        service = DatabaseService(db)
        stats = service.get_player_stats(player_name)

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
    description="Recalculate statistics for all players using the latest flag calculation logic"
)
async def recalculate_all_stats(db: Session = Depends(get_db)):
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
                "three_bet": f"{made_3bet_count}/{faced_raise_count} = {round(made_3bet_count/faced_raise_count*100, 1) if faced_raise_count > 0 else 'N/A'}",
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
    summary="Clear all database data",
    description="Delete all data from all tables (USE WITH CAUTION)"
)
async def clear_database(db: Session = Depends(get_db)):
    """
    Clear all data from the database.

    WARNING: This is a destructive operation that cannot be undone.

    Deletes all data from:
    - player_stats
    - player_hand_summary
    - hand_actions
    - raw_hands
    - upload_sessions

    Returns:
        Confirmation message with counts of deleted records
    """
    try:
        from backend.models.database_models import (
            PlayerStats, PlayerHandSummary, HandAction, RawHand, UploadSession
        )

        # Count records before deletion
        stats_count = db.query(PlayerStats).count()
        summary_count = db.query(PlayerHandSummary).count()
        actions_count = db.query(HandAction).count()
        hands_count = db.query(RawHand).count()
        sessions_count = db.query(UploadSession).count()

        logger.warning("Starting database clear operation")

        # Delete in order respecting foreign keys
        db.query(PlayerStats).delete()
        db.query(PlayerHandSummary).delete()
        db.query(HandAction).delete()
        db.query(RawHand).delete()
        db.query(UploadSession).delete()

        db.commit()

        logger.warning(f"Database cleared: {hands_count} hands, {actions_count} actions, {summary_count} summaries, {stats_count} player stats, {sessions_count} sessions")

        return {
            "message": "Database cleared successfully",
            "deleted": {
                "raw_hands": hands_count,
                "hand_actions": actions_count,
                "player_hand_summary": summary_count,
                "player_stats": stats_count,
                "upload_sessions": sessions_count
            }
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing database: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing database: {str(e)}"
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
        result = claude_service.query(
            user_query=request.query,
            conversation_history=request.conversation_history
        )

        # Convert tool calls to Pydantic models if present
        tool_calls = None
        tool_calls_json = None
        if result.get("tool_calls"):
            tool_calls = [
                ClaudeToolCall(**tc) for tc in result["tool_calls"]
            ]
            tool_calls_json = result.get("tool_calls")

        # Save assistant message
        assistant_message = ClaudeMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=result.get("response", ""),
            tool_calls=tool_calls_json,
            usage=result.get("usage")
        )
        db.add(assistant_message)
        db.commit()

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
    description="Runs the conversation tables migration. Safe to call multiple times."
)
async def run_migration(db: Session = Depends(get_db)):
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

    # Check database connection
    if check_db_connection():
        logger.info("Database connection successful")
    else:
        logger.warning("Database connection failed")


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
