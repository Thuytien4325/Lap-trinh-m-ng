from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User, Conversation, GroupMember
from routers.untils import get_admin_user, update_last_active_dependency
from schemas import AdminUserResponse, ConversationResponse
from typing import List
from datetime import datetime, timezone, timedelta

# Tạo router cho admin
admin_router = APIRouter(prefix="/admin", tags=["Admin"])


# API lấy danh sách tất cả user
@admin_router.get("/users", response_model=List[AdminUserResponse])
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
