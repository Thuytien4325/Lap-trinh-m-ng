from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
import os
import shutil
from database import get_db
import models
from routers.auth import oauth2_scheme, SECRET_KEY, ALGORITHM
from schemas import UserResponse, UserUpdate, UserProfile
from routers.untils import get_current_user, UPLOAD_DIR, update_last_active_dependency
from typing import List
from datetime import datetime, timedelta, timezone

# Tạo router
users_router = APIRouter(prefix="/users", tags=["User"])


# Lấy thông tin user hiện tại
@users_router.get(
    "/me",
    response_model=UserResponse,
    dependencies=[Depends(update_last_active_dependency)],
)
def get_user_info(current_user: models.User = Depends(get_current_user)):
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        nickname=current_user.nickname,
        email=current_user.email,
        avatar=current_user.avatar,
        last_active_UTC=current_user.last_active_UTC,
        created_at_UTC=current_user.created_at_UTC,
    )


@users_router.get(
    "/search-username",
    response_model=List[UserProfile],
    dependencies=[Depends(update_last_active_dependency)],
)
def search_username_users(
    username: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    users = (
        db.query(models.User)
        .filter(
            models.User.username.ilike(f"%{username}%"), models.User.is_admin == False
        )
        .all()
    )

    return [UserProfile.model_validate(user) for user in users]


@users_router.get(
    "/search-nickname",
    response_model=List[UserProfile],
    dependencies=[Depends(update_last_active_dependency)],
)
def search_nickname_users(
    nickname: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    users = (
        db.query(models.User)
        .filter(
            models.User.nickname.ilike(f"%{nickname}%"), models.User.is_admin == False
        )
        .all()
    )

    return [UserProfile.model_validate(user) for user in users]


# Upload Avatar
@users_router.post(
    "/upload-avatar", dependencies=[Depends(update_last_active_dependency)]
)
def upload_avatar(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Chặn admin thay đổi avatar
    if current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin không được thay đổi avatar.")

    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ["jpg", "jpeg", "png"]:
        raise HTTPException(
            status_code=400,
            detail="Định dạng ảnh không hợp lệ! (Chỉ chấp nhận jpg, jpeg, png)",
        )

    # Kiểm tra và xóa avatar cũ nếu có
    if current_user.avatar:
        old_avatar_path = current_user.avatar
        try:
            if os.path.exists(old_avatar_path):
                os.remove(old_avatar_path)
        except Exception as e:
            print(f"Lỗi khi xóa avatar cũ: {e}")

    # Định dạng tên file: user_id + phần mở rộng
    file_path = f"{UPLOAD_DIR}/userID_{current_user.user_id}.{file_extension}"

    # Lưu file lên server
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Cập nhật avatar vào database
    current_user.avatar = file_path
    db.commit()
    db.refresh(current_user)

    return {"message": "Tải ảnh đại diện thành công", "avatar_url": file_path}


# Cập nhật thông tin user
@users_router.put("/update", dependencies=[Depends(update_last_active_dependency)])
def update_user(
    user_update: UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Chặn admin cập nhật thông tin cá nhân
    if current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="Admin không được cập nhật thông tin cá nhân."
        )

    if user_update.email and user_update.email != current_user.email:
        existing_user = (
            db.query(models.User).filter(models.User.email == user_update.email).first()
        )
        if existing_user:
            raise HTTPException(
                status_code=400, detail="Email đã được sử dụng bởi người dùng khác"
            )

    if user_update.nickname:
        current_user.nickname = user_update.nickname
    if user_update.email:
        current_user.email = user_update.email

    db.commit()
    db.refresh(current_user)

    return {
        "message": "Cập nhật thông tin thành công",
        "nickname": current_user.nickname,
        "email": current_user.email,
    }


@users_router.delete("/delete")
def delete_user(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Xóa tài khoản"""
    # Chặn admin tự xóa tài khoản
    if current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin không thể tự xóa tài khoản.")

    # Xóa avatar nếu có
    if current_user.avatar:
        try:
            if os.path.exists(current_user.avatar):
                os.remove(current_user.avatar)
        except Exception as e:
            print(f"Lỗi khi xóa avatar: {e}")

    # Cập nhật sender_id, receiver_id của tin nhắn thành NULL
    db.query(models.Message).filter(
        models.Message.sender_id == current_user.user_id
    ).update({"sender_id": None})
    db.query(models.Message).filter(
        models.Message.receiver_id == current_user.user_id
    ).update({"receiver_id": None})

    # Xóa tài khoản
    db.delete(current_user)

    try:
        db.commit()
        return {
            "message": "Tài khoản đã bị xóa, tin nhắn vẫn còn nhưng không có thông tin người gửi/nhận."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")
