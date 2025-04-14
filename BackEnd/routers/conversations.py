import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Union

import models
from database import get_db
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from models import Conversation, GroupMember, Notification, User
from routers.untils import (
    AVATARS_GROUP_DIR,
    CONVERSATION_ATTACHMENTS_DIR,
    get_current_user,
    update_last_active_dependency,
)
from routers.websocket import websocket_manager
from schemas import ConversationResponse
from sqlalchemy import case, func
from sqlalchemy.orm import Session

conversation_router = APIRouter(prefix="/conversations", tags=["Conversations"])


@conversation_router.post(
    "/",
    response_model=ConversationResponse,
    dependencies=[Depends(update_last_active_dependency)],
)
async def create_conversation(
    type: str = Query(..., description="Loại cuộc hội thoại: private hoặc group"),
    username: Optional[List[str]] = Query(
        None, description="Danh sách thành viên (bắt buộc nếu là private)"
    ),
    name: Optional[str] = Query(
        None, description="Tên nhóm (chỉ sử dụng nếu type là group)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if type == "private":
        if not username or len(username) != 1:
            raise HTTPException(
                status_code=400,
                detail="Cần cung cấp đúng một username cho cuộc trò chuyện riêng tư.",
            )

        recipient_username = username[0]
        recipient = db.query(User).filter(User.username == recipient_username).first()
        if not recipient:
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại.")
        if recipient.username == current_user.username:
            raise HTTPException(
                status_code=400, detail="Bạn không thể nhắn tin với chính mình."
            )

        # Kiểm tra có phải bạn bè không
        are_friends = (
            db.query(models.Friend)
            .filter(
                (
                    (models.Friend.user_username == current_user.username)
                    & (models.Friend.friend_username == recipient.username)
                )
                | (
                    (models.Friend.user_username == recipient.username)
                    & (models.Friend.friend_username == current_user.username)
                )
            )
            .first()
        )
        if not are_friends:
            raise HTTPException(
                status_code=400, detail="Bạn chỉ có thể nhắn tin với bạn bè."
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
            raise HTTPException(
                status_code=400, detail="Cuộc trò chuyện với người này đã tồn tại."
            )

        new_conversation = Conversation(
            type="private",
            name=f"{current_user.username} & {recipient.username}",
            avatar_url=None,
            created_at_UTC=datetime.now(timezone.utc),
            is_read=False,
        )
        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)

        db.add_all(
            [
                GroupMember(
                    conversation_id=new_conversation.conversation_id,
                    username=current_user.username,
                    joined_at_UTC=datetime.now(timezone.utc),
                ),
                GroupMember(
                    conversation_id=new_conversation.conversation_id,
                    username=recipient.username,
                    joined_at_UTC=datetime.now(timezone.utc),
                ),
            ]
        )
        db.commit()

        # Thông báo cho người nhận
        notification = Notification(
            user_username=recipient.username,
            sender_username=None,
            message=f"Bạn có một cuộc trò chuyện mới với {current_user.nickname}.",
            type="system",
            related_id=new_conversation.conversation_id,
            related_table="conversations",
            created_at_UTC=datetime.now(timezone.utc),
        )
        db.add(notification)
        db.commit()

        await websocket_manager.send_notification(
            noti_id=notification.id,
            user_username=notification.user_username,
            sender_username=notification.sender_username,
            message=notification.message,
            notification_type=notification.type,
            related_id=notification.related_id,
            related_table=notification.related_table,
        )

    elif type == "group":
        if not name:
            raise HTTPException(
                status_code=400, detail="Tên nhóm là bắt buộc đối với nhóm."
            )

        # Nếu không có username, nhóm chỉ có mình người tạo
        if not username:
            username = []

        # Lấy danh sách bạn bè
        friend_usernames = set(
            db.query(models.Friend.friend_username)
            .filter(models.Friend.user_username == current_user.username)
            .union(
                db.query(models.Friend.user_username).filter(
                    models.Friend.friend_username == current_user.username
                )
            )
            .all()
        )
        friend_usernames = {username[0] for username in friend_usernames}

        # Kiểm tra danh sách hợp lệ
        invalid_users = [u for u in username if u not in friend_usernames]
        if invalid_users:
            raise HTTPException(
                status_code=400,
                detail="Danh sách thành viên chỉ có thể là bạn bè của bạn.",
            )

        new_conversation = Conversation(
            type="group",
            name=name,
            avatar_url=None,
            created_at_UTC=datetime.now(timezone.utc),
            is_read=False,
        )
        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)

        members = [
            GroupMember(
                conversation_id=new_conversation.conversation_id,
                username=current_user.username,
                role="admin",
                joined_at_UTC=datetime.now(timezone.utc),
            )
        ]

        users = db.query(User).filter(User.username.in_(username)).all()
        for user in users:
            members.append(
                GroupMember(
                    conversation_id=new_conversation.conversation_id,
                    username=user.username,
                    role="member",
                    joined_at_UTC=datetime.now(timezone.utc),
                )
            )

        db.add_all(members)
        db.commit()

        # Thông báo cho thành viên mới
        notifications = [
            Notification(
                user_username=user.username,
                sender_username=None,
                message=f"Bạn đã được thêm vào nhóm '{new_conversation.name}'.",
                type="system",
                related_id=new_conversation.conversation_id,
                related_table="conversations",
                created_at_UTC=datetime.now(timezone.utc),
            )
            for user in users
        ]

        db.add_all(notifications)
        db.commit()

        for notification in notifications:
            await websocket_manager.send_notification(
                noti_id=notification.id,
                user_username=notification.user_username,
                sender_username=notification.sender_username,
                message=notification.message,
                notification_type=notification.type,
                related_id=notification.related_id,
                related_table=notification.related_table,
            )

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
        "avatar_url": new_conversation.avatar_url,
        "created_at_UTC": new_conversation.created_at_UTC,
        "group_members": group_members,
    }


