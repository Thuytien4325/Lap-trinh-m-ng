from datetime import datetime, timezone

import models
import schemas
from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from routers.untils import update_last_active_dependency
from routers.users import get_current_user
from routers.websocket import websocket_manager
from sqlalchemy.orm import Session, aliased

friend_request_router = APIRouter(prefix="/friend-requests", tags=["Friend Requests"])


@friend_request_router.get(
    "/status", dependencies=[Depends(update_last_active_dependency)]
)
async def get_friend_status(
    username: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kiểm tra trạng thái kết bạn giữa người dùng hiện tại và {username}, không kiểm tra chính mình"""

    if username == current_user.username:
        raise HTTPException(
            status_code=400, detail="Không thể kiểm tra trạng thái của chính mình"
        )

    user = db.query(models.User).filter(models.User.username == username).first()

    if not user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại")

    if user.is_admin:
        raise HTTPException(status_code=403, detail="Người dùng là quản trị viên.")

    # Kiểm tra xem có phải bạn bè không
    friendship = (
        db.query(models.Friend)
        .filter(
            (
                (models.Friend.user_username == current_user.username)
                & (models.Friend.friend_username == username)
            )
            | (
                (models.Friend.user_username == username)
                & (models.Friend.friend_username == current_user.username)
            )
        )
        .first()
    )
    if friendship:
        return {"status": "Bạn bè", "nickname": user.nickname, "avatar": user.avatar}

    # Kiểm tra xem có đang chờ xử lý không
    sent_request = (
        db.query(models.FriendRequest)
        .filter(
            models.FriendRequest.sender_username == current_user.username,
            models.FriendRequest.receiver_username == username,
            models.FriendRequest.status == "Đợi",
        )
        .first()
    )
    if sent_request:
        return {
            "status": "Đã gửi lời mời",
            "nickname": user.nickname,
            "avatar": user.avatar,
        }

    received_request = (
        db.query(models.FriendRequest)
        .filter(
            models.FriendRequest.sender_username == username,
            models.FriendRequest.receiver_username == current_user.username,
            models.FriendRequest.status == "Đợi",
        )
        .first()
    )
    if received_request:
        return {
            "status": "Chờ xác nhận",
            "nickname": user.nickname,
            "avatar": user.avatar,
        }

    return {"status": "Chưa kết bạn", "nickname": user.nickname, "avatar": user.avatar}


@friend_request_router.post(
    "/",
    response_model=schemas.FriendRequestResponse,
    dependencies=[Depends(update_last_active_dependency)],
)
async def send_friend_request(
    receiver_username: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Gửi lời mời kết bạn"""
    sender = current_user
    receiver = (
        db.query(models.User).filter(models.User.username == receiver_username).first()
    )

    if not receiver:
        raise HTTPException(status_code=404, detail="Người dùng nhận không tồn tại")

    if sender.username == receiver.username:
        raise HTTPException(
            status_code=400, detail="Không thể gửi yêu cầu cho chính mình"
        )

    if receiver.is_admin:
        raise HTTPException(
            status_code=403, detail="Không thể kết bạn với quản trị viên."
        )

    existing_friendship = (
        db.query(models.Friend)
        .filter(
            (
                (models.Friend.user_username == sender.username)
                & (models.Friend.friend_username == receiver.username)
            )
            | (
                (models.Friend.user_username == receiver.username)
                & (models.Friend.friend_username == sender.username)
            )
        )
        .first()
    )
    if existing_friendship:
        raise HTTPException(status_code=400, detail="Hai người đã là bạn bè")

    existing_request = (
        db.query(models.FriendRequest)
        .filter(
            (
                (models.FriendRequest.sender_username == sender.username)
                & (models.FriendRequest.receiver_username == receiver.username)
            )
            | (
                (models.FriendRequest.sender_username == receiver.username)
                & (models.FriendRequest.receiver_username == sender.username)
            )
        )
        .first()
    )

    if existing_request:
        raise HTTPException(status_code=400, detail="Yêu cầu đã tồn tại")

    new_request = models.FriendRequest(
        sender_username=sender.username,
        receiver_username=receiver.username,
        status="Đợi",
        created_at_UTC=datetime.now(timezone.utc),
    )

    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # Tạo và lưu thông báo vào database
    new_notification = models.Notification(
        user_username=receiver.username,
        sender_username=sender.username,
        message=f"Bạn có một lời mời kết bạn từ {sender.nickname or sender.username}.",
        type="friend_request",
        related_id=new_request.id,
        related_table="friend_requests",
        created_at_UTC=datetime.now(timezone.utc),
    )

    db.add(new_notification)
    db.commit()

    # Gửi thông báo qua WebSocket
    await websocket_manager.send_notification(
        noti_id=new_request.id,
        user_username=receiver.username,
        sender_username=sender.username,
        message=f"Bạn có một lời mời kết bạn từ {sender.nickname or sender.username}",
        notification_type="friend_request",
        related_id=new_request.id,
        related_table="friend_requests",
    )

    # Lấy thông tin người gửi và người nhận
    sender_info = (
        db.query(models.User.nickname, models.User.avatar)
        .filter(models.User.username == sender.username)
        .first()
    )
    receiver_info = (
        db.query(models.User.nickname, models.User.avatar)
        .filter(models.User.username == receiver.username)
        .first()
    )

    # Trả về phản hồi
    return schemas.FriendRequestResponse(
        id=new_request.id,
        sender_username=new_request.sender_username,
        receiver_username=new_request.receiver_username,
        status=new_request.status,
        created_at_UTC=new_request.created_at_UTC,
        sender_nickname=sender_info.nickname,
        sender_avatar=sender_info.avatar,
        receiver_nickname=receiver_info.nickname,
        receiver_avatar=receiver_info.avatar,
    )


@friend_request_router.post(
    "/{request_id}/accept", dependencies=[Depends(update_last_active_dependency)]
)
async def accept_friend_request(
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chấp nhận lời mời kết bạn"""
    friend_request = (
        db.query(models.FriendRequest)
        .filter(
            models.FriendRequest.id == request_id,
            models.FriendRequest.receiver_username == current_user.username,
            models.FriendRequest.status == "Đợi",
        )
        .first()
    )

    if not friend_request:
        raise HTTPException(
            status_code=404, detail="Lời mời kết bạn không tồn tại hoặc đã xử lý"
        )

    sender_username = friend_request.sender_username
    receiver_username = friend_request.receiver_username

    existing_friendship = (
        db.query(models.Friend)
        .filter(
            (
                (models.Friend.user_username == sender_username)
                & (models.Friend.friend_username == receiver_username)
            )
            | (
                (models.Friend.user_username == receiver_username)
                & (models.Friend.friend_username == sender_username)
            )
        )
        .first()
    )

    if existing_friendship:
        raise HTTPException(status_code=400, detail="Hai người đã là bạn bè")

    new_friend = models.Friend(
        user_username=sender_username,
        friend_username=receiver_username,
        created_at_UTC=datetime.now(timezone.utc),
    )

    # Tạo thông báo cho người gửi
    new_notification = models.Notification(
        user_username=sender_username,
        sender_username=current_user.username,
        message=f"{current_user.nickname} đã chấp nhận lời mời kết bạn của bạn.",
        type="friend_accept",
        related_id=friend_request.id,
        related_table="friend_requests",
        created_at_UTC=datetime.now(timezone.utc),
    )

    db.add(new_friend)
    db.add(new_notification)
    db.delete(friend_request)  # Xóa lời mời sau khi chấp nhận
    db.commit()

    # Gửi thông báo qua WebSocket
    await websocket_manager.send_notification(
        noti_id=new_notification.id,
        user_username=sender_username,
        sender_username=current_user.username,
        message=f"{current_user.nickname} đã chấp nhận lời mời kết bạn của bạn.",
        notification_type="friend_accept",
        related_id=friend_request.id,
        related_table="friend_requests",
    )

    return {"message": "Đã chấp nhận lời mời kết bạn"}


@friend_request_router.post(
    "/{request_id}/reject", dependencies=[Depends(update_last_active_dependency)]
)
async def reject_friend_request(
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Từ chối lời mời kết bạn"""
    friend_request = (
        db.query(models.FriendRequest)
        .filter(
            models.FriendRequest.id == request_id,
            models.FriendRequest.receiver_username == current_user.username,
            models.FriendRequest.status == "Đợi",
        )
        .first()
    )

    if not friend_request:
        raise HTTPException(
            status_code=404, detail="Lời mời kết bạn không tồn tại hoặc đã xử lý"
        )

    sender = (
        db.query(models.User)
        .filter(models.User.username == friend_request.sender_username)
        .first()
    )

    if not sender:
        db.delete(friend_request)
        db.commit()
        return {"message": "Lời mời đã bị xóa vì người gửi không còn tồn tại"}

    # Tạo thông báo cho người gửi
    new_notification = models.Notification(
        user_username=sender.username,
        sender_username=current_user.username,
        message=f"{current_user.nickname} đã từ chối lời mời kết bạn của bạn.",
        type="friend_reject",
        related_id=friend_request.id,
        related_table="friend_requests",
        created_at_UTC=datetime.now(timezone.utc),
    )

    db.delete(friend_request)
    db.add(new_notification)
    db.commit()

    # Gửi thông báo qua WebSocket
    await websocket_manager.send_notification(
        noti_id=new_notification.id,
        user_username=sender.username,
        sender_username=current_user.username,
        message=f"{current_user.nickname} đã từ chối lời mời kết bạn của bạn.",
        notification_type="friend_reject",
        related_id=friend_request.id,
        related_table="friend_requests",
    )

    return {"message": "Đã từ chối lời mời kết bạn"}


@friend_request_router.get(
    "/received",
    response_model=list[schemas.FriendRequestResponse],
    dependencies=[Depends(update_last_active_dependency)],
)
async def get_received_friend_requests(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Lấy danh sách lời mời kết bạn đã nhận"""
    received_requests = (
        db.query(
            models.FriendRequest.id,
            models.FriendRequest.sender_username,
            models.FriendRequest.receiver_username,
            models.FriendRequest.status,
            models.FriendRequest.created_at_UTC,
            models.User.nickname.label("sender_nickname"),
            models.User.avatar.label("sender_avatar"),
        )
        .join(models.User, models.FriendRequest.sender_username == models.User.username)
        .filter(
            models.FriendRequest.receiver_username == current_user.username,
            models.FriendRequest.status == "Đợi",
        )
        .all()
    )

    return [
        schemas.FriendRequestResponse(
            id=req.id,
            sender_username=req.sender_username,
            receiver_username=req.receiver_username,
            status=req.status,
            created_at_UTC=req.created_at_UTC,
            sender_nickname=req.sender_nickname,
            sender_avatar=req.sender_avatar,
            receiver_nickname=current_user.nickname,
            receiver_avatar=current_user.avatar,
        )
        for req in received_requests
    ]


@friend_request_router.get(
    "/sent",
    response_model=list[schemas.FriendRequestResponse],
    dependencies=[Depends(update_last_active_dependency)],
)
async def get_sent_friend_requests(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Lấy danh sách lời mời kết bạn đã gửi"""
    Receiver = aliased(models.User)

    sent_requests = (
        db.query(
            models.FriendRequest.id,
            models.FriendRequest.sender_username,
            models.FriendRequest.receiver_username,
            models.FriendRequest.status,
            models.FriendRequest.created_at_UTC,
            models.User.nickname.label("sender_nickname"),
            models.User.avatar.label("sender_avatar"),
            Receiver.nickname.label("receiver_nickname"),
            Receiver.avatar.label("receiver_avatar"),
        )
        .join(models.User, models.FriendRequest.sender_username == models.User.username)
        .join(Receiver, models.FriendRequest.receiver_username == Receiver.username)
        .filter(
            models.FriendRequest.sender_username == current_user.username,
            models.FriendRequest.status == "Đợi",
        )
        .all()
    )

    return [
        schemas.FriendRequestResponse(
            id=req.id,
            sender_username=req.sender_username,
            receiver_username=req.receiver_username,
            status=req.status,
            created_at_UTC=req.created_at_UTC,
            sender_nickname=req.sender_nickname,
            sender_avatar=req.sender_avatar,
            receiver_nickname=req.receiver_nickname,
            receiver_avatar=req.receiver_avatar,
        )
        for req in sent_requests
    ]


@friend_request_router.delete(
    "/{request_id}", dependencies=[Depends(update_last_active_dependency)]
)
async def delete_friend_request(
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa lời mời kết bạn"""
    # Tìm lời mời kết bạn
    friend_request = (
        db.query(models.FriendRequest)
        .filter(
            models.FriendRequest.id == request_id,
            (models.FriendRequest.sender_username == current_user.username)
            | (models.FriendRequest.receiver_username == current_user.username),
        )
        .first()
    )

    if not friend_request:
        raise HTTPException(
            status_code=404,
            detail="Lời mời kết bạn không tồn tại hoặc bạn không có quyền xóa lời mời này",
        )

    # Xóa lời mời kết bạn
    db.delete(friend_request)
    db.commit()

    return {"message": "Lời mời kết bạn đã bị xóa"}
