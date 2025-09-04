import sqlite3
import logging

logger = logging.getLogger(__name__)

def upgrade(conn: sqlite3.Connection):
    """
    バージョン4へのアップグレード。
    - 仕掛進捗分析用のテーブル群 (`wip_details`, `zp02_records`, `zp58_records`) を作成する。
    """
    logger.info("Applying migration 004: Create tables for WIP analysis...")
    cursor = conn.cursor()

    # 1. wip_detailsテーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wip_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wip_type TEXT,
        wip_key TEXT,
        plant TEXT,
        mrp_controller TEXT,
        factory_name TEXT,
        line_name TEXT,
        order_number TEXT,
        item_text TEXT,
        amount_jpy REAL,
        item_code TEXT,
        initial_quantity INTEGER,
        wip_quantity INTEGER,
        completed_quantity INTEGER,
        initial_date TEXT,
        wip_age TEXT,
        cmpl_flag TEXT,
        material_cost REAL,
        expense_cost REAL,
        UNIQUE(wip_key, order_number, item_code)
    );
    """)
    logger.info("Table 'wip_details' created or already exists.")

    # 2. zp02_recordsテーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zp02_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE,
        order_status TEXT,
        mrp_controller TEXT,
        mrp_controller_name TEXT,
        item_code TEXT,
        item_text TEXT,
        quantity INTEGER,
        wbs_element TEXT,
        completion_date DATE,
        teco_date DATE
    );
    """)
    logger.info("Table 'zp02_records' created or already exists.")

    # 3. zp58_recordsテーブル (材料未処理フラグ用)
    # このテーブルは、存在するかどうかだけが重要なので、指図番号のみを格納
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zp58_records (
        order_number TEXT PRIMARY KEY
    );
    """)
    logger.info("Table 'zp58_records' created or already exists.")

    conn.commit()
    print("Migration 004 applied successfully.")
