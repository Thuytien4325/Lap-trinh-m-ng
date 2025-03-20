# routers/messages.py
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import models
from database import get_db
from auth import get_current_user
from pydantic import BaseModel
from datetime import datetime
import json
from schemas import MessageResponse, MessageCreate


message_router = APIRouter(prefix="/messages", tags=["Messages"])

# Schema để gửi tin nhắn (đã được định nghĩa trong schemas.py, không cần định nghĩa lại ở đây)

# API gửi tin nhắn
@message_router.post("/send", response_model=MessageResponse)
def send_message(message: MessageCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    conversation = db.query(models.Conversation).filter(models.Conversation.conversation_id == message.conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    new_message = models.Message(
        conversation_id=message.conversation_id,
        sender_id=current_user.user_id,
        content=message.content,
        sent_at=datetime.utcnow()
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return new_message  # Trả về toàn bộ thông tin tin nhắn

# API lấy tin nhắn theo cuộc hội thoại
@message_router.get("/{conversation_id}", response_model=list[MessageResponse])
def get_messages(conversation_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    messages = db.query(models.Message).filter(models.Message.conversation_id == conversation_id).order_by(models.Message.sent_at).all()
    return messages

# API xóa tin nhắn
@message_router.delete("/{message_id}")
def delete_message(message_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    message = db.query(models.Message).filter(models.Message.message_id == message_id, models.Message.sender_id == current_user.user_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found or unauthorized")

    db.delete(message)
    db.commit()
    
    return {"message": "Message deleted successfully"}

# WebSocket để chat thời gian thực
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@message_router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            content = message_data.get("content")

            new_message = models.Message(
                conversation_id=conversation_id,
                sender_id=current_user.user_id,
                content=content,
                sent_at=datetime.utcnow()
            )

            db.add(new_message)
            db.commit()
            db.refresh(new_message)

            message_json = json.dumps({
                "message_id": new_message.message_id,
                "sender_id": new_message.sender_id,
                "content": new_message.content,
                "sent_at": new_message.sent_at.isoformat()
            })

            await manager.broadcast(message_json)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
