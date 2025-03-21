from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from routers.users import get_current_user
import schemas

friends_router = APIRouter(prefix="/api/friends", tags=["Friends"])

@friends_router.get("/Get-friends", response_model=list[schemas.FriendResponse])
def get_friends(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách bạn bè hiện tại"""
    friends = (
        db.query(models.User)
        .join(models.Friend, (models.Friend.user_username == models.User.username) | (models.Friend.friend_username == models.User.username))
        .filter(
            (models.Friend.user_username == current_user.username) | 
            (models.Friend.friend_username == current_user.username)
        )
        .filter(models.User.username != current_user.username)
        .all()
    )

    return [
        schemas.FriendResponse(
            username=friend.username,
            nickname=friend.nickname,
            avatar=friend.avatar
        ) for friend in friends
    ]

@friends_router.post("/unfriend")
def unfriend(
    request: schemas.FriendRemoveRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xóa kết bạn"""
    friend_username = request.friend_username

    friendship = db.query(models.Friend).filter(
        (models.Friend.user_username == current_user.username) & 
        (models.Friend.friend_username == friend_username)
    ).first()

    if not friendship:
        friendship = db.query(models.Friend).filter(
            (models.Friend.user_username == friend_username) & 
            (models.Friend.friend_username == current_user.username)
        ).first()

    if not friendship:
        raise HTTPException(status_code=404, detail="Không tìm thấy bạn bè")

    try:
        db.delete(friendship)
        db.commit()
        return {"message": "Xóa bạn bè thành công"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")