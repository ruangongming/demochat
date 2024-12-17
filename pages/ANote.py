import streamlit as st


#Config
st.set_page_config(layout="wide", page_icon="🦙", page_title="Demo1 | Chat-Bot 🤖")


#Title
st.markdown(
    """
    <h2 style='text-align: center;'>Demo1, trợ lý thử nghiệm 🤖</h1>
    """,
    unsafe_allow_html=True,)

st.markdown("---")


#Description
st.markdown(
    """
    <h5 style='text-align:center;'>Tôi là Demo1, một chatbots thông minh được tạo ra bằng cách kết hợp
 điểm mạnh của Langchain và Streamlit, một số models LLMs nâng cao khác tuỳ thuộc vào điều kiện thực tế. 
 Tôi sử dụng các mô hình ngôn ngữ lớn để cung cấp tương tác theo ngữ cảnh. 
 Mục tiêu của tôi là giúp bạn hiểu rõ hơn về dữ liệu của mình và học lại những gì bạn cung cấp.
 Tôi đang thử nghiệm hỗ trợ bản ghi PDF, TXT, CSV, SQL 🧠</h5>
    """,
    unsafe_allow_html=True)
st.markdown("---")


#Demo Chatalls
st.subheader("🚀 Demo Chatalls chức năng")
st.write("""
- **ANote**: Danh sách các chức năng có trong hệ thống.
- **Home** (Trang chủ): Đọc tin tức nhanh của nhiều bài báo, có thể xem cả link gốc của bài báo [Ví dụ dữ liệu đang dùng như Thư viện pháp luật - Hỏi đáp pháp luật về Vi phạm hành chính](https://thuvienphapluat.vn/hoi-dap-phap-luat/vi-pham-hanh-chinh)
- **ChatBot**: Trò chuyện về nội dung trong SQL database hoặc file dữ liệu (PDF, TXT, CSV) đã training sẵn với [vectorstore - FAISS - thuật toán tìm kiếm của facebook](https://github.com/facebookresearch/faiss) (lập chỉ mục các phần hữu ích (tối đa 4) phản hồi người dùng) | 
hoạt động với mô hình Virtual Interactive Large Language Model - một mô hình ngôn ngữ lớn trên thư viện Hugging Face [VLIM](https://huggingface.co/vilm/vinallama-7b-chat) & [GPT4AllEmbeddings](https://api.python.langchain.com/en/latest/embeddings/langchain_community.embeddings.gpt4all.GPT4AllEmbeddings.html), [RAG](https://viblo.asia/p/chatgpt-series-5-tim-hieu-ve-retrieval-augmented-generation-rag-Ny0VGRd7LPA)
""")
st.write("""
- **FileControl (beta - chưa interview)** gồm các chức năng sau:
- **ConvertFile:** Chức năng Chuyển đổi định dạng dữ liệu giữa các file được upload lên (PDF, TXT, CSV)
- **RawData:** Chức năng thu thập xử lý dữ liệu thô, lưu dữ liệu nội dung trong SQL database hoặc file dữ liệu (PDF, TXT, CSV) 
- **Các chức năng khác chưa phát triển thêm ý tưởng...**
""")

st.markdown("---")



#Đóng góp
st.markdown("### 🎯 Đồng phát triển")
st.markdown("""
**Demo1 đang được phát triển thường xuyên. Vui lòng đóng góp và giúp tôi làm cho nó nhận thức nhiều hơn về các bài toán và dữ liệu thực tế trong tương lai!**
""", unsafe_allow_html=True)

st.write("""
[Document](https://sec.vnpt.vn/2024/04/xay-dung-chatbot-don-gian-voi-langchain/)""")