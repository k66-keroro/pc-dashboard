import sqlite3
import logging

logger = logging.getLogger(__name__)

def upgrade(conn: sqlite3.Connection):
    """
    バージョン3へのアップグレード。
    - `production_records`テーブルにUNIQUE制約を追加する。
    - SQLiteの制約により、テーブルを再作成してデータを移行する方法を取る。
    """
    logger.info("Applying migration 003: Add unique constraint to production_records...")
    cursor = conn.cursor()

    try:
        # 1. トランザクションを開始
        cursor.execute("BEGIN TRANSACTION;")

        # 2. 既存のテーブルをリネーム
        cursor.execute("ALTER TABLE production_records RENAME TO production_records_old;")
        logger.info("Renamed production_records to production_records_old.")

        # 3. UNIQUE制約を持つ新しいテーブルを作成
        #    元のCREATE TABLE文にUNIQUE制約を追加
        cursor.execute("""
            CREATE TABLE production_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant TEXT NOT NULL,
                storage_location TEXT,
                item_code TEXT NOT NULL,
                item_text TEXT NOT NULL,
                order_number TEXT NOT NULL,
                order_type TEXT NOT NULL,
                mrp_controller TEXT NOT NULL,
                order_quantity INTEGER NOT NULL,
                actual_quantity INTEGER NOT NULL,
                cumulative_quantity INTEGER NOT NULL,
                remaining_quantity INTEGER NOT NULL,
                input_datetime TIMESTAMP NOT NULL,
                planned_completion_date DATE,
                wbs_element TEXT,
                sales_order_number TEXT,
                sales_order_item_number TEXT,
                amount REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(order_number, input_datetime)
            );
        """)
        logger.info("Created new production_records table with UNIQUE constraint.")

        # 4. 古いテーブルから新しいテーブルにデータをコピー
        #    created_atは自動で設定されるのでコピー対象から外す
        cursor.execute("""
            INSERT INTO production_records (
                id, plant, storage_location, item_code, item_text, order_number,
                order_type, mrp_controller, order_quantity, actual_quantity,
                cumulative_quantity, remaining_quantity, input_datetime,
                planned_completion_date, wbs_element, sales_order_number,
                sales_order_item_number, amount
            )
            SELECT
                id, plant, storage_location, item_code, item_text, order_number,
                order_type, mrp_controller, order_quantity, actual_quantity,
                cumulative_quantity, remaining_quantity, input_datetime,
                planned_completion_date, wbs_element, sales_order_number,
                sales_order_item_number, amount
            FROM production_records_old;
        """)
        logger.info("Copied data from old table to new table.")

        # 5. 古いテーブルを削除
        cursor.execute("DROP TABLE production_records_old;")
        logger.info("Dropped old production_records table.")

        # 6. トランザクションをコミット
        conn.commit()
        print("Migration 003 applied successfully.")

    except Exception as e:
        logger.error(f"An error occurred during migration 003: {e}", exc_info=True)
        # エラーが発生した場合はロールバック
        conn.rollback()
        raise
