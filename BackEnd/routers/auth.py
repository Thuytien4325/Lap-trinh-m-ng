from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
import jwt
from database import get_db
import models
from schemas import UserCreate, TokenSchema, ResetPasswordConfirm, UserResponse,ResetPasswordRequest
from routers.untils import (
    pwd_context, create_access_token, create_refresh_token, 
    SECRET_KEY, ALGORITHM, send_reset_email, hash_password, 
    create_reset_token, get_vn_time
)
import pytz

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
# Tạo router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Hàm giải mã token dùng chung
def decode_jwt_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn!")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ!")

# Đăng ký người dùng
@auth_router.post("/register", response_model=TokenSchema)
def register(user: UserCreate, db: Session = Depends(get_db)):
    user.email = user.email.lower()
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
        last_active=get_vn_time(),
        created_at=get_vn_time(),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.username})
    refresh_token = create_refresh_token(data={"sub": new_user.username})

    # Trả về đúng `TokenSchema`
    return TokenSchema(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        user=UserResponse(
            user_id=new_user.user_id,
            username=new_user.username,
            nickname=new_user.nickname,
            email=new_user.email,
            avatar=new_user.avatar,
            last_active=new_user.last_active,
            created_at=new_user.created_at
        )
    )

# Đăng nhập
@auth_router.post("/login", response_model=TokenSchema)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(
        (models.User.username == form_data.username) | 
        (models.User.email.ilike(form_data.username))
    ).first()

    if not db_user or not pwd_context.verify(form_data.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Tên đăng nhập, email hoặc mật khẩu không đúng!")

    # Tạo access token và refresh token
    access_token = create_access_token(data={"sub": db_user.username, "user_id": db_user.user_id})
    refresh_token = create_refresh_token(data={"sub": db_user.username})

    # Trả về đúng `TokenSchema` với refresh token
    return TokenSchema(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        user=UserResponse(
            user_id=db_user.user_id,
            username=db_user.username,
            nickname=db_user.nickname,
            email=db_user.email,
            avatar=db_user.avatar,
            last_active=db_user.last_active,
            created_at=db_user.created_at
        )
    )

# API refresh token
@auth_router.post("/refresh-token", response_model=TokenSchema)
def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    payload = decode_jwt_token(refresh_token)
    if not payload: 
        raise HTTPException(status_code=401, detail="Refresh token không hợp lệ!")

    username = payload.get("sub")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Người dùng không tồn tại!")

    new_access_token = create_access_token(data={"sub": user.username, "user_id": user.user_id})

    # Trả về đúng `TokenSchema`
    return TokenSchema(
        access_token=new_access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        user=UserResponse(
            user_id=user.user_id,
            username=user.username,
            nickname=user.nickname,
            email=user.email,
            avatar=user.avatar,
            last_active=user.last_active,
            created_at=user.created_at
        )
    )

@auth_router.post("/reset-password-request")
def reset_password_request(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    reset_code = create_reset_token(db, user.user_id)
    send_reset_email(user.email, reset_code)
    
    return {"message": "Email đặt lại mật khẩu đã được gửi."}

@auth_router.post("/reset-password-confirm")
def reset_password_confirm(request: ResetPasswordConfirm, db: Session = Depends(get_db)):
    try:
        reset_uuid = request.reset_uuid
    except ValueError:
        raise HTTPException(status_code=400, detail="UUID không hợp lệ.")
    
    reset_entry = db.query(models.ResetToken).filter(
        models.ResetToken.reset_uuid == str(reset_uuid)
    ).first()

    if not reset_entry:
        raise HTTPException(status_code=400, detail="Liên kết đặt lại mật khẩu không hợp lệ.")
    if reset_entry.expires_at.replace(tzinfo=VN_TZ) < get_vn_time():
        raise HTTPException(status_code=400, detail="Liên kết đặt lại mật khẩu đã hết hạn.")
    
    user = db.query(models.User).filter(models.User.user_id == reset_entry.user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại.")

    user.password_hash = hash_password(request.new_password)
    db.commit()
    db.refresh(user)
    db.delete(reset_entry)
    db.commit()

    return {"message": "Mật khẩu đã được đặt lại thành công."}
