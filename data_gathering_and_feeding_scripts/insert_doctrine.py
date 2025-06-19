import fitz 
import psycopg2
import textwrap

DB_CONFIG = {
    "dbname": "military_db",
    "user": "military_user",
    "password": "military_pass",
    "host": "localhost",
    "port": 5432
}

# Set these two values before running
COUNTRY_NAME = "China"
WARFARE_TYPE = "Air" # Leave empty if not applicable (combined arms, air, naval, etc.)
PDF_FILE_PATH = "Doctrine_pdfs/Cliff-EvolutionChineseAir-2011.pdf" 
SOURCE_DESCRIPTION = "Book Title: Shaking the Heavens and Splitting the Earth, chapter 3 - jstor.org"

CHUNK_SIZE = 2000 

def test_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    print(cursor.fetchone())
    cursor.close()
    conn.close()

def extract_text_from_pdf(pdf_path):
    print(f"📄 Reading {pdf_path}...")
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        page_text = page.get_text()
        # Remove NUL characters
        full_text += page_text.replace('\x00', '')
    return full_text

def chunk_text(text, size=CHUNK_SIZE):
    """Split long text into semantic chunks"""
    print(f"🧱 Chunking into {size}-character segments...")
    return textwrap.wrap(text, size, break_long_words=False, replace_whitespace=False)

def insert_chunks_into_postgres(country, warfare_type, chunks, source):
    """Insert doctrine chunks into PostgreSQL"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        for i, chunk in enumerate(chunks):
            doc_id = f"{country.lower()}_{warfare_type}_doctrine_{i}"
            print(f"Inserting {doc_id}...")  # <- Add this line
            cursor.execute("""
                INSERT INTO military_doctrines (doc_id, country, warfare_type, chunk, source)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (doc_id) DO NOTHING;
            """, (doc_id, country, warfare_type, chunk, source))
            if cursor.statusmessage == 'INSERT 0 0':
                print(f"⚠️ Skipped {doc_id} due to conflict")
            else:
                print(f"✅ Inserted {doc_id}")

        conn.commit()
        print(f"✅ Inserted {len(chunks)} chunks for {country} ({warfare_type})")

    except Exception as e:
        print(f"❌ Error inserting data: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print(test_connection())
    try:
        full_text = extract_text_from_pdf(PDF_FILE_PATH)
        chunks = chunk_text(full_text, CHUNK_SIZE)
        insert_chunks_into_postgres(COUNTRY_NAME, WARFARE_TYPE, chunks, SOURCE_DESCRIPTION)
    except Exception as e:
        print(f"💥 Main error: {e}")