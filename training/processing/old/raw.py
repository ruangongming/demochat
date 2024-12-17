# File raw.py
import sys
import asyncio
import hashlib
import logging
from typing import List, Set, Tuple
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from config import config
from db import DatabaseManager

# Reconfigure stdout to use utf-8 (Python 3.7+)
if sys.version_info >= (3, 7):
    sys.stdout.reconfigure(encoding='utf-8')

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Setup logging handler (if not already configured)
if not logger.handlers:
    file_handler = logging.FileHandler(config.log_path, encoding='utf-8')
    console_handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def is_valid_url(url: str) -> bool:
    """Check if the URL is valid."""
    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc])

def read_existing_urls(file_path: str) -> Set[str]:
    """Read existing URLs from a TXT file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            urls = set(file.read().splitlines())
        logger.info(f"Read {len(urls)} existing URLs from {file_path}.")
    except FileNotFoundError:
        urls = set()
        logger.info(f"No existing URL file found at {file_path}. Starting fresh.")
    except Exception as e:
        logger.error(f"Error reading existing URLs from {file_path}: {e}")
        urls = set()
    return urls

def create_url_hash(url: str) -> str:
    """Create a SHA1 hash for the URL."""
    return hashlib.sha1(url.encode('utf-8')).hexdigest()

async def fetch_robots_txt(session: aiohttp.ClientSession, base_url: str) -> RobotFileParser:
    """Fetch and parse robots.txt using aiohttp and RobotFileParser."""
    robots_url = urljoin(base_url, '/robots.txt')
    try:
        async with session.get(robots_url, timeout=config.request_timeout) as response:
            if response.status == 200:
                content = await response.text()
                logger.info(f"Successfully fetched robots.txt from {robots_url}")
                # Use run_in_executor to parse robots.txt
                loop = asyncio.get_event_loop()
                robot_parser = await loop.run_in_executor(None, parse_robots_txt, content, robots_url)
                return robot_parser
            else:
                logger.warning(f"robots.txt not found at {robots_url}. Status: {response.status}")
    except aiohttp.ClientError as e:
        logger.error(f"Client error occurred while fetching robots.txt: {e}")
    except asyncio.TimeoutError:
        logger.error("Timeout occurred while fetching robots.txt")
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching robots.txt: {e}")
    # Return a RobotFileParser that allows everything if robots.txt cannot be fetched
    robot_parser = RobotFileParser()
    robot_parser.parse("")  # Allow all
    return robot_parser

def parse_robots_txt(content: str, url: str) -> RobotFileParser:
    """Parse robots.txt content."""
    robot_parser = RobotFileParser()
    robot_parser.parse(content.splitlines())
    robot_parser.set_url(url)
    robot_parser.read()  # Not necessary as already parsed
    return robot_parser

async def fetch_url(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch the content of a URL using aiohttp with timeout."""
    try:
        async with session.get(url, timeout=config.request_timeout) as response:
            response.raise_for_status()
            text = await response.text()
            logger.info(f"Successfully fetched {url}")
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
            logger.warning(f"Retry {attempt}/{retries} for {url}")
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

async def process_responses(responses: List[str], existing_hashes: Set[str]) -> List[Tuple[str, str, str, str]]:
    """Process the HTML responses to extract new URLs."""
    insert_queries = []
    link_count = 0

    for response_text in responses:
        if not response_text:
            continue
        soup = BeautifulSoup(response_text, 'html.parser')
        links = soup.find_all('a', class_='title-link')

        for link in links:
            href = link.get('href')
            title = link.get_text(strip=True) or "No Title"
            content = ""  # You can add logic to fetch or extract content if needed

            if not href:
                continue

            complete_url = urljoin('https://thuvienphapluat.vn', href)
            if not is_valid_url(complete_url):
                continue

            url_hash = create_url_hash(complete_url)

            if url_hash not in existing_hashes:
                insert_queries.append((complete_url, url_hash, title, content))
                existing_hashes.add(url_hash)
                link_count += 1

                if link_count % 100 == 0:
                    logger.info(f"Processed {link_count} unique links.")

    logger.info(f"Total new unique links found: {link_count}")
    return insert_queries

async def crawl_and_insert_data():
    """Crawl data from URLs and insert into the database."""
    db_manager = DatabaseManager()
    await db_manager.initialize_database()

    existing_urls = read_existing_urls(config.file_path)
    existing_hashes = {create_url_hash(url) for url in existing_urls}

    async with aiohttp.ClientSession(
        headers={'User-Agent': config.user_agent},
        connector=aiohttp.TCPConnector(limit=config.max_concurrent_requests)
    ) as session:
        # Fetch and parse robots.txt
        robot_parser = await fetch_robots_txt(session, config.target_url)
        # Check if crawling is allowed
        crawl_path = '/hoi-dap-phap-luat/giao-thong-van-tai'
        if not robot_parser.can_fetch(config.user_agent, crawl_path):
            logger.error(f"Crawling disallowed by robots.txt for path: {crawl_path}")
            return

        responses = await crawl_pages(session, config.page_count)
        insert_queries = await process_responses(responses, existing_hashes)

        if insert_queries:
            await db_manager.add_or_update_news_items_async(insert_queries)

            # Write new URLs to the TXT file
            try:
                with open(config.file_path, 'a', encoding='utf-8') as file:
                    for url, _, _, _ in insert_queries:  # Chỉ unpack 4 giá trị, bỏ url_with_index
                        file.write(url + '\n')
                logger.info(f"Written {len(insert_queries)} new URLs to {config.file_path}.")
            except IOError as e:
                logger.error(f"File I/O Error while writing to {config.file_path}: {e}")

    logger.info("Completed fetching URLs from all pages.")

if __name__ == '__main__':
    asyncio.run(crawl_and_insert_data())
