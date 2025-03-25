from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Text, TIMESTAMP, UniqueConstraint, CheckConstraint, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.dialects.mysql import CHAR
import hashlib
import uuid
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    nickname = Column(String(255), nullable=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    avatar = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False)
    last_active_UTC = Column(DateTime(timezone=True), default=None)
    created_at_UTC = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sent_messages = relationship("Message", foreign_keys="[Message.sender_id]", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="[Message.receiver_id]", back_populates="receiver")
    notifications = relationship("Notification", back_populates="user", foreign_keys="[Notification.user_username]")
    reset_tokens = relationship("ResetToken", back_populates="user", cascade="all, delete-orphan")
    
class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    type = Column(Enum("private", "group", name="conversation_type"), nullable=False)
    created_at_UTC = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("GroupMember", backref="conversation")
    messages = relationship("Message", backref="conversation", cascade="all, delete-orphan")

class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    role = Column(Enum("admin", "member", name="group_role"), default="member")
    joined_at_UTC = Column(DateTime(timezone=True), server_default=func.now())

class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id", ondelete="CASCADE"))
    sender_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))
    receiver_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))
    content = Column(Text, nullable=True)
    message_type = Column(Enum("text", "image", "video", "file", name="message_type"), default="text")
    sent_at_UTC = Column(DateTime(timezone=True), server_default=func.now())

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")

    __table_args__ = (
        CheckConstraint("message_type IN ('text', 'image', 'video', 'file')", name="valid_message_type"),
    )

class Attachment(Base):
    __tablename__ = "attachments"

    attachment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.message_id", ondelete="CASCADE"))
    file_url = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    uploaded_at_UTC = Column(DateTime(timezone=True), server_default=func.now())

class FriendRequest(Base):
    __tablename__ = "friend_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sender_username = Column(String(50), ForeignKey("users.username", ondelete="CASCADE"), nullable=False)
    receiver_username = Column(String(50), ForeignKey("users.username", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum("Đợi", "Chấp nhận", "Từ chối", name="friend_request_status"), default="Đợi", index=True)
    created_at_UTC = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint('sender_username', 'receiver_username', name='unique_friend_request'),)

class Friend(Base):
    __tablename__ = "friends"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_username = Column(String(50), ForeignKey("users.username", ondelete="CASCADE"), nullable=False)
    friend_username = Column(String(50), ForeignKey("users.username", ondelete="CASCADE"), nullable=False)
    created_at_UTC = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_username', 'friend_username', name='unique_friendship'),
        CheckConstraint('user_username != friend_username', name='no_self_friendship')
    )

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_username = Column(String(255), ForeignKey("users.username", ondelete="CASCADE"), index=True)
    sender_username = Column(String(255), ForeignKey("users.username", ondelete="SET NULL"), nullable=True)
    message = Column(String(255), nullable=False)
    type = Column(Enum("friend_request", "friend_accept","friend_reject", "message", name="notification_type"), nullable=False, index=True)
    related_id = Column(Integer, nullable=True, index=True)
    related_table = Column(Enum("friend_requests", "messages", name="related_table_type"), nullable=True, index=True)
    is_read = Column(Boolean, default=False, index=True)
    created_at_UTC = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications", foreign_keys=[user_username])
    sender = relationship("User", foreign_keys=[sender_username], lazy="joined")

class ResetToken(Base):
    __tablename__ = "reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    reset_uuid = Column(CHAR(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    token_hash = Column(String(255), nullable=False)
    expires_at_UTC = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="reset_tokens")

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()