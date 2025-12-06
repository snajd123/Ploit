"""
Pre-Game Strategy API Endpoints

Endpoints for viewing saved pre-game strategies.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db

router = APIRouter(prefix="/api/pregame", tags=["pregame"])


class PregameStrategySummary(BaseModel):
    """Summary of a pre-game strategy for list view."""
    id: int
    created_at: datetime
    stake_level: str
    softness_score: float
    table_classification: str
    opponent_count: int
    known_opponents: int
    email_sent: bool


class PregameStrategyDetail(BaseModel):
    """Full pre-game strategy details."""
    id: int
    created_at: datetime
    hero_nickname: Optional[str]
    stake_level: str
    hand_number: Optional[str]
    softness_score: float
    table_classification: str
    strategy: Dict[str, Any]
    opponents: List[Dict[str, Any]]
    email_sent: bool
    email_sent_at: Optional[datetime]
    ai_prompt: Optional[str] = None
    ai_response: Optional[str] = None


@router.get("/", response_model=List[PregameStrategySummary])
def get_pregame_strategies(
    limit: int = 50,
    db: Session = Depends(get_db)
) -> List[PregameStrategySummary]:
    """
    Get list of all saved pre-game strategies, most recent first.
    """
    result = db.execute(text("""
        SELECT
            id,
            created_at,
            stake_level,
            softness_score,
            table_classification,
            opponents,
            email_sent
        FROM pregame_strategies
        ORDER BY created_at DESC
        LIMIT :limit
    """), {"limit": limit})

    strategies = []
    for row in result:
        opponents = row[5] if row[5] else []
        if isinstance(opponents, str):
            import json
            opponents = json.loads(opponents)

        known_count = sum(1 for o in opponents if o.get("data_source") == "DATABASE")

        strategies.append(PregameStrategySummary(
            id=row[0],
            created_at=row[1],
            stake_level=row[2] or "Unknown",
            softness_score=float(row[3]) if row[3] else 3.0,
            table_classification=row[4] or "UNKNOWN",
            opponent_count=len(opponents),
            known_opponents=known_count,
            email_sent=row[6] or False
        ))

    return strategies


@router.get("/{strategy_id}", response_model=PregameStrategyDetail)
def get_pregame_strategy(
    strategy_id: int,
    db: Session = Depends(get_db)
) -> PregameStrategyDetail:
    """
    Get full details of a specific pre-game strategy.
    """
    result = db.execute(text("""
        SELECT
            id,
            created_at,
            hero_nickname,
            stake_level,
            hand_number,
            softness_score,
            table_classification,
            strategy,
            opponents,
            email_sent,
            email_sent_at,
            ai_prompt,
            ai_response
        FROM pregame_strategies
        WHERE id = :id
    """), {"id": strategy_id})

    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Strategy not found")

    strategy = row[7] if row[7] else {}
    opponents = row[8] if row[8] else []

    if isinstance(strategy, str):
        import json
        strategy = json.loads(strategy)
    if isinstance(opponents, str):
        import json
        opponents = json.loads(opponents)

    return PregameStrategyDetail(
        id=row[0],
        created_at=row[1],
        hero_nickname=row[2],
        stake_level=row[3] or "Unknown",
        hand_number=row[4],
        softness_score=float(row[5]) if row[5] else 3.0,
        table_classification=row[6] or "UNKNOWN",
        strategy=strategy,
        opponents=opponents,
        email_sent=row[9] or False,
        email_sent_at=row[10],
        ai_prompt=row[11],
        ai_response=row[12]
    )


@router.delete("/{strategy_id}")
def delete_pregame_strategy(
    strategy_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a pre-game strategy.
    """
    result = db.execute(text("""
        DELETE FROM pregame_strategies
        WHERE id = :id
        RETURNING id
    """), {"id": strategy_id})

    deleted = result.fetchone()
    if not deleted:
        raise HTTPException(status_code=404, detail="Strategy not found")

    db.commit()
    return {"deleted": True, "id": strategy_id}
