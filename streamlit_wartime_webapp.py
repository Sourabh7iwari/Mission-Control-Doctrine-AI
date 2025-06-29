import streamlit as st
import requests
import logging
import mindsdb_sdk
import pandas as pd
import fitz  # PyMuPDF
import psycopg2
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize text splitter for semantic chunking
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ".", " "]
)

# Database connection config
DB_CONFIG = {
    "dbname": "military_db",
    "user": "military_user",
    "password": "military_pass",
    "host": "localhost",
    "port": 5433  # Matches Docker port mapping
}

MINDSDB_API_URL = "http://127.0.0.1:47334"

def query_chatbot(question):
    """Query chatbot via direct HTTP call."""
    url = f"{MINDSDB_API_URL}/api/projects/mindsdb/agents/military_doctrine_chatbot/completions"
    payload = {
        "messages": [
            {"question": question, "answer": None}
        ]
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()["message"]["content"]
    except Exception as e:
        logger.error(f"HTTP chatbot error: {e}")
        return f"❌ Chatbot unavailable. Reason: {e}"

@st.cache_data
def fetch_kb_doctrine_combinations():
    """Fetch (country, warfare_type) combos from military_kb via SDK."""
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
            if results.empty:
                return []
            return [f"{row['country']} - {row['warfare_type']}" for _, row in results.iterrows()]
        elif not results:
            return []
        elif isinstance(results[0], dict):
            return [f"{row['country']} - {row['warfare_type']}" for row in results]
        elif isinstance(results[0], list):
            return [f"{row[0]} - {row[1]}" for row in results]
        else:
            raise ValueError("Unsupported result format.")

    except Exception as e:
        logger.warning(f"Could not load doctrine combos: {e}")
        return []

def is_irrelevant_page(text):
    """Detect known irrelevant content like index, acknowledgments, etc."""
    IRRELEVANT_KEYWORDS = [
        "acknowledgment", "table of contents",
        "contents", "index", "references", "bibliography",
        "glossary", "appendix"
    ]
    return any(kw.lower() in text.lower() for kw in IRRELEVANT_KEYWORDS)

def extract_text_from_pdf(pdf_path):
    """Extract clean text from PDF with page filtering"""
    logger.info(f"📄 Reading {pdf_path}...")
    doc = fitz.open(pdf_path)
    full_text = ""
    for page_num, page in enumerate(doc):
        page_text = page.get_text().strip()
        if len(page_text) > 50 and not is_irrelevant_page(page_text):
            full_text += page_text.replace('\x00', '') + "\n"
        else:
            logger.warning(f"🗑️ Skipping page {page_num} — likely irrelevant")
    return full_text

def insert_chunks_into_postgres(country, warfare_type, chunks, source):
    """Insert doctrine chunks into PostgreSQL table"""
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
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"❌ Database error: {e}")
        return False
    except Exception as e:
        conn.rollback()
        logger.error(f"💥 Unexpected error during insertion: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def handle_doctrine_upload():
    """Streamlit form handler for doctrine upload with clear processing timeline messaging"""
    with st.form("doctrine_upload_form"):
        st.subheader("📤 Upload New Doctrine")
        
        # Info box explaining the processing timeline
        with st.expander("ℹ️ About Doctrine Processing"):
            st.markdown("""
            **Doctrine Processing Pipeline:**
            1. Your uploaded document will be immediately stored in our database
            2. Our system processes new doctrines every **2 hours**
            3. After processing, the doctrine will appear in:
               - The available doctrines list
               - Chatbot knowledge base
            4. Typical availability: **within 2 hours** of upload
            
            Note: Very large documents may take longer to process.
            """)
        
        country = st.text_input("Country", "Russia")
        warfare_type = st.selectbox(
            "Warfare Type",
            ["Naval", "Military", "Air", "Land", "Cyber", "Space", "Nuclear"]
        )
        source = st.text_input("Source Description", "Official military doctrine document")
        pdf_file = st.file_uploader("Upload PDF", type="pdf")
        
        submitted = st.form_submit_button("Upload Doctrine")
        
        if submitted and pdf_file:
            try:
                # Save uploaded file temporarily
                temp_path = f"temp_upload.pdf"
                with open(temp_path, "wb") as f:
                    f.write(pdf_file.getbuffer())
                
                # Process the PDF
                with st.spinner("Processing doctrine document..."):
                    full_text = extract_text_from_pdf(temp_path)
                    chunks = splitter.split_text(full_text)
                    
                    if insert_chunks_into_postgres(country, warfare_type, chunks, source):
                        st.success("✅ Doctrine successfully uploaded to database!")
                        # Clear cache to refresh doctrine list
                        st.cache_data.clear()
                    else:
                        st.error("❌ Failed to upload doctrine to database")
                
                # Clean up temp file
                os.remove(temp_path)
            except Exception as e:
                st.error(f"Error processing document: {e}")
                logger.error(f"Doctrine upload error: {e}")

# Streamlit UI
st.set_page_config(page_title="Military Doctrine Chatbot", layout="wide")
st.title("🪖 Military Strategy Analyst")

# Sidebar with doctrine management
with st.sidebar:
    st.title("Manage Doctrines")
    
    # Available doctrines section
    st.header("🔍 Available Doctrines")
    kb_combos = fetch_kb_doctrine_combinations()
    doctrine_choice = st.selectbox("Select Doctrines", ['All'] + kb_combos)
    
    # Doctrine upload section
    handle_doctrine_upload()

# Main chat interface
question = st.text_input(
    "Ask about military doctrines, strategies, or comparisons:",
    "Compare the naval strategies of China and America"
)

# Normalize aliases like "USA" → "America"
COUNTRY_ALIASES = {
    "USA": "America",
    "United States": "America",
    "United States of America": "America"
}
for alias, real in COUNTRY_ALIASES.items():
    if alias.lower() in question.lower():
        question = question.replace(alias, real)

# If doctrine selected, append to question
if doctrine_choice != "All":
    question += f" (Focus on {doctrine_choice})"

# Chatbot response
if st.button("Analyze"):
    with st.spinner("Consulting military databases..."):
        response = query_chatbot(question)

    st.subheader("📘 Strategic Analysis")
    st.markdown(response)
    st.caption("Data and strategy powered by MindsDB + Streamlit.")