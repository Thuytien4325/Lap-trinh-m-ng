from fastapi import APIRouter, Depends, HTTPException, Response

from sqlalchemy.orm import Session
import models
from schemas import ConversationCreate, ConversationResponse
from database import get_db
from routers.untils import get_current_user
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from sqlalchemy import func, case
from models import User, Conversation, GroupMember, Notification

conversation_router = APIRouter(prefix="/conversations", tags=["Conversations"])


@conversation_router.post("/create-conversation", response_model=ConversationResponse)
def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if conversation.type == "private":
        recipient = (
            db.query(User).filter(User.username == conversation.username).first()
        )
        if not recipient:
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại.")
        if recipient.username == current_user.username:
            raise HTTPException(
                status_code=400, detail="Bạn không thể nhắn tin với chính mình."
            )

        existing_conversation = (
            db.query(Conversation)
            .join(GroupMember)
            .filter(
                Conversation.type == "private",
                GroupMember.username.in_([current_user.username, recipient.username]),
            )
            .group_by(Conversation.conversation_id)
            .having(func.count(GroupMember.username) == 2)
            .first()
        )

        if existing_conversation:
            return existing_conversation

        new_conversation = Conversation(
            type="private", name=f"{current_user.username} & {recipient.username}"
        )
        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)

        db.add_all(
            [
                GroupMember(
                    conversation_id=new_conversation.conversation_id,
                    username=current_user.username,
                ),
                GroupMember(
                    conversation_id=new_conversation.conversation_id,
                    username=recipient.username,
                ),
            ]
        )
        db.commit()

        # Thông báo cho người nhận về cuộc trò chuyện mới
        notification = Notification(
            user_username=recipient.username,
            sender_username=current_user.username,
            message=f"Bạn có một cuộc trò chuyện mới với {current_user.username}.",
            type="message",
            related_id=new_conversation.conversation_id,
            related_table="conversations",
        )
        db.add(notification)
        db.commit()
    elif conversation.type == "group":
        if isinstance(conversation.username, str) and conversation.username == "":
            conversation.username = []

        if not isinstance(conversation.username, list):
            raise HTTPException(
                status_code=400, detail="Danh sách thành viên phải là một danh sách."
            )

        existing_group = (
            db.query(Conversation)
            .filter(
                Conversation.name == conversation.name, Conversation.type == "group"
            )
            .first()
        )
        if existing_group:
            raise HTTPException(status_code=400, detail="Nhóm với tên này đã tồn tại.")

        new_conversation = Conversation(type="group", name=conversation.name)
        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)

        members = [
            GroupMember(
                conversation_id=new_conversation.conversation_id,
                username=current_user.username,
                role="admin",
            )
        ]
        users = db.query(User).filter(User.username.in_(conversation.username)).all()
        for user in users:
            members.append(
                GroupMember(
                    conversation_id=new_conversation.conversation_id,
                    username=user.username,
                    role="member",
                )
            )

        db.add_all(members)
        db.commit()

        # Thông báo cho các thành viên mới được thêm vào nhóm
        notifications = [
            Notification(
                user_username=user.username,
                sender_username=current_user.username,
                message=f"Bạn đã được thêm vào nhóm '{new_conversation.name}'.",
                type="group_invite",
                related_id=new_conversation.conversation_id,
                related_table="conversations",
            )
            for user in users
        ]

        db.add_all(notifications)
        db.commit()
    else:
        raise HTTPException(status_code=400, detail="Loại hội thoại không hợp lệ.")

    members = (
        db.query(User.username, User.avatar, User.nickname, GroupMember.role)
        .join(GroupMember, User.username == GroupMember.username)
        .filter(GroupMember.conversation_id == new_conversation.conversation_id)
        .all()
    )

    group_members = [
        {
            "username": member.username,
            "avatar": member.avatar,
            "nickname": member.nickname,
            "role": member.role,
        }
        for member in members
    ]

    return {
        "conversation_id": new_conversation.conversation_id,
        "type": new_conversation.type,
        "name": new_conversation.name,
        "group_members": group_members,
    }


# Lấy danh sách cuộc hội thoại
@conversation_router.get(
    "/get-conversations", response_model=list[ConversationResponse]
)
def get_conversations(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    conversations = (
        db.query(models.Conversation)
        .join(models.GroupMember)
        .filter(models.GroupMember.username == current_user.username)
        .all()
    )

    conversation_list = []
    for convo in conversations:
        members = (
            db.query(
                models.User.username,
                models.User.avatar,
                models.User.nickname,
                models.GroupMember.role,
            )
            .join(
                models.GroupMember, models.User.username == models.GroupMember.username
            )
            .filter(models.GroupMember.conversation_id == convo.conversation_id)
            .all()
        )

        group_members = [
            {
                "username": member.username,
                "avatar": member.avatar,
                "nickname": member.nickname,
                "role": member.role,
            }
            for member in members
        ]

        conversation_list.append(
            {
                "conversation_id": convo.conversation_id,
                "type": convo.type,
                "name": convo.name,
                "group_members": group_members,
            }
        )

    return conversation_list


@conversation_router.delete("/delete-conversation/{conversation_id}", status_code=200)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    conversation = (
        db.query(models.Conversation)
        .filter(models.Conversation.conversation_id == conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Hội thoại không tồn tại.")

    is_member = (
        db.query(models.GroupMember)
        .filter(
            models.GroupMember.conversation_id == conversation_id,
            models.GroupMember.username == current_user.username,
        )
        .first()
    )

    if not is_member:
        raise HTTPException(
            status_code=403, detail="Bạn không phải là thành viên của hội thoại này."
        )

    if conversation.type == "group":
        is_admin = (
            db.query(models.GroupMember)
            .filter(
                models.GroupMember.conversation_id == conversation_id,
                models.GroupMember.username == current_user.username,
                models.GroupMember.role == "admin",
            )
            .first()
        )

        if not is_admin:
            raise HTTPException(
                status_code=403, detail="Chỉ quản trị viên mới có thể xóa nhóm."
            )

    db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    ).delete()
    db.query(models.GroupMember).filter(
        models.GroupMember.conversation_id == conversation_id
    ).delete()
    db.delete(conversation)
    db.commit()

    return {"message": "Xóa hội thoại thành công.", "conversation_id": conversation_id}
