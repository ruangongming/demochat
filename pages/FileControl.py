import os
import re
import sqlite3
import streamlit as st
from bs4 import BeautifulSoup

# Function to clean HTML tags from the content
def clean_html(content_html):
    soup = BeautifulSoup(content_html, 'html.parser')
    return soup.get_text()

# Function to save data to a text file
def save_to_txt(title, content_text, id, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Sanitize title for file naming
    file_name = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_') + ".txt"
    file_path = os.path.join(output_dir, file_name)

    # Check if file already exists
    if os.path.exists(file_path):
        st.warning(f"File {file_name} already exists. Skipping...")
        return

    # Write the title and content to the text file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(f"Title: {title}\n\n")
        file.write(f"Content:\n{content_text}")

    st.success(f"Saved TXT to {file_path}")
    st.write(f"Saved TXT to {file_path}")

# Function to process and save data from the database
def process_from_db(db_path, output_dir):
    processed_ids = set()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Fetch id, title, and content_html from the database
        cursor.execute('SELECT id, title, content_html FROM news')
        rows = cursor.fetchall()

        for row in rows:
            id, title, content_html = row

            # Skip if ID has already been processed
            if id in processed_ids:
                st.write(f"ID {id} has already been processed. Skipping...")
                continue

            # Clean the HTML content
            content_text = clean_html(content_html)

            # Save to a text file
            save_to_txt(title, content_text, id, output_dir)
            processed_ids.add(id)

    except sqlite3.Error as err:
        st.error(f"SQLite Error: {err}")
    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        conn.close()

# Function to process and save data from a file
def process_from_file(file, output_dir):
    try:
        file_content = file.read().decode('utf-8')
        content_text = clean_html(file_content)
        title = file.name
        save_to_txt(title, content_text, 0, output_dir)
    except Exception as e:
        st.error(f"Error: {e}")

# Streamlit app
st.title("Convert HTML Content to TXT")

# Select mode
mode = st.radio("Select Conversion Mode:", ("Convert from Database", "Convert from File"))

output_dir = os.path.join('training', 'processing', 'data', 'convert' , 'txt_files')
db_path = os.path.join('training', 'processing', 'db', 'news_data.db')

if mode == "Convert from Database":
    st.write("Processing from database...")
    process_from_db(db_path, output_dir)
elif mode == "Convert from File":
    uploaded_file = st.file_uploader("Choose a file...", type=["html", "htm"])
    if uploaded_file is not None:
        process_from_file(uploaded_file, output_dir)

# Display news items from database
def display_news(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Fetch id, title, and content_html from the database
        cursor.execute('SELECT id, title, content_html FROM news')
        rows = cursor.fetchall()

        for row in rows:
            id, title, content_html = row
            st.write(f"### {title}")
            if st.button(f"Read more", key=f"button_{id}"):
                st.write(clean_html(content_html))
            st.write("---")

    except sqlite3.Error as err:
        st.error(f"SQLite Error: {err}")
    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        conn.close()

if st.button("Show News List"):
    display_news(db_path)
