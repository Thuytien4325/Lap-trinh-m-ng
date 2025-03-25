from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User
from routers.untils import get_admin_user
import schemas
from typing import List
# Tạo router cho admin
admin_router = APIRouter(prefix="/admin", tags=["Admin"])

@admin_router.get("/users",response_model=List[schemas.AdminUserResponse])
def get_all_users(db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    users = db.query(User).all()
    return users