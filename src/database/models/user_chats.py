from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database.database import Base

class UserChats(Base):
    __tablename__ = "user_chats"

    id = Column(BigInteger, primary_key=True, autoincrement=True)  # автоинкремент
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False)
    role = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    title = Column(String)

    __table_args__ = (
        UniqueConstraint('user_id', 'chat_id', name='uq_user_chats_user_chat'),
    )