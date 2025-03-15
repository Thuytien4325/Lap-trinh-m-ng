from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer
from auth import router as auth_router

app = FastAPI()

# OAuth2PasswordBearer yêu cầu đường dẫn cho tokenUrl chính xác
# Đảm bảo token được lấy từ Authorization header theo định dạng Bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Thêm router auth vào ứng dụng
app.include_router(auth_router)

@app.get("/")
def home():
    return {"message": "API is running"}
