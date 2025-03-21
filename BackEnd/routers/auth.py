from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
import jwt
import os
from database import get_db
import models
from dotenv import load_dotenv
from schemas import UserCreate, TokenSchema
# Load biến môi trường từ .env
load_dotenv()
SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback_secret_key")
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# Tạo router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Mã hóa mật khẩu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Tạo access token
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Đăng ký người dùng
@auth_router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user_email = db.query(models.User).filter(models.User.email == user.email).first()
    db_user_username = db.query(models.User).filter(models.User.username == user.username).first()

    if db_user_username:
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã được sử dụng!")
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng!")

    hashed_password = pwd_context.hash(user.password)
    new_user = models.User(
        username=user.username,
        nickname=user.nickname,
        email=user.email,
        password_hash=hashed_password,
        created_at=datetime.utcnow()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Tạo token ngay sau khi đăng ký thành công
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.username}, expires_delta=access_token_expires
    )

    return {
        "message": "Tạo tài khoản thành công",
        "user": {
            "username": new_user.username,
            "nickname": new_user.nickname,
            "email": new_user.email,
            "created_at": new_user.created_at
        },
        "access_token": access_token,
        "token_type": "bearer"
    }

# Đăng nhập
@auth_router.post("/login", response_model=TokenSchema)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(
        (models.User.username == form_data.username) | 
        (models.User.email == form_data.username)
    ).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc email không tồn tại!")
    if not pwd_context.verify(form_data.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Mật khẩu không đúng!")

    access_token = create_access_token(
        data={"sub": db_user.username, "user_id": db_user.user_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "user": {
            "user_id": db_user.user_id,
            "username": db_user.username,
            "nickname": db_user.nickname,
            "email": db_user.email,
            "avatar_url": db_user.avatar
        }
    }
