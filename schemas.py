# schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MessageResponse(BaseModel):
    message_id: int
    conversation_id: int
    sender_id: int
    content: Optional[str] = None
    file_url: Optional[str] = None
    sent_at: datetime

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    conversation_id: int
    content: Optional[str] = None
    file_url: Optional[str] = None