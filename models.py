# models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    messages = relationship("Message", back_populates="sender")
    group_members = relationship("GroupMember", back_populates="user")

class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)

    messages = relationship("Message", back_populates="conversation")
    group_members = relationship("GroupMember", back_populates="conversation")

class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id"))
    user_id = Column(Integer, ForeignKey("users.user_id"))

    conversation = relationship("Conversation", back_populates="group_members")
    user = relationship("User", back_populates="group_members")

class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id"))
    sender_id = Column(Integer, ForeignKey("users.user_id"))
    content = Column(Text, nullable=True)
    file_url = Column(String, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", back_populates="messages")