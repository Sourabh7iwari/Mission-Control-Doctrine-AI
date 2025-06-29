# optional
-- Testing Creation of Knowledge Base only if not existssql --
```sql
CREATE KNOWLEDGE_BASE IF NOT EXISTS testing_military_kb USING
  embedding_model = {
    "provider": "ollama",
    "model_name": "nomic-embed-text",
    "base_url": "http://ollama:11434"
  },
  metadata_columns = ['country', 'branch', 'category'],
  content_columns = ['strategy_text'],
  id_column = 'doc_id';
```
--Testing of Insertion sample data into KB
```sql
INSERT INTO testing_military_kb (doc_id, country, branch, category, strategy_text)
VALUES 
  ('R001', 'Russia', 'Army', 'Hybrid Warfare', 'Hybrid warfare combines conventional and unconventional tactics including cyber attacks and disinformation campaigns.'),
  ('I001', 'India', 'Navy', 'Naval Doctrine', 'India''s naval doctrine emphasizes maritime security and regional dominance in the Indian Ocean.'),
  ('C001', 'China', 'Air Force', 'Air Superiority', 'China''s air force focuses on securing airspace and enhancing long-range strike capabilities.');
```



# Mandotory operations (serial wise)
### connecting mindsdb to postgres military_db
```sql
CREATE DATABASE military_psql
WITH ENGINE = 'pgvector',
PARAMETERS = {
    "user": "military_user",
    "password": "military_pass",
    "host": "postgres",
    "port": "5432",
    "database": "military_db"
};
```

### Creating the knowledge base
```sql
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
```

