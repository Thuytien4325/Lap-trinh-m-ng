from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from routers.users import get_current_user
import schemas

notifications_router = APIRouter(prefix="/noti", tags=["Notifications"])

@notifications_router.get("/", response_model=list[schemas.NotificationResponse])
def get_notifications(
    unread_only: bool = Query(False, description="Chỉ lấy thông báo chưa đọc"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Notification).filter(models.Notification.user_username == current_user.username)

    if unread_only:
        query = query.filter(models.Notification.is_read == False)

    notifications = query.all()
    return notifications

@notifications_router.post("/{notification_id}/mark-as-read", response_model=schemas.NotificationResponse)
def mark_notification_as_read(
    notification_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Đánh dấu thông báo là đã đọc"""
    
    notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_username == current_user.username
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Thông báo không tồn tại")
    
    notification.is_read = True

    db.commit()
    db.refresh(notification)

    return schemas.NotificationResponse.from_orm(notification)

@notifications_router.post("/mark-all-as-read", response_model=list[schemas.NotificationResponse])
def mark_all_notifications_as_read(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Đánh dấu tất cả thông báo của người dùng là đã đọc"""
    
    # Lấy tất cả thông báo của người dùng hiện tại
    notifications = db.query(models.Notification).filter(
        models.Notification.user_username == current_user.username,
        models.Notification.is_read == False  # Chỉ lấy thông báo chưa đọc
    ).all()

    if not notifications:
        raise HTTPException(status_code=404, detail="Không có thông báo chưa đọc")

    # Cập nhật tất cả thông báo là đã đọc
    for notification in notifications:
        notification.is_read = True

    db.commit()

    # Trả về danh sách thông báo đã được cập nhật
    return [schemas.NotificationResponse.from_orm(notification) for notification in notifications]

@notifications_router.post("/{notification_id}/mark-as-unread", response_model=schemas.NotificationResponse)
def mark_notification_as_unread(
    notification_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Đánh dấu một thông báo là chưa đọc"""
    
    # Lấy thông báo từ cơ sở dữ liệu
    notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_username == current_user.username
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Thông báo không tồn tại")

    # Cập nhật thông báo thành chưa đọc
    notification.is_read = False

    db.commit()

    # Trả về thông báo đã được cập nhật
    return schemas.NotificationResponse.from_orm(notification)

@notifications_router.post("/mark-all-as-unread", response_model=list[schemas.NotificationResponse])
def mark_all_notifications_as_unread(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Đánh dấu tất cả thông báo của người dùng là chưa đọc"""
    
    # Lấy tất cả thông báo đã đọc của người dùng
    notifications = db.query(models.Notification).filter(
        models.Notification.user_username == current_user.username,
        models.Notification.is_read == True  # Chỉ lấy thông báo đã đọc
    ).all()

    if not notifications:
        raise HTTPException(status_code=404, detail="Không có thông báo đã đọc để đánh dấu lại")

    # Cập nhật tất cả thông báo là chưa đọc
    for notification in notifications:
        notification.is_read = False

    db.commit()

    # Trả về danh sách thông báo đã được cập nhật
    return [schemas.NotificationResponse.from_orm(notification) for notification in notifications]

@notifications_router.delete("/{notification_id}", response_model=schemas.NotificationBase)
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