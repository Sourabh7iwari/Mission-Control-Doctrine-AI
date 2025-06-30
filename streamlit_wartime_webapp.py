import streamlit as st
import requests
import logging
import mindsdb_sdk
import pandas as pd
import fitz  # PyMuPDF
import psycopg2
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os

# ----------------------------------
# ✅ Logging Setup
# ----------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------------
# ✅ Config
# ----------------------------------
DB_CONFIG = {
    "dbname": "military_db",
    "user": "military_user",
    "password": "military_pass",
    "host": "localhost",
    "port": 5433
}

MINDSDB_API_URL = "http://127.0.0.1:47334"

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ".", " "]
)

COUNTRY_ALIASES = {
    "USA": "America",
    "United States": "America",
    "United States of America": "America"
}

# ----------------------------------
# ✅ Backend Functions
# ----------------------------------
def query_chatbot(question):
    url = f"{MINDSDB_API_URL}/api/projects/mindsdb/agents/military_doctrine_chatbot/completions"
    payload = {"messages": [{"question": question, "answer": None}]}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()["message"]["content"]
    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return f"❌ Chatbot unavailable. Reason: {e}"

@st.cache_data
def fetch_kb_doctrine_combinations():
    try:
        server = mindsdb_sdk.connect()
        project = server.get_project()
        results = project.query("""
            SELECT DISTINCT 
                REPLACE(REPLACE(JSON_EXTRACT(metadata, '$.country'), '"', ''), "'", '') AS country,
                REPLACE(REPLACE(JSON_EXTRACT(metadata, '$.warfare_type'), '"', ''), "'", '') AS warfare_type
            FROM military_kb
        """).fetch()

        if isinstance(results, pd.DataFrame):
            return [f"{row['country']} - {row['warfare_type']}" for _, row in results.iterrows()]
        elif isinstance(results[0], dict):
            return [f"{row['country']} - {row['warfare_type']}" for row in results]
        elif isinstance(results[0], list):
            return [f"{row[0]} - {row[1]}" for row in results]
        return []

    except Exception as e:
        logger.warning(f"Doctrine combo load failed: {e}")
        return []

def is_irrelevant_page(text):
    keywords = ["acknowledgment", "table of contents", "index", "references", "bibliography", "glossary", "appendix"]
    return any(kw.lower() in text.lower() for kw in keywords)

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page_num, page in enumerate(doc):
        text = page.get_text().strip()
        if len(text) > 50 and not is_irrelevant_page(text):
            full_text += text.replace('\x00', '') + "\n"
        else:
            logger.warning(f"🗑️ Skipping page {page_num} as irrelevant")
    return full_text

def insert_chunks_into_postgres(country, warfare_type, chunks, source):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        for i, chunk in enumerate(chunks):
            doc_id = f"{country.lower()}_{warfare_type.lower()}_doctrine_{i}"
            cursor.execute("""
                INSERT INTO military_doctrines (doc_id, country, warfare_type, chunk, source)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (doc_id) DO NOTHING;
            """, (doc_id, country, warfare_type, chunk, source))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Insertion error: {e}")
        return False
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

def handle_doctrine_upload():
    with st.form("doctrine_upload_form"):
        st.subheader("📤 Upload New Doctrine")

        with st.expander("ℹ️ How Doctrine Processing Works"):
            st.markdown("""
            **Pipeline Overview:**
            - Doctrines are stored immediately.
            - The KB is updated every **2 hours**.
            - Doctrine will appear in dropdown + chatbot after update.
            - ⚠️ Large documents may require more time.
            """)

        country = st.text_input("Country", "Russia")
        warfare_type = st.selectbox("Warfare Type", ["Naval", "Military", "Air", "Land", "Cyber", "Space", "Nuclear"])
        source = st.text_input("Source Description", "Official military doctrine document")
        pdf_file = st.file_uploader("Upload PDF", type="pdf")

        submitted = st.form_submit_button("Upload Doctrine")
        if submitted and pdf_file:
            try:
                with open("temp_upload.pdf", "wb") as f:
                    f.write(pdf_file.getbuffer())
                with st.spinner("⏳ Processing PDF..."):
                    text = extract_text_from_pdf("temp_upload.pdf")
                    chunks = splitter.split_text(text)
                    if insert_chunks_into_postgres(country, warfare_type, chunks, source):
                        st.success("✅ Doctrine successfully uploaded!")
                        st.cache_data.clear()
                    else:
                        st.error("🚫 Upload failed")
                os.remove("temp_upload.pdf")
            except Exception as e:
                st.error(f"🚨 Error: {e}")

# ----------------------------------
# ✅ UI Layout
# ----------------------------------
st.set_page_config(page_title="Military Doctrine Chatbot", layout="wide")
st.title("🪖 Military Strategy Analyst")

# Sidebar
with st.sidebar:
    st.title("📚 Doctrine Manager")
    st.markdown("""---""")
    st.header("🔍 Available Doctrines")
    kb_combos = fetch_kb_doctrine_combinations()
    doctrine_choice = st.selectbox("Doctrine Filter", ['All'] + kb_combos)
    st.markdown("""---""")
    handle_doctrine_upload()

# Main QA section
question = st.text_input("Ask your question:", "Compare the naval strategies of China and America")

for alias, real in COUNTRY_ALIASES.items():
    if alias.lower() in question.lower():
        question = question.replace(alias, real)

if doctrine_choice != "All":
    question += f" (Focus on {doctrine_choice})"

if st.button("Analyze"):
    with st.spinner("🔍 Analyzing military data..."):
        response = query_chatbot(question)
    st.subheader("📘 Strategic Analysis")
    st.markdown(response)
    st.caption("Data powered by 🧠 MindsDB & Streamlit")
