import streamlit as st
import sqlite3
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain.docstore.document import Document

# Đường dẫn tới cơ sở dữ liệu
DB_PATH = os.path.join('training', 'processing', 'db', 'news_data.db')
VECTOR_DB_PATH = os.path.join('training', 'processing', 'data', 'vectorstores', 'db_faiss')
MODEL_NAME = "all-MiniLM-L6-v2.gguf2.f16.gguf"

# Tạo giao diện
st.title("Hệ thống Tự Học Tăng Cường")

# Tạo bố cục ngang cho các phần nhập liệu và các nút
col1, col2, col3 = st.columns([5, 1.5, 1.5])

with col1:
    title = st.text_input("", placeholder="Mời bạn nhập tiêu đề bài viết...")

with col2:
    search_button = st.button("Tìm kiếm bài viết", use_container_width=True)

with col3:
    reset_button = st.button("Reset", use_container_width=True)

# Kiểm tra đầu vào và thực hiện tìm kiếm
if search_button:
    if title.strip():  # Kiểm tra xem tiêu đề có dữ liệu hay không
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM news WHERE title LIKE ?", (f"%{title}%",))
            search_results = cursor.fetchall()
            if search_results:
                st.write("Kết quả tìm kiếm:")
                for result in search_results:
                    st.write(result[0])
            else:
                st.warning("Không tìm thấy bài viết nào với tiêu đề này.")
    else:
        st.warning("Vui lòng nhập tiêu đề để tìm kiếm.")

# Xử lý nút reset để xóa trắng các trường nhập liệu
if reset_button:
    st.experimental_rerun()

# Hiển thị nội dung bài viết
content = st.text_area("Nội dung kết quả của mô hình:")

# Phản hồi của người dùng
user_feedback = st.radio("Phản hồi của bạn về kết quả:", ("Chính xác", "Không chính xác"))

# Nếu người dùng cho rằng kết quả không chính xác, cho phép nhập chỉnh sửa
corrected_content = None
if user_feedback == "Không chính xác":
    corrected_content = st.text_area("Nhập nội dung đúng:")

# Lưu phản hồi và cập nhật
if st.button("Lưu phản hồi và cập nhật"):
    if title and content and (user_feedback == "Chính xác" or corrected_content):
        # Thêm dữ liệu mới vào bảng news
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO news (title, content) 
                VALUES (?, ?)
            """, (title, corrected_content if corrected_content else content))
            conn.commit()

        st.success("Dữ liệu đã được thêm vào bảng news!")

        # Tạo lại các chunk và cập nhật embedding
        st.write("Cập nhật các chunk và embedding...")

        # Tạo các Document từ dữ liệu đã thêm
        document = Document(page_content=corrected_content if corrected_content else content)

        # Tạo các chunk từ Document
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
        chunks = text_splitter.split_documents([document])

        # Tạo lại các embedding từ chunk
        embeddings = GPT4AllEmbeddings(model_name=MODEL_NAME, gpt4all_kwargs={'allow_download': True})

        if os.path.exists(VECTOR_DB_PATH):
            db = FAISS.load_local(VECTOR_DB_PATH, embeddings, allow_dangerous_deserialization=True)
            db.add_documents(chunks)
            db.save_local(VECTOR_DB_PATH)

        st.success("Embedding đã được cập nhật!")
    else:
        st.error("Vui lòng nhập đầy đủ thông tin trước khi lưu!")
