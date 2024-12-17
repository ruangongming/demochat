import gc
import os
import json
import sqlite3
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma  # Đổi từ FAISS sang Chroma
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain.docstore.document import Document
from config import DB_PATH, VECTOR_DB_PATH, METADATA_PATH, OUTPUT_DIR, LOG_PATH

# Cấu hình logging để ghi vào file và console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def load_metadata():
    """Tải metadata từ file JSON."""
    if os.path.exists(METADATA_PATH):
        with open(METADATA_PATH, "r", encoding='utf-8') as f:
            return json.load(f)
    else:
        return {"processed_files": []}


def save_metadata(metadata):
    """Lưu metadata vào file JSON."""
    with open(METADATA_PATH, "w", encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False)


def read_text_file(file_path):
    """Đọc nội dung của tệp văn bản với xử lý lỗi encoding."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read()


def load_documents_from_db():
    """Tải tất cả các tài liệu từ cơ sở dữ liệu SQLite."""
    documents = []
    if os.path.exists(DB_PATH):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT url, title, content FROM news')
                rows = cursor.fetchall()
                for row in rows:
                    # Kiểm tra nếu content hợp lệ (không None hoặc rỗng)
                    if row[2] and row[2].strip():
                        documents.append(
                            Document(page_content=row[2], metadata={'source': row[0], 'title': row[1]}))
                    else:
                        logging.warning(f"Skipping document with empty content: {row[0]}")
        except sqlite3.Error as e:
            logging.error(f"SQLite Error: {e}")
    return documents


def load_documents_from_files():
    """Tải tất cả các tài liệu văn bản từ tệp .txt trong thư mục."""
    documents = []
    metadata = load_metadata()

    def process_file(file_path):
        if file_path.endswith('.txt') and os.path.exists(file_path):
            try:
                text = read_text_file(file_path)
                if text and text.strip():  # Kiểm tra nếu nội dung không rỗng
                    return Document(page_content=text, metadata={'source': file_path})
                else:
                    logging.warning(f"Skipping empty file: {file_path}")
            except Exception as e:
                logging.error(f"Error loading file {file_path}: {e}")
        return None

    with ThreadPoolExecutor() as executor:
        future_to_file = {executor.submit(process_file, os.path.join(OUTPUT_DIR, file)): file for file in os.listdir(OUTPUT_DIR) if file.endswith('.txt')}
        for future in as_completed(future_to_file):
            result = future.result()
            if result:
                documents.append(result)

    return documents


def create_db_from_files_and_db():
    """Tạo cơ sở dữ liệu vector từ cả file và cơ sở dữ liệu SQLite."""
    # Tải tài liệu từ tệp .txt
    text_documents = load_documents_from_files()

    # Tải tài liệu từ cơ sở dữ liệu
    db_documents = load_documents_from_db()

    # Kết hợp dữ liệu từ cả hai nguồn
    documents = text_documents + db_documents

    if not documents:
        logging.info("No documents found in either text files or database.")
        return

    # Embedding
    model_name = "all-MiniLM-L6-v2.gguf2.f16.gguf"
    gpt4all_kwargs = {'allow_download': True}
    embeddings = GPT4AllEmbeddings(
        model_name=model_name,
        gpt4all_kwargs=gpt4all_kwargs
    )

    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)

    # Tạo hoặc tải cơ sở dữ liệu vector từ Chroma
    if os.path.exists(VECTOR_DB_PATH):
        db = Chroma.load_local(VECTOR_DB_PATH, embeddings)
        db.add_documents(chunks)
    else:
        db = Chroma.from_documents(chunks, embeddings)

    logging.info("Vector database created/updated successfully.")


if __name__ == '__main__':
    create_db_from_files_and_db()
    gc.collect()  # Explicit garbage collection
