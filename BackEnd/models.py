import hashlib
import uuid

from database import Base
from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


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
    created_at_UTC = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sent_messages = relationship(
        "Message", foreign_keys="[Message.sender_id]", back_populates="sender"
    )
    notifications = relationship(
        "Notification",
        back_populates="user",
        foreign_keys="[Notification.user_username]",
    )
    reset_tokens = relationship(
        "ResetToken", back_populates="user", cascade="all, delete-orphan"
    )


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    type = Column(Enum("private", "group", name="conversation_type"), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at_UTC = Column(DateTime(timezone=True), server_default=func.now())

    group_members = relationship("GroupMember", back_populates="conversation")


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.conversation_id", ondelete="CASCADE")
    )
    username = Column(String(255), ForeignKey("users.username", ondelete="CASCADE"))
    role = Column(Enum("admin", "member", name="group_role"), default="member")
    joined_at_UTC = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="group_members")
    conversation = relationship("Conversation", back_populates="group_members")


class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sender_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True
    )
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Boolean, default=False, nullable=False)

    sender = relationship(
        "User", foreign_keys=[sender_id], back_populates="sent_messages"
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
    sender_username = Column(
        String(50), ForeignKey("users.username", ondelete="CASCADE"), nullable=False
    )
    receiver_username = Column(
        String(50),
        ForeignKey("users.username", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum("Đợi", "Chấp nhận", "Từ chối", name="friend_request_status"),
        default="Đợi",
        index=True,
    )
    created_at_UTC = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "sender_username", "receiver_username", name="unique_friend_request"
        ),
    )


class Friend(Base):
    __tablename__ = "friends"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_username = Column(
        String(50), ForeignKey("users.username", ondelete="CASCADE"), nullable=False
    )
    friend_username = Column(
        String(50), ForeignKey("users.username", ondelete="CASCADE"), nullable=False
    )
    created_at_UTC = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_username", "friend_username", name="unique_friendship"),
        CheckConstraint("user_username != friend_username", name="no_self_friendship"),
    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_username = Column(
        String(255), ForeignKey("users.username", ondelete="CASCADE"), index=True
    )
    sender_username = Column(
        String(255), ForeignKey("users.username", ondelete="SET NULL"), nullable=True
    )
    message = Column(String(255), nullable=False)
    type = Column(
        Enum(
            "conversations",
            "friend_request",
            "friend_accept",
            "friend_reject",
            "message",
            "system",
            "report",
            "warning",
            name="notification_type",
        ),
        nullable=False,
        index=True,
    )
    related_id = Column(Integer, nullable=True, index=True)
    related_table = Column(
        Enum(
            "friend_requests",
            "messages",
            "conversations",
            "reports",
            "users",
            "warnings",
            name="related_table_type",
        ),
        nullable=True,
        index=True,
    )
    is_read = Column(Boolean, default=False, index=True)
    created_at_UTC = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship(
        "User", back_populates="notifications", foreign_keys=[user_username]
    )
    sender = relationship("User", foreign_keys=[sender_username], lazy="joined")


class ResetToken(Base):
    __tablename__ = "reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    reset_uuid = Column(
        CHAR(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False
    )
    token_hash = Column(String(255), nullable=False)
    expires_at_UTC = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="reset_tokens")

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()


class Report(Base):
    __tablename__ = "reports"

    report_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    reporter_username = Column(
        String(50), ForeignKey("users.username", ondelete="CASCADE"), nullable=True
    )
    report_type = Column(
        Enum("user", "group", "bug", name="report_type"), nullable=False, index=True
    )
    target_id = Column(Integer, nullable=True)
    target_table = Column(
        Enum("users", "conversations", name="report_target_table"),
        nullable=True,
        index=True,
    )
    description = Column(Text, nullable=False)
    status = Column(
        Enum("pending", "resolved", name="report_status"),
        default="pending",
        nullable=False,
        index=True,
    )
    created_at_UTC = Column(DateTime(timezone=True), server_default=func.now())
    updated_at_UTC = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    reporter = relationship("User", backref="reports")


class Warning(Base):
    __tablename__ = "warnings"

    warning_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    target_type = Column(Enum("users", "groups"), nullable=False)
    target_id = Column(Integer, nullable=True)
    reason = Column(Text, nullable=False)
    ban_duration = Column(Integer, default=0)
    ban_count = Column(Integer, default=1)
    created_at_UTC = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "ban_duration IN (0, 5, 15, 30, 60)", name="check_valid_ban_duration"
        ),
    )
