from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from database import get_db
from pydantic import EmailStr
import models
from schemas import (
    UserCreate,
    TokenSchema,
    ResetPasswordConfirm,
    UserResponse,
    UserProfile,
)
from routers.untils import (
    pwd_context,
    create_access_token,
    create_refresh_token,
    SECRET_KEY,
    ALGORITHM,
    send_reset_email,
    hash_password,
    create_reset_token,
    decode_jwt_token,
)
import os
from dotenv import load_dotenv


# Load biến môi trường từ .env
load_dotenv()

# Lấy thời gian hết hạn của các token
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# Lấy thời gian hết hạn của các token từ .env
access_token_time = f"{ACCESS_TOKEN_EXPIRE_MINUTES} phút"
refresh_token_time = f"{REFRESH_TOKEN_EXPIRE_DAYS} ngày"

# Tạo router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Đăng ký người dùng
@auth_router.post("/register", response_model=TokenSchema)
def register(user: UserCreate, db: Session = Depends(get_db)):
    user.email = user.email.lower()
    db_user_email = (
        db.query(models.User).filter(models.User.email == user.email).first()
    )
    db_user_username = (
        db.query(models.User).filter(models.User.username == user.username).first()
    )

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
        last_active_UTC=datetime.now(timezone.utc),
        created_at_UTC=datetime.now(timezone.utc),
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
        access_token_time=access_token_time,
        refresh_token_time=refresh_token_time,
        user=UserResponse(
            user_id=new_user.user_id,
            username=new_user.username,
            nickname=new_user.nickname,
            email=new_user.email,
            avatar=new_user.avatar,
            last_active_UTC=new_user.last_active_UTC,
            created_at_UTC=new_user.created_at_UTC,
        ),
    )


# Đăng nhập
@auth_router.post("/login", response_model=TokenSchema)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    db_user = (
        db.query(models.User)
        .filter(
            (models.User.username == form_data.username)
            | (models.User.email.ilike(form_data.username))
        )
        .first()
    )

    if not db_user or not pwd_context.verify(form_data.password, db_user.password_hash):
        raise HTTPException(
            status_code=401, detail="Tên đăng nhập, email hoặc mật khẩu không đúng!"
        )

    # Cập nhật thời gian online
    db_user.last_active_UTC = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_user)

    # Tạo access token và refresh token
    access_token = create_access_token(
        data={"sub": db_user.username, "user_id": db_user.user_id}
    )
    refresh_token = create_refresh_token(data={"sub": db_user.username})

    # Trả về đúng `TokenSchema` với refresh token
    return TokenSchema(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        access_token_time=access_token_time,
        refresh_token_time=refresh_token_time,
        user=UserResponse(
            user_id=db_user.user_id,
            username=db_user.username,
            nickname=db_user.nickname,
            email=db_user.email,
            avatar=db_user.avatar,
            last_active_UTC=db_user.last_active_UTC,
            created_at_UTC=db_user.created_at_UTC,
        ),
    )


# API refresh token
@auth_router.post("/refresh-token", response_model=TokenSchema)
def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    payload = decode_jwt_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Refresh token không hợp lệ!")

    exp = payload.get("exp")
    if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(
        timezone.utc
    ):
        raise HTTPException(status_code=401, detail="Refresh token đã hết hạn!")

    username = payload.get("sub")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Người dùng không tồn tại!")

    # Cập nhật thời gian online
    user.last_active_UTC = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    new_access_token = create_access_token(
        data={"sub": user.username, "user_id": user.user_id}
    )

    # Trả về đúng `TokenSchema`
    return TokenSchema(
        access_token=new_access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        access_token_time=access_token_time,
        refresh_token_time=refresh_token_time,
        user=UserResponse(
            user_id=user.user_id,
            username=user.username,
            nickname=user.nickname,
            email=user.email,
            avatar=user.avatar,
            last_active_UTC=user.last_active_UTC,
            created_at_UTC=user.created_at_UTC,
        ),
    )


@auth_router.post("/reset-password-request")
def reset_password_request(email: EmailStr, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng!")
    if user.is_admin:
        raise HTTPException(
            status_code=403, detail="Admin không thể sử dụng chức năng này!"
        )

    reset_code = create_reset_token(db, user.user_id)
    try:
        send_reset_email(user.email, reset_code)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Không thể gửi email, vui lòng thử lại sau!"
        )

    return {"message": "Email đặt lại mật khẩu đã được gửi."}


@auth_router.post("/reset-password-confirm")
def reset_password_confirm(
    request: ResetPasswordConfirm, db: Session = Depends(get_db)
):
    reset_entry = (
        db.query(models.ResetToken)
        .filter(models.ResetToken.reset_uuid == str(request.reset_uuid))
        .first()
    )

    if not reset_entry:
        raise HTTPException(
            status_code=400, detail="Liên kết đặt lại mật khẩu không hợp lệ!"
        )

    if reset_entry.expires_at_UTC.replace(tzinfo=timezone.utc) < datetime.now(
        timezone.utc
    ):
        raise HTTPException(
            status_code=400, detail="Liên kết đặt lại mật khẩu đã hết hạn!"
        )

    user = (
        db.query(models.User).filter(models.User.user_id == reset_entry.user_id).first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại!")

    if user.is_admin:
        raise HTTPException(
            status_code=403, detail="Admin không thể sử dụng chức năng này!"
        )

    # Cập nhật thời gian online
    user.last_active_UTC = datetime.now(timezone.utc)

    # Cập nhật mật khẩu mới
    user.password_hash = hash_password(request.new_password)

    try:
        db.commit()  # Chỉ commit nếu mọi thứ ổn
        db.refresh(user)

        # Thông báo cho người dùng
        new_notification = models.Notification(
            user_username=user.username,
            sender_username=None,
            message="Mật khẩu của bạn đã được đổi thành công.",
            type="message",
            related_id=0,
            related_table=None,
        )

        db.add(new_notification)
        db.commit()

        # Xóa reset token sau khi đã cập nhật thành công
        db.delete(reset_entry)
        db.commit()

        return {"message": "Mật khẩu đã được đặt lại thành công!"}
    except Exception:
        db.rollback()  # Hủy bỏ nếu có lỗi
        raise HTTPException(
            status_code=500, detail="Có lỗi xảy ra, vui lòng thử lại sau!"
        )


@auth_router.get("/get-profile", response_model=UserProfile)
def get_user_profile(username: str, db: Session = Depends(get_db)):
    user = (
        db.query(models.User)
        .filter(models.User.username == username, models.User.is_admin == False)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=404, detail="Người dùng không tồn tại hoặc là admin"
        )
    return user
