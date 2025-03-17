from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from auth import auth_router, users_router
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

app.include_router(auth_router)
app.include_router(users_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả domain (có thể thay đổi thành ["http://localhost:5500"])
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép tất cả phương thức (POST, GET, OPTIONS, v.v.)
    allow_headers=["*"],  # Cho phép tất cả headers
)

@app.get("/")
def home():
    return {"message": "API is running"}