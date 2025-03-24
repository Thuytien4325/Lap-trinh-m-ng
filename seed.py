# seed.py
from sqlalchemy.orm import Session
from database import SessionLocal
import models

def seed_data():
    db = SessionLocal()
    try:
        # Thêm user
        user1 = models.User(user_id=1, username="user1", email="user1@example.com", hashed_password="fakehashedpassword")
        user2 = models.User(user_id=2, username="user2", email="user2@example.com", hashed_password="fakehashedpassword")
        db.add(user1)
        db.add(user2)

        # Thêm conversation
        conversation = models.Conversation(conversation_id=1, name="private")
        db.add(conversation)

        # Thêm group members
        member1 = models.GroupMember(conversation_id=1, user_id=1)
        member2 = models.GroupMember(conversation_id=1, user_id=2)
        db.add(member1)
        db.add(member2)

        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
    print("Dữ liệu mẫu đã được thêm vào database!")