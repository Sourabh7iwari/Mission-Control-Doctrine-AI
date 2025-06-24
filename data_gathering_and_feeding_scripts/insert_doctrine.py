import fitz  # PyMuPDF
import psycopg2
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Initialize text splitter for semantic chunking
splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
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

COUNTRY_NAME = "America"
WARFARE_TYPE = "Air"  # blank for general doctrine, or specify like "naval", "air", etc.
PDF_FILE_PATH = "Doctrine_pdfs/AmericaAirDoctrine.pdf"
SOURCE_DESCRIPTION = "Official United States Air Force Website - (doctrine.af.mil)"

def test_connection():
    """Test if database is reachable"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        result = cursor.fetchone()
        logging.info(f"Connected to DB: {result}")
        cursor.close()
        conn.close()
    except Exception as e:
        logging.error(f"❌ Connection failed: {e}")
        raise

def extract_text_from_pdf(pdf_path):
    """Extract clean text from PDF with page filtering"""
    logging.info(f"📄 Reading {pdf_path}...")
    doc = fitz.open(pdf_path)
    full_text = ""
    for page_num, page in enumerate(doc):
        page_text = page.get_text().strip()
        # Skip empty or irrelevant pages
        if len(page_text) > 50 and not is_irrelevant_page(page_text):
            full_text += page_text.replace('\x00', '') + "\n"
        else:
            logging.warning(f"🗑️ Skipping page {page_num} — likely irrelevant")
    return full_text

def is_irrelevant_page(text):
    """Detect known irrelevant content like index, acknowledgments, etc."""
    IRRELEVANT_KEYWORDS = [
        "acknowledgment", "copyright", "table of contents",
        "contents", "index", "references", "bibliography",
        "glossary", "appendix"
    ]
    return any(kw.lower() in text.lower() for kw in IRRELEVANT_KEYWORDS)

def chunk_text(text):
    """Split long text into semantic chunks"""
    logging.info(f"🧱 Chunking into 2000-character segments...")
    return splitter.split_text(text)

def insert_chunks_into_postgres(country, warfare_type, chunks, source):
    """Insert doctrine chunks into PostgreSQL table"""
    logging.info(f"📦 Inserting doctrine data for {country} ({warfare_type})...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        for i, chunk in enumerate(chunks):
            doc_id = f"{country.lower()}_{warfare_type}_doctrine_{i}" if warfare_type else f"{country.lower()}_doctrine_{i}"
            logging.debug(f"Inserting {doc_id}...")

            cursor.execute("""
                INSERT INTO military_doctrines (doc_id, country, warfare_type, chunk, source)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (doc_id) DO NOTHING;
            """, (doc_id, country, warfare_type, chunk, source))

            if cursor.statusmessage == 'INSERT 0 0':
                logging.warning(f"⚠️ Skipped {doc_id} due to conflict")
            else:
                logging.info(f"✅ Inserted {doc_id}")

        conn.commit()
        logging.info(f"✅ Successfully inserted {len(chunks)} chunks")

    except psycopg2.Error as e:
        conn.rollback()
        logging.error(f"❌ Database error: {e}")
    except Exception as e:
        conn.rollback()
        logging.error(f"💥 Unexpected error during insertion: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    try:
        test_connection()
        full_text = extract_text_from_pdf(PDF_FILE_PATH)
        chunks = chunk_text(full_text)
        insert_chunks_into_postgres(COUNTRY_NAME, WARFARE_TYPE, chunks, SOURCE_DESCRIPTION)
    except Exception as e:
        logging.critical(f"🛑 Critical error: {e}")