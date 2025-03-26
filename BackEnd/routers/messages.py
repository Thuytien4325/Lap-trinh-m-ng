from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
)
from sqlalchemy.orm import Session
import models
from database import get_db
from routers.untils import get_current_user, UPLOAD_DIR
from datetime import datetime
import json
import os
from schemas import MessageResponse, MessageCreate

message_router = APIRouter(prefix="/messages", tags=["Messages"])


# API gửi tin nhắn
@message_router.post("/send", response_model=MessageResponse)
def send_message(
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    conversation = (
        db.query(models.Conversation)
        .filter(models.Conversation.conversation_id == message.conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    member = (
        db.query(models.GroupMember)
        .filter(
            models.GroupMember.conversation_id == message.conversation_id,
            models.GroupMember.user_id == current_user.user_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="User not in this conversation")

    new_message = models.Message(
        conversation_id=message.conversation_id,
        sender_id=current_user.user_id,
        content=message.content,
        file_url=message.file_url,
        sent_at=datetime.utcnow(),
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return new_message


# API lấy tin nhắn theo cuộc hội thoại
@message_router.get("/{conversation_id}", response_model=list[MessageResponse])
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
@message_router.delete("/{message_id}")
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


# API tải lên file
@message_router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())

    return {"file_url": f"/static/uploads/{file.filename}"}


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


@message_router.websocket("/ws/{conversation_id}")
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
