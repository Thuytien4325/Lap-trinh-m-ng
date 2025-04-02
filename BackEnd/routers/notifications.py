import models
import schemas
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from routers.untils import update_last_active_dependency
from routers.users import get_current_user
from sqlalchemy.orm import Session

notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])


@notifications_router.get(
    "/",
    response_model=list[schemas.NotificationResponse],
    dependencies=[Depends(update_last_active_dependency)],
)
async def get_notifications(
    unread_only: bool = Query(False, description="Chỉ lấy thông báo chưa đọc"),
    from_system: bool = Query(False, description="Chỉ lấy thông báo từ hệ thống"),
    newest_first: bool = Query(
        True,
        description="Sắp xếp theo thời gian (True = mới nhất trước, False = cũ nhất trước)",
    ),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Notification).filter(
        models.Notification.user_username == current_user.username
    )

    if from_system:
        query = query.filter(
            models.Notification.sender_username.is_(None),
            models.Notification.related_id == 0,
            models.Notification.related_table.is_(None),
        )

    if unread_only:
        query = query.filter(models.Notification.is_read == False)
    query = query.order_by(
        models.Notification.created_at_UTC.desc()
        if newest_first
        else models.Notification.created_at_UTC.asc()
    )
    notifications = query.all()
    return notifications


@notifications_router.post(
    "/{notification_id}/read",
    response_model=schemas.NotificationResponse,
    dependencies=[Depends(update_last_active_dependency)],
)
async def mark_notification_as_read(
    notification_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đánh dấu thông báo là đã đọc"""

    notification = (
        db.query(models.Notification)
        .filter(
            models.Notification.id == notification_id,
            models.Notification.user_username == current_user.username,
        )
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Thông báo không tồn tại")

    notification.is_read = True
    db.commit()
    db.refresh(notification)

    return schemas.NotificationResponse.from_orm(notification)


@notifications_router.post(
    "/{notification_id}/unread",
    response_model=schemas.NotificationResponse,
    dependencies=[Depends(update_last_active_dependency)],
)
async def mark_notification_as_unread(
    notification_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đánh dấu thông báo là chưa đọc"""

    notification = (
        db.query(models.Notification)
        .filter(
            models.Notification.id == notification_id,
            models.Notification.user_username == current_user.username,
        )
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Thông báo không tồn tại")

    notification.is_read = False
    db.commit()
    db.refresh(notification)

    return schemas.NotificationResponse.from_orm(notification)


@notifications_router.post(
    "/read",
    response_model=list[schemas.NotificationResponse],
    dependencies=[Depends(update_last_active_dependency)],
)
async def mark_all_notifications_as_read(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đánh dấu tất cả thông báo là đã đọc"""

    notifications = (
        db.query(models.Notification)
        .filter(
            models.Notification.user_username == current_user.username,
            models.Notification.is_read == False,
        )
        .all()
    )

    if not notifications:
        raise HTTPException(status_code=404, detail="Không có thông báo chưa đọc")

    for notification in notifications:
        notification.is_read = True

    db.commit()

    return [
        schemas.NotificationResponse.from_orm(notification)
        for notification in notifications
    ]


@notifications_router.post(
    "/unread",
    response_model=list[schemas.NotificationResponse],
    dependencies=[Depends(update_last_active_dependency)],
)
async def mark_all_notifications_as_unread(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đánh dấu tất cả thông báo là chưa đọc"""

    notifications = (
        db.query(models.Notification)
        .filter(
            models.Notification.user_username == current_user.username,
            models.Notification.is_read == True,
        )
        .all()
    )

    if not notifications:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo đã đọc")

    for notification in notifications:
        notification.is_read = False

    db.commit()

    return [
        schemas.NotificationResponse.from_orm(notification)
        for notification in notifications
    ]


@notifications_router.delete(
    "/{notification_id}",
    dependencies=[Depends(update_last_active_dependency)],
)
async def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    ),  # Lấy người dùng hiện tại từ token
):
    """Xóa thông báo theo ID"""
    # Tìm thông báo trong cơ sở dữ liệu
    notification = (
        db.query(models.Notification)
        .filter(models.Notification.id == notification_id)
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Thông báo không tồn tại")

    # Kiểm tra nếu thông báo là của người dùng hiện tại
    if notification.user_username != current_user.username:
        raise HTTPException(
            status_code=403, detail="Bạn không có quyền xóa thông báo này"
        )

    # Xóa thông báo và commit thay đổi vào cơ sở dữ liệu
    db.delete(notification)
    db.commit()

    return {"message": "Thông báo đã được xóa thành công"}
