-- Testing Creation of Knowledge Base only if not exists
CREATE KNOWLEDGE_BASE IF NOT EXISTS military_kb USING
  embedding_model = {
    "provider": "ollama",
    "model_name": "nomic-embed-text",
    "base_url": "http://ollama:11434"
  },
  metadata_columns = ['country', 'branch', 'category'],
  content_columns = ['strategy_text'],
  id_column = 'doc_id';

--Testing of Insertion sample data into KB
INSERT INTO military_kb (doc_id, country, branch, category, strategy_text)
VALUES 
  ('R001', 'Russia', 'Army', 'Hybrid Warfare', 'Hybrid warfare combines conventional and unconventional tactics including cyber attacks and disinformation campaigns.'),
  ('I001', 'India', 'Navy', 'Naval Doctrine', 'India''s naval doctrine emphasizes maritime security and regional dominance in the Indian Ocean.'),
  ('C001', 'China', 'Air Force', 'Air Superiority', 'China''s air force focuses on securing airspace and enhancing long-range strike capabilities.');


-- connecting mindsdb to postgres military_db
CREATE DATABASE military_psql
WITH ENGINE = 'pgvector',
PARAMETERS = {
    "user": "military_user",
    "password": "military_pass",
    "host": "postgres",
    "port": "5432",
    "database": "military_db"
};

-- Creating the knowledge base
CREATE KNOWLEDGE_BASE military_kb USING
  storage = military_psql.storage_table,
  embedding_model = {
    "provider": "ollama",
    "model_name": "nomic-embed-text",
    "base_url": "http://ollama:11434"
  },
  metadata_columns = ['country', 'warfare_type'],
  content_columns = ['chunk'],
  id_column = 'doc_id';

-- Inserting the data into kb
INSERT INTO military_kb
SELECT d.doc_id, d.country, d.warfare_type, d.chunk
FROM military_psql.military_doctrines AS d
LEFT JOIN military_kb AS kb
ON d.doc_id = kb.id
WHERE kb.id IS NULL
USING kb_no_upsert = true;
--took 2000 seconds to complete(first time) ;-(

-- Testing the kb 
SELECT * FROM military_kb 
WHERE content = 'counter china and pakistan' and warfare_type='Naval' and country="India" and relevance >= 0.72;

-- create index on the knowledge base
CREATE INDEX ON KNOWLEDGE_BASE military_kb;


-- creating job for ingesting chunk into kb
CREATE JOB ingest_new_doctrine_chunks
AS (
    INSERT INTO military_kb
    SELECT doc_id, country, warfare_type, chunk
    FROM military_psql.military_doctrines
    WHERE doc_id NOT IN (
        SELECT DISTINCT id
        FROM military_kb
    )
    USING kb_no_upsert = true
)
EVERY 6 HOURS
IF (
    SELECT COUNT(*) > 0
    FROM military_psql.military_doctrines
    WHERE doc_id NOT IN (
        SELECT DISTINCT id
        FROM military_kb
    )
);