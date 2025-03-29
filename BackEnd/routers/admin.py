from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, Conversation, GroupMember, Report, Notification
import models
from routers.untils import get_admin_user, update_last_active_dependency
from schemas import AdminUserResponse, ConversationResponse
from typing import List
from datetime import datetime, timezone, timedelta
import os

# Tạo router cho admin
admin_router = APIRouter(prefix="/admin", tags=["Admin"])


# API lấy danh sách tất cả user
@admin_router.get(
    "/users",
    response_model=List[AdminUserResponse],
    dependencies=[Depends(update_last_active_dependency)],
)
def get_all_users(db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    users = db.query(User).all()
    return [AdminUserResponse.model_validate(user) for user in users]


# API lấy danh sách người dùng online
@admin_router.get(
    "/online-users",
    response_model=List[AdminUserResponse],
    dependencies=[Depends(update_last_active_dependency)],
)
def get_online_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    # Thời gian tối đa để xác định người dùng online (5 phút)
    online_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)

    users = (
        db.query(User)
        .filter(User.last_active_UTC >= online_threshold, User.is_admin == False)
        .all()
    )

    return [AdminUserResponse.model_validate(user) for user in users]


@admin_router.get(
    "/get-groups",
    response_model=list[ConversationResponse],
    dependencies=[Depends(update_last_active_dependency)],
)
def get_groups(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    groups = db.query(Conversation).filter(Conversation.type == "group").all()

    group_list = []
    for group in groups:
        members = (
            db.query(GroupMember.username, GroupMember.role)
            .filter(GroupMember.conversation_id == group.conversation_id)
            .all()
        )

        group_members = [
            {"username": member.username, "role": member.role} for member in members
        ]

        group_list.append(
            {
                "conversation_id": group.conversation_id,
                "type": group.type,
                "name": group.name,
                "group_members": group_members,
            }
        )

    return group_list


@admin_router.delete(
    "/delete-user", dependencies=[Depends(update_last_active_dependency)]
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),  # Chỉ cho phép admin gọi API
):
    """Xóa tài khoản người dùng (chỉ admin)."""
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng!")

    if user.is_admin:
        raise HTTPException(status_code=403, detail="Không thể xóa tài khoản admin!")

    # Kiểm tra nếu user là admin của nhóm nào đó và xử lý quyền admin hoặc xóa nhóm
    conversations = (
        db.query(models.Conversation).filter(models.Conversation.type == "group").all()
    )
    for conversation in conversations:
        new_admin = (
            db.query(models.GroupMember)
            .filter(
                models.GroupMember.conversation_id == conversation.conversation_id,
                models.GroupMember.username != user.username,
            )
            .first()
        )

        if new_admin:
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
            models.GroupMember.username == user.username,
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
            .filter(models.GroupMember.conversation_id == conversation.conversation_id)
            .all()
        )

        # Nếu cuộc trò chuyện có 2 thành viên
        if len(participants) == 2 and any(
            p.username == user.username for p in participants
        ):
            # Xóa người dùng khỏi cuộc trò chuyện
            db.query(models.GroupMember).filter(
                models.GroupMember.username == user.username,
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
    if user.avatar:
        try:
            if os.path.exists(user.avatar):
                os.remove(user.avatar)
        except Exception as e:
            print(f"Lỗi khi xóa avatar: {e}")

    # Cập nhật sender_id, receiver_id của tin nhắn thành NULL
    db.query(models.Message).filter(models.Message.sender_id == user_id).update(
        {"sender_id": None}
    )

    db.query(models.Message).filter(models.Message.receiver_id == user_id).update(
        {"receiver_id": None}
    )

    # Set id_target trong Report và Warning thành None
    db.query(models.Report).filter(
        models.Report.reporter_username == user.username
    ).update({"target_id": None})

    db.query(models.Report).filter(models.Report.target_id == user_id).update(
        {"target_id": None}
    )

    db.query(models.Warning).filter(models.Warning.target_id == user_id).update(
        {"target_id": None}
    )
    # Xóa tài khoản
    db.delete(user)

    try:
        db.commit()  # Commit tất cả thay đổi sau khi hoàn thành

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
            "message": "Tài khoản đã bị xóa, tin nhắn vẫn còn nhưng không có thông tin người gửi/nhận.",
            "user_id": user_id,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")


@admin_router.delete(
    "/delete-group", dependencies=[Depends(update_last_active_dependency)]
)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Xóa một nhóm chat (chỉ admin hệ thống mới có thể xóa)."""

    group = (
        db.query(models.Conversation)
        .filter(
            models.Conversation.conversation_id == group_id,
            models.Conversation.type == "group",
        )
        .first()
    )

    if not group:
        raise HTTPException(status_code=404, detail="Nhóm không tồn tại.")

    # Lấy danh sách thành viên nhóm
    group_members = (
        db.query(models.GroupMember.username)
        .filter(models.GroupMember.conversation_id == group_id)
        .all()
    )

    # Gửi thông báo đến tất cả thành viên trong nhóm
    notifications = [
        models.Notification(
            user_username=member.username,
            sender_username=None,
            message=f"Nhóm '{group.name}' đã bị xóa bởi quản trị viên hệ thống.",
            type="system",
            related_id=group.conversation_id,
            related_table="conversations",
            created_at_UTC=datetime.now(timezone.utc),
        )
        for member in group_members
    ]

    db.add_all(notifications)
    db.commit()

    # Xóa tin nhắn & thành viên nhóm
    db.query(models.Message).filter(models.Message.conversation_id == group_id).delete()
    db.query(models.GroupMember).filter(
        models.GroupMember.conversation_id == group_id
    ).delete()
    db.delete(group)
    db.commit()

    return {"message": "Nhóm đã được xóa thành công.", "group_id": group_id}


@admin_router.get("/get-reports", dependencies=[Depends(update_last_active_dependency)])
def get_reports(
    db: Session = Depends(get_db),
    is_pending: bool = Query(False, description="Xem các báo cáo chưa xử lý!"),
    is_in_progress: bool = Query(False, description="Xem các báo cáo đang xử lý!"),
    is_resolved: bool = Query(False, description="Xem các báo cáo đã xử lý!"),
    newest_first: bool = Query(
        True,
        description="Sắp xếp theo thời gian (True = mới nhất trước, False = cũ nhất trước)",
    ),
    admin: User = Depends(get_admin_user),
):
    query = db.query(Report)
    status_filters = []
    if is_pending:
        status_filters.append("pending")
    if is_in_progress:
        status_filters.append("in_progress")
    if is_resolved:
        status_filters.append("resolved")

    if status_filters:
        query = query.filter(Report.status.in_(status_filters))

    # Sắp xếp theo giá trị newest_first
    query = query.order_by(
        Report.created_at_UTC.desc() if newest_first else Report.created_at_UTC.asc()
    )
    reports = query.all()
    return [
        {
            "report_id": report.report_id,
            "reporter_username": report.reporter_username,
            "report_type": report.report_type,
            "target_id": report.target_id,
            "title": report.title,
            "description": report.description,
            "severity": report.severity,
            "status": report.status,
            "created_at": report.created_at_UTC,
            "updated_at": report.updated_at_UTC,
        }
        for report in reports
    ]


@admin_router.put("/process-reports")
def update_report_status(
    report_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Báo cáo không tồn tại")

    if report.status == "resolved":
        raise HTTPException(
            status_code=400, detail="Báo cáo này đã được xử lý trước đó!"
        )

    report.status = "resolved"
    report.updated_at_UTC = datetime.now(timezone.utc)

    db.commit()

    # Gửi thông báo cho người gửi báo cáo
    notification = Notification(
        user_username=report.reporter_username,
        sender_username=None,
        message=f"Báo cáo của bạn về '{report.report_type}' đã được cập nhật thành resolved.",
        type="system",
        related_id=report.report_id,
        related_table="reports",
        created_at_UTC=datetime.now(timezone.utc),
    )
    db.add(notification)
    db.commit()

    return {"message": "Cập nhật trạng thái báo cáo thành công"}


BAN_DURATIONS = [0, 5, 15, 30, 60]


@admin_router.post("/send-warning")
def send_warning(
    report_id: int = Query(..., description="ID của báo cáo"),
    reason: str = Query(..., description="Lý do gửi cảnh báo"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    report = db.query(Report).filter(Report.report_id == report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report không tồn tại!")

    if report.report_type == "bug":
        raise HTTPException(
            status_code=400, detail="Không thể gửi cảnh báo cho báo cáo loại 'bug'!"
        )

    target_id = report.target_id

    db.query(models.Report).filter(
        models.Report.target_id == target_id,
        models.Report.status != "resolved",
    ).update({"status": "resolved", "updated_at_UTC": datetime.now(timezone.utc)})

    target_id = report.target_id
    target_type = report.target_table  # "users" hoặc "conversations"

    # Chuyển đổi target_type nếu cần
    if target_type == "conversations":
        target_type = "groups"

    # Kiểm tra nếu target là user, cần chuyển target_id từ username -> user_id
    if target_type == "users":
        user = db.query(User).filter(User.user_id == target_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại!")

    # Kiểm tra số lần vi phạm trước đó
    previous_warnings = (
        db.query(models.Warning)
        .filter(
            models.Warning.target_id == target_id,
            models.Warning.target_type == target_type,
        )
        .count()
    )

    # Xác định thời gian ban hợp lệ
    ban_duration = BAN_DURATIONS[min(previous_warnings, len(BAN_DURATIONS) - 1)]
    assert ban_duration in BAN_DURATIONS, "Giá trị ban_duration không hợp lệ!"

    # Tạo cảnh báo mới
    new_warning = models.Warning(
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        ban_duration=ban_duration,
        created_at_UTC=datetime.now(timezone.utc),
    )
    db.add(new_warning)

    # Gửi thông báo
    notifications = []
    if target_type == "users":
        notification_message = (
            f"Bạn đã nhận được cảnh báo vì: {reason}."
            if ban_duration == 0
            else f"Bạn bị cấm chat {ban_duration} phút do vi phạm!"
        )
        user = db.query(User).filter(User.user_id == report.target_id).first()
        notifications.append(
            Notification(
                user_username=user.username,
                sender_username=None,
                message=notification_message,
                type="warning",
                related_id=new_warning.warning_id,
                related_table="warnings",
                created_at_UTC=datetime.now(timezone.utc),
            )
        )

    elif target_type == "groups":
        group = (
            db.query(Conversation)
            .filter(Conversation.conversation_id == target_id)
            .first()
        )
        group_name = group.name if group else f"Nhóm {target_id}"

        group_admins = (
            db.query(GroupMember.username)
            .filter(
                GroupMember.conversation_id == target_id,
                GroupMember.role == "admin",
            )
            .all()
        )
        group_admins = [admin[0] for admin in group_admins]

        for admin in group_admins:
            notification_message = (
                f"Nhóm {group_name} đã nhận được cảnh báo vì: {reason}."
                if ban_duration == 0
                else f"Nhóm {group_name} có thể bị cấm chat {ban_duration} phút do vi phạm!"
            )
            notifications.append(
                Notification(
                    user_username=admin,
                    sender_username=None,
                    message=notification_message,
                    type="warning",
                    related_id=new_warning.warning_id,
                    related_table="warnings",
                    created_at_UTC=datetime.now(timezone.utc),
                )
            )

    db.add_all(notifications)
    db.commit()

    # Cập nhật trạng thái của report
    db.query(models.Report).filter(
        models.Report.target_id == target_id,
        models.Report.status != "resolved",
    ).update({"status": "resolved", "updated_at_UTC": datetime.now(timezone.utc)})
    db.commit()

    # Gửi thông báo đến tất cả những người đã gửi report trước đó
    reporters = (
        db.query(models.Report.reporter_username)
        .filter(models.Report.target_id == target_id)
        .distinct()
        .all()
    )
    reporters = [r[0] for r in reporters]

    for reporter in reporters:
        notifications.append(
            models.Notification(
                user_username=reporter,
                sender_username=None,
                message=f"Báo cáo của bạn về '{report.report_type}' đã được xử lý.",
                type="system",
                related_id=report.report_id,
                related_table="reports",
                created_at_UTC=datetime.now(timezone.utc),
            )
        )

    db.add_all(notifications)
    db.commit()

    return {"message": "Cảnh báo đã được gửi thành công!", "ban_duration": ban_duration}
