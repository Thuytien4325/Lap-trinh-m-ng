# auth.py
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models

def get_current_user(db: Session = Depends(get_db)):
    # Giả lập user_id=1 (thay bằng xác thực thật nếu cần)
    user = db.query(models.User).filter(models.User.user_id == 1).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user