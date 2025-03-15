from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from database import get_db
import models
import jwt
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from jwt import PyJWTError

# Load biến môi trường từ .env
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key")  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Access Token hết hạn sau 1 giờ

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# =========================
# 🔹 HÀM TẠO TOKEN
# =========================
def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# =========================
# 🔹 SCHEMA DỮ LIỆU
# =========================
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr  
    password: str = Field(..., min_length=8, max_length=100)

class UserLogin(BaseModel):
    email: str
    password: str

class TokenSchema(BaseModel):
    access_token: str

# =========================
# 🔹 ĐĂNG KÝ TÀI KHOẢN
# =========================
@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.username == user.username)
    ).first()
    
    if db_user:
        raise HTTPException(status_code=400, detail="Email or username already registered")

    hashed_password = pwd_context.hash(user.password)
    
    new_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        created_at=datetime.utcnow()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "message": "User created successfully",
        "user_id": new_user.user_id,
        "username": new_user.username,
        "email": new_user.email,
        "created_at": new_user.created_at,
    }

# =========================
# 🔹 ĐĂNG NHẬP & CẤP TOKEN
# =========================
@router.post("/login", response_model=TokenSchema)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not pwd_context.verify(user.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Tạo Access Token
    access_token = create_access_token(
        data={"sub": db_user.email, "user_id": db_user.user_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token
    }

# =========================
# 🔹 API LẤY USER TỪ TOKEN
# =========================
async def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    try:
        token = authorization.split(" ")[1]  # Lấy token sau "Bearer "
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(models.User).filter(models.User.email == email).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
    except (PyJWTError, IndexError):
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    return user

# =========================
# 🔹 API LẤY THÔNG TIN USER
# =========================
@router.get("/me")
def get_user_info(current_user: models.User = Depends(get_current_user)):
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "avatar": current_user.avatar,
        "created_at": current_user.created_at
    }
