import sys
import sqlite3
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.models.database import create_inventory_table

def upgrade(conn: sqlite3.Connection):
    """
    バージョン4へのアップグレード。
    `inventory_records` テーブルを作成する。
    """
    print("Applying migration 004: Create inventory_records table...")
    create_inventory_table(conn)
    print("Migration 004 applied successfully.")

if __name__ == "__main__":
    from src.models.database import get_db_connection
    from src.config import settings

    print(f"Running migration 004 directly on database: {settings.DB_PATH}")
    db_conn = None
    try:
        db_conn = get_db_connection()
        upgrade(db_conn)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if db_conn:
            db_conn.close()
            print("Database connection closed.")
