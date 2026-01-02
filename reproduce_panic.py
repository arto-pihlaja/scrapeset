import chromadb
from chromadb.config import Settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

persist_dir = "./data/chroma_db"

try:
    print(f"Attempting to initialize PersistentClient with path: {persist_dir}")
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    print("Successfully initialized client.")
    
    collections = client.list_collections()
    print(f"Found {len(collections)} collections:")
    for col in collections:
        print(f" - {col.name}")
        
except Exception as e:
    print(f"Caught exception: {e}")
    import traceback
    traceback.print_exc()
