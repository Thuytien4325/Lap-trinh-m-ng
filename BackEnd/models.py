from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Text, TIMESTAMP, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    nickname = Column(String(255), nullable=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    avatar = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)

    messages = relationship("Message", backref="sender", cascade="all, delete-orphan")
    group_memberships = relationship("GroupMember", backref="user", cascade="all, delete-orphan")
    created_conversations = relationship("Conversation", backref="creator")

class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    type = Column(Enum("private", "group", name="conversation_type"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    creator_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

    members = relationship("GroupMember", backref="conversation")
    messages = relationship("Message", backref="conversation", cascade="all, delete-orphan")  # Thêm quan hệ ORM

class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    role = Column(Enum("admin", "member", name="group_role"), default="member")
    joined_at = Column(TIMESTAMP, server_default=func.now())

class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id", ondelete="CASCADE"))
    sender_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"))
    content = Column(Text, nullable=True)
    message_type = Column(Enum("text", "image", "video", "file", name="message_type"), default="text")
    sent_at = Column(TIMESTAMP, server_default=func.now())

    attachments = relationship("Attachment", backref="message", cascade="all, delete-orphan")  # Thêm quan hệ ORM

    __table_args__ = (
        CheckConstraint("message_type IN ('text', 'image', 'video', 'file')", name="valid_message_type"),
    )

class Attachment(Base):
    __tablename__ = "attachments"

    attachment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.message_id", ondelete="CASCADE"))
    file_url = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    uploaded_at = Column(TIMESTAMP, server_default=func.now())

class FriendRequest(Base):
    __tablename__ = "friend_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sender_username = Column(String(50), ForeignKey("users.username", ondelete="CASCADE"), nullable=False)
    receiver_username = Column(String(50), ForeignKey("users.username", ondelete="CASCADE"), nullable=False)
    status = Column(Enum("Đợi", "Chấp nhận", "Từ chối", name="friend_request_status"), default="Đợi")
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (UniqueConstraint('sender_username', 'receiver_username', name='unique_friend_request'),)

class Friend(Base):
    __tablename__ = "friends"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_username = Column(String(50), ForeignKey("users.username", ondelete="CASCADE"), nullable=False)
    friend_username = Column(String(50), ForeignKey("users.username", ondelete="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_username', 'friend_username', name='unique_friendship'),
        CheckConstraint('user_username != friend_username', name='no_self_friendship')
    )