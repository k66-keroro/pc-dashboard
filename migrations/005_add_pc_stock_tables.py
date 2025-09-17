import sqlite3
import logging

logger = logging.getLogger(__name__)

def upgrade(conn: sqlite3.Connection):
    """
    バージョン5へのアップグレード。
    - PC在庫分析用のテーブル (`storage_locations`, `zs65_records`) を作成する。
    """
    logger.info("Applying migration 005: Create tables for PC Stock analysis...")
    cursor = conn.cursor()

    # 1. storage_locationsテーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS storage_locations (
        plant TEXT,
        responsible_dept TEXT,
        inventory_report_category TEXT,
        storage_location TEXT PRIMARY KEY,
        storage_location_name TEXT,
        factory_stock_category TEXT,
        sales_stock_category TEXT,
        factory_category TEXT,
        factory_category_2 TEXT,
        unusable_category TEXT,
        shelf_check_flag BOOLEAN,
        requirements_check TEXT
    );
    """)
    logger.info("Table 'storage_locations' created or already exists.")

    # 2. zs65_recordsテーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zs65_records (
        item_code TEXT,
        plant TEXT,
        item_text TEXT,
        storage_location TEXT,
        stock_type TEXT,
        stock_valuation TEXT,
        stock_number TEXT,
        delete_flag BOOLEAN,
        lot_number TEXT,
        base_unit TEXT,
        available_stock REAL,
        currency TEXT,
        available_value REAL,
        in_transfer_stock REAL,
        in_transfer_value REAL,
        in_inspection_stock REAL,
        in_inspection_value REAL,
        unusable_stock REAL,
        restricted_value REAL,
        blocked_stock REAL,
        blocked_stock_value REAL,
        returns_stock REAL,
        returns_stock_value REAL,
        sales_order_number TEXT,
        sales_order_item TEXT,
        shelf_number TEXT,
        account_code TEXT,
        account_name TEXT,
        item_type TEXT,
        stagnant_days INTEGER,
        valuation_class TEXT,
        valuation_class_text TEXT,
        procurement_type TEXT,
        procurement_type_text TEXT,
        valuation_reduction_category TEXT,
        PRIMARY KEY (item_code, storage_location, lot_number)
    );
    """)
    logger.info("Table 'zs65_records' created or already exists.")

    conn.commit()
    print("Migration 005 applied successfully.")
