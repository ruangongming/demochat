# File: scraper.py

import gc
import sys
import os
import codecs
import validators
import re
import sqlite3
from datetime import datetime
import shutil
import logging
from threading import Lock
from bs4 import BeautifulSoup
import asyncio
import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed
from hashlib import sha1

from config import config  # Sử dụng đối tượng config từ config.py
from db import DatabaseManager  # Import DatabaseManager từ db.py

# Thiết lập lại stdout và stderr sang 'utf-8' để xử lý Unicode đúng cách
if sys.version_info >= (3, 7):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
else:
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Cấu hình logging để ghi vào file và console, mức log là INFO
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.log_path, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Tạo một khóa để đảm bảo việc ghi vào SQLite an toàn trong môi trường đa luồng
db_lock = Lock()


def read_existing_urls(file_path):
    """Đọc các URL được lưu trong file TXT."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            urls = file.read().splitlines()
        logging.info(f"Đã đọc {len(urls)} URL từ file {file_path}.")
    except FileNotFoundError:
        urls = []
        logging.info(f"Không tìm thấy file URL tại {file_path}. Bắt đầu mới.")
    except Exception as e:
        logging.error(f"Lỗi khi đọc file URL {file_path}: {e}")
        urls = []
    return urls


def backup_database():
    """Sao lưu cơ sở dữ liệu bằng cách ghi đè file sao lưu."""
    if os.path.exists(config.db_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f'news_data_backup_{timestamp}.db'
        backup_path = os.path.join(os.path.dirname(config.db_path), backup_filename)
        try:
            shutil.copy(config.db_path, backup_path)
            logging.info(f"Cơ sở dữ liệu đã được sao lưu tại: {backup_path}")
        except IOError as e:
            logging.error(f"Không thể sao lưu cơ sở dữ liệu: {e}")
    else:
        logging.warning("Không tìm thấy file cơ sở dữ liệu để sao lưu.")


async def initialize_database():
    """Kiểm tra và khởi tạo cơ sở dữ liệu SQLite."""
    db_manager = DatabaseManager()
    await db_manager.initialize_database()
    backup_database()


def is_url(url):
    """Kiểm tra xem URL có hợp lệ không."""
    return validators.url(url)


def is_youtube_url(url):
    """Kiểm tra xem URL có phải là URL YouTube không."""
    return 'youtube.com' in url or 'youtu.be' in url


def fix_spacing(text):
    """Hàm xử lý khoảng cách và loại bỏ các chuỗi không mong muốn trong văn bản tiếng Việt."""
    # Loại bỏ bất kỳ chuỗi nào có dạng [. .. ], [... ], [. . . ], [.. . ]
    text = re.sub(r'\[\s*([.\s]{1,})\s*\]', '', text)

    # Loại bỏ bất kỳ nội dung nào trong dấu ngoặc vuông chứa các ký tự không phải chữ cái hoặc số
    text = re.sub(r'\[\s*[^\w\s]+\s*\]', '', text)

    # Loại bỏ khoảng trắng thừa trong số mục và tham chiếu
    def replace_section_numbers(m):
        numbers = re.findall(r'\d+', m.group(2))
        return f"{m.group(1)} {'.'.join(numbers)}"

    text = re.sub(
        r'(\bTiểu mục|Mục|Điều|Chương|Phần|Khoản|Điểm)\s+((?:\d+\s*\.\s*)+\d+)',
        replace_section_numbers,
        text)

    # Sửa định dạng số mục như "6. Các trường hợp" thành "6. Các trường hợp"
    text = re.sub(
        r'^(\d+)\s*\.\s*',
        lambda m: f"{m.group(1)}. ",
        text,
        flags=re.MULTILINE)

    # Loại bỏ khoảng trắng thừa trong tham chiếu văn bản pháp luật
    def replace_legal_refs(m):
        return f"{m.group(1)}:{m.group(2)}"

    text = re.sub(
        r'(\bQCVN\s*\d+)\s*:\s*(\d+(?:/\d+)?(?:-\d+)?(?:/\d+)?)',
        replace_legal_refs,
        text)

    def replace_legal_refs_2(m):
        return f"{m.group(1)} {m.group(2)}"

    text = re.sub(
        r'(\bNĐ-CP|TT-BCA|TT-BTC)\s*:\s*(\d+(?:/\d+)?)',
        replace_legal_refs_2,
        text)

    # Loại bỏ khoảng trắng thừa trong ngày tháng và thời gian
    def replace_time(m):
        return f"{m.group(1)}{m.group(2)}"

    text = re.sub(
        r'(\b\d{1,2})\s*[hg]\s*(\d{2}\b)',
        replace_time,
        text)

    text = re.sub(
        r'(\bngày\s+\d{1,2})\.\s*(\d{1,2}\b)',
        r'\1.\2',
        text)

    text = re.sub(
        r'(\b\d{1,2})\.\s*(\d{4}\b)',
        r'\1.\2',
        text)

    # Loại bỏ khoảng trắng xung quanh dấu câu
    text = re.sub(r'\s*([.,:;!?“”‘’])\s*', r'\1', text)

    # Thêm khoảng trắng sau dấu câu nếu thiếu và ký tự tiếp theo là chữ cái
    text = re.sub(
        r'([.,:;!?“”‘’])([^\s\W\d])',
        r'\1 \2',
        flags=re.UNICODE)

    # Thêm khoảng trắng giữa chữ thường và chữ hoa liền kề
    text = re.sub(
        r'([a-zàáảãạăâấầẩẫậắằẳẵặèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ])'
        r'([A-ZÀÁẢÃẠĂÂẤẦẨẪẬẮẰẲẴẶÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ])',
        r'\1 \2',
        text)

    # Xử lý trường hợp không có khoảng trắng sau một số từ viết tắt
    text = re.sub(
        r'(\b(?:TT-BCA|QĐ-TTg|NĐ-CP|QCVN)\b)([^\s])',
        r'\1 \2',
        text)

    # Loại bỏ khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def process_legal_text(text):
    """Xử lý văn bản pháp luật với khoảng cách đúng chuẩn."""
    # Áp dụng xử lý khoảng cách chung
    text = fix_spacing(text)

    # Tách văn bản thành các dòng
    lines = text.split('\n')
    processed_lines = []
    current_section = []

    for line in lines:
        # Kiểm tra xem dòng có phải là tiêu đề mục mới không
        if re.match(
            r'^(Tiểu mục|Mục|Điều|Chương|Phần|Khoản|Điểm)\s+\d+(\.\d+)*',
            line):
            if current_section:
                processed_lines.append(' '.join(current_section))
                current_section = []
            processed_lines.append(line)
        else:
            # Nếu không phải tiêu đề, thêm vào phần hiện tại
            current_section.append(line)

    # Thêm phần cuối cùng nếu có
    if current_section:
        processed_lines.append(' '.join(current_section))

    # Kết hợp các dòng đã xử lý thành một văn bản duy nhất
    processed_text = '\n'.join(processed_lines)

    # Loại bỏ khoảng trắng thừa
    processed_text = re.sub(r'\s+', ' ', processed_text).strip()

    return processed_text


def create_hash(url: str, index: int) -> str:
    """Tạo một hash SHA1 cho URL và chỉ số."""
    return sha1(f"{url}_{index}".encode('utf-8')).hexdigest()


@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
async def fetch_page(session, url):
    """Thực hiện yêu cầu HTTP bất đồng bộ với cơ chế thử lại."""
    async with session.get(url, timeout=10) as response:
        response.raise_for_status()
        return await response.text()


async def crawl(url):
    """Thu thập dữ liệu từ URL và trích xuất các bài viết con."""
    result = {
        'url': url,
        'articles': []
    }

    async with aiohttp.ClientSession() as session:
        try:
            html = await fetch_page(session, url)
            soup = BeautifulSoup(html, 'html.parser')

            # Lấy tất cả các thẻ h2 và nội dung dưới mỗi thẻ
            titles = soup.find_all('h2')
            if not titles:
                # Nếu không tìm thấy thẻ h2, thử với thẻ h1
                titles = soup.find_all('h1')

            for idx, title in enumerate(titles):
                article_content = []
                next_tag = title.find_next_sibling()

                # Thu thập tất cả các thẻ p, blockquote sau h2 cho đến thẻ h2 hoặc h1 tiếp theo
                while next_tag and next_tag.name not in ['h2', 'h1']:
                    if next_tag.name in ['p', 'blockquote', 'div', 'span']:
                        raw_text = next_tag.get_text(strip=True)
                        clean_text = fix_spacing(raw_text)
                        article_content.append(clean_text)
                    next_tag = next_tag.find_next_sibling()

                if article_content:
                    unique_url = f"{url}#{idx + 1}"
                    result['articles'].append({
                        'url': unique_url,
                        'title': fix_spacing(title.get_text(strip=True)),
                        'content': '\n'.join(article_content),
                        'hash': create_hash(url, idx + 1),
                        'index': idx + 1
                    })

        except Exception as e:
            logging.error(f"Lỗi khi xử lý URL {url}: {e}")

    return result


def save_articles_to_file(data, output_dir, log_every=10):
    """Lưu từng bài viết vào file với tiêu đề đầy đủ."""
    for count, article in enumerate(data['articles'], start=1):
        # Loại bỏ các ký tự không hợp lệ trong tên file
        file_name = re.sub(r'[\\/*?:"<>|]', "_", article['title'])
        file_path = os.path.join(output_dir, f"{file_name}.txt")

        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(f"Tiêu đề: {article['title']}\n\n")
                file.write("Nội dung:\n")
                file.write(article['content'])
            if count % log_every == 0:
                logging.info(f"Đã lưu bài viết vào file: {file_path}")
        except IOError as e:
            logging.error(f"Lỗi khi lưu file {file_path}: {e}")


def insert_into_db(data):
    """Chèn từng bài viết từ một URL vào cơ sở dữ liệu."""
    articles = data['articles']
    if not articles:
        logging.warning("Không có bài viết hợp lệ để chèn vào cơ sở dữ liệu.")
        return

    with db_lock:
        try:
            with sqlite3.connect(config.db_path) as conn:
                cursor = conn.cursor()
                cursor.executemany('''
                    INSERT OR REPLACE INTO news (url, title, content, hash) VALUES (?, ?, ?, ?)
                ''', [(article['url'], article['title'], article['content'], article['hash']) for article in articles])
                conn.commit()
                logging.info(f"Đã chèn {len(articles)} bài viết vào cơ sở dữ liệu từ URL: {data['url']}")
        except sqlite3.Error as e:
            logging.error(f"Lỗi SQLite: {e}")


async def process_url(url, count):
    """Xử lý một URL và lưu từng bài viết con."""
    if is_youtube_url(url):
        logging.info(f"URL là YouTube, bỏ qua: {url}")
        return 0

    result = await crawl(url)
    if result and result['articles']:
        save_articles_to_file(result, config.output_dir, count)
        insert_into_db(result)
        return len(result['articles'])
    return 0


async def main():
    await initialize_database()

    urls = read_existing_urls(config.file_path)

    if not urls:
        logging.info("Không có URL nào để xử lý.")
        return

    total_inserted = 0

    tasks = [process_url(url, idx) for idx, url in enumerate(urls, start=1)]

    results = await asyncio.gather(*tasks)

    for result in results:
        if result:
            total_inserted += result

    logging.info(f"Tổng số bài viết được chèn vào cơ sở dữ liệu: {total_inserted}")


if __name__ == '__main__':
    try:
        asyncio.run(main())
        gc.collect()
    except Exception as e:
        logging.error(f"Lỗi: {e}")
    finally:
        gc.collect()
