from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database.database import Base

class Chat(Base):
    __tablename__ = "chats"

    id = Column(BigInteger, primary_key=True)  # не автогенерируемый
    title = Column(String, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)
    type = Column(String, nullable=False)