from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, WatchlistItem
from backend.schemas import WatchlistAdd, WatchlistItemResponse, WatchlistResponse
from backend.auth import get_current_user

router = APIRouter(tags=["watchlist"])


@router.get("", response_model=WatchlistResponse)
def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = db.query(WatchlistItem).filter(WatchlistItem.user_id == current_user.id).all()
    return WatchlistResponse(
        items=[WatchlistItemResponse.model_validate(i) for i in items],
        count=len(items),
    )


@router.post("", response_model=WatchlistItemResponse)
def add_to_watchlist(
    data: WatchlistAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == current_user.id, WatchlistItem.symbol == data.symbol)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Symbol already in watchlist")

    item = WatchlistItem(user_id=current_user.id, symbol=data.symbol)
    db.add(item)
    db.commit()
    db.refresh(item)
    return WatchlistItemResponse.model_validate(item)


@router.delete("/{symbol}")
def remove_from_watchlist(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == current_user.id, WatchlistItem.symbol == symbol)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not in watchlist")

    db.delete(item)
    db.commit()
    return {"detail": "removed"}
