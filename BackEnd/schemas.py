from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime

# Schema xác thực người dùng
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    nickname: str | None
    email: EmailStr
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

class UserProfile(BaseModel):
    username: str
    nickname: str | None
    email: EmailStr
    avatar: str | None
    created_at: datetime

    class Config:
        from_attributes = True 

class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse

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
    receiver_username: str

class FriendRequestResponse(BaseModel):
    id: int
    sender_username: str
    receiver_username: str
    sender_nickname: str | None 
    sender_avatar: str | None 
    receiver_nickname: str | None  
    receiver_avatar: str | None 
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
#  Schema friend
class FriendResponse(BaseModel):
    username: str
    nickname: str | None = None
    avatar: str | None = None

    class Config:
        from_attributes = True

class FriendRemoveRequest(BaseModel):
    friend_username: str

# Thông báo
class NotificationBase(BaseModel):
    message: str

class NotificationCreate(NotificationBase):
    user_username: str
    sender_username: str
    type: str
    related_id: int
    related_table: str

class NotificationResponse(NotificationBase):
    id: int 
    type: str 
    is_read: bool 
    created_at: datetime 
    related_id: int
    related_table: str


    class Config:
        from_attributes = True