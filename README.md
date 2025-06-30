# 🪖 Control Room : Doctrine Ai

A comprehensive platform for analyzing military doctrines using AI-powered knowledge bases, with capabilities for document ingestion, semantic search, and strategic analysis.

## 🚀 System Architecture

```
Ollama (Embeddings) ←→ MindsDB (AI/ML Layer) ←→ PostgreSQL (Vector DB)
       ↑
Streamlit Web Interface
```

## 📋 Prerequisites

- Docker Desktop ([Windows](https://docs.docker.com/desktop/install/windows-install/) | [Mac](https://docs.docker.com/desktop/install/mac-install/) | [Linux](https://docs.docker.com/desktop/install/linux-install/))
- Python 3.9+
- Git

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/Sourabh7iwari/Mission-Control-Doctrine-AI.git
cd military-doctrine-analysis
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up the environment
Run the setup script based on your OS:

#### Linux/macOS
```bash
chmod +x setup.sh
./setup.sh
```

#### Windows (PowerShell)
```powershell
.\setup.ps1  # See Windows-specific setup section below
```

## 🐋 Windows-Specific Setup

Create `setup.ps1` with:
```powershell
Write-Host "=== Starting Knowledge Base Setup ==="

# Verify Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Docker not found. Install Docker Desktop first."
    exit 1
}

Write-Host "1/4 Starting Ollama container..."
docker compose up -d ollama

Write-Host "2/4 Waiting for Ollama initialization (10 seconds)..."
Start-Sleep -Seconds 10

Write-Host "3/4 Pulling lightweight embedding model: nomic-embed-text"
docker compose exec ollama ollama pull nomic-embed-text

Write-Host "✅ Models available:"
docker compose exec ollama ollama list

Write-Host "4/4 Start MindsDB..."
docker compose up -d

Write-Host "=== Setup Complete ==="
Write-Host "Verify containers: docker compose ps"
Write-Host "Access MindsDB at: http://localhost:47334"
```

## 🧠 MindsDB Configuration

After containers are running:

1. Access MindsDB Studio at [http://localhost:47334](http://localhost:47334)
2. Execute the following SQL commands in sequence:

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
all though it shows attribute error ''NoneType' object has no attribute 'affected_rows'' but the operation gets successfull.


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
```sql
DROP AGENT IF EXISTS military_doctrine_chatbot;
```

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
WHERE question = 'Compare the air doctrine of America and Russia in detail';
```

## ⏳ Processing Timeline

- **Initial data load**: ~20-30 minutes (depending on hardware)
- **Scheduled jobs**:
  - New doctrine ingestion: Every 2 hours
  - Summary generation: Every 6 hours
- **Document availability**: New uploads appear in system within 2 hours

## 🖥️ Running the Web Interface

```bash
streamlit run streamlit_wartime_webapp.py
```

Access the web interface at [http://localhost:8501](http://localhost:8501)



## working demo video of web app
[![Watch Demo Video](https://img.youtube.com/vi/8cAuZiVjXR0/maxresdefault.jpg)](https://youtu.be/8cAuZiVjXR0)
inserting new doctrine will be ready to chat after two hours as the kb insertion job run every 2 hours

## 🔄 System Maintenance

### View active jobs
```sql
show jobs;
```

### Monitor system health
```bash
docker compose logs -f  # View container logs
```

## 📚 Data Flow

1. **Upload**: PDFs added via Streamlit interface
2. **Processing**:
   - Chunking and embedding (immediate)
   - Knowledge base integration (every 2 hours), checking source every 2 hours
   - Summary generation (every 6 hours), generating data from existing table and ingesting it to another table 
3. **Analysis**: Available through chatbot after processing

## 🛑 Troubleshooting

### Common Issues

1. **Port conflicts**:
   - Ensure ports 47334 (MindsDB), 11434 (Ollama), and 5432 (Postgres) are free

2. **Model download failures**:
   ```bash
   docker compose exec ollama ollama pull nomic-embed-text
   ```

3. **Database connection issues**:
   Verify Postgres is running:
   ```bash
   docker compose ps
   ```

## 📜 License

[MIT License](LICENSE)

```

This README includes:

1. Clear multi-OS setup instructions
2. Complete MindsDB configuration workflow
3. Processing timeline expectations
4. System monitoring commands
5. Troubleshooting guide
6. Visual architecture diagram
7. Windows-specific PowerShell script
8. Maintenance procedures

The document manages user expectations about processing times and provides all necessary commands in an organized, professional format.