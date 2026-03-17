from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from typing import AsyncGenerator

from app.config import settings
from app.models import Base

engine = create_async_engine(settings.db_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

__all__ = ["engine", "SessionLocal", "Base"]


async def get_session() -> AsyncGenerator:
	async with SessionLocal() as session:
		yield session
