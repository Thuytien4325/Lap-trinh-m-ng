import os
import shutil
from datetime import datetime, timedelta, timezone
from typing import List

import models
from database import get_db
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import EmailStr
from routers.auth import ALGORITHM, SECRET_KEY, oauth2_scheme
from routers.untils import (
    AVATARS_USER_DIR,
    get_current_user,
    hash_password,
    pwd_context,
    update_last_active_dependency,
)
from routers.websocket import websocket_manager
from schemas import ChangePassword, UserProfile, UserResponse, UserWithFriendStatus
from sqlalchemy.orm import Session

# Tạo router
users_router = APIRouter(prefix="/users", tags=["User"])


# Lấy thông tin user hiện tại
@users_router.get(
    "/",
    response_model=UserResponse,
    dependencies=[Depends(update_last_active_dependency)],
)
async def get_user_info(current_user: models.User = Depends(get_current_user)):
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
    "/search",
    response_model=List[UserWithFriendStatus],
    dependencies=[Depends(update_last_active_dependency)],
)
async def search_users(
    query: str = Query(..., description="Từ khóa tìm kiếm"),
    search_by_nickname: bool = Query(False, description="Tìm kiếm theo nickname"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if search_by_nickname:
        users = (
            db.query(models.User)
            .filter(
                models.User.nickname.ilike(f"%{query}%"),
                models.User.is_admin == False,
                models.User.username != current_user.username,
            )
            .all()
        )
    else:
        users = (
            db.query(models.User)
            .filter(
                models.User.username.ilike(f"%{query}%"),
                models.User.is_admin == False,
                models.User.username != current_user.username,
            )
            .all()
        )

    results = []

    for user in users:
        # Mặc định trạng thái
        status = "Chưa kết bạn"

        # Là bạn bè?
        is_friend = (
            db.query(models.Friend)
            .filter(
                (
                    (models.Friend.user_username == current_user.username)
                    & (models.Friend.friend_username == user.username)
                )
                | (
                    (models.Friend.user_username == user.username)
                    & (models.Friend.friend_username == current_user.username)
                )
            )
            .first()
        )
        if is_friend:
            status = "Bạn bè"
        else:
            # Đã gửi lời mời?
            sent = (
                db.query(models.FriendRequest)
                .filter(
                    models.FriendRequest.sender_username == current_user.username,
                    models.FriendRequest.receiver_username == user.username,
                    models.FriendRequest.status == "Đợi",
                )
                .first()
            )
            if sent:
                status = "Đã gửi lời mời"
            else:
                # Đã nhận lời mời?
                received = (
                    db.query(models.FriendRequest)
                    .filter(
                        models.FriendRequest.sender_username == user.username,
                        models.FriendRequest.receiver_username == current_user.username,
                        models.FriendRequest.status == "Đợi",
                    )
                    .first()
                )
                if received:
                    status = "Chờ xác nhận"

        results.append(
            UserWithFriendStatus(
                username=user.username,
                nickname=user.nickname,
                email=user.email,
                avatar=user.avatar,
                created_at_UTC=user.created_at_UTC,
                last_active_UTC=user.last_active_UTC,
                status=status,
            )
        )

    return results


@users_router.put("/", dependencies=[Depends(update_last_active_dependency)])
async def update_user_and_avatar(
    nickname: str | None = None,
    email: str | None = None,
    avatar_file: UploadFile | None = File(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin không được cập nhật thông tin cá nhân hoặc avatar.",
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

    if avatar_file:
        file_extension = avatar_file.filename.split(".")[-1].lower()
        if file_extension not in ["jpg", "jpeg", "png"]:
            raise HTTPException(
                status_code=400,
                detail="Định dạng ảnh không hợp lệ! (Chỉ chấp nhận jpg, jpeg, png)",
            )

        if current_user.avatar:
            old_avatar_path = current_user.avatar
            try:
                if os.path.exists(old_avatar_path):
                    os.remove(old_avatar_path)
            except Exception as e:
                print(f"Lỗi khi xóa avatar cũ: {e}")

        # Lưu avatar vào thư mục với đường dẫn 'uploads/avatars/users/userID_2.jpg'
        file_path = os.path.join(
            AVATARS_USER_DIR, f"userID_{current_user.user_id}.{file_extension}"
        )
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(avatar_file.file, buffer)

        # Cập nhật lại avatar với đường dẫn đầy đủ
        normalized_path = file_path.replace("\\", "/")
        current_user.avatar = normalized_path

    db.commit()
    db.refresh(current_user)

    return {
        "message": "Cập nhật thông tin thành công",
        "nickname": current_user.nickname,
        "email": current_user.email,
        "avatar_url": current_user.avatar,
    }


@users_router.delete("/")
async def delete_user(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Xóa tài khoản"""
    # Chặn admin tự xóa tài khoản
    if current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin không thể tự xóa tài khoản.")

    # Kiểm tra nếu người dùng là admin của nhóm nào đó
    conversations = (
        db.query(models.Conversation)
        .filter(
            models.Conversation.type == "group",
        )
        .all()
    )
    for conversation in conversations:
        # Tìm thành viên khác trong nhóm
        new_admin = (
            db.query(models.GroupMember)
            .filter(
                models.GroupMember.conversation_id == conversation.conversation_id,
                models.GroupMember.username != current_user.username,
            )
            .first()
        )

        if new_admin:
            # Gán quyền admin cho thành viên mới
            group_member = (
                db.query(models.GroupMember)
                .filter(
                    models.GroupMember.conversation_id == conversation.conversation_id,
                    models.GroupMember.username == new_admin.username,
                )
                .first()
            )
            group_member.role = "admin"
        else:
            db.delete(conversation)

        # Xóa thông tin người dùng trong bảng group_members
        db.query(models.GroupMember).filter(
            models.GroupMember.username == current_user.username,
            models.GroupMember.conversation_id == conversation.conversation_id,
        ).delete()

    # Xử lý cuộc trò chuyện private
    private_conversations = (
        db.query(models.Conversation)
        .filter(models.Conversation.type == "private")
        .all()
    )

    for conversation in private_conversations:
        participants = (
            db.query(models.GroupMember)
            .filter(
                models.Conversation.type == "private",
            )
            .all()
        )

        # Nếu cuộc trò chuyện có 2 thành viên
        if len(participants) == 2 and any(
            p.username == current_user.username for p in participants
        ):
            # Xóa người dùng khỏi cuộc trò chuyện
            db.query(models.GroupMember).filter(
                models.GroupMember.username == current_user.username,
                models.GroupMember.conversation_id == conversation.conversation_id,
            ).delete()

        # Nếu còn ít hơn 2 thành viên (sau khi xóa người dùng)
        if len(participants) <= 1:
            db.delete(conversation)
            # Xóa các bản ghi thừa trong bảng group_member
            db.query(models.GroupMember).filter(
                models.GroupMember.conversation_id == None
            ).delete()

    # Commit thay đổi vào cơ sở dữ liệu
    db.commit()

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

    # Set id_target trong Report và Warning thành None
    db.query(models.Report).filter(
        models.Report.reporter_username == current_user.username
    ).update({"target_id": None})

    db.query(models.Report).filter(
        models.Report.target_id == current_user.user_id
    ).update({"target_id": None})

    db.query(models.Warning).filter(
        models.Warning.target_id == current_user.user_id
    ).update({"target_id": None})
    # Xóa tài khoản
    db.delete(current_user)

    try:
        db.commit()

        # Xóa các thông báo không cần thiết
        db.query(models.Notification).filter(
            models.Notification.user_username.is_(None),
            models.Notification.sender_username.is_(None),
        ).delete(synchronize_session=False)
        db.commit()

        db.query(models.GroupMember).filter(
            models.GroupMember.conversation_id == None,
            models.GroupMember.username == None,
        ).delete()
        db.commit()

        db.query(models.Warning).filter(models.Warning.target_id == None).delete()
        db.commit()

        db.query(models.Report).filter(models.Report.reporter_username == None).delete()
        db.commit()

        return {
            "message": "Tài khoản đã bị xóa, tin nhắn vẫn còn nhưng không có thông tin người gửi/nhận."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")


@users_router.post("/report", dependencies=[Depends(update_last_active_dependency)])
async def report(
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
        if target_exists.is_admin:
            raise HTTPException(
                status_code=403, detail="Không thể báo cáo quản trị viên."
            )
        if target_exists.username == current_user.username:
            raise HTTPException(status_code=404, detail="Không thể tự report bản thân!")
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

    await websocket_manager.notify_new_report(
        report_id=new_report.report_id,  # ➜ Truyền ID của report
        reporter_username=current_user.username,
        report_type=report_type,
        target_id=target_id if report_type in ["user", "group"] else None,
        target_table=(
            "users"
            if report_type == "user"
            else "conversations" if report_type == "group" else None
        ),
        description=description,
        title=title if report_type == "bug" else None,  # ➜ Truyền title nếu là bug
        severity=(
            severity if report_type == "bug" else None
        ),  # ➜ Truyền severity nếu là bug
    )

    # Thông báo cho admin
    admin_users = db.query(models.User).filter(models.User.is_admin == True).all()
    notifications = []

    for admin in admin_users:
        notification = models.Notification(
            user_username=admin.username,
            sender_username=current_user.username,
            message=f"Người dùng {current_user.nickname} đã gửi một báo cáo.",
            type="report",
            related_id=new_report.report_id,
            related_table="reports",
            created_at_UTC=datetime.now(timezone.utc),
        )
        db.add(notification)
        notifications.append(notification)

    db.commit()

    # Gửi thông báo qua WebSocket
    for notification in notifications:
        db.refresh(notification)
        await websocket_manager.send_notification(
            noti_id=notification.id,
            user_username=notification.user_username,
            sender_username=notification.sender_username,
            message=notification.message,
            notification_type=notification.type,
            related_id=notification.related_id,
            related_table=notification.related_table,
        )

    return {
        "message": "Báo cáo đã được gửi thành công.",
        "report_id": new_report.report_id,
    }


@users_router.get("/reports", dependencies=[Depends(update_last_active_dependency)])
async def get_user_reports(
    db: Session = Depends(get_db),
    is_pending: bool = Query(False, description="Xem các báo cáo chưa xử lý!"),
    is_in_progress: bool = Query(False, description="Xem các báo cáo đang xử lý!"),
    is_resolved: bool = Query(False, description="Xem các báo cáo đã xử lý!"),
    current_user: models.User = Depends(get_current_user),
):
    """
    API lấy danh sách các báo cáo mà người dùng hiện tại đã gửi.
    Hỗ trợ lọc theo trạng thái báo cáo: pending, in_progress, resolved.
    """

    query = db.query(models.Report).filter(
        models.Report.reporter_username == current_user.username
    )

    status_filters = []
    if is_pending:
        status_filters.append("pending")
    if is_in_progress:
        status_filters.append("in_progress")
    if is_resolved:
        status_filters.append("resolved")

    if status_filters:
        query = query.filter(models.Report.status.in_(status_filters))

    reports = query.order_by(models.Report.created_at_UTC.desc()).all()

    return [
        {
            "report_id": report.report_id,
            "report_type": report.report_type,
            "title": report.title,
            "description": report.description,
            "severity": report.severity,
            "status": report.status,
            "created_at": report.created_at_UTC,
            "updated_at": report.updated_at_UTC,
        }
        for report in reports
    ]


@users_router.get("/ban-status", dependencies=[Depends(update_last_active_dependency)])
async def check_user_ban(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    API kiểm tra xem người dùng hiện tại có đang bị ban không.
    Trả về thông tin về lệnh cấm nếu có.
    """
    print(f"Current user: {current_user.user_id}, Username: {current_user.username}")

    # Lấy tất cả các cảnh báo liên quan đến user
    warnings = (
        db.query(models.Warning)
        .filter(models.Warning.target_id == current_user.user_id)
        .all()
    )
    # Lấy thời gian hiện tại UTC
    now_utc = datetime.now(timezone.utc)

    # Kiểm tra xem có lệnh cấm nào đang còn hiệu lực không
    active_bans = []
    for warning in warnings:
        if warning.ban_duration > 0:  # Nếu có thời gian cấm
            ban_end_time = (
                warning.created_at_UTC + timedelta(minutes=warning.ban_duration)
            ).replace(tzinfo=timezone.utc)

            if now_utc < ban_end_time:
                active_bans.append(
                    {
                        "reason": warning.reason,
                        "ban_start": warning.created_at_UTC,
                        "ban_end": ban_end_time,
                    }
                )

    if active_bans:
        return {
            "is_banned": True,
            "active_bans": active_bans,
        }

    return {"is_banned": False, "message": "Người dùng không bị ban."}


@users_router.post(
    "/password/change",
    dependencies=[Depends(update_last_active_dependency)],
)
async def change_password(
    request: ChangePassword,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Kiểm tra mật khẩu cũ
    if not pwd_context.verify(request.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng!")

    # Cập nhật mật khẩu mới
    current_user.password_hash = hash_password(request.new_password)

    try:
        db.commit()
        db.refresh(current_user)

        # Thông báo cho người dùng
        new_notification = models.Notification(
            user_username=current_user.username,
            sender_username=None,
            message="Mật khẩu của bạn đã được thay đổi thành công.",
            type="system",
            related_id=0,
            related_table=None,
            created_at_UTC=datetime.now(timezone.utc),
        )

        db.add(new_notification)
        db.commit()

        await websocket_manager.send_notification(
            noti_id=new_notification.id,
            user_username=new_notification.user_username,
            sender_username=new_notification.sender_username,
            message=new_notification.message,
            notification_type=new_notification.type,
            related_id=new_notification.related_id,
            related_table=new_notification.related_table,
        )

        return {"message": "Mật khẩu đã được thay đổi thành công!"}
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Có lỗi xảy ra, vui lòng thử lại sau!"
        )
