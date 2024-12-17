# scraper.py
import asyncio
import os
import re
from hashlib import sha1

import aiohttp
import aiofiles
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_fixed

from config import config  # Sử dụng đối tượng config từ config.py
from db import DatabaseManager  # Import DatabaseManager từ db.py
from logger import get_logger  # Import get_logger từ logger.py

# Tạo logger cho tệp này
logger = get_logger(__name__)

def read_existing_urls(file_path):
    """Đọc các URL đã lưu trong file TXT."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            urls = file.read().splitlines()
        # logger.info(f"Đọc {len(urls)} URL từ file {file_path}.")
    except FileNotFoundError:
        urls = []
        logger.warning(f"Không tìm thấy file URL tại {file_path}. Bắt đầu mới.")
    except Exception as e:
        logger.error(f"Lỗi khi đọc file URL {file_path}: {e}")
        urls = []
    return urls

def is_youtube_url(url):
    """Kiểm tra URL có phải YouTube không."""
    return 'youtube.com' in url or 'youtu.be' in url

def fix_spacing(text):
    """
    Hàm tổng quát để đảm bảo các từ luôn được cách nhau bằng dấu cách,
    bao gồm cả trường hợp số dính vào chữ và dấu câu không có khoảng cách.
    """
    text = re.sub(
        r'([a-záàảãạâấầẩẫậăắằẳẵặđéèẻẽẹêếềểễệíìỉĩịôồốổỗộơờớởỡợúùủũụưứừửữựýỳỷỹỵ])([A-ZÁÀẢÃẠÂẤẦẨẪẬĂẮẰẲẴẶĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÔỒỐỔỖỘƠỜỚỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ])',
        r'\1 \2', text)
    text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)  # "10Luật" -> "10 Luật"
    text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)  # "Luật10" -> "Luật 10"
    text = re.sub(r'([A-Z]{2,})([a-z])', r'\1 \2', text)
    text = re.sub(r'([.,:;!?])([^\s])', r'\1 \2', text)  # Thêm khoảng cách sau dấu câu
    text = re.sub(r'\[\.\s*\.\s*\.\s*\]', '', text)  # Loại bỏ "[. .. ]" hoặc "[...]"
    text = re.sub(r'\s+', ' ', text).strip()  # Loại bỏ khoảng trắng thừa
    return text

def create_hash(url: str, index: int) -> str:
    """Tạo hash SHA1 cho URL và index."""
    return sha1(f"{url}_{index}".encode('utf-8')).hexdigest()

@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
async def fetch_page(session, url):
    """Thực hiện yêu cầu HTTP không đồng bộ với cơ chế retry."""
    async with session.get(url, timeout=config.request_timeout) as response:
        response.raise_for_status()
        return await response.text()

async def process_url(url, semaphore):
    """Xử lý URL và lưu từng bài viết nhỏ."""
    async with semaphore:
        if is_youtube_url(url):
            # logger.info(f"URL là YouTube, bỏ qua: {url}")
            return 0

        result = await crawl(url)
        if result and result['articles']:
            total_articles = 0
            for article in result['articles']:
                await save_article_to_file(article, config.output_dir)
                await insert_article_into_db(article)
                total_articles += 1
            return total_articles
        return 0

async def crawl(url):
    """Thu thập dữ liệu từ URL không đồng bộ và trích xuất các bài viết nhỏ."""
    result = {
        'url': url,
        'articles': []
    }

    connector = aiohttp.TCPConnector(limit_per_host=config.max_concurrent_requests, keepalive_timeout=30)

    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            html = await fetch_page(session, url)
            soup = BeautifulSoup(html, 'lxml')

            # Lấy tất cả các thẻ h2 và phần nội dung dưới mỗi thẻ
            titles = soup.find_all('h2')
            for idx, title in enumerate(titles):
                article_content = []
                next_tag = title.find_next_sibling()

                # Thu thập tất cả các thẻ p, blockquote sau h2 cho đến thẻ h2 tiếp theo
                while next_tag and next_tag.name not in ['h2', 'h1']:
                    if next_tag.name in ['p', 'blockquote']:
                        clean_text = fix_spacing(next_tag.get_text(strip=True))
                        article_content.append(clean_text)
                    next_tag = next_tag.find_next_sibling()

                if article_content:
                    unique_url = f"{url}#{idx + 1}"
                    article = {
                        'url': unique_url,
                        'title': title.get_text(strip=True),
                        'content': '\n'.join(article_content),
                        'hash': create_hash(url, idx + 1),
                        'index': idx + 1
                    }
                    result['articles'].append(article)

            # Giải phóng bộ nhớ
            del soup
            del html
            del titles

        except Exception as e:
            logger.error(f"Lỗi khi xử lý URL {url}: {e}")

    return result

async def save_article_to_file(article, output_dir):
    """Lưu bài viết vào file với tiêu đề đầy đủ."""
    file_name = re.sub(r'[\\/*?:"<>|]', "_", article['title'])
    file_path = os.path.join(output_dir, f"{file_name}.txt")

    try:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as file:
            await file.write(f"Tiêu đề: {article['title']}\n\n")
            await file.write("Nội dung:\n")
            await file.write(article['content'])
        # logger.debug(f"Đã lưu bài viết vào file: {file_path}")
    except IOError as e:
        logger.error(f"Lỗi khi lưu file {file_path}: {e}")

async def insert_article_into_db(article):
    """Chèn bài viết vào cơ sở dữ liệu."""
    db_manager = DatabaseManager()
    await db_manager.add_news_item(article)

async def main():
    # Khởi tạo cơ sở dữ liệu
    db_manager = DatabaseManager()
    await db_manager.initialize_database()

    urls = read_existing_urls(config.file_path)

    if not urls:
        logger.warning("Không có URL nào để xử lý.")
        return

    total_inserted = 0

    semaphore = asyncio.Semaphore(config.max_concurrent_requests)

    tasks = [process_url(url, semaphore) for url in urls]

    results = await asyncio.gather(*tasks)

    for result in results:
        if result:
            total_inserted += result

    logger.info(f"Tổng số bài viết được chèn vào cơ sở dữ liệu: {total_inserted}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Lỗi: {e}")
