from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import UserCreate, Token
from backend.auth import hash_password, verify_password, create_access_token

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=Token)
def register(data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = User(username=data.username, hashed_password=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.username})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
def login(data: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": user.username})
    return Token(access_token=token)
