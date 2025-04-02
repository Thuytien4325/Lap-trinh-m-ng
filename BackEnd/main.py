from datetime import datetime

from database import SessionLocal
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from models import User
from routers.admin import admin_router
from routers.auth import auth_router
from routers.conversations import conversation_router
from routers.friends import friends_router
from routers.friends_requests import friend_request_router
from routers.messages import messages_router
from routers.notifications import notifications_router
from routers.untils import pwd_context
from routers.users import users_router
from routers.websocket import websocket_manager


def create_default_admin():
    """Kiểm tra nếu chưa có Admin, tự động tạo một Admin mặc định."""
    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.is_admin == True).first()

        if not existing_admin:
            hashed_password = pwd_context.hash("Admin1234@")  # Đổi mật khẩu nếu muốn
            new_admin = User(
                username="admin",
                nickname="Admin",
                email="appchat.noreply@gmail.com",
                password_hash=hashed_password,
                is_admin=True,
                last_active_UTC=datetime.utcnow(),
                created_at_UTC=datetime.utcnow(),
            )
            db.add(new_admin)
            db.commit()
            print(
                "🔹 Admin mặc định đã được tạo! Đăng nhập với: username='admin', password='Admin1234@'"
            )
        else:
            print("Đã tồn tại Admin trong hệ thống.")
    except Exception as e:
        print(f"Lỗi khi kiểm tra/tạo Admin: {e}")
    finally:
        db.close()


# 💡 Gọi hàm ngay khi ứng dụng khởi động
create_default_admin()

app = FastAPI()

# Thêm middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thêm router
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(conversation_router)
app.include_router(messages_router)
app.include_router(friend_request_router)
app.include_router(friends_router)
app.include_router(notifications_router)
app.include_router(admin_router)


# WebSocket Endpoint
@app.websocket("/ws/{user_type}/{username}")
async def websocket_endpoint(websocket: WebSocket, user_type: str, username: str):
    """Endpoint WebSocket để kết nối user hoặc admin"""
    await websocket_manager.connect(websocket, user_type, username)
    try:
        while True:
            await websocket.receive_text()  # Lắng nghe tin nhắn (không làm gì)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, user_type, username)


@app.get("/ws/active-connections")
async def get_active_connections():
    """Trả về danh sách các kết nối WebSocket đang hoạt động"""
    active_users = list(websocket_manager.active_connections["user"].keys())
    active_admins = len(websocket_manager.active_connections["admin"])  # Đếm số admin

    return JSONResponse(
        content={
            "active_users": active_users,
            "active_admins": active_admins,
        }
    )


# Cho phép truy cập file tĩnh (uploads)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Chạy ứng dụng
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, reload=True)
