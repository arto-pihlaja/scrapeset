import sqlite3
import os

db_path = "./data/chroma_db/chroma.sqlite3"

if not os.path.exists(db_path):
    print(f"Database {db_path} does not exist.")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Listing tables:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table in tables:
        print(f" - {table[0]}")
        
    print("\nListing collections:")
    cursor.execute("SELECT name, topic FROM collections;")
    collections = cursor.fetchall()
    for col in collections:
        print(f" - {col[0]} (topic: {col[1]})")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
