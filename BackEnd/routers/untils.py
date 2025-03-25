import os
import jwt
import secrets
import uuid
import logging
import smtplib
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from dotenv import load_dotenv
from fastapi import HTTPException, Depends, Security, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import models
from database import get_db

# Load biến môi trường từ .env
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Cấu hình logging
logging.basicConfig(level=logging.ERROR)

# OAuth2 scheme để xác thực token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Mã hóa mật khẩu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_jwt_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn!")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ!")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_jwt_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Người dùng không tồn tại")
    return user

def get_admin_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Bạn không có quyền admin!")
    return user

def create_reset_token(db: Session, user_id: int):
    db.query(models.ResetToken).filter(models.ResetToken.user_id == user_id).delete()
    reset_uuid = str(uuid.uuid4())
    raw_token = secrets.token_urlsafe(32)
    token_hash = models.ResetToken.hash_token(raw_token)
    reset_entry = models.ResetToken(
        user_id=user_id,
        reset_uuid=reset_uuid,
        token_hash=token_hash,
        expires_at_UTC=datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    db.add(reset_entry)
    db.commit()
    return reset_uuid

def send_reset_email(to_email: str, reset_uuid: str):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        raise HTTPException(status_code=500, detail="Email sender credentials are missing!")
    reset_link = f"http://your-frontend.com/reset-password?uuid={reset_uuid}"
    subject = "Reset your password"
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg["Subject"] = subject
    email_content = f"""
    <html>
    <body>
        <h2>Password Reset</h2>
        <p>Click the link below to reset your password:</p>
        <a href="{reset_link}">{reset_link}</a>
        <p>This link will expire in 5 minutes.</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(email_content, "html"))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

def update_last_active_dependency(request: Request, db: Session = Depends(get_db)):
    token = request.headers.get("Authorization")
    if token:
        token = token.replace("Bearer ", "")
        try:
            payload = decode_jwt_token(token)
            username = payload.get("sub")
            user = db.query(models.User).filter(models.User.username == username).first()
            if user:
                user.last_active_UTC = datetime.now(timezone.utc)
                db.commit()
                db.refresh(user)
        except Exception as e:
            logging.error(f"Lỗi khi cập nhật last_active: {e}")
    return None

UPLOAD_DIR = "uploads/avatars"
os.makedirs(UPLOAD_DIR, exist_ok=True)
