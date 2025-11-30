# FILE: app/routes/auth.py

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import User
from ..security import hash_password, verify_password, create_access_token, decode_token
from ..schemas import UserRegisterIn, LoginIn, TokenOut, UserOut
from ..config import settings
from ..services.audit import create_audit_log

router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalid sau expirat")
    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inexistent sau inactiv")
    return user


@router.post("/register", response_model=UserOut)
def register_user(data: UserRegisterIn, request: Request, db: Session = Depends(get_db)):
    if not data.accept_policy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trebuie să accepți politica aplicației pentru a continua.",
        )

    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email deja folosit.")

    user = User(
        email=data.email,
        name=data.name,
        password_hash=hash_password(data.password),
        policy_version=settings.policy_version,
        policy_accepted_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    create_audit_log(db, "REGISTER", user.id, request, details={"email": user.email})
    return user


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        create_audit_log(db, "LOGIN_FAIL", None, request, details={"email": data.email})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credențiale invalide.")

    user.last_login_at = datetime.utcnow()
    db.commit()

    token = create_access_token({"sub": str(user.id)})
    create_audit_log(db, "LOGIN_SUCCESS", user.id, request)

    return TokenOut(access_token=token, user=user)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
