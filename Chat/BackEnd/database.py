import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base  # Import Base từ models

# Load biến môi trường từ .env
load_dotenv()

# Lấy URL database từ file .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Tạo engine kết nối MySQL
engine = create_engine(DATABASE_URL)

# Tạo session để làm việc với database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Hàm để lấy session trong API
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Tạo bảng trong database
def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    try:
        init_db()
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Database table creation failed: {e}")
