from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from routers import messages
from models import Conversation
from datetime import datetime
import webbrowser
import os
import uvicorn
import socket

app = FastAPI()
app.mount("/static/uploads", StaticFiles(directory="static/uploads"), name="uploads")

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Tạo bảng nếu chưa có
Base.metadata.create_all(bind=engine)

# Thêm router messages
app.include_router(messages.message_router)

# Phục vụ file tĩnh với Cache-Control để tắt cache
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/static/{filename}")
async def get_static_file(filename: str):
    """Tắt cache file tĩnh"""
    file_path = os.path.join("static", filename)
    return FileResponse(file_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

# Trả về giao diện HTML
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
    timestamp = datetime.utcnow().timestamp()
    content = content.replace("styles.css", f"styles.css?v={timestamp}").replace("script.js", f"script.js?v={timestamp}")
    return content

# Thêm một conversation mẫu khi khởi động
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    if not db.query(Conversation).first():
        db.add(Conversation(name="private"))
        db.commit()
    db.close()

# Lấy địa chỉ IP của máy
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

# Mở trình duyệt khi khởi động
@app.on_event("startup")
async def open_browser():
    ip = get_local_ip()
    print(f"Server running at http://{ip}:8000")
    webbrowser.open(f"http://{ip}:8000")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)