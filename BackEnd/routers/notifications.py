from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from routers.users import get_current_user
import schemas
from routers.untils import update_last_active_dependency
notifications_router = APIRouter(prefix="/noti", tags=["Notifications"])

@notifications_router.get("/", response_model=list[schemas.NotificationResponse],dependencies=[Depends(update_last_active_dependency)])
def get_notifications(
    unread_only: bool = Query(False, description="Chỉ lấy thông báo chưa đọc"),
    from_system: bool = Query(False, description="Chỉ lấy thông báo từ hệ thống"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Notification).filter(models.Notification.user_username == current_user.username)

    if from_system:
        query = query.filter(
            models.Notification.sender_username.is_(None),
            models.Notification.related_id == 0,
            models.Notification.related_table.is_(None)
        )

    if unread_only:
        query = query.filter(models.Notification.is_read == False)

    notifications = query.all()
    return notifications

@notifications_router.post("/mark-as-read", response_model=list[schemas.NotificationResponse], dependencies=[Depends(update_last_active_dependency)])
def mark_notifications_as_read(
    notification_id: int | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Đánh dấu đã xem một (nhập id) hoặc tất cả thông báo (để trống)"""

    if notification_id:
        # Đánh dấu một thông báo
        notification = db.query(models.Notification).filter(
            models.Notification.id == notification_id,
            models.Notification.user_username == current_user.username
        ).first()

        if not notification:
            raise HTTPException(status_code=404, detail="Thông báo không tồn tại")

        notification.is_read = True
        db.commit()
        db.refresh(notification)
        return [schemas.NotificationResponse.from_orm(notification)]
    
    else:
        # Đánh dấu tất cả thông báo
        notifications = db.query(models.Notification).filter(
            models.Notification.user_username == current_user.username,
            models.Notification.is_read == False
        ).all()

        if not notifications:
            raise HTTPException(status_code=404, detail="Không có thông báo chưa đọc")

        for notification in notifications:
            notification.is_read = True

        db.commit()

        return [schemas.NotificationResponse.from_orm(notification) for notification in notifications]

@notifications_router.post("/mark-as-unread", response_model=list[schemas.NotificationResponse], dependencies=[Depends(update_last_active_dependency)])
def mark_notifications_as_unread(
    notification_id: int | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Đánh dấu một (nhập id) hoặc tất cả thông báo (để trống) là chưa đọc"""
    
    query = db.query(models.Notification).filter(
        models.Notification.user_username == current_user.username,
        models.Notification.is_read == True
    )

    if notification_id:
        query = query.filter(models.Notification.id == notification_id)

    notifications = query.all()

    if not notifications:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo phù hợp")

    # Cập nhật trạng thái của thông báo
    for notification in notifications:
        notification.is_read = False

    db.commit()
    
    return [schemas.NotificationResponse.model_validate(notification) for notification in notifications]


@notifications_router.delete("/{notification_id}", response_model=schemas.NotificationBase,dependencies=[Depends(update_last_active_dependency)])
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)  # Lấy người dùng hiện tại từ token
):
    """Xóa thông báo theo ID"""
    # Tìm thông báo trong cơ sở dữ liệu
    notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Thông báo không tồn tại")
    
    # Kiểm tra nếu thông báo là của người dùng hiện tại
    if notification.user_username != current_user.username:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xóa thông báo này")

    # Xóa thông báo và commit thay đổi vào cơ sở dữ liệu
    db.delete(notification)
    db.commit()

    return {"message": "Thông báo đã được xóa thành công"}