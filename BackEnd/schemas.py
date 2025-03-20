from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

# Schema xác thực người dùng
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    nickname: str | None
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)

class TokenSchema(BaseModel):
    access_token: str
    token_type: str

# Schema người dùng
class UserResponse(BaseModel):
    user_id: int
    username: str
    nickname: str | None
    email: EmailStr
    avatar: str | None
    created_at: datetime

    class Config:
        from_attributes = True 

class UserUpdate(BaseModel):
    nickname: str | None = None
    email: EmailStr | None = None

# Schema tin nhắn
class MessageCreate(BaseModel):
    conversation_id: int
    content: str

class MessageResponse(BaseModel):
    message_id: int
    conversation_id: int
    sender_id: int
    content: str
    sent_at: datetime

    class Config:
        from_attributes = True
