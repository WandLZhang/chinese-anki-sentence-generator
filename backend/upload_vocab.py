import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore
import os
from dotenv import load_dotenv
from google.oauth2 import service_account

# Load environment variables
load_dotenv()

def parse_vocab_file(file_path):
    """Parse the vocab.txt file and return a list of entries."""
    entries = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    # Skip the first two lines (Anki configuration)
    lines = lines[2:]
    
    current_entry = None
    for line in lines:
        line = line.strip()
        if not line:  # Skip empty lines
            continue
            
        # If line contains a tab, it's a new entry
        if '\t' in line:
            if current_entry:
                entries.append(current_entry)
            simplified, sentences = line.split('\t')
            
            # Split sentences into Mandarin and Cantonese using <br><br>
            parts = sentences.split('<br><br>')
            mandarin = parts[0]
            cantonese = parts[1] if len(parts) > 1 else ""
            
            current_entry = {
                'simplified': simplified,
                'mandarin': mandarin,
                'cantonese': cantonese
            }
        else:
            # If no tab, it's a continuation of the previous entry
            if current_entry:
                if '<br><br>' in line:
                    parts = line.split('<br><br>')
                    current_entry['mandarin'] += '\n' + parts[0]
                    current_entry['cantonese'] += '\n' + parts[1] if len(parts) > 1 else ""
                else:
                    # If no <br><br>, append to the last field that was being populated
                    if current_entry['cantonese']:
                        current_entry['cantonese'] += '\n' + line
                    else:
                        current_entry['mandarin'] += '\n' + line
    
    # Don't forget to add the last entry
    if current_entry:
        entries.append(current_entry)
        
    return entries

def upload_to_firestore(entries):
    """Upload entries to Firestore."""
    # Load credentials
    creds = service_account.Credentials.from_service_account_file(
        os.getenv('FIREBASE_ADMIN_SDK_PATH'),
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    
    # Get Firestore client for chinese-anki database
    db = firestore.Client(
        project='wz-data-catalog-demo',
        database='chinese-anki',
        credentials=creds
    )
    
    # Reference to the vocabulary collection
    vocab_ref = db.collection('vocabulary')
    
    # Delete all existing documents first
    docs = vocab_ref.stream()
    batch = db.batch()
    for doc in docs:
        batch.delete(doc.reference)
    batch.commit()
    print("Deleted all existing documents")
    
    # Upload new documents in batches
    batch = db.batch()
    count = 0
    batch_size = 500  # Firestore batch size limit is 500
    
    for entry in entries:
        # Create a new document with auto-generated ID
        doc_ref = vocab_ref.document()
        batch.set(doc_ref, entry)
        count += 1
        
        # If batch is full, commit it and start a new one
        if count % batch_size == 0:
            batch.commit()
            batch = db.batch()
    
    # Commit any remaining documents
    if count % batch_size != 0:
        batch.commit()
    
    print(f"Successfully uploaded {len(entries)} entries to Firestore")

def main():
    # Parse vocab.txt
    entries = parse_vocab_file('vocab.txt')
    print(f"Parsed {len(entries)} entries from vocab.txt")
    
    # Upload to Firestore
    upload_to_firestore(entries)

if __name__ == "__main__":
    main()
