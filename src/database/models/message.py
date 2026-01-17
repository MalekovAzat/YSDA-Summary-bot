from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database.database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False)
    from_id = Column(BigInteger, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    reply_to = Column(BigInteger, ForeignKey("messages.id"), nullable=True)
    link_in_chat= Column(String, nullable=False)
    from_name = Column(String)

    # связи
    chat = relationship("Chat", back_populates="messages")
    reply = relationship("Message", remote_side=[id], uselist=False)