"""
User Settings API Endpoints

Manages hero nicknames and other user settings for distinguishing
'My Game' (hero) from 'Pools' (opponents).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])


class HeroNicknameResponse(BaseModel):
    """Hero nickname response"""
    nickname_id: int
    nickname: str
    site: Optional[str] = None
    created_at: datetime


class HeroNicknameCreate(BaseModel):
    """Request to create a hero nickname"""
    nickname: str
    site: Optional[str] = None


class HeroNicknameUpdate(BaseModel):
    """Request to update a hero nickname"""
    nickname: Optional[str] = None
    site: Optional[str] = None


@router.get("/hero-nicknames", response_model=List[HeroNicknameResponse])
def get_hero_nicknames(db: Session = Depends(get_db)):
    """
    Get all hero nicknames.
    """
    result = db.execute(text("""
        SELECT nickname_id, nickname, site, created_at
        FROM hero_nicknames
        ORDER BY created_at DESC
    """))
    rows = result.fetchall()

    return [
        HeroNicknameResponse(
            nickname_id=row.nickname_id,
            nickname=row.nickname,
            site=row.site,
            created_at=row.created_at
        )
        for row in rows
    ]


@router.post("/hero-nicknames", response_model=HeroNicknameResponse)
def add_hero_nickname(
    request: HeroNicknameCreate,
    db: Session = Depends(get_db)
):
    """
    Add a new hero nickname.
    """
    # Check if nickname already exists for this site
    existing = db.execute(text("""
        SELECT nickname_id FROM hero_nicknames
        WHERE nickname = :nickname AND (site = :site OR (site IS NULL AND :site IS NULL))
    """), {"nickname": request.nickname, "site": request.site}).fetchone()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Nickname '{request.nickname}' already exists for site '{request.site or 'All Sites'}'"
        )

    result = db.execute(text("""
        INSERT INTO hero_nicknames (nickname, site)
        VALUES (:nickname, :site)
        RETURNING nickname_id, nickname, site, created_at
    """), {"nickname": request.nickname, "site": request.site})
    db.commit()

    row = result.fetchone()
    return HeroNicknameResponse(
        nickname_id=row.nickname_id,
        nickname=row.nickname,
        site=row.site,
        created_at=row.created_at
    )


@router.delete("/hero-nicknames/{nickname_id}")
def delete_hero_nickname(
    nickname_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a hero nickname.
    """
    result = db.execute(text("""
        DELETE FROM hero_nicknames
        WHERE nickname_id = :nickname_id
        RETURNING nickname_id
    """), {"nickname_id": nickname_id})
    db.commit()

    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Nickname not found")

    return {"message": "Nickname deleted successfully"}


@router.put("/hero-nicknames/{nickname_id}", response_model=HeroNicknameResponse)
def update_hero_nickname(
    nickname_id: int,
    request: HeroNicknameUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a hero nickname.
    """
    # Build update query dynamically
    updates = []
    params = {"nickname_id": nickname_id}

    if request.nickname is not None:
        updates.append("nickname = :nickname")
        params["nickname"] = request.nickname

    if request.site is not None:
        updates.append("site = :site")
        params["site"] = request.site

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = db.execute(text(f"""
        UPDATE hero_nicknames
        SET {", ".join(updates)}
        WHERE nickname_id = :nickname_id
        RETURNING nickname_id, nickname, site, created_at
    """), params)
    db.commit()

    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Nickname not found")

    return HeroNicknameResponse(
        nickname_id=row.nickname_id,
        nickname=row.nickname,
        site=row.site,
        created_at=row.created_at
    )


@router.get("/hero-nicknames/check/{player_name}")
def check_if_hero(
    player_name: str,
    db: Session = Depends(get_db)
):
    """
    Check if a player name matches any hero nickname.
    Returns whether the player is the hero.
    """
    result = db.execute(text("""
        SELECT nickname_id, nickname, site
        FROM hero_nicknames
        WHERE LOWER(nickname) = LOWER(:player_name)
    """), {"player_name": player_name})

    match = result.fetchone()

    return {
        "is_hero": match is not None,
        "nickname_id": match.nickname_id if match else None,
        "site": match.site if match else None
    }


@router.get("/hero-nicknames/list-names")
def get_hero_nickname_list(db: Session = Depends(get_db)):
    """
    Get a simple list of all hero nicknames (lowercase for matching).
    Used for quick hero identification.
    """
    result = db.execute(text("""
        SELECT LOWER(nickname) as nickname
        FROM hero_nicknames
    """))

    return {
        "nicknames": [row.nickname for row in result.fetchall()]
    }
