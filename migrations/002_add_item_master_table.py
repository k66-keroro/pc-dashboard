import sqlite3
import logging
import pandas as pd
from pathlib import Path
import sys

# プロジェクトのルートディレクトリをPythonパスに追加
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.config import settings

logger = logging.getLogger(__name__)

def upgrade(conn: sqlite3.Connection):
    """
    バージョン2へのアップグレード。
    - `item_master`テーブルを作成する。
    - 初回のみ`MARA_DL.csv`からデータをシードする。
    """
    logger.info("Applying migration 002: Create item_master table...")
    cursor = conn.cursor()

    # 1. item_masterテーブルを作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS item_master (
            item_code TEXT PRIMARY KEY,
            standard_cost REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("Table 'item_master' created or already exists.")

    # 2. テーブルが空の場合のみ、CSVからデータをシードする
    cursor.execute("SELECT COUNT(*) FROM item_master")
    if cursor.fetchone()[0] == 0:
        logger.info("'item_master' table is empty. Seeding data from CSV...")
        try:
            master_df = pd.read_csv(
                settings.ITEM_MASTER_PATH,
                sep='\t',
                dtype={'品目': str, '標準原価': float}
            )
            master_df.rename(columns={'品目': 'item_code', '標準原価': 'standard_cost'}, inplace=True)

            # DataFrameをDBに挿入
            master_df.to_sql('item_master', conn, if_exists='append', index=False)
            logger.info(f"Successfully seeded {len(master_df)} records into 'item_master'.")
        except FileNotFoundError:
            logger.error(f"Could not find item master CSV for seeding: {settings.ITEM_MASTER_PATH}")
        except Exception as e:
            logger.error(f"An error occurred during seeding of 'item_master': {e}", exc_info=True)
    else:
        logger.info("'item_master' table already contains data. Skipping seed.")

    conn.commit()
    print("Migration 002 applied successfully.")

if __name__ == "__main__":
    db_conn = None
    try:
        db_conn = sqlite3.connect(settings.DB_PATH)
        upgrade(db_conn)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if db_conn:
            db_conn.close()
