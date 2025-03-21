from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine
import models
from routers.auth import auth_router
from routers.users import users_router
from routers.messages import message_router
from routers.friends_requests import friend_request_router
app = FastAPI()

# Thêm middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tạo bảng nếu chưa có
models.Base.metadata.create_all(bind=engine)

# Thêm router
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(message_router)
app.include_router(friend_request_router)

# Cho phép truy cập file tĩnh (uploads)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Chạy ứng dụng
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,reload=True)
