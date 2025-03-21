from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, aliased
from database import get_db
import models
import schemas
from routers.users import get_current_user

friend_request_router = APIRouter(prefix="/friend-requests", tags=["Friend Requests"])

@friend_request_router.post("/", response_model=schemas.FriendRequestResponse)
def send_friend_request(
    request: schemas.FriendRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Gửi lời mời kết bạn"""
    sender = current_user
    receiver = db.query(models.User).filter(models.User.username == request.receiver_username).first()

    if not receiver:
        raise HTTPException(status_code=404, detail="Người dùng nhận không tồn tại")
    if sender.username == receiver.username:
        raise HTTPException(status_code=400, detail="Không thể gửi yêu cầu cho chính mình")

    existing_friendship = db.query(models.Friend).filter(
        ((models.Friend.user_username == sender.username) & (models.Friend.friend_username == receiver.username)) |
        ((models.Friend.user_username == receiver.username) & (models.Friend.friend_username == sender.username))
    ).first()
    if existing_friendship:
        raise HTTPException(status_code=400, detail="Hai người đã là bạn bè")

    received_request = db.query(models.FriendRequest).filter(
        models.FriendRequest.sender_username == receiver.username,
        models.FriendRequest.receiver_username == sender.username,
        models.FriendRequest.status == "Đợi"
    ).first()
    if received_request:
        raise HTTPException(status_code=400, detail="Bạn có một lời mời từ người này, hãy chấp nhận hoặc từ chối trước")

    existing_request = db.query(models.FriendRequest).filter(
        models.FriendRequest.sender_username == sender.username,
        models.FriendRequest.receiver_username == receiver.username
    ).first()

    if existing_request and existing_request.status == "Đợi":
        raise HTTPException(status_code=400, detail="Yêu cầu đã tồn tại")

    new_request = models.FriendRequest(
        sender_username=sender.username,
        receiver_username=receiver.username,
        status="Đợi"
    )

    try:
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        return new_request
    except:
        db.rollback()
        raise HTTPException(status_code=500, detail="Lỗi server, vui lòng thử lại sau")


@friend_request_router.get("/received", response_model=list[schemas.FriendRequestResponse])
def get_received_friend_requests(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách lời mời kết bạn đã nhận"""
    Receiver = aliased(models.User)

    received_requests = (
        db.query(
            models.FriendRequest.id,
            models.FriendRequest.sender_username,
            models.FriendRequest.receiver_username,
            models.FriendRequest.status,
            models.FriendRequest.created_at,
            models.User.nickname.label("sender_nickname"),
            models.User.avatar.label("sender_avatar"),
            Receiver.nickname.label("receiver_nickname"),
            Receiver.avatar.label("receiver_avatar")
        )
        .join(models.User, models.FriendRequest.sender_username == models.User.username)
        .join(Receiver, models.FriendRequest.receiver_username == Receiver.username)
        .filter(
            models.FriendRequest.receiver_username == current_user.username,
            models.FriendRequest.status == "Đợi"
        )
        .all()
    )
    
    return received_requests


@friend_request_router.get("/sent", response_model=list[schemas.FriendRequestResponse])
def get_sent_friend_requests(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách lời mời kết bạn đã gửi"""
    Receiver = aliased(models.User)

    sent_requests = (
        db.query(
            models.FriendRequest.id,
            models.FriendRequest.sender_username,
            models.FriendRequest.receiver_username,
            models.FriendRequest.status,
            models.FriendRequest.created_at,
            models.User.nickname.label("sender_nickname"),
            models.User.avatar.label("sender_avatar"),
            Receiver.nickname.label("receiver_nickname"),
            Receiver.avatar.label("receiver_avatar")
        )
        .join(models.User, models.FriendRequest.sender_username == models.User.username)
        .join(Receiver, models.FriendRequest.receiver_username == Receiver.username)
        .filter(
            models.FriendRequest.sender_username == current_user.username,
            models.FriendRequest.status == "Đợi"
        )
        .all()
    )

    return sent_requests


@friend_request_router.post("/{request_id}/accept")
def accept_friend_request(
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Chấp nhận lời mời kết bạn"""
    friend_request = db.query(models.FriendRequest).filter(
        models.FriendRequest.id == request_id,
        models.FriendRequest.receiver_username == current_user.username,
        models.FriendRequest.status == "Đợi"
    ).first()

    if not friend_request:
        raise HTTPException(status_code=404, detail="Lời mời kết bạn không tồn tại hoặc đã xử lý")

    sender_username = friend_request.sender_username
    receiver_username = friend_request.receiver_username

    existing_friendship = db.query(models.Friend).filter(
        ((models.Friend.user_username == sender_username) & (models.Friend.friend_username == receiver_username)) |
        ((models.Friend.user_username == receiver_username) & (models.Friend.friend_username == sender_username))
    ).first()

    if existing_friendship:
        raise HTTPException(status_code=400, detail="Hai người đã là bạn bè")

    reverse_request = db.query(models.FriendRequest).filter(
        models.FriendRequest.sender_username == receiver_username,
        models.FriendRequest.receiver_username == sender_username,
        models.FriendRequest.status == "Đợi"
    ).first()
    if reverse_request:
        db.delete(reverse_request)

    new_friend = models.Friend(user_username=sender_username, friend_username=receiver_username)
    
    friend_request.status = "Chấp nhận"

    try:
        db.add(new_friend)
        db.commit()
        return {"message": "Đã chấp nhận lời mời kết bạn"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")


@friend_request_router.post("/{request_id}/reject")
def reject_friend_request(
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Từ chối lời mời kết bạn"""
    friend_request = db.query(models.FriendRequest).filter(
        models.FriendRequest.id == request_id,
        models.FriendRequest.receiver_username == current_user.username,
        models.FriendRequest.status == "Đợi"
    ).first()

    if not friend_request:
        raise HTTPException(status_code=404, detail="Lời mời kết bạn không tồn tại hoặc đã xử lý")

    try:
        db.delete(friend_request)
        db.commit()
        return {"message": "Đã từ chối lời mời kết bạn"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")
