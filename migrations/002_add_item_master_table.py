import sqlite3
import logging

logger = logging.getLogger(__name__)

def upgrade(conn: sqlite3.Connection):
    """
    バージョン2へのアップグレード。
    - `item_master`テーブルを作成する。
    - データは別途 --sync-master コマンドで投入する。
    """
    logger.info("Applying migration 002: Create item_master table...")
    cursor = conn.cursor()

    # item_masterテーブルを作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS item_master (
            item_code TEXT PRIMARY KEY,
            standard_cost REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("Table 'item_master' created or already exists.")

    conn.commit()
    print("Migration 002 applied successfully.")
