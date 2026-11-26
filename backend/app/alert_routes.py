
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Literal

import pandas as pd

from .database import get_db
from .models import PriceAlert
from .data import load_data
from .auth_routes import require_user

router = APIRouter(
    prefix="/api/alerts",
    tags=["Price Alerts"]
)


class AlertRequest(BaseModel):
    commodity: str = Field(min_length=1, max_length=100)
    target_price: int = Field(gt=0)
    condition: Literal["above", "below"]


@router.get("/")
def get_alerts(
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    items = db.query(PriceAlert).filter(
        PriceAlert.user_id == user.id
    ).all()

    results = []

    for item in items:
        results.append({
            "id": item.id,
            "commodity": item.commodity,
            "target_price": item.target_price,
            "condition": item.condition,
            "current_price": item.last_checked_price,
            "is_triggered": bool(item.is_triggered),
            "is_active": item.is_active
        })

    return results


@router.post("/")
def create_alert(
    payload: AlertRequest,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    item = PriceAlert(
        user_id=user.id,
        commodity=payload.commodity.strip(),
        target_price=payload.target_price,
        condition=payload.condition,
        is_active=1,
        is_triggered=0,
        last_checked_price=None
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "message": "Price alert created successfully",
        "id": item.id
    }


@router.delete("/{alert_id}")
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    item = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == user.id
    ).first()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Alert not found"
        )

    db.delete(item)
    db.commit()

    return {
        "message": "Alert deleted successfully"
    }
