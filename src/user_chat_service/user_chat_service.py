from sqlalchemy.future import select
from src.database.models.user_chats import UserChats
from src.database.database import AsyncSessionLocal
from sqlalchemy import select
from datetime import datetime

class UserChatService:
    def __init__(self):
        pass

    async def get_by_user_id(self, user_id: int):
        """Получить все UserChats для пользователя"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserChats).where(UserChats.user_id == user_id)
            )
            return result.scalars().all()

    async def get_by_chat_id(self, chat_id: int):
        """Получить всех участников чата"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserChats).where(UserChats.chat_id == chat_id)
            )
            return result.scalars().all()
        
    async def get_one(self, chat_id: int, user_id: int):
        """Получить одну запись UserChats для пользователя в чате"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserChats).where(
                    UserChats.chat_id == chat_id,
                    UserChats.user_id == user_id
                )
            )
            return result.scalar_one_or_none()  # вернет объект или None

    async def create(self, user_id: int, chat_id: int, role: str = None):
        """Добавить пользователя в чат"""
        async with AsyncSessionLocal() as session:
            user_chat = UserChats(
                user_id=user_id,
                chat_id=chat_id,
                role=role,
                created_at=datetime.utcnow()
            )
            session.add(user_chat)
            await session.commit()
            await session.refresh(user_chat)
            return user_chat

    async def get_or_create(self, user_id: int, chat_id: int, role: str = None):
        """Получить существующую запись или создать новую"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserChats).where(
                    UserChats.user_id == user_id,
                    UserChats.chat_id == chat_id
                )
            )
            user_chat = result.scalar_one_or_none()
            if user_chat:
                return user_chat
            # если нет, создаём новую
            user_chat = UserChats(
                user_id=user_id,
                chat_id=chat_id,
                role=role,
                created_at=datetime.utcnow()
            )
            session.add(user_chat)
            await session.commit()
            await session.refresh(user_chat)
            return user_chat

    async def remove(self, user_id: int, chat_id: int):
        """Удалить пользователя из чата"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserChats).where(
                    UserChats.user_id == user_id,
                    UserChats.chat_id == chat_id
                )
            )
            user_chat = result.scalar_one_or_none()
            if user_chat:
                await session.delete(user_chat)
                await session.commit()
                return True
            return False
