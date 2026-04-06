from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class WatchlistAdd(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50)


class WatchlistItemResponse(BaseModel):
    id: int
    symbol: str
    added_at: datetime

    class Config:
        from_attributes = True


class WatchlistResponse(BaseModel):
    items: List[WatchlistItemResponse]
    count: int
