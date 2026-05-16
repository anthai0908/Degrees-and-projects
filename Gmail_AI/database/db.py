from sqlmodel import SQLModel, select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models.user_model import UserModel
from models.message_model import MessageModel
from models.repo_model import RepoModel
import os
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timezone
from typing import Optional
load_dotenv()


class DBService:
    def __init__(self):
        url = (
            f"postgresql+asyncpg://"
            f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
            f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}"
            f"/{os.getenv('DB_NAME')}"
        )

        self.engine = create_async_engine(
            url=url,
            echo=True,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
        )

        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def add_user(self, user):
        async with self.async_session() as session:
            async with session.begin():
                session.add(user)

    async def add_message(self, message):
       async with self.async_session() as session:
           async with session.begin():
               stmt = insert(MessageModel).values(
                   message_id=message.message_id,
                   thread_id=message.thread_id,
                   user_id=message.user_id,
                   sender=message.sender,
                   subject=message.subject,
                   date=message.date,
                   content=message.content
               )

               stmt = stmt.on_conflict_do_nothing(
                   index_elements=["user_id", "thread_id", "message_id"]
               )
               await session.execute(stmt)
               
               
    async def get_unsolved_messages(self, user_id: str):
        async with self.async_session() as session:
            result = await session.execute(
                select(MessageModel).where(
                    MessageModel.user_id == user_id
                )
            )
            return result.scalars().all()

    async def get_message_by_id(self, message_id: str):
        async with self.async_session() as session:
            result = await session.execute(
                select(MessageModel).where(
                    MessageModel.message_id == message_id
                )
            )
            return result.scalar_one_or_none()

    async def delete_message_by_id(self, message_id: str):
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    delete(MessageModel).where(
                        MessageModel.message_id == message_id
                    )
                )
            return result.rowcount > 0
        
        
    async def add_commit(self, repo_name: str, commit: str):
        async with self.async_session() as session:
            async with session.begin():
                stmt = insert(RepoModel).values(
                    repo_name=repo_name,
                    last_processed_commit=commit,
                    last_processed_commit_time = datetime.now(tz=timezone.utc)
                    ).on_conflict_do_update(
                        index_elements=["repo_name"],
                        set_={
                            "last_processed_commit": commit,
                            "last_processed_commit_time": datetime.now(tz=timezone.utc)
                        }
                    )
                await session.execute(stmt)
                
                
    async def get_user(self, user_id: str)->UserModel:
        async with self.async_session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.user_id == user_id)
            )
            return result.scalar_one_or_none()

    async def close(self):
        await self.engine.dispose()
        
dbservice = DBService()
 