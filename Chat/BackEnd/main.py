from fastapi import FastAPI
from auth import router as auth_router

app = FastAPI()

# Thêm router xác thực
app.include_router(auth_router)

@app.get("/")
def home():
    return {"message": "API is running"}
