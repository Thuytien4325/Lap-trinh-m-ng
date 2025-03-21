from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
import os
import shutil
from database import get_db
import models
from routers.auth import oauth2_scheme, SECRET_KEY, ALGORITHM
import jwt
from pydantic import BaseModel, EmailStr
from datetime import datetime
from schemas import UserResponse, UserUpdate

# Tạo router
users_router = APIRouter(prefix="/users", tags=["User"])

# Thư mục lưu avatar
UPLOAD_DIR = "uploads/avatars"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Lấy thông tin user từ JWT token
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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

# Lấy thông tin user hiện tại
@users_router.get("/me", response_model=UserResponse)
def get_user_info(current_user: models.User = Depends(get_current_user)):
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        nickname=current_user.nickname,
        email=current_user.email,
        avatar=current_user.avatar,
        created_at=current_user.created_at
    )

# Upload Avatar
@users_router.post("/upload-avatar")
def upload_avatar(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ["jpg", "jpeg", "png"]:
        raise HTTPException(status_code=400, detail="Định dạng ảnh không hợp lệ! (Chỉ chấp nhận jpg, jpeg, png)")

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
@users_router.put("/update")
def update_user(
    user_update: UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user_update.email and user_update.email != current_user.email:
        existing_user = db.query(models.User).filter(models.User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email đã được sử dụng bởi người dùng khác")

    if user_update.nickname:
        current_user.nickname = user_update.nickname
    if user_update.email:
        current_user.email = user_update.email

    db.commit()
    db.refresh(current_user)

    return {"message": "Cập nhật thông tin thành công", "nickname": current_user.nickname, "email": current_user.email}

@users_router.delete("/delete")
def delete_user(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Xóa tài khoản"""

    # Xóa avatar nếu có
    if current_user.avatar:
        try:
            if os.path.exists(current_user.avatar):
                os.remove(current_user.avatar)
        except Exception as e:
            print(f"Lỗi khi xóa avatar: {e}")

    # Cập nhật sender_id, receiver_id của tin nhắn thành NULL
    db.query(models.Message).filter(models.Message.sender_id == current_user.user_id).update(
        {"sender_id": None}
    )
    db.query(models.Message).filter(models.Message.receiver_id == current_user.user_id).update(
        {"receiver_id": None}  
    )

    # Xóa tài khoản
    db.delete(current_user)
    
    try:
        db.commit()
        return {"message": "Tài khoản đã bị xóa, tin nhắn vẫn còn nhưng không có thông tin người gửi/nhận."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")