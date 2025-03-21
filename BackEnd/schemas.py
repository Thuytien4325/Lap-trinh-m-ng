from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
import re

# Schema xác thực người dùng
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    nickname: str | None
    email: str
    password: str = Field(..., min_length=8)

    @validator("password")
    def validate_password(cls, value):
        if not any(c.isalpha() for c in value):
            raise ValueError("Mật khẩu phải chứa ít nhất một chữ cái.")
        if not any(c.isdigit() for c in value):
            raise ValueError("Mật khẩu phải chứa ít nhất một số.")
        if not any(c in "@$!%*?&" for c in value):
            raise ValueError("Mật khẩu phải chứa ít nhất một ký tự đặc biệt (@$!%*?&).")
        return value
    
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

# Schema gửi kết bạn
class FriendRequestCreate(BaseModel):
    receiver_username: str  # Chỉ cần nhập username người nhận

class FriendRequestResponse(BaseModel):
    id: int
    sender_username: str
    receiver_username: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True