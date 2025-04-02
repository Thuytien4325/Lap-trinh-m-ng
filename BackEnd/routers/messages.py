import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import List

import models
from database import get_db
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from models import Attachment, Conversation, GroupMember, Message
from routers.untils import CONVERSATION_ATTACHMENTS_DIR, get_current_user
from sqlalchemy.orm import Session

messages_router = APIRouter(prefix="/messages", tags=["Messages"])


@messages_router.post("/")
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

    # Trả về kết quả
    return {
        "message": "Gửi tin nhắn thành công",
        "message_id": new_message.message_id,
        "content": new_message.content,
        "files": file_urls,
    }


# API lấy tin nhắn theo cuộc hội thoại
@messages_router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    limit: int = Query(20, ge=1, le=100),  # Số tin nhắn mỗi lần load (tối đa 100)
    offset: int = Query(0, ge=0),  # Vị trí bắt đầu lấy tin nhắn
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

    # Lấy tin nhắn theo thứ tự thời gian (cũ nhất -> mới nhất)
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp.asc())  # Sắp xếp từ cũ đến mới
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Lấy danh sách file đính kèm theo từng tin nhắn
    message_list = []
    for msg in messages:
        attachments = (
            db.query(Attachment).filter(Attachment.message_id == msg.message_id).all()
        )
        message_list.append(
            {
                "message_id": msg.message_id,
                "sender_id": msg.sender_id,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "attachments": [
                    {"file_url": att.file_url, "file_type": att.file_type}
                    for att in attachments
                ],
            }
        )

    return {"messages": message_list, "limit": limit, "offset": offset}


# API xóa tin nhắn
@messages_router.put("/delete/{message_id}")
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

    # Cập nhật nội dung tin nhắn thành null
    message.content = f"Tin nhắn đã bị xóa bởi {current_user.username}"
    db.commit()

    # Trả về thông báo thành công
    return {
        "message": "Tin nhắn và file đính kèm đã được xóa",
        "message_id": message_id,
    }
