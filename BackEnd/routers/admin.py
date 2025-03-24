from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User
from routers.untils import get_current_admin

# Tạo router cho admin
admin_router = APIRouter(prefix="/admin", tags=["Admin"])

@admin_router.get("/users")
def get_all_users(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    users = db.query(User).all()
    return users