## Inserting the data into kb
```sql
-- use this for first time 
INSERT INTO military_kb
SELECT d.doc_id, d.country, d.warfare_type, d.chunk
FROM military_psql.military_doctrines AS d
ORDER BY d.doc_id
USING kb_no_upsert = true;

-- or 

-- if kb already has data 
INSERT INTO military_kb
SELECT d.doc_id, d.country, d.warfare_type, d.chunk
FROM military_psql.military_doctrines AS d
LEFT JOIN military_kb AS kb ON d.doc_id = kb.id
WHERE kb.id IS NULL
ORDER BY d.doc_id
USING kb_no_upsert = true;
```
-- takes around 2000 seconds in my low end system ;-(

## Testing the kb (optional)
```sql
SELECT * FROM military_kb 
WHERE content = 'counter china and russia' and country="America" and relevance >= 0.65;
```

## create index on the knowledge base
```sql
CREATE INDEX ON KNOWLEDGE_BASE military_kb;
```

## creating job for ingesting chunk into kb
```sql
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
EVERY 4 HOURS
IF (
    SELECT COUNT(*) > 0
    FROM military_psql.military_doctrines
    WHERE doc_id NOT IN (
        SELECT DISTINCT id
        FROM military_kb
    )
);
```

## create engine
```sql
CREATE ML_ENGINE google_gemini_engine
FROM google_gemini
USING
    api_key = ''; -- your actual API key
```

## create Model for summary creation
```sql
CREATE MODEL military_doctrine_summarizer
PREDICT summary
USING
    engine = 'google_gemini_engine',
    model_name = 'gemini-1.5-flash',
    prompt_template = 'You are a military analyst. Summarize the following military doctrine text for {{country}} regarding {{warfare_type}}. Provide a concise, comprehensive summary that captures the key strategic concepts, tactics, and principles in coherent 300–400 word explanation:

{{chunk}}

Summary:';
```

## check its status(optional)
```sql
SELECT name, status, training_options 
FROM mindsdb.models 
WHERE name = 'military_doctrine_summarizer';
```


## Create comprehensive summaries and insert them in summary_table
```sql
INSERT INTO military_psql.doctrine_summaries (id, country, warfare_type, summary_text)
SELECT 
    CONCAT(grouped.country, '_', grouped.warfare_type, '_master_summary') as id,
    grouped.country,
    grouped.warfare_type,
    output.summary as summary_text
FROM (
    SELECT 
        country,
        warfare_type,
        STRING_AGG(chunk, '\n\n') as chunk,
        ROW_NUMBER() OVER (ORDER BY country, warfare_type) as rn
    FROM military_psql.military_doctrines
    WHERE NOT EXISTS (
        SELECT 1 
        FROM military_psql.doctrine_summaries ds 
        WHERE ds.id = CONCAT(military_doctrines.country, '_', military_doctrines.warfare_type, '_master_summary')
    )
    GROUP BY country, warfare_type
    ORDER BY country, warfare_type
    LIMIT 1 -- creating only one summary for testing will make job if successfull
) as grouped,
military_doctrine_summarizer as output
WHERE output.chunk = grouped.chunk
  AND output.country = grouped.country
  AND output.warfare_type = grouped.warfare_type;
```



## creating job for summarizing doctrines
```sql
CREATE JOB process_military_doctrines (
    INSERT INTO military_psql.doctrine_summaries (id, country, warfare_type, summary_text)
    SELECT 
        CONCAT(grouped.country, '_', grouped.warfare_type, '_master_summary') as id,
        grouped.country,
        grouped.warfare_type,
        output.summary as summary_text
    FROM (
        SELECT 
            country,
            warfare_type,
            STRING_AGG(chunk, '\n\n') as chunk
        FROM military_psql.military_doctrines
        GROUP BY country, warfare_type
        HAVING NOT EXISTS (
            SELECT 1 
            FROM military_psql.doctrine_summaries ds 
            WHERE ds.id = CONCAT(country, '_', warfare_type, '_master_summary')
        )
        ORDER BY country, warfare_type
        LIMIT 1
    ) as grouped,
    military_doctrine_summarizer as output
    WHERE output.chunk = grouped.chunk
      AND output.country = grouped.country
      AND output.warfare_type = grouped.warfare_type
)
EVERY 6 hours
IF (
    SELECT COUNT(*) 
    FROM military_psql.military_doctrines md
    WHERE NOT EXISTS (
        SELECT 1 
        FROM military_psql.doctrine_summaries ds 
        WHERE ds.id = CONCAT(md.country, '_', md.warfare_type, '_master_summary')
    )
);
```
## Remove the agent if already exist
DROP AGENT IF EXISTS military_doctrine_chatbot;

## creating chatbot agent
```sql
CREATE AGENT military_doctrine_chatbot
USING
    model = 'gemini-2.0-flash',
    google_api_key = '',
    include_knowledge_bases = ['mindsdb.military_kb'],
    include_tables = ['military_psql.military_personnel'],
    prompt_template = '
        You are an expert in military doctrine with access to two data sources:
        - Knowledge base: `military_kb`
        - Table: `military_personnel`
        
        ### ⚠️ VERY IMPORTANT
        - Valid `warfare_type` values in `military_kb` are: 
        - `Military`
        - `Naval`
        - `Air`
        - `Cyber`
        - `Space`
        - `Hybrid`

        Available data sources:
        - military_kb: Knowledge base containing military doctrine content in chunks having metadata country(first letter capital) and warfare_type(first letter capital)
        - military_personnel: Statistical data about military forces including:
          * country: Nation name
          * active_military: Number of active military personnel
          * reserve_military: Number of reserve personnel  
          * paramilitary: Number of paramilitary forces
          * total: Total military personnel
          * per_1000_total: Military personnel per 1000 total population
          * per_1000_active: Active military per 1000 population
          * ref: Reference/source information
        - military_doctrines (
                doc_id text NOT NULL,
                country text NOT NULL,
                warfare_type text,
                chunk text NOT NULL,
                source text)
        
        When answering questions:
        1. Use the knowledge base for doctrinal concepts, strategies, and tactical information
        2. Use military_personnel data for force structure, comparative analysis, and statistical insights
        3. Combine both sources when relevant (e.g., relating doctrine to force capabilities)
        4. Provide specific numbers and statistics when discussing military capabilities
        5. Reference countries and warfare types appropriately
        6. Maintain analytical precision and cite data sources

        User question: {{question}}

        Response:
';

```


## Testing the chatbot
```sql
SELECT answer
FROM military_doctrine_chatbot 
WHERE question = 'Compare the air doctrine of America and Russia in detail';```