import os
from datetime import datetime, timedelta, timezone
from typing import List

import models
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from models import Conversation, GroupMember, Notification, Report, User
from routers.untils import get_admin_user, update_last_active_dependency
from routers.websocket import websocket_manager
from schemas import AdminUserResponse, ConversationResponse
from sqlalchemy.orm import Session

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
async def delete_group(
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
    notifications = []
    for member in group_members:
        notifications.append(
            models.Notification(
                user_username=member.username,
                sender_username=None,
                message=f"Nhóm '{group.name}' đã bị xóa bởi quản trị viên hệ thống.",
                type="system",
                related_id=group.conversation_id,
                related_table="conversations",
                created_at_UTC=datetime.now(timezone.utc),
            )
        )

        # Gửi thông báo qua WebSocket
        await websocket_manager.send_notification(
            noti_id=group_id,
            user_username=member.username,
            sender_username=admin.username,
            message=f"Nhóm '{group.name}' đã bị xóa bởi quản trị viên hệ thống.",
            notification_type="system",
            related_id=group_id,
            related_table="conversations",
        )

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
            "description": report.description,
            "status": report.status,
            "created_at": report.created_at_UTC,
            "updated_at": report.updated_at_UTC,
        }
        for report in reports
    ]


@admin_router.put("/process-reports")
async def update_report_status(
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
        message=f"Báo cáo của bạn về '{report.report_type}' đã được xử lí.",
        type="report",
        related_id=report.report_id,
        related_table="reports",
        created_at_UTC=datetime.now(timezone.utc),
    )
    db.add(notification)
    db.commit()

    # Gửi thông báo qua WebSocket
    await websocket_manager.send_notification(
        noti_id=report_id,
        user_username=report.reporter_username,
        sender_username=admin.username,
        message=f"Báo cáo của bạn về '{report.report_type}' đã được xử lí.",
        notification_type="report",
        related_id=report_id,
        related_table="reports",
    )

    return {"message": "Cập nhật trạng thái báo cáo thành công"}


BAN_DURATIONS = [0, 5, 15, 30, 60]


