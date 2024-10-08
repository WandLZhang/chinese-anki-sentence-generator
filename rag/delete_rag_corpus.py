from vertexai.preview import rag
import vertexai
import logging
from google.api_core import exceptions

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Project details
PROJECT_ID = "<redacted>"  # Replace with your actual project ID if different
LOCATION = "us-central1"

def delete_all_corpora():
    # Initialize Vertex AI
    vertexai.init(project=PROJECT_ID, location=LOCATION)

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
