# models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "Users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="sender")
    conversations = relationship("Conversation", secondary="GroupMember", back_populates="members")

class Conversation(Base):
    __tablename__ = "Conversations"

    conversation_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="conversation")
    members = relationship("User", secondary="GroupMember", back_populates="conversations")

class GroupMember(Base):
    __tablename__ = "GroupMember"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("Conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("Users.user_id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "Messages"

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("Conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("Users.user_id", ondelete="CASCADE"), nullable=False)
    content = Column(Text)
    file_url = Column(String(255))
    sent_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", back_populates="messages")
