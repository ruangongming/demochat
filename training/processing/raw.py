# raw.py
import sys
import asyncio
import hashlib
from typing import List, Tuple

import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from config import config
from db import DatabaseManager
from logger import get_logger  # Import get_logger từ logger.py

# Tạo logger cho tệp này
logger = get_logger(__name__)

def is_valid_url(url: str) -> bool:
    """Check if the URL is valid."""
    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc])

def create_url_hash(url: str) -> str:
    """Create a SHA1 hash for the URL."""
    return hashlib.sha1(url.encode('utf-8')).hexdigest()

async def fetch_url(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch the content of a URL using aiohttp with timeout."""
    try:
        async with session.get(url, timeout=config.request_timeout) as response:
            response.raise_for_status()
            text = await response.text()
            # logger.debug(f"Successfully fetched {url}")
            return text
    except aiohttp.ClientError as e:
        logger.error(f"Client error occurred while fetching {url}: {e}")
    except asyncio.TimeoutError:
        logger.error(f"Timeout occurred while fetching {url}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching {url}: {e}")
    return None

async def fetch_url_with_retry(session: aiohttp.ClientSession, url: str, retries: int = 3) -> str:
    """Fetch a URL with retry mechanism in case of failure."""
    for attempt in range(1, retries + 1):
        result = await fetch_url(session, url)
        if result:
            return result
        if attempt < retries:
            # logger.warning(f"Retry {attempt}/{retries} for {url}")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    logger.error(f"Failed to fetch {url} after {retries} retries.")
    return None

async def crawl_pages(session: aiohttp.ClientSession, page_count: int = 1) -> List[str]:
    """Crawl multiple pages to fetch their HTML content."""
    tasks = [
        fetch_url_with_retry(session, f'{config.target_url}?page={page}')
        for page in range(1, page_count + 1)
    ]
    responses = await asyncio.gather(*tasks, return_exceptions=False)
    return responses

async def process_responses(responses: List[str], db_manager: DatabaseManager) -> List[Tuple[str, str, str, str]]:
    """Process the HTML responses to extract new URLs."""
    insert_queries = []
    link_count = 0

    # Tải tất cả các hash hiện có từ cơ sở dữ liệu
    existing_hashes = await db_manager.get_all_hashes()
    existing_hashes_set = set(existing_hashes)

    for response_text in responses:
        if not response_text:
            continue
        # Sử dụng parser 'lxml' để tăng tốc độ và giảm tiêu thụ bộ nhớ
        soup = BeautifulSoup(response_text, 'lxml')
        links = soup.find_all('a', class_='title-link')

        for link in links:
            href = link.get('href')
            title = link.get_text(strip=True) or "No Title"
            content = ""  # Bạn có thể thêm logic để fetch hoặc extract nội dung nếu cần

            if not href:
                continue

            complete_url = urljoin('https://thuvienphapluat.vn', href)
            if not is_valid_url(complete_url):
                continue

            url_hash = create_url_hash(complete_url)

            # Kiểm tra sự tồn tại trong tập hợp hash
            if url_hash not in existing_hashes_set:
                insert_queries.append((complete_url, url_hash, title, content))
                existing_hashes_set.add(url_hash)  # Thêm vào tập hợp để tránh trùng lặp trong cùng phiên
                link_count += 1

        # Giải phóng bộ nhớ sau khi xử lý mỗi phản hồi
        del response_text
        del soup
        del links

    logger.info(f"Total new unique links found: {link_count}")
    return insert_queries

async def crawl_and_insert_data():
    """Crawl data from URLs and insert into the database."""
    db_manager = DatabaseManager()
    await db_manager.initialize_database()

    connector = aiohttp.TCPConnector(limit_per_host=config.max_concurrent_requests, keepalive_timeout=30)

    async with aiohttp.ClientSession(
        headers={'User-Agent': config.user_agent},
        connector=connector
    ) as session:
        responses = await crawl_pages(session, config.page_count)
        insert_queries = await process_responses(responses, db_manager)

        if insert_queries:
            await db_manager.add_or_update_news_items_async(insert_queries, existing_hashes_set=set())

            # Write new URLs to the TXT file
            try:
                with open(config.file_path, 'a', encoding='utf-8') as file:
                    for url, _, _, _ in insert_queries:
                        file.write(url + '\n')
                # logger.info(f"Written {len(insert_queries)} new URLs to {config.file_path}.")
            except IOError as e:
                logger.error(f"File I/O Error while writing to {config.file_path}: {e}")

    logger.info("Completed fetching URLs from all pages.")

if __name__ == '__main__':
    asyncio.run(crawl_and_insert_data())
