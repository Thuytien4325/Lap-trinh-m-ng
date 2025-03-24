from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Cấu hình kết nối MySQL
DATABASE_URL = "mysql+pymysql://ThuyTien:38632347tT%40@localhost:3306/chat_app"

# Tạo engine cho MySQL
engine = create_engine(DATABASE_URL)

# Tạo session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho các model
Base = declarative_base()

# Hàm để lấy session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
