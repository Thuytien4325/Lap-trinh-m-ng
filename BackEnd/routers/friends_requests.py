from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from routers.users import get_current_user  # Import hàm xác thực

friend_request_router = APIRouter(prefix="/friend-requests", tags=["Friend Requests"])

@friend_request_router.post("/", response_model=schemas.FriendRequestResponse)
def send_friend_request(
    request: schemas.FriendRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)  # Lấy user từ token
):
    sender = current_user  # Người gửi là user hiện tại
    receiver = db.query(models.User).filter(models.User.username == request.receiver_username).first()
    
    if not receiver:
        raise HTTPException(status_code=404, detail="Người dùng nhận không tồn tại")
    if sender.username == receiver.username:
        raise HTTPException(status_code=400, detail="Không thể gửi yêu cầu cho chính mình")

    # Kiểm tra nếu hai người đã là bạn bè
    existing_friendship = db.query(models.Friend).filter(
        ((models.Friend.user_username == sender.username) & (models.Friend.friend_username == receiver.username)) |
        ((models.Friend.user_username == receiver.username) & (models.Friend.friend_username == sender.username))
    ).first()
    if existing_friendship:
        raise HTTPException(status_code=400, detail="Hai người đã là bạn bè")

    # Kiểm tra nếu đã có yêu cầu đang chờ
    existing_request = db.query(models.FriendRequest).filter(
        models.FriendRequest.sender_username == sender.username,
        models.FriendRequest.receiver_username == receiver.username
    ).first()
    
    if existing_request and existing_request.status == "Đợi":
        raise HTTPException(status_code=400, detail="Yêu cầu đã tồn tại")

    # Tạo yêu cầu kết bạn mới
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
