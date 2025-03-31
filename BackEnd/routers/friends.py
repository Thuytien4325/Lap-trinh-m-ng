import models
import schemas
from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from routers.untils import update_last_active_dependency
from routers.users import get_current_user
from sqlalchemy.orm import Session

friends_router = APIRouter(prefix="/friends", tags=["Friends"])


@friends_router.get(
    "/Get-friends",
    response_model=list[schemas.FriendResponse],
    dependencies=[Depends(update_last_active_dependency)],
)
async def get_friends(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Lấy danh sách bạn bè hiện tại"""
    friends = (
        db.query(models.User)
        .join(
            models.Friend,
            (models.Friend.user_username == models.User.username)
            | (models.Friend.friend_username == models.User.username),
        )
        .filter(
            (models.Friend.user_username == current_user.username)
            | (models.Friend.friend_username == current_user.username)
        )
        .filter(models.User.username != current_user.username)
        .all()
    )

    return [
        schemas.FriendResponse(
            username=friend.username, nickname=friend.nickname, avatar=friend.avatar
        )
        for friend in friends
    ]


@friends_router.post("/unfriend", dependencies=[Depends(update_last_active_dependency)])
async def unfriend(
    friend_username: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa kết bạn"""
    friend_username = friend_username

    friendship = (
        db.query(models.Friend)
        .filter(
            (models.Friend.user_username == current_user.username)
            & (models.Friend.friend_username == friend_username)
        )
        .first()
    )

    if not friendship:
        friendship = (
            db.query(models.Friend)
            .filter(
                (models.Friend.user_username == friend_username)
                & (models.Friend.friend_username == current_user.username)
            )
            .first()
        )

    if not friendship:
        raise HTTPException(status_code=404, detail="Không tìm thấy bạn bè")

    try:
        db.delete(friendship)
        db.commit()
        return {"message": "Xóa bạn bè thành công"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")


@friends_router.get("/mutual", dependencies=[Depends(update_last_active_dependency)])
async def get_mutual_friends(
    username: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy danh sách bạn chung giữa người dùng hiện tại và {username} (hỗ trợ truy vấn 2 chiều)"""

    # Danh sách bạn của current_user (cả hai chiều)
    user_friends = db.query(models.Friend.friend_username).filter(
        models.Friend.user_username == current_user.username
    )
    user_friends_reverse = db.query(models.Friend.user_username).filter(
        models.Friend.friend_username == current_user.username
    )
    user_friends = user_friends.union(user_friends_reverse).subquery()

    # Danh sách bạn của username (cả hai chiều)
    target_friends = db.query(models.Friend.friend_username).filter(
        models.Friend.user_username == username
    )
    target_friends_reverse = db.query(models.Friend.user_username).filter(
        models.Friend.friend_username == username
    )
    target_friends = target_friends.union(target_friends_reverse).subquery()

    # Lấy bạn chung giữa hai danh sách
    mutual_friends = (
        db.query(models.User)
        .filter(models.User.username.in_(user_friends))
        .filter(models.User.username.in_(target_friends))
        .all()
    )

    return mutual_friends
