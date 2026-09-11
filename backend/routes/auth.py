"""
Auth routes: /auth/register, /auth/login
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.database import get_db, User, RoleType
from models.schemas import UserRegister, UserLogin, TokenResponse
from utils.auth_utils import hash_password, verify_password, create_access_token

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(data: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    role = RoleType.ADMIN if data.role.upper() == "ADMIN" else RoleType.INSPECTOR

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role.value, "name": user.name})
    return TokenResponse(access_token=token, role=user.role.value, name=user.name, user_id=str(user.id))


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(user.id), "role": user.role.value, "name": user.name})
    return TokenResponse(access_token=token, role=user.role.value, name=user.name, user_id=str(user.id))
