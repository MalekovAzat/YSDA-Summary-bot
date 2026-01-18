from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pgInsert

from src.database.models.chat import Chat
from src.database.models.message import Message


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- ЧАТЫ ----------

    async def get_chat(self, chat_id: int) -> Optional[Chat]:
        result = await self.db.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_chat(
        self,
        chat_id: int,
        title: str | None,
        chat_type: str,
    ) -> Chat:
        chat_obj = await self.get_chat(chat_id)

        if not chat_obj:
            chat_obj = Chat(
                id=chat_id,
                title=title or "Без названия",
                is_admin=False,
                type=chat_type,
            )
            self.db.add(chat_obj)
            await self.db.commit()
            await self.db.refresh(chat_obj)

        return chat_obj

    async def set_admin_status(self, chat_id: int, is_admin: bool) -> None:
        chat_obj = await self.get_chat(chat_id)
        if not chat_obj:
            return

        chat_obj.is_admin = is_admin
        await self.db.commit()

    # ---------- СООБЩЕНИЯ ----------

    async def get_messages_for_day(
        self,
        chat_id: int,
        bot_id: int,
        date_from: datetime,
        date_to: datetime,
        limit: int | None = None,
    ) -> List[Message]:
        stmt = (
            select(Message)
            .where(
                Message.chat_id == chat_id,
                Message.from_id != bot_id,
                Message.created_at >= date_from,
                Message.created_at < date_to,
            )
            .order_by(Message.created_at.asc())
        )

        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def save_message(
        self,
        message_id: int,
        chat_id: int,
        from_id: int,
        text: str | None,
        link_in_chat: str | None,
        from_name: str | None,
    ) -> None:
        chat_message = Message(
            id=message_id,
            chat_id=chat_id,
            from_id=from_id,
            text=text,
            link_in_chat=link_in_chat,
            from_name=from_name,
        )

        self.db.add(chat_message)
        await self.db.commit()
    
    async def save_history(self, messages: list[Message]) -> None:
        if not messages:
            return

        values = [
            {
                "id": m.id,
                "chat_id": m.chat_id,
                
                "from_id": m.from_id,
                "text": m.text,
                "created_at": m.created_at,
                "link_in_chat": m.link_in_chat,
                "from_name": m.from_name,
            }
            for m in messages
        ]

        stmt = (
            pgInsert(Message)
            .values(values)
            .on_conflict_do_nothing(
                index_elements=["id", "chat_id"]
            )
        )

        await self.db.execute(stmt)
        await self.db.commit()