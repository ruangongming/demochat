# File db.py

import os
import shutil
import hashlib
import logging
import sys
from datetime import datetime
from typing import List, Tuple

from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import SQLAlchemyError

from config import config, async_engine, AsyncSessionLocal

# Reconfigure stdout to use utf-8
if sys.version_info >= (3, 7):
    sys.stdout.reconfigure(encoding='utf-8')

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Setup logging handler (only if not already set)
if not logger.handlers:
    file_handler = logging.FileHandler(config.log_path, encoding='utf-8')
    console_handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

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

class DatabaseManager:
    """Manage interactions with the database."""

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

    async def add_or_update_news_items_async(
        self,
        queries: List[Tuple[str, str, str, str]]
    ) -> None:
        """Add or update multiple news items asynchronously."""
        async with AsyncSessionLocal() as session:
            try:
                # Extract all hashes
                hashes = [q[2] for q in queries]  # hash_val is the third element
                stmt = select(News).where(News.hash.in_(hashes))
                result = await session.execute(stmt)
                existing_items = {item.hash: item for item in result.scalars().all()}

                new_items = []
                for query in queries:
                    url, title, hash_val, content = query
                    if hash_val not in existing_items:
                        new_item = News(
                            url=url,
                            hash=hash_val,
                            title=title,
                            content=content
                        )
                        new_items.append(new_item)
                    else:
                        # Update existing item
                        existing_item = existing_items[hash_val]
                        existing_item.url = url
                        existing_item.title = title
                        existing_item.content = content

                if new_items:
                    session.add_all(new_items)  # Thêm tất cả các đối tượng mới
                    logger.info(f"Added {len(new_items)} new items.")

                await session.commit()
                logger.info(f"Processed {len(queries)} news items.")
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Failed to add or update news items: {e}")