from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
from database import get_db
from auth import get_current_user
from pydantic import BaseModel
from datetime import datetime

message_router = APIRouter(prefix="/messages", tags=["Messages"])

class MessageCreate(BaseModel):
    conversation_id: int
    content: str

@message_router.post("/send")
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

    return {"message": "Message sent successfully", "message_id": new_message.message_id}

@message_router.get("/{conversation_id}")
def get_messages(conversation_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    messages = db.query(models.Message).filter(models.Message.conversation_id == conversation_id).order_by(models.Message.sent_at).all()
    
    return [{"message_id": msg.message_id, "sender_id": msg.sender_id, "content": msg.content, "sent_at": msg.sent_at} for msg in messages]

@message_router.delete("/{message_id}")
def delete_message(message_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    message = db.query(models.Message).filter(models.Message.message_id == message_id, models.Message.sender_id == current_user.user_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found or unauthorized")

    db.delete(message)
    db.commit()
    
    return {"message": "Message deleted successfully"}