import os
from pathlib import Path
from dotenv import load_dotenv
from vertexai.preview import rag
import vertexai
import logging
from google.api_core import exceptions

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_env():
    """Load environment variables from .env file in parent directory"""
    # Get the parent directory of the current script
    parent_dir = Path(__file__).parent.parent
    env_path = parent_dir / '.env'
    
    # Load the .env file
    if not load_dotenv(env_path):
        raise EnvironmentError(f"Could not load .env file at {env_path}")
    
    # Get PROJECT_ID from environment variables
    project_id = os.getenv('PROJECT_ID')
    if not project_id:
        raise EnvironmentError("PROJECT_ID not found in .env file")
    
    return project_id

def delete_all_corpora():
    # Get project ID from .env
    try:
        project_id = load_env()
        logger.info(f"Loaded PROJECT_ID from .env")
    except EnvironmentError as e:
        logger.error(f"Environment error: {e}")
        return

    # Location constant
    LOCATION = "us-central1"

    # Initialize Vertex AI
    vertexai.init(project=project_id, location=LOCATION)

    try:
        # List all corpora
        corpora_pager = rag.list_corpora()
        
        corpus_count = 0
        deleted_count = 0

        # Iterate through the pager and delete each corpus
        for corpus in corpora_pager:
            corpus_count += 1
            try:
                rag.delete_corpus(name=corpus.name)
                logger.info(f"Successfully deleted corpus: {corpus.name}")
                deleted_count += 1
            except exceptions.GoogleAPICallError as e:
                logger.error(f"Error deleting corpus {corpus.name}: {e}")

        logger.info(f"Deletion process completed. Attempted to delete {corpus_count} corpora, successfully deleted {deleted_count}.")

    except exceptions.GoogleAPICallError as e:
        logger.error(f"Error listing corpora: {e}")

if __name__ == "__main__":
    delete_all_corpora()