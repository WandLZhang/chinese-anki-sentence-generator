from google.cloud import firestore
import os
from dotenv import load_dotenv
from google.oauth2 import service_account

# Load environment variables
load_dotenv()

def add_timestamps_to_documents():
    """Add server timestamps to all documents in the vocabulary collection."""
    # Load credentials
    creds = service_account.Credentials.from_service_account_file(
        os.getenv('FIREBASE_ADMIN_SDK_PATH'),
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    
    # Get Firestore client for default database
    db = firestore.Client(
        project='wz-data-catalog-demo',
        credentials=creds
    )
    
    # Reference to the vocabulary collection
    vocab_ref = db.collection('vocabulary')
    
    # Get all documents
    docs = list(vocab_ref.stream())
    print(f"Found {len(docs)} documents")
    
    # Update documents in batches
    batch = db.batch()
    count = 0
    batch_size = 500  # Firestore batch size limit is 500
    
    for doc in docs:
        # Add timestamp to document
        batch.update(doc.reference, {
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        count += 1
        
        # If batch is full, commit it and start a new one
        if count % batch_size == 0:
            batch.commit()
            print(f"Updated {count} documents")
            batch = db.batch()
    
    # Commit any remaining documents
    if count % batch_size != 0:
        batch.commit()
    
    print(f"Successfully added timestamps to {len(docs)} documents")

if __name__ == "__main__":
    add_timestamps_to_documents()
