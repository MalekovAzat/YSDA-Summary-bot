from sqlalchemy.future import select
from src.database.models.user import User
from src.database.database import AsyncSessionLocal

class UserService:
    def __init__(self):
        # Здесь можно хранить настройки, если нужно
        pass

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получить пользователя по telegram_id"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            return user

    async def create_user(self, telegram_id: int, first_name: str, last_name: str = None,
                          username: str = None, language_code: str = None) -> User:
        """Создать нового пользователя"""
        async with AsyncSessionLocal() as session:
            user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                language_code=language_code
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def get_or_create(self, telegram_id: int, first_name: str, last_name: str = None,
                            username: str = None, language_code: str = None) -> User:
        """Получить пользователя или создать, если не существует"""
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            return user
        return await self.create_user(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code=language_code
        )