import os
import jwt
from dotenv import load_dotenv
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, Security, status, Request
from sqlalchemy.orm import Session
import models
from database import get_db
from fastapi.security import OAuth2PasswordBearer
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from models import User, ResetToken
import secrets
import uuid
import pytz
from datetime import datetime

# Múi giờ Việt Nam
VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")

def get_vn_time():
    """Lấy thời gian hiện tại theo múi giờ Việt Nam"""
    return datetime.now(VN_TZ)

# Load biến môi trường từ .env
load_dotenv()
SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback_secret_key")
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
# OAuth2 scheme để xác thực token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Mã hóa mật khẩu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Mã hóa mật khẩu bằng bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu có khớp với hash hay không"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Tạo access token với thời gian hết hạn"""
    to_encode = data.copy()
    expire = get_vn_time() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Tạo refresh token có thời gian dài hơn"""
    expire = get_vn_time() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_jwt_token(token: str):
    """
    Giải mã JWT token và trả về payload nếu hợp lệ.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn!")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ!")
    
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Lấy thông tin user từ JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token không hợp lệ")

        user = db.query(models.User).filter(models.User.user_id == user_id).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Người dùng không tồn tại")

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

    return user


def send_reset_email(to_email: str, reset_link: str):
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
    </body>
    </html>
    """  # Chỉ khai báo nội dung email một lần
    msg.attach(MIMEText(email_content, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
    
def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Middleware kiểm tra quyền admin"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        user = db.query(User).filter(User.user_id == user_id).first()
        if not user or not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền admin!"
            )

        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn!")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ!")    
    
def admin_required(token: str = Security(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        # Giải mã token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(status_code=401, detail="Token không hợp lệ!")

        # Kiểm tra user trong database
        user = db.query(models.User).filter(models.User.user_id == user_id).first()

        if not user or not user.is_admin:
            raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập!")

        return user  # Trả về user nếu là admin

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn!")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ!")

def create_reset_token(db: Session, user_id: int):
    """Xóa token cũ và tạo reset token mới"""
    
    # Xóa tất cả token cũ của user trước khi tạo mới
    db.query(ResetToken).filter(ResetToken.user_id == user_id).delete()
    
    reset_uuid = str(uuid.uuid4())
    raw_token = secrets.token_urlsafe(32)
    token_hash = ResetToken.hash_token(raw_token)

    reset_entry = ResetToken(
        user_id=user_id,
        reset_uuid=reset_uuid,
        token_hash=token_hash,
        expires_at=get_vn_time() + timedelta(minutes=5)
    )

    db.add(reset_entry)
    db.commit()
    return reset_uuid

def send_reset_email(to_email: str, reset_uuid: str):
    """Gửi email đặt lại mật khẩu với reset_uuid"""
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

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, to_email, msg.as_string())

# Update thời gian online mỗi khi gọi api
def update_last_active_dependency(request: Request, db: Session = Depends(get_db)):
    token = request.headers.get("Authorization")
    if token:
        token = token.replace("Bearer ", "")
        try:
            payload = decode_jwt_token(token)
            username = payload.get("sub")
            user = db.query(models.User).filter(models.User.username == username).first()
            if user:
                user.last_active = get_vn_time()
                db.commit()
        except:
            pass

# Thư mục lưu avatar
UPLOAD_DIR = "uploads/avatars"
os.makedirs(UPLOAD_DIR, exist_ok=True)
