import logging

import streamlit as st
from streamlit_chat import message
import os
import sys
from langchain_community.llms import CTransformers
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS
from sentence_transformers import SentenceTransformer

# Load SentenceTransformer model for embedding
MODEL = SentenceTransformer("maiduchuy321/vietnamese-bi-encoder-fine-tuning-for-law-chatbot")

# Set page configuration
st.set_page_config(page_title="Chatbot", page_icon="🦙", layout="wide")

# Add the processing directory to the system path to import modules
sys.path.append(os.path.abspath(os.path.join(__file__, "../../training/processing")))

# Configuration for Vector DB path
VECTOR_DB_PATH = os.path.abspath(os.path.join(__file__, "../../training/processing/data/vectorstores/db_faiss"))

def load_llm(model_file, temperature):
    """Load LLM với các thiết lập tùy chỉnh."""
    llm = CTransformers(
        model=model_file,
        model_type="llama",
        max_new_tokens=1024,
        temperature=temperature
    )
    return llm

def create_prompt(template):
    """Tạo prompt template cho mô hình."""
    prompt = PromptTemplate(template=template, input_variables=["context", "question"])
    return prompt


def create_qa_chain(prompt, llm, db):
    """Tạo chuỗi QA từ mô hình và cơ sở dữ liệu vector."""
    retriever = db.as_retriever(search_kwargs={"k": 5}, max_tokens_limit=1024)

    # Kiểm tra xem có dữ liệu từ FAISS không
    test_query = "khoản 5 Điều 57 Luật Trật tự, an toàn giao thông đường bộ 2024 quy định giấy phép lái xe"
    results = retriever.get_relevant_documents(test_query)
    if not results:
        logging.warning("No relevant documents found in FAISS.")
    else:
        logging.info(f"Found {len(results)} relevant documents in FAISS for query '{test_query}'.")

    llm_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=False,
        chain_type_kwargs={'prompt': prompt}
    )
    return llm_chain


def read_vectors_db():
    """Load cơ sở dữ liệu vector."""
    model_name = "all-MiniLM-L6-v2.gguf2.f16.gguf"
    gpt4all_kwargs = {'allow_download': True}
    embeddings = GPT4AllEmbeddings(
        model_name=model_name,
        gpt4all_kwargs=gpt4all_kwargs
    )
    # Kiểm tra và log số lượng vector hiện có trong FAISS
    try:
        db = FAISS.load_local(VECTOR_DB_PATH, embeddings, allow_dangerous_deserialization=True)
        logging.info(f"Vector database loaded with {db.index.ntotal} vectors.")
        return db
    except Exception as e:
        logging.error(f"Failed to load vector database: {e}")
        return None

# Load vector database
DB = read_vectors_db()

# Custom CSS for the app
st.markdown("""
    <style>
    .chat-container {
        max-width: 800px;
        margin: auto;
    }
    .stChatMessage {
        background-color: #f0f0f0;
        border-radius: 12px;
        padding: 12px;
        margin: 10px 0;
    }
    .stChatMessageUser {
        background-color: #007bff;
        color: white;
        border-radius: 12px;
        padding: 12px;
        margin: 10px 0;
    }
    .stChatMessageBot {
        background-color: #e0e0e0;
        color: black;
        border-radius: 12px;
        padding: 12px;
        margin: 10px 0;
    }
    .stTextInput>div>div>input {
        width: 100%;
        padding: 12px;
        border-radius: 12px;
        border: 1px solid #ccc;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize Streamlit app
st.title('Chatbot with Streamlit')

# Initialize session state for storing chat history
if 'generated' not in st.session_state:
    st.session_state['generated'] = []
if 'past' not in st.session_state:
    st.session_state['past'] = []
if 'chat_dialogue' not in st.session_state:
    st.session_state['chat_dialogue'] = []
if 'temperature' not in st.session_state:
    st.session_state['temperature'] = 0.75
if 'model_selected' not in st.session_state:
    st.session_state['model_selected'] = 'vinallama-7b-chat'

# Sidebar options
st.sidebar.header("Chatbot Settings")

# Model selection
model_option = st.sidebar.selectbox(
    'Chọn Models phù hợp:',
    ['vinallama-7b-chat', 'Meta Llama 3.1 405B', 'Meta Llama 2.7 360B', 'Meta Llama 1.2 150B']
)

# Map model options to file paths
model_paths = {
    'vinallama-7b-chat': os.path.abspath(os.path.join(__file__, "../../training/models/vinallama-7b-chat_q5_0.gguf"))
}

st.session_state['model_selected'] = model_paths[model_option]

# Temperature Slider
st.session_state['temperature'] = st.sidebar.slider(
    'Temperature',
    min_value=0.0,
    max_value=1.0,
    value=st.session_state['temperature'],
    step=0.01,
    help="Adjusts randomness of outputs, greater than 1 is random and 0 is deterministic."
)

# Max Tokens Slider
max_tokens = st.sidebar.slider(
    'Max Tokens',
    min_value=100,
    max_value=2000,
    value=800,
    step=50,
    help="Maximum number of tokens to generate. A word is generally 2-3 tokens."
)

# Top P Slider
top_p = st.sidebar.slider(
    'Top P',
    min_value=0.0,
    max_value=1.0,
    value=0.9,
    step=0.01,
    help="When decoding text, samples from the top P percentage of most likely tokens; lower to ignore less likely tokens."
)

# Load the selected model with the chosen temperature
LLM = load_llm(st.session_state['model_selected'], st.session_state['temperature'])

# Create Prompt
template = """system\nSử dụng thông tin sau đây để trả lời câu hỏi. Nếu bạn không biết câu trả lời, hãy nói không biết, đừng cố tạo ra câu trả lời\n
{context}\nuser\n{question}\nassistant"""
prompt = create_prompt(template)
LLM_CHAIN = create_qa_chain(prompt, LLM, DB)

# Clear chat history button
if st.sidebar.button("Xoá lịch sử Chat"):
    st.session_state['generated'] = []
    st.session_state['past'] = []
    st.session_state['chat_dialogue'] = []

# Display chat messages from history on app rerun
for message_item in st.session_state.chat_dialogue:
    with st.chat_message(message_item["role"]):
        st.markdown(message_item["content"])

# Accept user input
if prompt := st.chat_input("Mời bạn nhập câu hỏi: "):
    # Add user message to chat history
    st.session_state.chat_dialogue.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    response = LLM_CHAIN.invoke({"query": prompt})['result']

    # Nếu không có kết quả trả về, bot sẽ trả về thông báo mặc định
    if not response or response.lower().strip() == 'không biết':
        response = "Không có thông tin nào được cung cấp để trả lời câu hỏi này."

    # Hiển thị câu trả lời của bot trong phần hội thoại
    with st.chat_message("assistant"):
        st.markdown(f"Theo thông tin bạn nhập:\n\n{response}\n\nBạn muốn hỏi gì tiếp theo?")

    # Add assistant response to chat history
    st.session_state.chat_dialogue.append({"role": "assistant", "content": f"Theo thông tin bạn nhập:\n\n{response}\n\nBạn muốn hỏi gì tiếp theo?"})
