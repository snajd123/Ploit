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


@app.get(
    "/api/players",
    response_model=List[PlayerListItem],
    tags=["Players"],
    summary="Get all players",
    description="Retrieve list of all players with optional filtering"
)
async def get_all_players(
    min_hands: int = 100,
    stake_level: Optional[str] = None,
    sort_by: str = 'total_hands',
    limit: int = 100,
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

        # Initialize Claude service
        claude_service = ClaudeService(db)

        # Process query
        result = claude_service.query(
            user_query=request.query,
            conversation_history=request.conversation_history
        )

        # Convert tool calls to Pydantic models if present
        tool_calls = None
        if result.get("tool_calls"):
            tool_calls = [
                ClaudeToolCall(**tc) for tc in result["tool_calls"]
            ]

        return ClaudeQueryResponse(
            success=result["success"],
            response=result.get("response", ""),
            tool_calls=tool_calls,
            usage=result.get("usage"),
            error=result.get("error")
        )

    except Exception as e:
        logger.error(f"Error processing Claude query: {str(e)}", exc_info=True)
        return ClaudeQueryResponse(
            success=False,
            response="I apologize, but I encountered an error processing your query. Please try rephrasing your question.",
            error=str(e)
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
