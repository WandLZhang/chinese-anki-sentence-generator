from pathlib import Path
import json
import shutil
import logging
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def move_processed_entries(dry_run=False):
    """
    Move processed dictionary entries to done/ folder based on upload_progress.json
    
    Args:
        dry_run (bool): If True, only show what would be moved without actually moving
    """
    try:
        # Get paths
        script_dir = Path(__file__).parent.parent
        entries_dir = script_dir / 'dictionary_entries'
        done_dir = entries_dir / 'done'
        progress_file = script_dir / 'rag' / 'upload_progress.json'

        if dry_run:
            logger.info("DRY RUN MODE - No files will be moved")
        else:
            # Create done directory if it doesn't exist
            done_dir.mkdir(exist_ok=True)
        
        # Load progress file
        with open(progress_file, 'r') as f:
            processed_entries = set(json.load(f))
            
        logger.info(f"Found {len(processed_entries)} processed entries in progress file")
        
        # Counter for moved/would-be-moved files
        moved_count = 0
        to_move = []
        
        # Process each entry file
        for file_path in entries_dir.glob('entry_*.txt'):
            # Skip files already in done directory
            if 'done' in str(file_path):
                continue
                
            entry_id = file_path.stem.split('_')[1]
            
            if entry_id in processed_entries:
                target_path = done_dir / file_path.name
                to_move.append((file_path, target_path))
                moved_count += 1
                
                if moved_count % 100 == 0:
                    if dry_run:
                        logger.info(f"Would move {moved_count} files...")
                    else:
                        logger.info(f"Moved {moved_count} files...")

        # Summary before moving
        if dry_run:
            logger.info(f"Would move {moved_count} files to {done_dir}")
            logger.info("\nFirst 10 files that would be moved:")
            for source, target in to_move[:10]:
                logger.info(f"  {source.name} -> {target}")
            if len(to_move) > 10:
                logger.info(f"  ... and {len(to_move) - 10} more files")
        else:
            logger.info(f"Moving {moved_count} files to {done_dir}")
            # Actually move the files
            for source, target in to_move:
                shutil.move(str(source), str(target))
            logger.info("Move completed successfully")
        
    except FileNotFoundError as e:
        logger.error(f"Could not find required file: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Error reading progress file: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

def main():
    parser = argparse.ArgumentParser(description='Move processed dictionary entries to done folder')
    parser.add_argument('--dry-run', action='store_true', 
                      help='Show what would be moved without actually moving files')
    
    args = parser.parse_args()
    move_processed_entries(dry_run=args.dry_run)

if __name__ == "__main__":
    main()