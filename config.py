# config.py
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

class Config:
    """Configuration for the crawler application."""

    def __init__(self, env_path: str = ".env") -> None:
        """Initialize configuration from the .env file."""
        load_dotenv(dotenv_path=env_path)

        # Directories and file names
        self.data_directory = os.getenv('DATA_DIRECTORY', 'data')
        self.db_directory = os.getenv('DB_DIRECTORY', 'db')
        self.logs_directory = os.getenv('LOGS_DIRECTORY', 'logs')
        self.output_dir = os.getenv('OUTPUT_DIR', 'data/news_articles')
        self.vector_db_directory = os.getenv('VECTOR_DB_DIRECTORY', 'data/vectorstores')
        self.db_file = os.getenv('DB_FILE', 'news_data.db')
        self.log_file = os.getenv('LOG_FILE', 'crawl_log.log')
        self.txt_file = os.getenv('TXT_FILE', 'news_data.txt')
        self.vector_db_file = os.getenv('VECTOR_DB_FILE', 'db_faiss')
        self.metadata_file = os.getenv('METADATA_FILE', 'metadata.json')

        # Crawler information
        self.user_agent = os.getenv('USER_AGENT', 'MyCrawler/1.0')
        self.target_url = os.getenv(
            'TARGET_URL',
            'https://thuvienphapluat.vn/hoi-dap-phap-luat/giao-thong-van-tai'
        )
        self.page_count = int(os.getenv('PAGE_COUNT', 1))
        self.request_timeout = int(os.getenv('REQUEST_TIMEOUT', 10))
        self.max_concurrent_requests = int(os.getenv('MAX_CONCURRENT_REQUESTS', 10))
        self.retry_limit = int(os.getenv('RETRY_LIMIT', 3))

        # Full paths
        self.db_path = os.path.join(self.db_directory, self.db_file)
        self.file_path = os.path.join(self.data_directory, self.txt_file)
        self.log_path = os.path.join(self.logs_directory, self.log_file)
        self.vector_db_path = os.path.join(self.vector_db_directory, self.vector_db_file)
        self.metadata_path = os.path.join(self.data_directory, self.metadata_file)

        # Database URL for SQLAlchemy (Using async driver)
        self.database_url = f'sqlite+aiosqlite:///{self.db_path}'

        # Create directories if they do not exist
        self._create_directories()

    def _create_directories(self) -> None:
        """Create necessary directories if they do not exist."""
        directories = [
            self.data_directory,
            self.db_directory,
            self.logs_directory,
            self.output_dir,
            self.vector_db_directory
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

# Instantiate config
config = Config()

# Create async engine without pool settings (remove pool_size and max_overflow)
async_engine = create_async_engine(
    config.database_url,
    echo=False
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)
