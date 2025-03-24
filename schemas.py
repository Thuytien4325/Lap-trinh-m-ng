# schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MessageCreate(BaseModel):
    conversation_id: int
    content: Optional[str] = None
    file_url: Optional[str] = None

class MessageResponse(BaseModel):
    message_id: int
    conversation_id: int
    sender_id: int
    content: Optional[str]
    file_url: Optional[str]
    sent_at: datetime

    class Config:
        from_attributes = True  # Thay orm_mode thành from_attributes

class ConversationCreate(BaseModel):
    name: str

class ConversationResponse(BaseModel):
    conversation_id: int
    name: str

    class Config:
        from_attributes = True  # Thay orm_mode thành from_attributes
