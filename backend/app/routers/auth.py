from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import STAFF, current_user, require_roles
from ..models import User
from ..schemas import LoginIn, TokenOut, UserOut
from ..security import create_token, verify_password

router = APIRouter(prefix="/api")


@router.post("/auth/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Wrong username or password")
    return TokenOut(access_token=create_token(user.id), user=user)


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


# Logout is client-side (stateless JWT): the frontend discards the token.

@router.get("/users/technicians", response_model=list[UserOut])
def technicians(db: Session = Depends(get_db), _: User = Depends(require_roles(*STAFF))):
    return db.scalars(select(User).where(User.role.in_(STAFF)).order_by(User.full_name)).all()
