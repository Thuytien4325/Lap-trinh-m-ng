from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Text, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    avatar = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    type = Column(Enum("private", "group", name="conversation_type"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

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
    sender_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    content = Column(Text, nullable=True)
    message_type = Column(Enum("text", "image", "video", "file", name="message_type"), default="text")
    sent_at = Column(TIMESTAMP, server_default=func.now())

class Attachment(Base):
    __tablename__ = "attachments"

    attachment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.message_id", ondelete="CASCADE"))
    file_url = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    uploaded_at = Column(TIMESTAMP, server_default=func.now())
