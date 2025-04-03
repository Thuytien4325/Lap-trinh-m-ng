import json
from datetime import datetime, timezone
from typing import List

from fastapi import WebSocket, WebSocketDisconnect


class WebSocketManager:
    def __init__(self):
        self.active_connections: dict[str, dict[str, WebSocket] | list[WebSocket]] = {
            "user": {},  # Lưu kết nối user theo username
            "admin": [],  # Lưu danh sách WebSocket của admin
        }

    async def connect(self, websocket: WebSocket, user_type: str, username: str = None):
        """Xử lý khi một user hoặc admin kết nối WebSocket"""
        await websocket.accept()
        if user_type == "user" and username:
            self.active_connections["user"][username] = websocket
        elif user_type == "admin":
            self.active_connections["admin"].append(websocket)

    def disconnect(self, websocket: WebSocket, user_type: str, username: str = None):
        """Xử lý khi một user hoặc admin mất kết nối"""
        if user_type == "user" and username:
            self.active_connections["user"].pop(username, None)
        elif user_type == "admin" and websocket in self.active_connections["admin"]:
            self.active_connections["admin"].remove(websocket)

    async def send_message(self, message: str, user_type: str):
        """Gửi tin nhắn đến đúng nhóm user hoặc admin"""
        if user_type in self.active_connections:
            if isinstance(
                self.active_connections[user_type], list
            ):  # Kiểm tra xem là danh sách WebSocket
                for connection in self.active_connections[user_type]:
                    try:
                        await connection.send_text(message)
                    except WebSocketDisconnect:
                        self.disconnect(connection, user_type)
            elif isinstance(
                self.active_connections[user_type], dict
            ):  # Kiểm tra kiểu từ 'user'
                for connection in self.active_connections[
                    user_type
                ].values():  # Duyệt qua các kết nối user theo username
                    try:
                        await connection.send_text(message)
                    except WebSocketDisconnect:
                        self.disconnect(connection, user_type)
            else:
                print(
                    f"Lỗi: active_connections[{user_type}] không phải là kiểu hợp lệ."
                )
        else:
            print(f"Lỗi: Không có kết nối cho loại người dùng '{user_type}'")

    async def notify_new_report(
        self,
        report_id: int,
        reporter_username: str,
        report_type: str,
        target_id: int = None,
        target_table: str = None,
        description: str = "",
        title: str = None,
        severity: str = None,
    ):
        """Gửi thông báo báo cáo mới đến admin"""
        message = json.dumps(
            {
                "report_id": report_id,
                "reporter_username": reporter_username,
                "report_type": report_type,
                "target_id": target_id,  # Dùng giá trị từ tham số
                "target_table": target_table,  # Dùng giá trị từ tham số
                "description": description,
                "title": title,
                "severity": severity,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        await self.send_message(message, "admin")

    async def send_notification(
        self,
        noti_id: int,
        user_username: str,
        sender_username: str,
        message: str,
        notification_type: str,
        related_id: int = None,
        related_table: str = None,
    ):
        """Gửi thông báo đến một user cụ thể hoặc đến admin nếu user_username == 'admin'"""
        notification_data = json.dumps(
            {
                "id": noti_id,
                "user_username": user_username,
                "sender_username": sender_username,
                "message": message,
                "type": notification_type,
                "related_id": related_id,
                "related_table": related_table,
                "created_at_UTC": datetime.now(timezone.utc).isoformat(),
            }
        )

        if user_username == "admin":
            # Gửi thông báo đến tất cả admin đang kết nối
            for admin_ws in self.active_connections["admin"]:
                try:
                    await admin_ws.send_text(notification_data)
                except WebSocketDisconnect:
                    self.active_connections["admin"].remove(admin_ws)
        else:
            # Gửi thông báo đến user cụ thể
            connection = self.active_connections["user"].get(user_username)
            if connection:
                try:
                    await connection.send_text(notification_data)
                except WebSocketDisconnect:
                    self.active_connections["user"].pop(user_username, None)

    async def send_chat_message(
        self, conversation_id: int, recipient_username: str, message_data: dict
    ):
        """Gửi tin nhắn real-time đến người nhận"""
        message = json.dumps(
            {
                "type": "new_message",
                "conversation_id": conversation_id,
                "message": message_data,
            }
        )

        connection = self.active_connections["user"].get(recipient_username)
        if connection:
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                self.disconnect(connection, "user", recipient_username)
        else:
            print(f"❌ Người nhận {recipient_username} không có kết nối WebSocket.")


websocket_manager = WebSocketManager()
