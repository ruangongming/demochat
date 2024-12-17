import os
import sqlite3
import streamlit as st

# Đường dẫn tới file cơ sở dữ liệu
db_path = os.path.join('training', 'processing', 'db', 'news_data.db')

# Hàm kết nối tới cơ sở dữ liệu SQLite
def get_db_connection():
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Để sử dụng tên cột thay vì chỉ số
        st.write("Connected to database successfully.")
        return conn
    except Exception as e:
        st.write(f"Failed to connect to the database: {e}")
        return None

# Hàm quay lại danh sách bài viết
def back_to_list():
    st.session_state['selected_news'] = None

# Hàm hiển thị nội dung bài viết dưới dạng HTML an toàn
def display_news_item(news_item, is_preview=True):
    if not is_preview:
        if st.button('Back to list', key='back_button'):
            back_to_list()
            st.experimental_rerun()

    st.markdown(f"### {news_item['title']}", unsafe_allow_html=True)
    if is_preview:
        st.markdown(f"{news_item['content'][:200]}...", unsafe_allow_html=True)  # Display a preview of the content
        if st.button('Read more', key=news_item['id']):
            st.session_state['selected_news'] = news_item['id']
            st.experimental_rerun()
    else:
        st.markdown(f"**URL:** {news_item['url']}", unsafe_allow_html=True)
        st.markdown(news_item['content'], unsafe_allow_html=True)
        st.markdown("---")
        if st.button('Back to list', key='back_button_bottom'):
            back_to_list()
            st.experimental_rerun()

# Hàm để hiển thị danh sách tin tức với phân trang
def display_news_list(news, page_size=5):
    num_pages = len(news) // page_size + (1 if len(news) % page_size > 0 else 0)
    if 'page_num' not in st.session_state:
        st.session_state['page_num'] = 0

    start_idx = st.session_state['page_num'] * page_size
    end_idx = start_idx + page_size
    for news_item in news[start_idx:end_idx]:
        display_news_item(news_item)

    if st.session_state['page_num'] > 0:
        if st.button('Previous', key='prev'):
            st.session_state['page_num'] -= 1
            st.experimental_rerun()
    if st.session_state['page_num'] < num_pages - 1:
        if st.button('Next', key='next'):
            st.session_state['page_num'] += 1
            st.experimental_rerun()

# Tiêu đề ứng dụng
st.title("DemoChatAlls Danh sách Tin tức")

# Thêm CSS tùy chỉnh
st.markdown("""
    <style>
    .reportview-container {
        max-width: 800px;
        margin: auto;
    }
    .stMarkdown h3 {
        font-size: 24px;
        color: #2c3e50;
    }
    .stMarkdown p {
        font-size: 18px;
        color: #34495e;
        line-height: 1.6;
    }
    .stMarkdown strong {
        color: #2c3e50;
    }
    </style>
    """, unsafe_allow_html=True)

# Thêm sidebar để quay lại danh sách bài viết
with st.sidebar:
    if st.button('Back to list'):
        back_to_list()
        st.experimental_rerun()

# Kết nối tới cơ sở dữ liệu
conn = get_db_connection()
if not conn:
    st.stop()

if 'selected_news' not in st.session_state:
    st.session_state['selected_news'] = None

if st.session_state['selected_news'] is None:
    # Lấy danh sách các bài viết, sắp xếp theo id giảm dần
    news = conn.execute('SELECT id, title, url, content FROM news ORDER BY id DESC').fetchall()
    st.write(f"Fetched {len(news)} news articles from the database.")
    # Hiển thị danh sách tin tức với phân trang
    display_news_list(news)
else:
    # Hiển thị chi tiết bài viết
    news_id = st.session_state['selected_news']
    news_item = conn.execute('SELECT id, title, url, content FROM news WHERE id = ?', (news_id,)).fetchone()
    if news_item:
        st.write(f"Displaying details for news ID: {news_id}")  # Debugging line
        display_news_item(news_item, is_preview=False)
    else:
        st.write("Bài viết không tồn tại.")
conn.close()
