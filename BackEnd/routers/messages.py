import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import List

import models
from database import get_db
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from models import Attachment, Conversation, GroupMember, Message, User
from routers.untils import (
    CONVERSATION_ATTACHMENTS_DIR,
    get_current_user,
    update_last_active_dependency,
)
from routers.websocket import websocket_manager
from sqlalchemy.orm import Session

messages_router = APIRouter(prefix="/messages", tags=["Messages"])


@messages_router.post(
    "/",
    dependencies=[Depends(update_last_active_dependency)],
)
async def send_message(
    conversation_id: int,
    content: str | None = None,  # Tin nhắn văn bản (nếu có)
    files: List[UploadFile] | None = File(None),  # Danh sách file đính kèm (nếu có)
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Kiểm tra cuộc hội thoại
    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Cuộc hội thoại không tồn tại")

    # Kiểm tra xem người dùng có phải là thành viên của nhóm không
    is_member = (
        db.query(GroupMember)
        .filter(
            GroupMember.conversation_id == conversation_id,
            GroupMember.username == current_user.username,
        )
        .first()
    )
    if not is_member:
        raise HTTPException(status_code=403, detail="Bạn không thuộc nhóm này")

    # Tạo tin nhắn mới (text message)
    new_message = Message(
        sender_id=current_user.user_id,
        conversation_id=conversation_id,
        content=content or "",  # Nếu không có nội dung thì gán chuỗi rỗng
        timestamp=datetime.now(timezone.utc),
        is_read=False,
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    # Tạo thư mục riêng cho cuộc hội thoại nếu chưa có
    conversation_dir = os.path.join(CONVERSATION_ATTACHMENTS_DIR, str(conversation_id))
    os.makedirs(conversation_dir, exist_ok=True)

    # Danh sách lưu các đường dẫn file
    file_urls = []
    if files:
        for i, file in enumerate(files):
            file_extension = file.filename.split(".")[-1].lower()

            # Kiểm tra định dạng file
            allowed_extensions = ["jpg", "jpeg", "png", "pdf", "mp4", "mp3"]
            if file_extension not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Định dạng file {file_extension} không được hỗ trợ!",
                )

            # Tạo tên file duy nhất và đường dẫn lưu trữ (sử dụng UUID)
            file_name = f"{new_message.message_id}_{uuid.uuid4().hex}.{file_extension}"
            file_path = os.path.join(conversation_dir, file_name)

            # Lưu file vào hệ thống tệp tin
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Đảm bảo đường dẫn sử dụng dấu gạch chéo "/"
            file_url = f"uploads/conversations/{conversation_id}/{file_name}"

            # Lưu thông tin file vào bảng Attachment
            attachment = Attachment(
                message_id=new_message.message_id,
                file_url=file_url,
                file_type=file.content_type,
            )
            db.add(attachment)
            file_urls.append(file_url)

        db.commit()

    message_data = {
        "message_id": new_message.message_id,
        "sender_id": current_user.user_id,
        "sender_username": current_user.username,
        "sender_nickname": current_user.nickname,
        "content": new_message.content,
        "timestamp": new_message.timestamp.isoformat(),
        "is_read": new_message.is_read,
        "attachments": file_urls,
    }

    # Lấy danh sách thành viên nhóm (trừ người gửi)
    group_members = (
        db.query(GroupMember.username)
        .filter(GroupMember.conversation_id == conversation_id)
        .all()
    )
    recipient_list = [
        member[0] for member in group_members if member[0] != current_user.username
    ]

    # Gửi tin nhắn đến tất cả thành viên nhóm
    for recipient in recipient_list:
        await websocket_manager.send_chat_message(
            conversation_id, recipient, message_data
        )

    # Trả về kết quả

    return {
        "message_id": new_message.message_id,
        "sender_id": current_user.user_id,
        "sender_username": current_user.username,
        "sender_nickname": current_user.nickname,
        "content": new_message.content,
        "timestamp": new_message.timestamp.isoformat(),
        "is_read": new_message.is_read,
        "attachments": [
            {"file_url": url, "file_type": att.file_type}
            for url, att in zip(
                file_urls,
                db.query(Attachment)
                .filter(Attachment.message_id == new_message.message_id)
                .all(),
            )
        ],
    }


# API lấy tin nhắn theo cuộc hội thoại
@messages_router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Kiểm tra cuộc hội thoại tồn tại không
    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Cuộc hội thoại không tồn tại")

    # Kiểm tra người dùng có thuộc nhóm không
    is_member = (
        db.query(GroupMember)
        .filter(
            GroupMember.conversation_id == conversation_id,
            GroupMember.username == current_user.username,
        )
        .first()
    )
    if not is_member:
        raise HTTPException(status_code=403, detail="Bạn không thuộc nhóm này")

    # Lấy tin nhắn kèm thông tin người gửi
    messages = (
        db.query(Message, User)
        .join(User, Message.sender_id == User.user_id)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Lấy danh sách file đính kèm theo từng tin nhắn
    message_list = []
    for msg, sender in messages:
        attachments = (
            db.query(Attachment).filter(Attachment.message_id == msg.message_id).all()
        )
        message_list.append(
            {
                "message_id": msg.message_id,
                "sender_id": msg.sender_id,
                "sender_username": sender.username,
                "sender_nickname": sender.nickname,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "is_read": msg.is_read,
                "attachments": [
                    {"file_url": att.file_url, "file_type": att.file_type}
                    for att in attachments
                ],
            }
        )

    return {"messages": message_list, "limit": limit, "offset": offset}


# API xóa tin nhắn
@messages_router.put(
    "/delete/{message_id}",
    dependencies=[Depends(update_last_active_dependency)],
)
async def delete_message(
    message_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Lấy tin nhắn từ cơ sở dữ liệu
    message = db.query(Message).filter(Message.message_id == message_id).first()

    if not message:
        raise HTTPException(status_code=404, detail="Tin nhắn không tồn tại")

    # Kiểm tra xem người gửi có phải là người dùng hiện tại không
    if message.sender_id != current_user.user_id:
        raise HTTPException(
            status_code=403, detail="Bạn không có quyền xóa tin nhắn này"
        )

    # Lấy danh sách các file đính kèm từ cơ sở dữ liệu
    attachments = db.query(Attachment).filter(Attachment.message_id == message_id).all()

    # Xóa các file đính kèm
    for attachment in attachments:
        file_path = os.path.join(
            CONVERSATION_ATTACHMENTS_DIR, attachment.file_url.lstrip("/")
        )  # Lấy đường dẫn đầy đủ của file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)  # Xóa file
            except Exception as e:
                print(f"Lỗi khi xóa file: {e}")

        # Xóa thông tin file trong bảng Attachment
        db.delete(attachment)

    message.content = f"Tin nhắn đã bị xóa bởi {current_user.nickname}"
    db.commit()

    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_id == message.conversation_id)
        .first()
    )

    if conversation:
        members = (
            db.query(GroupMember.username)
            .filter(GroupMember.conversation_id == conversation.conversation_id)
            .all()
        )
        for member in members:
            notification_message = json.dumps(
                {
                    "type": "message_deleted",
                    "message_id": message_id,
                    "content": f"Tin nhắn đã bị xóa bởi {current_user.nickname}.",
                }
            )
            await websocket_manager.send_message(notification_message, "user")

    # Trả về thông báo thành công
    return {
        "message": "Tin nhắn và file đính kèm đã được xóa",
        "message_id": message_id,
    }


@messages_router.delete(
    "/{conversation_id}/clear",
    dependencies=[Depends(update_last_active_dependency)],
)
async def clear_conversation(
    conversation_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Cuộc hội thoại không tồn tại")

    is_member = (
        db.query(GroupMember)
        .filter(
            GroupMember.conversation_id == conversation_id,
            GroupMember.username == current_user.username,
        )
        .first()
    )
    if not is_member:
        raise HTTPException(status_code=403, detail="Bạn không thuộc nhóm này")

    messages = (
        db.query(Message).filter(Message.conversation_id == conversation_id).all()
    )

    for message in messages:
        attachments = (
            db.query(Attachment)
            .filter(Attachment.message_id == message.message_id)
            .all()
        )

        # Xóa các file đính kèm
        for attachment in attachments:
            file_path = os.path.join(
                CONVERSATION_ATTACHMENTS_DIR, attachment.file_url.lstrip("/")
            )
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)  # Xóa file
                except Exception as e:
                    print(f"Lỗi khi xóa file: {e}")

            # Xóa thông tin file trong bảng Attachment
            db.delete(attachment)

        # Xóa tin nhắn
        db.delete(message)

    db.commit()

    # Trả về thông báo thành công
    return {"message": "Tất cả tin nhắn và file đính kèm đã được xóa thành công"}


@messages_router.put("/mark-read/{message_id}")
async def mark_message_as_read(
    message_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Tìm tin nhắn trong cơ sở dữ liệu
    message = db.query(Message).filter(Message.message_id == message_id).first()

    if not message:
        raise HTTPException(status_code=404, detail="Tin nhắn không tồn tại")

    # Kiểm tra xem người dùng có phải là thành viên của cuộc trò chuyện không
    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_id == message.conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Cuộc hội thoại không tồn tại")

    is_member = (
        db.query(GroupMember)
        .filter(
            GroupMember.conversation_id == message.conversation_id,
            GroupMember.username == current_user.username,
        )
        .first()
    )

    if not is_member:
        raise HTTPException(
            status_code=403, detail="Bạn không phải là thành viên của nhóm này"
        )

    # Cập nhật trạng thái is_read của tin nhắn
    message.is_read = True
    db.commit()

    # Trả về kết quả thành công
    return {"message": "Tin nhắn đã được đánh dấu là đã đọc"}
