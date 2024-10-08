from vertexai.preview import rag
import vertexai
import logging
import os
from google.api_core import exceptions, retry

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Project and corpus details
PROJECT_ID = "<redacted>"
LOCATION = "us-central1"
DISPLAY_NAME = "wordshk"
FILE_PREFIX = "wordshk-dictionary_"
FILE_EXTENSION = ".txt"
NUM_CHUNKS = 5
LOCAL_FILE_DIR = ""  # Update this with your actual local directory path

@retry.Retry()
def upload_file_with_retry(corpus_name, file_path, display_name, description):
    """Upload a file to the RAG corpus with retry logic."""
    return rag.upload_file(
        corpus_name=corpus_name,
        path=file_path,
        display_name=display_name,
        description=description,
    )

def upload_chunks_to_existing_corpus():
    # Initialize Vertex AI
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    try:
        # List existing corpora
        corpora = rag.list_corpora()
        existing_corpus = next((c for c in corpora if c.display_name == DISPLAY_NAME), None)

        if not existing_corpus:
            logger.error(f"No corpus found with display name '{DISPLAY_NAME}'. Please create one first.")
            return

        logger.info(f"Found existing corpus: {existing_corpus.name}")

        # Upload each chunk file
        for i in range(1, NUM_CHUNKS + 1):
            file_name = f"{FILE_PREFIX}{i}{FILE_EXTENSION}"
            file_path = os.path.join(LOCAL_FILE_DIR, file_name)
            display_name = f"wordshk_dictionary_chunk_{i}"
            description = f"Chunk {i} of Cantonese vocabulary and examples from Words.hk"

            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}. Skipping this chunk.")
                continue

            try:
                rag_file = upload_file_with_retry(
                    corpus_name=existing_corpus.name,
                    file_path=file_path,
                    display_name=display_name,
                    description=description,
                )
                logger.info(f"Successfully uploaded chunk {i}: {rag_file.name}")
            except exceptions.GoogleAPICallError as e:
                logger.error(f"Error uploading chunk {i}: {e}")

        # List files in the corpus to verify uploads
        files = rag.list_files(existing_corpus.name)
        logger.info("Files in the corpus after uploads:")
        for file in files:
            logger.info(f"- {file.name}: {file.display_name}")

    except exceptions.GoogleAPICallError as e:
        logger.error(f"Error during API call: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    upload_chunks_to_existing_corpus()
