from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
from database import get_db
from auth import get_current_user
from pydantic import BaseModel

conversation_router = APIRouter(prefix="/conversations", tags=["Conversations"])

# Schema cho cuộc hội thoại
class ConversationCreate(BaseModel):
    name: str

class ConversationResponse(BaseModel):
    conversation_id: int
    name: str

# API tạo hội thoại mới (hỗ trợ group chat)
@conversation_router.post("/", response_model=ConversationResponse)
def create_conversation(conversation: ConversationCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    new_conversation = models.Conversation(name=conversation.name)
    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)
    return new_conversation

# API lấy danh sách hội thoại của user
@conversation_router.get("/", response_model=list[ConversationResponse])
def get_conversations(db: Session = Depends(get_db)):
    conversations = db.query(models.Conversation).all()
    return conversations