@conversation_router.post(
    "/{conversation_id}/members",
    response_model=list[ConversationResponse],
    dependencies=[Depends(update_last_active_dependency)],
)
async def add_to_group(
    conversation_id: int,
    new_member_username: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    group = (
        db.query(models.Conversation)
        .filter(
            models.Conversation.conversation_id == conversation_id,
            models.Conversation.type == "group",
        )
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Nhóm không tồn tại!")

    existing_member = (
        db.query(models.GroupMember)
        .filter(
            models.GroupMember.conversation_id == conversation_id,
            models.GroupMember.username == current_user.username,
        )
        .first()
    )

    if not existing_member:
        raise HTTPException(
            status_code=403, detail="Bạn không phải thành viên của nhóm này."
        )

    new_member = (
        db.query(models.User)
        .filter(models.User.username == new_member_username)
        .first()
    )

    if not new_member:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    already_in_group = (
        db.query(models.GroupMember)
        .filter(
            models.GroupMember.conversation_id == conversation_id,
            models.GroupMember.username == new_member_username,
        )
        .first()
    )

    if already_in_group:
        raise HTTPException(
            status_code=400, detail="Người dùng đã là thành viên của nhóm."
        )

    are_friends = (
        db.query(models.Friend)
        .filter(
            (
                (models.Friend.user_username == current_user.username)
                & (models.Friend.friend_username == new_member_username)
            )
            | (
                (models.Friend.user_username == new_member_username)
                & (models.Friend.friend_username == current_user.username)
            )
        )
        .first()
    )

    if not are_friends:
        raise HTTPException(
            status_code=400, detail="Bạn chỉ có thế thêm bạn bè vào nhóm."
        )

    new_group_member = models.GroupMember(
        conversation_id=conversation_id,
        username=new_member_username,
        role="member",
        joined_at_UTC=datetime.now(timezone.utc),
    )
    db.add(new_group_member)
    db.commit()

    notification = Notification(
        user_username=new_member.username,
        sender_username=None,
        message=f"Bạn đã được thêm vào nhóm {group.name} bởi {current_user.nickname}.",
        type="system",
        related_id=group.conversation_id,
        related_table="conversations",
        created_at_UTC=datetime.now(timezone.utc),
    )
    db.add(notification)
    db.commit()

    await websocket_manager.send_notification(
        noti_id=notification.id,
        user_username=notification.user_username,
        sender_username=notification.sender_username,
        message=notification.message,
        notification_type=notification.type,
        related_id=notification.related_id,
        related_table=notification.related_table,
    )

    members = (
        db.query(models.GroupMember, models.User)
        .join(models.User, models.GroupMember.username == models.User.username)
        .filter(models.GroupMember.conversation_id == conversation_id)
        .all()
    )

    conversation_list = [
        {
            "conversation_id": group.conversation_id,
            "type": group.type,
            "name": group.name,
            "avatar_url": group.avatar_url,
            "created_at_UTC": group.created_at_UTC,
            "group_members": [
                {
                    "username": member.User.username,
                    "avatar": member.User.avatar,
                    "nickname": member.User.nickname,
                    "role": member.GroupMember.role,
                }
                for member in members
            ],
        }
    ]

    return conversation_list


@conversation_router.get(
    "/",
    response_model=list[ConversationResponse],
    dependencies=[Depends(update_last_active_dependency)],
)
async def get_conversations(
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
        # Lấy thông tin thành viên
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

        # Lấy thời gian tin nhắn gần nhất
        last_message_time = (
            db.query(func.max(models.Message.timestamp))
            .filter(models.Message.conversation_id == convo.conversation_id)
            .scalar()
        )

        conversation_list.append(
            {
                "conversation_id": convo.conversation_id,
                "type": convo.type,
                "name": convo.name,
                "avatar_url": convo.avatar_url,
                "created_at_UTC": convo.created_at_UTC,
                "last_message_time": last_message_time,
                "group_members": group_members,
            }
        )

    return conversation_list


@conversation_router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    dependencies=[Depends(update_last_active_dependency)],
)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    conversation = (
        db.query(models.Conversation)
        .filter(models.Conversation.conversation_id == conversation_id)
        .join(models.GroupMember)
        .filter(models.GroupMember.username == current_user.username)
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cuộc hội thoại hoặc bạn không có quyền!",
        )

    # Lấy danh sách thành viên của nhóm
    members = (
        db.query(models.GroupMember, models.User)
        .join(models.User, models.GroupMember.username == models.User.username)
        .filter(models.GroupMember.conversation_id == conversation_id)
        .all()
    )

    return {
        "conversation_id": conversation.conversation_id,
        "type": conversation.type,
        "name": conversation.name,
        "avatar_url": conversation.avatar_url,
        "created_at_UTC": conversation.created_at_UTC,
        "group_members": [
            {
                "username": member.User.username,
                "avatar": member.User.avatar,
                "nickname": member.User.nickname,
                "role": member.GroupMember.role,
            }
            for member in members
        ],
    }


@conversation_router.put(
    "/{conversation_id}/group",
    response_model=ConversationResponse,
    dependencies=[Depends(update_last_active_dependency)],
)
async def update_group(
    conversation_id: int,
    name_group: str | None = None,
    avatar_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    conversation = (
        db.query(models.Conversation)
        .filter(models.Conversation.conversation_id == conversation_id)
        .join(models.GroupMember)
        .filter(models.GroupMember.username == current_user.username)
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cuộc hội thoại hoặc bạn không có quyền!",
        )

    if name_group:
        conversation.name = name_group

    if avatar_file:
        file_extension = avatar_file.filename.split(".")[-1].lower()
        if file_extension not in ["jpg", "jpeg", "png"]:
            raise HTTPException(
                status_code=400,
                detail="Định dạng ảnh không hợp lệ! (Chỉ chấp nhận jpg, jpeg, png)",
            )

        # Xóa avatar cũ nếu có
        if conversation.avatar_url:
            old_avatar_path = os.path.join(
                AVATARS_GROUP_DIR, os.path.basename(conversation.avatar_url)
            )
            if os.path.exists(old_avatar_path):
                os.remove(old_avatar_path)

        # Lưu file mới với format
        file_path = f"{AVATARS_GROUP_DIR}/groupID_{conversation_id}.{file_extension}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(avatar_file.file, buffer)

        # Cập nhật avatar_url trong database
        conversation.avatar_url = f"/{file_path}"

    # Lưu thay đổi vào database
    db.commit()
    db.refresh(conversation)

    members = (
        db.query(models.GroupMember, models.User)
        .join(models.User, models.GroupMember.username == models.User.username)
        .filter(models.GroupMember.conversation_id == conversation_id)
        .all()
    )

    return {
        "conversation_id": conversation.conversation_id,
        "type": conversation.type,
        "name": conversation.name,
        "avatar_url": conversation.avatar_url,
        "created_at_UTC": conversation.created_at_UTC,
        "group_members": [
            {
                "username": member.User.username,
                "avatar": member.User.avatar,
                "nickname": member.User.nickname,
                "role": member.GroupMember.role,
            }
            for member in members
        ],
    }


@conversation_router.delete("/{conversations_id}/members/{member_username}")
async def remove_member_from_group(
    conversations_id: int,
    member_username: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Kiểm tra nếu cuộc hội thoại có tồn tại không
    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_id == conversations_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Cuộc hội thoại không tồn tại.")

    if conversation.type == "private":
        raise HTTPException(
            status_code=400,
            detail="Không thể xóa thành viên trong cuộc trò chuyện riêng tư.",
        )

    # Kiểm tra quyền người dùng (chỉ admin mới có quyền xóa thành viên)
    is_admin = (
        db.query(models.GroupMember)
        .filter(
            models.GroupMember.conversation_id == conversations_id,
            models.GroupMember.username == current_user.username,
            models.GroupMember.role == "admin",
        )
        .first()
    )

    if not is_admin:
        raise HTTPException(
            status_code=403, detail="Chỉ quản trị viên mới có thể xóa nhóm."
        )

    if current_user.username == member_username:
        raise HTTPException(
            status_code=400, detail="Quản trị viên không thể xóa chính mình."
        )

    # Tìm thành viên trong nhóm
    member = (
        db.query(GroupMember)
        .filter(
            GroupMember.username == member_username,
            GroupMember.conversation_id == conversations_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=404, detail="Thành viên không tồn tại trong nhóm."
        )

    # Xóa thành viên khỏi nhóm
    db.delete(member)
    db.commit()

    notification = Notification(
        user_username=member_username,
        sender_username=None,
        message=f"Bạn đã bị xóa khỏi nhóm {conversation.name} bởi {current_user.username}.",
        type="system",
        related_id=conversation.conversation_id,
        related_table="conversations",
        created_at_UTC=datetime.now(timezone.utc),
    )
    db.add(notification)
    db.commit()

    await websocket_manager.send_notification(
        noti_id=notification.id,
        user_username=notification.user_username,
        sender_username=notification.sender_username,
        message=notification.message,
        notification_type=notification.type,
        related_id=notification.related_id,
        related_table=notification.related_table,
    )

    return {"message": f"Thành viên {member_username} đã bị xóa khỏi nhóm."}


@conversation_router.put("/{conversation_id}/members/{member_username}/admin")
async def assign_admin(
    conversation_id: int,
    member_username: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Kiểm tra nếu cuộc hội thoại có tồn tại không
    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_id == conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Cuộc hội thoại không tồn tại.")

    if conversation.type == "private":
        raise HTTPException(
            status_code=400,
            detail="Không thể chỉ định người dùng làm admin trong cuộc trò chuyện riêng tư",
        )

    # Kiểm tra quyền người dùng (chỉ admin mới có quyền chỉ định admin)
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
            status_code=403, detail="Chỉ quản trị viên mới có thể chỉ định admin."
        )

    if current_user.username == member_username:
        raise HTTPException(
            status_code=400, detail="Quản trị viên tự chỉ định chính mình."
        )

    # Tìm thành viên trong nhóm
    member = (
        db.query(GroupMember)
        .filter(
            GroupMember.username == member_username,
            GroupMember.conversation_id == conversation_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=404, detail="Thành viên không tồn tại trong nhóm."
        )

    current_admin = (
        db.query(models.GroupMember)
        .filter(
            models.GroupMember.conversation_id == conversation_id,
            models.GroupMember.role == "admin",
        )
        .first()
    )

    if current_admin and current_admin.username == current_user.username:

        current_admin.role = "member"
        db.add(current_admin)

        member.role = "admin"
        db.add(member)

        db.commit()

        notification = Notification(
            user_username=member_username,
            sender_username=None,
            message=f"Bạn đã được chỉ định làm admin nhóm '{conversation.name}' bởi {current_admin.username}.",
            type="system",
            related_id=conversation.conversation_id,
            related_table="conversations",
            created_at_UTC=datetime.now(timezone.utc),
        )
        db.add(notification)
        db.commit()

        await websocket_manager.send_notification(
            noti_id=notification.id,
            user_username=notification.user_username,
            sender_username=notification.sender_username,
            message=notification.message,
            notification_type=notification.type,
            related_id=notification.related_id,
            related_table=notification.related_table,
        )

        return {
            "message": f"Thành viên {member_username} đã được chỉ định làm admin và bạn trở thành member."
        }

    raise HTTPException(status_code=400, detail="Không thể thay đổi quyền admin.")


@conversation_router.delete(
    "/{conversation_id}",
    dependencies=[Depends(update_last_active_dependency)],
)
async def delete_conversation(
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

        # Lấy danh sách thành viên nhóm
        group_members = (
            db.query(models.GroupMember.username)
            .filter(
                models.GroupMember.conversation_id == conversation_id,
                models.GroupMember.role == "member",
            )
            .all()
        )

        # Gửi thông báo đến tất cả thành viên trong nhóm
        notifications = [
            models.Notification(
                user_username=member.username,
                sender_username=None,
                message=f"Nhóm '{conversation.name}' đã bị xóa bởi {current_user.nickname}.",
                type="system",
                related_id=conversation.conversation_id,
                related_table="conversations",
                created_at_UTC=datetime.now(timezone.utc),
            )
            for member in group_members
        ]

        db.add_all(notifications)
        db.commit()

        for notification in notifications:
            await websocket_manager.send_notification(
                noti_id=notification.id,
                user_username=notification.user_username,
                sender_username=notification.sender_username,
                message=notification.message,
                notification_type=notification.type,
                related_id=notification.related_id,
                related_table=notification.related_table,
            )

    db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    ).delete()
    db.query(models.GroupMember).filter(
        models.GroupMember.conversation_id == conversation_id
    ).delete()
    db.delete(conversation)
    db.commit()

    conversation_dir = os.path.join(CONVERSATION_ATTACHMENTS_DIR, str(conversation_id))
    if os.path.exists(conversation_dir):
        try:
            shutil.rmtree(conversation_dir)  # Xóa thư mục chứa file của cuộc trò chuyện
        except Exception as e:
            print(f"Lỗi khi xóa thư mục: {e}")

    return {"message": "Xóa hội thoại thành công.", "conversation_id": conversation_id}


@conversation_router.get(
    "/{conversation_id}/ban-status",
    dependencies=[Depends(update_last_active_dependency)],
)
async def check_group_ban(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    API kiểm tra xem nhóm chat có đang bị ban không.
    Trả về thông tin về lệnh cấm nếu có.
    """

    # Kiểm tra nhóm có tồn tại không
    conversation = (
        db.query(models.Conversation)
        .filter(
            models.Conversation.conversation_id == conversation_id,
            models.Conversation.type == "group",
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Nhóm không tồn tại.")

    # Lấy tất cả các cảnh báo liên quan đến nhóm chat
    warnings = (
        db.query(models.Warning)
        .filter(
            models.Warning.target_id == conversation_id,
            models.Warning.target_type == "groups",
        )
        .all()
    )

    # Lấy thời gian hiện tại UTC
    now_utc = datetime.now(timezone.utc)

    # Kiểm tra xem có lệnh cấm nào đang còn hiệu lực không
    active_bans = []
    for warning in warnings:
        if warning.ban_duration > 0:  # Nếu có thời gian cấm
            ban_end_time = (
                warning.created_at_UTC + timedelta(minutes=warning.ban_duration)
            ).replace(tzinfo=timezone.utc)

            if now_utc < ban_end_time:
                active_bans.append(
                    {
                        "reason": warning.reason,
                        "ban_start": warning.created_at_UTC,
                        "ban_end": ban_end_time,
                    }
                )

    if active_bans:
        return {
            "is_banned": True,
            "active_bans": active_bans,
        }

    return {"is_banned": False, "message": "Nhóm không bị ban."}


@conversation_router.post(
    "/{conversation_id}/leave", dependencies=[Depends(update_last_active_dependency)]
)
async def leave_group(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    API để người dùng rời khỏi nhóm chat.
    Nếu người dùng là admin, thành viên đầu tiên trong danh sách sẽ được chọn làm admin mới.
    Nếu nhóm chỉ còn một thành viên, nhóm sẽ bị xóa.
    """
    # Kiểm tra nhóm có tồn tại không
    group = (
        db.query(models.Conversation)
        .filter(
            models.Conversation.conversation_id == conversation_id,
            models.Conversation.type == "group",
        )
        .first()
    )

    if not group:
        raise HTTPException(status_code=404, detail="Nhóm không tồn tại!")

    # Kiểm tra người dùng có trong nhóm không
    user_in_group = (
        db.query(models.GroupMember)
        .filter(
            models.GroupMember.conversation_id == conversation_id,
            models.GroupMember.username == current_user.username,
        )
        .first()
    )

    if not user_in_group:
        raise HTTPException(
            status_code=403, detail="Bạn không phải thành viên của nhóm này!"
        )

    # Lấy danh sách thành viên nhóm, sắp xếp theo thời gian tham gia
    group_members = (
        db.query(models.GroupMember)
        .filter(models.GroupMember.conversation_id == conversation_id)
        .order_by(models.GroupMember.joined_at_UTC.asc())
        .all()
    )

    # Nếu nhóm chỉ còn 1 thành viên (người rời nhóm là thành viên cuối cùng) => Xóa nhóm
    if len(group_members) == 1:
        db.query(models.Message).filter(
            models.Message.conversation_id == conversation_id
        ).delete()
        db.query(models.GroupMember).filter(
            models.GroupMember.conversation_id == conversation_id
        ).delete()
        db.delete(group)
        db.commit()
        return {"message": "Nhóm đã bị xóa vì không còn thành viên nào."}

    # Nếu người dùng là ADMIN, chọn thành viên đầu tiên làm admin mới
    if user_in_group.role == "admin":
        # Lấy thành viên đầu tiên trong danh sách (bỏ qua người đang thoát)
        new_admin = next(
            (
                member
                for member in group_members
                if member.username != current_user.username
            ),
            None,
        )

        if new_admin:
            new_admin.role = "admin"
            db.commit()

            # Thông báo cho admin mới
            notification = models.Notification(
                user_username=new_admin.username,
                sender_username=None,
                message=f"Bạn đã trở thành quản trị viên của nhóm '{group.name}' vì {current_user.nickname} đã rời nhóm.",
                type="system",
                related_id=group.conversation_id,
                related_table="conversations",
                created_at_UTC=datetime.now(timezone.utc),
            )
            db.add(notification)
            db.commit()

            await websocket_manager.send_notification(
                noti_id=notification.id,
                user_username=notification.user_username,
                sender_username=notification.sender_username,
                message=notification.message,
                notification_type=notification.type,
                related_id=notification.related_id,
                related_table=notification.related_table,
            )

        else:
            raise HTTPException(
                status_code=500,
                detail="Không tìm thấy thành viên nào để chuyển quyền admin.",
            )

    else:  # Nếu người dùng là thành viên thường
        # Tìm danh sách admin nhóm
        admin_users = (
            db.query(models.GroupMember.username)
            .filter(
                models.GroupMember.conversation_id == conversation_id,
                models.GroupMember.role == "admin",
            )
            .all()
        )

        # Gửi thông báo cho tất cả admin rằng thành viên đã rời nhóm
        notifications = [
            models.Notification(
                user_username=admin.username,
                sender_username=None,
                message=f"{current_user.username} đã rời khỏi nhóm '{group.name}'.",
                type="system",
                related_id=group.conversation_id,
                related_table="conversations",
                created_at_UTC=datetime.now(timezone.utc),
            )
            for admin in admin_users
        ]
        db.add_all(notifications)
        db.commit()

        for notification in notifications:
            await websocket_manager.send_notification(
                noti_id=notification.id,
                user_username=notification.user_username,
                sender_username=notification.sender_username,
                message=notification.message,
                notification_type=notification.type,
                related_id=notification.related_id,
                related_table=notification.related_table,
            )

    # Xóa người dùng khỏi nhóm
    db.query(models.GroupMember).filter(
        models.GroupMember.conversation_id == conversation_id,
        models.GroupMember.username == current_user.username,
    ).delete()
    db.commit()

    return {"message": f"{current_user.username} đã rời khỏi nhóm '{group.name}'."}


@conversation_router.get("/download/{conversation_id}/{filename}")
def download_file(conversation_id: int, filename: str):
    file_url = f"uploads/conversations/{conversation_id}/{filename}"
    file_path = Path(file_url)

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File không tồn tại")

    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=filename,
    )


@conversation_router.put("/conversations/{conversation_id}/mark-read")
async def mark_conversation_as_read(
    conversation_id: int, db: Session = Depends(get_db)
):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_id == conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Cuộc trò chuyện không tồn tại!")

    conversation.is_read = True
    db.commit()

    return {"message": "Thành công"}
