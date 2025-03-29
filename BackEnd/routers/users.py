from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from sqlalchemy.orm import Session
import os
import shutil
from database import get_db
import models
from routers.auth import oauth2_scheme, SECRET_KEY, ALGORITHM
from schemas import UserResponse, UserProfile
from routers.untils import get_current_user, UPLOAD_DIR, update_last_active_dependency
from typing import List
from pydantic import EmailStr
from datetime import datetime, timezone

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
def search_users(
    query: str = Query(..., description="Từ khóa tìm kiếm"),
    search_by_nickname: bool = Query(False, description="Tìm kiếm theo nickname"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if search_by_nickname:
        users = (
            db.query(models.User)
            .filter(
                models.User.nickname.ilike(f"%{query}%"), models.User.is_admin == False
            )
            .all()
        )
    else:
        users = (
            db.query(models.User)
            .filter(
                models.User.username.ilike(f"%{query}%"), models.User.is_admin == False
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
    nickname: str | None = None,
    email: EmailStr | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Chặn admin cập nhật thông tin cá nhân
    if current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="Admin không được cập nhật thông tin cá nhân."
        )

    if email and email != current_user.email:
        existing_user = db.query(models.User).filter(models.User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=400, detail="Email đã được sử dụng bởi người dùng khác"
            )

    if nickname:
        current_user.nickname = nickname
    if email:
        current_user.email = email

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


@users_router.post("/report")
def report(
    report_type: str = Query(
        ..., description="Loại báo cáo: 'user', 'group' hoặc 'bug'"
    ),
    target_id: int = Query(
        None, description="ID của người dùng hoặc nhóm chat bị báo cáo (nếu có)"
    ),
    title: str = Query(None, description="Tiêu đề báo cáo (chỉ dùng cho bug)"),
    description: str = Query(..., description="Mô tả chi tiết về lý do báo cáo"),
    severity: str = Query(
        None,
        description="Mức độ nghiêm trọng của lỗi ('low', 'medium', 'high', 'critical') - chỉ dành cho bug",
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    API để người dùng báo cáo người dùng khác, nhóm chat hoặc báo cáo lỗi (bug).
    """

    if report_type == "user":
        if not target_id:
            raise HTTPException(status_code=400, detail="Cần ID người dùng để báo cáo.")
        target_exists = (
            db.query(models.User).filter(models.User.user_id == target_id).first()
        )
        if not target_exists:
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại.")
        new_report = models.Report(
            reporter_username=current_user.username,
            report_type=report_type,
            target_id=target_id,
            target_table="users",
            description=description,
            status="pending",
            created_at_UTC=datetime.now(timezone.utc),
            updated_at_UTC=datetime.now(timezone.utc),
        )

    elif report_type == "group":
        if not target_id:
            raise HTTPException(status_code=400, detail="Cần ID nhóm để báo cáo.")
        target_exists = (
            db.query(models.Conversation)
            .filter(models.Conversation.conversation_id == target_id)
            .first()
        )
        if not target_exists:
            raise HTTPException(status_code=404, detail="Nhóm không tồn tại.")
        new_report = models.Report(
            reporter_username=current_user.username,
            report_type=report_type,
            target_id=target_id,
            target_table="conversations",
            description=description,
            status="pending",
            created_at_UTC=datetime.now(timezone.utc),
            updated_at_UTC=datetime.now(timezone.utc),
        )

    elif report_type == "bug":
        if not title:
            raise HTTPException(status_code=400, detail="Cần tiêu đề cho báo cáo bug.")
        if severity not in ["low", "medium", "high", "critical"]:
            raise HTTPException(
                status_code=400, detail="Mức độ nghiêm trọng không hợp lệ."
            )
        new_report = models.Report(
            reporter_username=current_user.username,
            report_type="bug",
            title=title,
            description=description,
            severity=severity,
            status="pending",
            created_at_UTC=datetime.now(timezone.utc),
            updated_at_UTC=datetime.now(timezone.utc),
        )

    else:
        raise HTTPException(status_code=400, detail="Loại báo cáo không hợp lệ!")

    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return {
        "message": "Báo cáo đã được gửi thành công.",
        "report_id": new_report.report_id,
    }
