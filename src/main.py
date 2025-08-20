import sqlite3
import os

def initialize_database():
    """
    Initializes the SQLite database and creates the necessary tables.
    """
    db_path = 'data/sqlite/dashboard.db'

    # Ensure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create a sample table for production data
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS production_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        product_id TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        status TEXT
    )
    ''')

    conn.commit()
    conn.close()
    print(f"Database initialized at {db_path}")

if __name__ == '__main__':
    initialize_database()
