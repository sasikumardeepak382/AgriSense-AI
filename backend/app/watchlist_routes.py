from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from .database import get_db
from .models import Watchlist
from .auth_routes import require_user

router = APIRouter(
    prefix="/api/watchlist",
    tags=["Watchlists"]
)


class WatchlistRequest(BaseModel):
    commodity: str = Field(min_length=1, max_length=100)


@router.get("/")
def get_watchlist(
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    items = db.query(Watchlist).filter(
        Watchlist.user_id == user.id
    ).all()

    return [
        {
            "id": item.id,
            "commodity": item.commodity
        }
        for item in items
    ]


@router.post("/")
def add_watchlist(
    payload: WatchlistRequest,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    commodity = payload.commodity.strip()

    existing = db.query(Watchlist).filter(
        Watchlist.user_id == user.id,
        Watchlist.commodity == commodity
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Already in your watchlist"
        )

    item = Watchlist(
        user_id=user.id,
        commodity=commodity
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "message": "Added to watchlist",
        "id": item.id,
        "commodity": item.commodity
    }


@router.delete("/{item_id}")
def remove_watchlist(
    item_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    item = db.query(Watchlist).filter(
        Watchlist.id == item_id,
        Watchlist.user_id == user.id
    ).first()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Watchlist item not found"
        )

    db.delete(item)
    db.commit()

    return {"message": "Removed from watchlist"}