import json
import os
import shutil
from datetime import datetime, timezone
from typing import List

import models
from database import get_db
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from models import Attachment, Conversation, GroupMember, Message
from routers.untils import CONVERSATION_ATTACHMENTS_DIR, get_current_user
from schemas import MessageResponse
from sqlalchemy.orm import Session

messages_router = APIRouter(prefix="/messages", tags=["Messages"])


@messages_router.post("/")
async def send_message(
    conversation_id: int,
    content: str | None = None,
    files: List[UploadFile] = File(None),
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

    # Tạo tin nhắn mới
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
        for file in files:
            file_extension = file.filename.split(".")[-1].lower()

            # Kiểm tra định dạng file
            allowed_extensions = ["jpg", "jpeg", "png", "pdf", "mp4", "mp3"]
            if file_extension not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Định dạng file {file_extension} không được hỗ trợ!",
                )

            # Tạo tên file và đường dẫn lưu trữ
            file_name = f"messageID_{new_message.message_id}.{file_extension}"
            file_path = os.path.join(conversation_dir, file_name)

            # Lưu file vào hệ thống tệp tin
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Lưu thông tin file vào bảng Attachment
            attachment = Attachment(
                message_id=new_message.message_id,
                file_url=f"/{file_path}",  # Đường dẫn file lưu trữ
                file_type=file.content_type,
            )
            db.add(attachment)
            file_urls.append(f"/{file_path}")

        db.commit()

    return {
        "message": "Gửi tin nhắn thành công",
        "message_id": new_message.message_id,
        "attachments": file_urls,
    }


# API lấy tin nhắn theo cuộc hội thoại
@messages_router.get("/{conversation_id}", response_model=list[MessageResponse])
def get_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    member = (
        db.query(models.GroupMember)
        .filter(
            models.GroupMember.conversation_id == conversation_id,
            models.GroupMember.user_id == current_user.user_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="User not in this conversation")

    messages = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.sent_at)
        .all()
    )
    return messages


# API xóa tin nhắn
@messages_router.delete("/{message_id}")
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    message = (
        db.query(models.Message)
        .filter(
            models.Message.message_id == message_id,
            models.Message.sender_id == current_user.user_id,
        )
        .first()
    )

    if not message:
        raise HTTPException(status_code=404, detail="Message not found or unauthorized")

    db.delete(message)
    db.commit()

    return {"message": "Message deleted successfully"}


# WebSocket để chat thời gian thực
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversation_id: int):
        await websocket.accept()
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(websocket)

    def disconnect(self, websocket: WebSocket, conversation_id: int):
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].remove(websocket)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]

    async def broadcast(self, message: dict, conversation_id: int):
        if conversation_id in self.active_connections:
            for connection in self.active_connections[conversation_id]:
                await connection.send_json(message)


manager = ConnectionManager()


@messages_router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    member = (
        db.query(models.GroupMember)
        .filter(
            models.GroupMember.conversation_id == conversation_id,
            models.GroupMember.user_id == current_user.user_id,
        )
        .first()
    )
    if not member:
        await websocket.close(code=1008, reason="User not in this conversation")
        return

    await manager.connect(websocket, conversation_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            content = message_data.get("content")
            file_url = message_data.get("file_url", None)

            new_message = models.Message(
                conversation_id=conversation_id,
                sender_id=current_user.user_id,
                content=content,
                file_url=file_url,
                sent_at=datetime.utcnow(),
            )

            db.add(new_message)
            db.commit()
            db.refresh(new_message)

            message_json = {
                "message_id": new_message.message_id,
                "sender_id": new_message.sender_id,
                "content": new_message.content,
                "file_url": new_message.file_url,
                "sent_at": new_message.sent_at.isoformat(),
            }

            await manager.broadcast(message_json, conversation_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, conversation_id)
