from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer
from auth import router as auth_router

app = FastAPI()

# Định nghĩa Bearer Token để Swagger UI hiển thị
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app.include_router(auth_router)

@app.get("/")
def home():
    return {"message": "API is running"}

