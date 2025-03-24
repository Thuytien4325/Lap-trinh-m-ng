from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from database import SessionLocal
from models import User
from routers.untils import pwd_context
from routers.auth import auth_router
from routers.users import users_router
from routers.messages import message_router
from routers.friends_requests import friend_request_router
from routers.friends import friends_router
from routers.notifications import notifications_router
from routers.admin import admin_router

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
                created_at=datetime.utcnow()
            )
            db.add(new_admin)
            db.commit()
            print("🔹 Admin mặc định đã được tạo! Đăng nhập với: username='admin', password='Admin1234@'")
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
app.include_router(message_router)
app.include_router(friend_request_router)
app.include_router(friends_router)
app.include_router(notifications_router)
app.include_router(admin_router)

# Cho phép truy cập file tĩnh (uploads)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Chạy ứng dụng
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,reload=True)
