from datetime import datetime
from typing import List, Optional, Union

from pydantic import UUID4, BaseModel, EmailStr, Field, validator


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


# Schema reset mật khẩu
class ResetPasswordConfirm(BaseModel):
    reset_uuid: UUID4
    new_password: str

    @validator("new_password")
    def validate_new_password(cls, value):
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
    last_active_UTC: datetime | None
    created_at_UTC: datetime | None

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    username: str
    nickname: str | None
    email: EmailStr
    avatar: str | None
    last_active_UTC: datetime | None
    created_at_UTC: datetime | None

    class Config:
        from_attributes = True


class UserWithFriendStatus(BaseModel):
    username: str
    nickname: Optional[str]
    email: Optional[str]
    avatar: Optional[str]
    created_at_UTC: datetime
    last_active_UTC: Optional[datetime]
    status: str


# Schema admin trả về thông tin người dùng
class AdminUserResponse(BaseModel):
    user_id: int
    username: str
    nickname: str | None
    email: EmailStr
    avatar: str | None
    last_active_UTC: datetime | None
    created_at_UTC: datetime | None

    class Config:
        from_attributes = True


# Schema token
class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    access_token_time: str
    refresh_token_time: str
    user: UserResponse | None


# Schema tin nhắn


class MessageResponse(BaseModel):
    message_id: int
    conversation_id: int
    sender_id: int
    content: str
    sent_at_UTC: datetime

    class Config:
        from_attributes = True


# Schema gửi kết bạn


class FriendRequestResponse(BaseModel):
    id: int
    sender_username: str
    receiver_username: str
    sender_nickname: str | None
    sender_avatar: str | None
    receiver_nickname: str | None
    receiver_avatar: str | None
    status: str
    created_at_UTC: datetime | None

    class Config:
        from_attributes = True


#  Schema friend
class FriendResponse(BaseModel):
    username: str
    nickname: str | None = None
    avatar: str | None = None

    class Config:
        from_attributes = True


# Thông báo
class NotificationBase(BaseModel):
    message: str


class NotificationCreate(NotificationBase):
    user_username: str
    sender_username: str
    type: str
    related_id: int
    related_table: str


class NotificationResponse(BaseModel):
    id: int
    user_username: str
    sender_username: str | None
    message: str
    type: str
    related_id: int
    related_table: str | None
    is_read: bool
    created_at_UTC: datetime | None

    class Config:
        from_attributes = True


# Schema cho tạo cuộc hội thoại
class ConversationCreate(BaseModel):
    type: str  # "private" hoặc "group"
    username: Optional[Union[str, List[str]]] = Field(
        default=None
    )  # Chuỗi nếu private, danh sách nếu group
    name: Optional[str] = None  # Tên nhóm, chỉ dùng cho group

    class Config:
        from_attributes = True


# Schema cho thành viên nhóm
class GroupMemberResponse(BaseModel):
    username: str
    nickname: str | None = None
    avatar: str | None = None
    role: str


# Schema cho phản hồi cuộc hội thoại
class ConversationResponse(BaseModel):
    conversation_id: int
    type: str
    name: str | None = None
    avatar_url: str | None = None
    created_at_UTC: datetime | None
    last_message_time: datetime | None = None
    group_members: Optional[List[GroupMemberResponse]] = []

    class Config:
        from_attributes = True
