from vertexai.preview import rag
import vertexai
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from google.api_core import exceptions, retry
from tqdm import tqdm
import concurrent.futures
from time import sleep
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for parallel processing
MAX_WORKERS = 10  # Number of parallel uploads
BATCH_SIZE = 20   # Number of files per worker
PROGRESS_FILE = "upload_progress.json"

def load_env():
    """Load environment variables from .env file in parent directory"""
    parent_dir = Path(__file__).parent.parent
    env_path = parent_dir / '.env'
    
    if not load_dotenv(env_path):
        raise EnvironmentError(f"Could not load .env file at {env_path}")
    
    project_id = os.getenv('PROJECT_ID')
    if not project_id:
        raise EnvironmentError("PROJECT_ID not found in .env file")
    
    return project_id

def load_progress():
    """Load progress from previous upload session"""
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                return set(json.load(f))
        return set()
    except Exception as e:
        logger.error(f"Error loading progress file: {e}")
        return set()

def save_progress(uploaded_entries):
    """Save progress of uploaded entries"""
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(list(uploaded_entries), f)
    except Exception as e:
        logger.error(f"Error saving progress: {e}")

def get_existing_entries(corpus_name):
    """Get list of already uploaded entries"""
    try:
        existing_files = rag.list_files(corpus_name)
        existing_entries = set()
        for file in existing_files:
            # Extract entry ID from display name (wordshk_entry_XXXXX)
            entry_id = file.display_name.split('_')[-1]
            existing_entries.add(entry_id)
        return existing_entries
    except exceptions.GoogleAPICallError as e:
        logger.error(f"Error listing existing files: {e}")
        return set()

@retry.Retry(
    initial=45.0,      # Start waiting 45 seconds (1 minute) after first failure
    maximum=900.0,     # Never wait more than 900 seconds between retries
    multiplier=1.5,    # Increase wait time by 50% after each failure
    deadline=7200.0,   # Keep retrying for up to 7200 seconds
    predicate=lambda e: isinstance(e, exceptions.GoogleAPICallError)  # Only retry on Google API errors
)
def upload_file_with_retry(corpus_name, file_path, display_name, description):
    """Upload a file to the RAG corpus with retry logic."""
    try:
        return rag.upload_file(
            corpus_name=corpus_name,
            path=file_path,
            display_name=display_name,
            description=description,
        )
    except exceptions.GoogleAPICallError as e:
        if "quota" in str(e).lower() or "rate limit" in str(e).lower():
            logger.warning(f"Quota/Rate limit hit. Waiting before retry: {e}")
            sleep(5)  # Longer delay for quota issues
        raise

def create_corpus(display_name):
    """Create a new RAG corpus."""
    try:
        corpus = rag.create_corpus(
            display_name=display_name,
            description="Cantonese dictionary entries from Words.hk"
        )
        logger.info(f"Created new corpus: {corpus.name}")
        return corpus
    except exceptions.GoogleAPICallError as e:
        logger.error(f"Error creating corpus: {e}")
        raise

def upload_file_batch(args):
    """Upload a single file and return the result."""
    corpus_name, file_info = args
    try:
        result = upload_file_with_retry(
            corpus_name=corpus_name,
            file_path=str(file_info['path']),
            display_name=file_info['display_name'],
            description=file_info['description']
        )
        return {'success': True, 'entry_id': file_info['entry_id'], 'error': None}
    except Exception as e:
        return {'success': False, 'entry_id': file_info['entry_id'], 'error': str(e)}

def chunk_list(lst, chunk_size):
    """Split list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def upload_dictionary_entries():
    # Load environment variables
    try:
        project_id = load_env()
        logger.info(f"Loaded PROJECT_ID from .env")
    except EnvironmentError as e:
        logger.error(f"Environment error: {e}")
        return

    # Constants
    LOCATION = "us-central1"
    DISPLAY_NAME = "wordshk"
    
    # Get paths
    script_dir = Path(__file__).parent.parent
    entries_dir = script_dir / 'dictionary_entries'

    # Initialize Vertex AI
    vertexai.init(project=project_id, location=LOCATION)

    try:
        # List existing corpora
        corpora = rag.list_corpora()
        existing_corpus = next((c for c in corpora if c.display_name == DISPLAY_NAME), None)

        if not existing_corpus:
            logger.info(f"No corpus found with display name '{DISPLAY_NAME}'. Creating new corpus...")
            existing_corpus = create_corpus(DISPLAY_NAME)

        logger.info(f"Using corpus: {existing_corpus.name}")

        # Load progress and get existing entries
        uploaded_entries = load_progress()
        existing_entries = get_existing_entries(existing_corpus.name)
        uploaded_entries.update(existing_entries)
        logger.info(f"Found {len(uploaded_entries)} already uploaded entries")

        # Get list of all entry files and prepare upload information
        entry_files = list(entries_dir.glob('entry_*.txt'))
        upload_info = []
        
        for file_path in entry_files:
            entry_id = file_path.stem.split('_')[1]
            if entry_id not in uploaded_entries:
                upload_info.append({
                    'path': file_path,
                    'entry_id': entry_id,
                    'display_name': f"wordshk_entry_{entry_id}",
                    'description': f"Dictionary entry {entry_id} from Words.hk"
                })

        total_files = len(upload_info)
        logger.info(f"Found {total_files} entries remaining to upload")

        if total_files == 0:
            logger.info("All entries have been uploaded!")
            return

        # Split files into batches
        batches = chunk_list(upload_info, BATCH_SIZE)
        successful_uploads = 0
        failed_uploads = 0

        with tqdm(total=total_files, desc="Uploading entries") as pbar:
            # Process batches with parallel workers
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                for batch in batches:
                    # Create arguments for each file in the batch
                    upload_args = [(existing_corpus.name, file_info) for file_info in batch]
                    
                    # Submit batch of files for parallel upload
                    future_to_file = {executor.submit(upload_file_batch, args): args[1] for args in upload_args}
                    
                    # Process completed uploads
                    for future in concurrent.futures.as_completed(future_to_file):
                        result = future.result()
                        file_info = future_to_file[future]
                        
                        if result['success']:
                            successful_uploads += 1
                            uploaded_entries.add(result['entry_id'])
                            if successful_uploads % 50 == 0:  # Save progress periodically
                                save_progress(uploaded_entries)
                        else:
                            failed_uploads += 1
                            logger.error(f"Failed to upload entry {result['entry_id']}: {result['error']}")
                        
                        pbar.update(1)
                        
                        if (successful_uploads + failed_uploads) % 100 == 0:
                            logger.info(f"Progress: {successful_uploads} successful uploads, {failed_uploads} failed")

        # Final save of progress
        save_progress(uploaded_entries)

        # Final summary
        logger.info(f"Upload complete. Successfully uploaded {successful_uploads} entries, {failed_uploads} failed")

        # List first few files in the corpus to verify uploads
        logger.info("Sampling first few files in the corpus after uploads:")
        for file in list(rag.list_files(existing_corpus.name))[:5]:
            logger.info(f"- {file.name}: {file.display_name}")

    except exceptions.GoogleAPICallError as e:
        logger.error(f"Error during API call: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    upload_dictionary_entries()