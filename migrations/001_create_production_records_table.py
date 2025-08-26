import sys
import sqlite3
from pathlib import Path

# プロジェクトのルートディレクトリをPythonパスに追加
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.models.database import create_tables

def upgrade(conn: sqlite3.Connection):
    """
    バージョン1へのアップグレード。
    初期テーブル `production_records` を作成する。
    """
    print("Applying migration 001: Create initial tables...")
    create_tables(conn)
    print("Migration 001 applied successfully.")

# このスクリプトが直接実行された場合のフォールバック（基本的には使用しない）
if __name__ == "__main__":
    from src.models.database import get_db_connection, DEFAULT_DB_PATH

    print(f"Running migration 001 directly on database: {DEFAULT_DB_PATH}")
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
