import mindsdb_sdk
import logging
from time import sleep
from typing import Dict, Any


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MilitaryDoctrineAutomation:
    def __init__(self, host: str = 'http://localhost:47334'):
        """Initialize connection to MindsDB"""
        self.host = host
        self.server = None
        self._connect()

    def _connect(self, retries: int = 3, delay: int = 5):
        """Establish connection with retry logic"""
        for attempt in range(retries):
            try:
                self.server = mindsdb_sdk.connect(self.host)
                logger.info(f"Successfully connected to MindsDB at {self.host}")
                return
            except Exception as e:
                if attempt == retries - 1:
                    logger.error(f"Failed to connect after {retries} attempts")
                    raise
                logger.warning(f"Connection attempt {attempt + 1} failed. Retrying in {delay} seconds...")
                sleep(delay)

    def execute_query(self, query: str, description: str = "") -> Any:
        """Execute a SQL query with error handling"""
        try:
            logger.info(f"Executing: {description}")
            result = self.server.query(query)
            logger.info(f"Successfully executed: {description}")
            return result
        except Exception as e:
            logger.error(f"Failed to execute '{description}': {str(e)}")
            raise

    def connect_postgres_db(self, db_params: Dict[str, str]) -> None:
        """Connect to PostgreSQL database with proper existence checking"""
        try:
            # First check if database already exists
            existing_dbs = self.server.list_databases()
            logger.info(f"Existing databases: {existing_dbs}")
            
            # Check if our database is already connected
            db_names = [db.name for db in existing_dbs]
            if 'military_psql' in db_names:
                logger.info("✅ PostgreSQL connection already exists")
                return

            # Create new connection if it doesn't exist
            logger.info("Creating new PostgreSQL connection...")
            pg_connection = self.server.create_database(
                engine="pgvector",
                name="military_psql",
                connection_args={
                    "user": db_params['user'],
                    "password": db_params['password'],
                    "host": db_params['host'],
                    "port": db_params['port'],
                    "database": db_params['database']
                }
            )
            logger.info("✅ Successfully connected to PostgreSQL database")
            
            # Verify the connection
            updated_dbs = self.server.list_databases()
            updated_db_names = [db.name for db in updated_dbs]
            if 'military_psql' in updated_db_names:
                logger.info("✅ PostgreSQL connection verified")
            else:
                raise Exception("PostgreSQL connection not found after creation")

        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {str(e)}")
            raise

    def create_knowledge_base(self) -> None:
        """Create military doctrine knowledge base with hybrid approach"""
        try:
            project = self.server.get_project()
            logger.info(f"Using project: {project.name}")

            # Create knowledge base
            military_kb = project.knowledge_bases.create(
                name='military_kb',
                embedding_model={
                    'provider': 'ollama',
                    'model_name': 'nomic-embed-text',
                    'base_url': 'http://ollama:11434'
                },
                storage=self.server.databases.military_psql.tables.storage_table,
                metadata_columns=['country', 'warfare_type'],
                content_columns=['chunk'],
                id_column='doc_id',
            )
            logger.info(f"Knowledge base '{military_kb.name}' created successfully!")

        except Exception as e:
            logger.error(f"Setup failed: {str(e)}")
            raise

        
if __name__ == "__main__":
    POSTGRES_CONFIG = {
        'user': 'military_user',
        'password': 'military_pass',
        'host': 'postgres',  
        'port': '5432',     
        'database': 'military_db'
    }

    try:
        logger.info("Starting military doctrine setup...")
        automation = MilitaryDoctrineAutomation()
        
        automation.connect_postgres_db(POSTGRES_CONFIG)
        
        automation.create_knowledge_base()
        

    except Exception as e:
        logger.error(f"Setup failed: {str(e)}")