@admin_router.post("/send-warning")
def send_warning(
    id: int = Query(..., description="ID của report, user hoặc group"),
    id_type: str = Query(..., description="Loại ID: 'report', 'user', 'group'"),
    reason: str = Query(..., description="Lý do gửi cảnh báo"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    try:
        is_report = False

        # 🔹 Xác định target_id và target_type
        if id_type == "report":
            report = (
                db.query(models.Report).filter(models.Report.report_id == id).first()
            )
            if not report:
                raise HTTPException(status_code=404, detail="Report không tồn tại!")
            if report.report_type == "bug":
                raise HTTPException(
                    status_code=400, detail="Không thể cảnh báo lỗi bug!"
                )
            if report.status == "resolved":
                raise HTTPException(
                    status_code=400, detail="Báo cáo đã được xử lý trước đó!"
                )
            target_id = report.target_id
            target_type = report.target_table  # "users" hoặc "groups"
            if target_type == "conversations":
                target_type = "groups"
            is_report = True

        elif id_type == "user":
            user = db.query(models.User).filter(models.User.user_id == id).first()
            if not user:
                raise HTTPException(status_code=404, detail="Người dùng không tồn tại!")
            if user.is_admin:
                raise HTTPException(status_code=403, detail="Không thể ban admin!")

            target_id = user.user_id
            target_type = "users"

        elif id_type == "group":
            conversation = (
                db.query(models.Conversation)
                .filter(
                    models.Conversation.conversation_id == id,
                    models.Conversation.type == "group",
                )
                .first()
            )
            if not conversation:
                raise HTTPException(status_code=404, detail="Nhóm không tồn tại!")
            target_id = conversation.conversation_id
            target_type = "groups"

        else:
            raise HTTPException(status_code=400, detail="Loại ID không hợp lệ!")

        # 🔹 Kiểm tra xem warning đã tồn tại chưa
        existing_warning = (
            db.query(models.Warning)
            .filter(
                models.Warning.target_id == target_id,
                models.Warning.target_type == target_type,
            )
            .first()
        )
        now_utc = datetime.now(timezone.utc)
        if existing_warning:
            ban_end_time = existing_warning.created_at_UTC.replace(
                tzinfo=timezone.utc
            ) + timedelta(minutes=existing_warning.ban_duration)
            if now_utc < ban_end_time:
                raise HTTPException(status_code=404, detail="Lệnh cấm vẫn còn tồn tại!")

            # Nếu đã có warning, tăng số lần bị ban và cập nhật thời gian
            existing_warning.ban_count += 1
            index = min(
                existing_warning.ban_count - 1, len(BAN_DURATIONS) - 1
            )  # Tránh vượt mảng
            existing_warning.ban_duration = BAN_DURATIONS[index]  # Cập nhật mức ban mới
            existing_warning.created_at_UTC = datetime.now(
                timezone.utc
            )  # Cập nhật thời gian ban mới
            existing_warning.reason = reason  # Cập nhật lý do mới nhất
            db.commit()
            db.refresh(existing_warning)
            ban_count = existing_warning.ban_count
            ban_duration = existing_warning.ban_duration
        else:
            # Nếu chưa có warning, tạo mới
            ban_count = 1
            ban_duration = BAN_DURATIONS[0]  # Ban mức thấp nhất

            new_warning = models.Warning(
                target_type=target_type,
                target_id=target_id,
                reason=reason,
                ban_duration=ban_duration,
                ban_count=ban_count,
                created_at_UTC=datetime.now(timezone.utc),
            )
            db.add(new_warning)
            db.commit()
            db.refresh(new_warning)

        # 🔹 Gửi thông báo
        notifications = []
        notification_message = (
            f"Bạn đã nhận được cảnh báo vì: {reason}."
            if ban_duration == 0
            else f"Bạn bị cấm chat {ban_duration} phút vì: {reason}!"
        )

        if target_type == "users":
            user = (
                db.query(models.User).filter(models.User.user_id == target_id).first()
            )
            notifications.append(
                models.Notification(
                    user_username=user.username,
                    sender_username=None,
                    message=notification_message,
                    type="warning",
                    related_id=(
                        existing_warning.warning_id
                        if existing_warning
                        else new_warning.warning_id
                    ),
                    related_table="warnings",
                    created_at_UTC=datetime.now(timezone.utc),
                )
            )

        elif target_type == "groups":
            group = (
                db.query(models.Conversation)
                .filter(models.Conversation.conversation_id == target_id)
                .first()
            )
            group_name = group.name if group else f"Nhóm {target_id}"
            group_admins = (
                db.query(models.GroupMember.username)
                .filter(
                    models.GroupMember.conversation_id == target_id,
                    models.GroupMember.role == "admin",
                )
                .all()
            )
            group_admins = [admin[0] for admin in group_admins]

            for admin in group_admins:
                notifications.append(
                    models.Notification(
                        user_username=admin,
                        sender_username=None,
                        message=(
                            f"Nhóm {group_name} bị cảnh báo: {reason}."
                            if ban_duration == 0
                            else f"Nhóm {group_name} bị cấm chat {ban_duration} phút vì: {reason}!"
                        ),
                        type="warning",
                        related_id=(
                            existing_warning.warning_id
                            if existing_warning
                            else new_warning.warning_id
                        ),
                        related_table="warnings",
                        created_at_UTC=datetime.now(timezone.utc),
                    )
                )

        db.add_all(notifications)
        db.commit()

        # 🔹 Cập nhật trạng thái report nếu có
        if is_report:
            db.query(models.Report).filter(
                models.Report.target_id == target_id, models.Report.status != "resolved"
            ).update(
                {"status": "resolved", "updated_at_UTC": datetime.now(timezone.utc)}
            )
            db.commit()

            # Gửi thông báo đến những người đã report
            reporters = (
                db.query(models.Report.reporter_username)
                .filter(models.Report.target_id == target_id)
                .distinct()
                .all()
            )
            reporters = [r[0] for r in reporters]

            report_notifications = [
                models.Notification(
                    user_username=reporter,
                    sender_username=None,
                    message=f"Báo cáo của bạn về '{report.report_type}' đã được xử lý.",
                    type="report",
                    related_id=report.report_id,
                    related_table="reports",
                    created_at_UTC=datetime.now(timezone.utc),
                )
                for reporter in reporters
            ]
            db.add_all(report_notifications)
            db.commit()

        return {
            "message": "Cảnh báo đã được gửi thành công!",
            "ban_duration": ban_duration,
            "ban_count": ban_count,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")


@admin_router.post("/unban")
def unban_target(
    id: int = Query(..., description="ID của user hoặc group cần gỡ cấm"),
    id_type: str = Query(..., description="Loại ID: 'user' hoặc 'group'"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    try:
        # 🔹 Xác định loại mục tiêu
        if id_type == "user":
            target = db.query(models.User).filter(models.User.user_id == id).first()
            target_type = "users"
        elif id_type == "group":
            target = (
                db.query(models.Conversation)
                .filter(
                    models.Conversation.conversation_id == id,
                    models.Conversation.type == "group",
                )
                .first()
            )
            target_type = "groups"
        else:
            raise HTTPException(status_code=400, detail="Loại ID không hợp lệ!")

        if not target:
            raise HTTPException(status_code=404, detail="Mục tiêu không tồn tại!")

        # 🔹 Kiểm tra có lệnh cấm hay không
        active_bans = (
            db.query(models.Warning)
            .filter(
                models.Warning.target_id == id,
                models.Warning.target_type == target_type,
                models.Warning.ban_duration > 0,
            )
            .all()
        )

        if not active_bans:
            raise HTTPException(status_code=400, detail="Không có lệnh cấm nào cần gỡ!")

        # 🔹 Gỡ bỏ lệnh cấm (cập nhật `ban_duration = 0`)
        for ban in active_bans:
            ban.ban_duration = 0  # Gỡ cấm
        db.commit()

        # 🔹 Gửi thông báo về việc gỡ cấm
        notifications = []
        if target_type == "users":
            notifications.append(
                models.Notification(
                    user_username=target.username,
                    sender_username=None,
                    message="Bạn đã được gỡ cấm và có thể tiếp tục chat.",
                    type="system",
                    related_id=target.user_id,
                    related_table="users",
                    created_at_UTC=datetime.now(timezone.utc),
                )
            )
        elif target_type == "groups":
            group_admins = (
                db.query(models.GroupMember.username)
                .filter(
                    models.GroupMember.conversation_id == id,
                    models.GroupMember.role == "admin",
                )
                .all()
            )
            group_admins = [admin[0] for admin in group_admins]

            for admin in group_admins:
                notifications.append(
                    models.Notification(
                        user_username=admin,
                        sender_username=None,
                        message=f"Nhóm {target.name} đã được gỡ cấm và có thể hoạt động trở lại.",
                        type="system",
                        related_id=target.conversation_id,
                        related_table="groups",
                        created_at_UTC=datetime.now(timezone.utc),
                    )
                )

        db.add_all(notifications)
        db.commit()

        return {"message": "Đã gỡ cấm thành công!"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")
