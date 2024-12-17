# db.py
import os
import shutil
from datetime import datetime
from typing import List, Tuple

from sqlalchemy import Column, Integer, String, select, Index
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import SQLAlchemyError

from config import config, async_engine, AsyncSessionLocal
from logger import get_logger  # Import get_logger từ logger.py

# Tạo logger cho tệp này
logger = get_logger(__name__)

# Define the declarative base
Base = declarative_base()

class News(Base):
    """Define the 'news' table."""
    __tablename__ = 'news'

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, nullable=False)  # Original URL, no unique constraint
    hash = Column(String, nullable=False, unique=True)  # Unique per article
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)

    __table_args__ = (
        Index('idx_hash', 'hash'),
    )

class DatabaseManager:
    """Manage interactions with the database."""

    BATCH_SIZE = 100  # Kích thước lô commit

    def __init__(self) -> None:
        """Initialize DatabaseManager."""
        pass  # No initialization needed, using async_engine and AsyncSessionLocal

    async def initialize_database(self) -> None:
        """Backup and initialize the database."""
        try:
            await self.backup_database()
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialized successfully.")
        except (IOError, SQLAlchemyError) as e:
            logger.error(f"Error during database initialization: {e}")

    async def backup_database(self) -> None:
        """Backup the database if it exists."""
        if os.path.exists(config.db_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f'news_data_backup_{timestamp}.db'
            backup_path = os.path.join(os.path.dirname(config.db_path), backup_filename)
            try:
                shutil.copy(config.db_path, backup_path)
                logger.info(f"Database backup created at: {backup_path}")
            except IOError as e:
                logger.error(f"Failed to backup database: {e}")
        else:
            logger.warning("Database file does not exist for backup.")

    async def get_all_hashes(self) -> List[str]:
        """Lấy tất cả các hash từ cơ sở dữ liệu."""
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(News.hash)
                result = await session.execute(stmt)
                hashes = [row[0] for row in result.scalars().all()]
                return hashes
            except SQLAlchemyError as e:
                logger.error(f"Database error during fetching hashes: {e}")
                return []

    async def add_or_update_news_items_async(
        self,
        queries: List[Tuple[str, str, str, str]],
        existing_hashes_set: set
    ) -> None:
        """Add or update multiple news items asynchronously with batch commits."""
        async with AsyncSessionLocal() as session:
            try:
                new_items = []
                # Prepare mapping for existing items
                existing_hashes = existing_hashes_set

                for query in queries:
                    url, hash_val, title, content = query
                    if hash_val not in existing_hashes:
                        new_item = News(
                            url=url,
                            hash=hash_val,
                            title=title,
                            content=content
                        )
                        new_items.append(new_item)
                        existing_hashes.add(hash_val)  # Add to existing_hashes to prevent duplicates in the same batch

                if new_items:
                    session.add_all(new_items)  # Thêm tất cả các đối tượng mới
                    logger.info(f"Added {len(new_items)} new items.")

                # Commit theo từng lô
                for i in range(0, len(new_items), self.BATCH_SIZE):
                    await session.commit()
                    # logger.debug(f"Committed batch {i // self.BATCH_SIZE + 1}")

                logger.info(f"Processed {len(queries)} news items.")
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Failed to add or update news items: {e}")
            finally:
                await session.close()

    async def add_news_item(self, news_item):
        """Add a single news item to the database."""
        async with AsyncSessionLocal() as session:
            try:
                new_item = News(
                    url=news_item['url'],
                    hash=news_item['hash'],
                    title=news_item['title'],
                    content=news_item['content']
                )
                session.add(new_item)
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Failed to add news item: {e}")
            finally:
                await session.close()
