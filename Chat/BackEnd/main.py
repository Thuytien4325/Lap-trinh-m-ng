from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from routers import messages
from models import Conversation
import webbrowser
import uvicorn

app = FastAPI()

# Thêm middleware CORS
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

# Phục vụ file tĩnh (CSS, JS, favicon)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Trả về giao diện HTML
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# Thêm một conversation mẫu khi khởi động
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    if not db.query(Conversation).first():
        db.add(Conversation(name="private"))
        db.commit()
    db.close()

# Mở trình duyệt khi khởi động
@app.on_event("startup")
async def open_browser():
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
