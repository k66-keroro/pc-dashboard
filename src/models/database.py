import sqlite3
from pathlib import Path
from typing import List

from src.models.production import ProductionRecord
from src.config import settings

def get_db_connection(db_path: Path = settings.DB_PATH) -> sqlite3.Connection:
    """
    SQLiteデータベースへの接続を確立し、Connectionオブジェクトを返す。
    データベースファイルが存在しない場合は、親ディレクトリを作成してから接続する。
    """
    # The directory creation is now handled in settings.py
    # detect_typesを無効化し、型変換をPandasに完全に委ねる
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_schema_version(conn: sqlite3.Connection):
    """
    `schema_version`テーブルを作成し、バージョン0で初期化する。
    テーブルが既に存在する場合は何もしない。
    """
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL PRIMARY KEY
        );
    """)
    # テーブルが空の場合のみバージョン0を挿入
    cursor.execute("SELECT COUNT(*) FROM schema_version")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO schema_version (version) VALUES (0)")
        conn.commit()

def get_schema_version(conn: sqlite3.Connection) -> int:
    """現在のスキーマバージョンを取得する。"""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT version FROM schema_version")
        result = cursor.fetchone()
        return result[0] if result else 0
    except sqlite3.OperationalError:
        # テーブルが存在しない場合はバージョン0とみなす
        return 0

def create_tables(conn: sqlite3.Connection):
    """
    データベース内に必要なテーブルとインデックスを作成する。
    テーブルが既に存在する場合は、何もしない。
    """
    sql_create_table = """
    CREATE TABLE IF NOT EXISTS production_records (
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    sql_create_index_order_number = "CREATE INDEX IF NOT EXISTS idx_order_number ON production_records (order_number);"
    sql_create_index_input_datetime = "CREATE INDEX IF NOT EXISTS idx_input_datetime ON production_records (input_datetime);"
    sql_create_index_item_code = "CREATE INDEX IF NOT EXISTS idx_item_code ON production_records (item_code);"

    cursor = conn.cursor()
    cursor.execute(sql_create_table)
    cursor.execute(sql_create_index_order_number)
    cursor.execute(sql_create_index_input_datetime)
    cursor.execute(sql_create_index_item_code)
    conn.commit()

def insert_production_records(conn: sqlite3.Connection, records: List[ProductionRecord]):
    """
    複数の生産実績レコードをデータベースに一括で挿入する。
    """
    sql = """
    INSERT OR IGNORE INTO production_records (
        plant, storage_location, item_code, item_text, order_number, order_type,
        mrp_controller, order_quantity, actual_quantity, cumulative_quantity,
        remaining_quantity, input_datetime, planned_completion_date, wbs_element,
        sales_order_number, sales_order_item_number, amount
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    # Pydanticモデルをタプルのリストに変換
    data_to_insert = [
        (
            r.plant, r.storage_location, r.item_code, r.item_text, r.order_number, r.order_type,
            r.mrp_controller, r.order_quantity, r.actual_quantity, r.cumulative_quantity,
            r.remaining_quantity, r.input_datetime, r.planned_completion_date, r.wbs_element,
            r.sales_order_number, r.sales_order_item_number, r.amount
        ) for r in records
    ]

    cursor = conn.cursor()
    cursor.executemany(sql, data_to_insert)
    conn.commit()
