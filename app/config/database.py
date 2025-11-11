from typing import AsyncGenerator
from sqlalchemy.orm import sessionmaker as orm_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.config.config import config

# Async engine + session for use with async code (FastAPI async endpoints)
# Note: settings.ASYNC_DATABASE_URL should be like 'postgresql+asyncpg://user:pass@host/db'
async_engine = create_async_engine(config.ASYNC_DATABASE_URL, pool_pre_ping=True, future=True)
AsyncSessionLocal = orm_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False, future=True)

# Async read replica engine + session
async_read_replica_engine = create_async_engine(config.ASYNC_READ_DATABASE_URL, pool_pre_ping=True, future=True)
AsyncReadReplicaSessionLocal = orm_sessionmaker(bind=async_read_replica_engine, class_=AsyncSession, expire_on_commit=False, future=True)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession for use in async endpoints/dependencies.
    
    Uses read replica if USE_READ_REPLICA config is True, otherwise uses primary database.
    """
    if config.USE_READ_REPLICA:
        async with AsyncReadReplicaSessionLocal() as session:
            yield session
    else:
        async with AsyncSessionLocal() as session:
            yield session


