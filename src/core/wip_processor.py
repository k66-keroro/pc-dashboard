import pandas as pd
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class WipDataProcessor:
    """
    仕掛関連のデータファイルを処理し、データベースにロードするクラス。
    """
    def __init__(self, conn: sqlite3.Connection, mode: str = 'dev'):
        self.conn = conn
        self.mode = mode
        logger.info(f"WipDataProcessor initialized in '{self.mode}' mode.")

    def process_wip_details(self, file_path: Path):
        logger.info(f"仕掛明細ファイルの処理を開始します: {file_path}")
        try:
            if not file_path or not file_path.exists():
                logger.error(f"仕掛明細ファイルが見つかりません: {file_path}")
                return

            # 本番はxlsx、テストはcsvのため拡張子で分岐
            if file_path.suffix.lower() == '.xlsx':
                df = pd.read_excel(file_path, skiprows=3, header=0, engine='openpyxl')
            else: # テスト用のCSVファイル
                # 開発(サンプル)はヘッダー0行、本番は3行と想定
                skip = 3 if self.mode == 'prod' else 0
                df = pd.read_csv(file_path, sep='\\t', engine='python', skiprows=skip, header=0, encoding='utf-8-sig')

            column_mapping = {
                'キー': 'wip_type', 'ﾌﾟﾗﾝﾄ': 'plant', 'MRP管理者': 'mrp_controller',
                '工場': 'factory_name', 'ライン': 'line_name', 'ﾈｯﾄﾜｰｸ/指図番号': 'order_number',
                'テキスト': 'item_text', '金額（国内通貨）': 'amount_jpy', '品目': 'item_code',
                '初期数量': 'initial_quantity', '仕掛数': 'wip_quantity', '完成数量': 'completed_quantity',
                '初期実績日付': 'initial_date', '仕掛年齢': 'wip_age', 'CMPL': 'cmpl_flag',
                '材料': 'material_cost', '経費': 'expense_cost'
            }
            df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns}, inplace=True)

            if 'order_number' not in df.columns:
                 raise ValueError("仕掛明細ファイルに 'ﾈｯﾄﾜｰｸ/指図番号' 列が見つかりません。")

            df['wip_key'] = df['order_number']

            numeric_cols = ['amount_jpy', 'material_cost', 'expense_cost']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            subset_cols = ['wip_key', 'order_number', 'item_code']
            df.drop_duplicates(subset=subset_cols, keep='first', inplace=True)

            df.to_sql('wip_details', self.conn, if_exists='replace', index=False)
            logger.info(f"{len(df)}件の仕掛明細データをDBにロードしました。")
        except Exception as e:
            logger.error(f"仕掛明細ファイルの処理中にエラーが発生しました: {e}", exc_info=True)

    def process_zp58(self, file_path: Path):
        logger.info(f"ZP58ファイルの処理を開始します: {file_path}")
        try:
            encoding = 'cp932' if self.mode == 'prod' else 'utf-8'
            logger.info(f"Using encoding: {encoding} for ZP58")
            df = pd.read_csv(file_path, sep='\\t', engine='python', encoding=encoding, usecols=['指図／ネットワーク'])
            df.rename(columns={'指図／ネットワーク': 'order_number'}, inplace=True)
            df.dropna(subset=['order_number'], inplace=True)
            df['order_number'] = df['order_number'].astype(str).str.strip()

            df.drop_duplicates(inplace=True)
            df.to_sql('zp58_records', self.conn, if_exists='replace', index=False)
            logger.info(f"{len(df)}件のZP58データをDBにロードしました。")
        except Exception as e:
            logger.error(f"ZP58ファイルの処理中にエラーが発生しました: {e}", exc_info=True)

    def process_zp02(self, file_path: Path):
        logger.info(f"ZP02ファイルの処理を開始します: {file_path}")
        try:
            encoding = 'cp932' if self.mode == 'prod' else 'utf-8'
            logger.info(f"Using encoding: {encoding} for ZP02")
            df = pd.read_csv(file_path, sep='\\t', engine='python', encoding=encoding)

            # フィルタリング: MRP管理者が'PC'で始まるもののみ
            if 'MRP管理者' in df.columns:
                df = df[df['MRP管理者'].str.startswith('PC', na=False)]

            column_mapping = {
                '指図番号': 'order_number', '指図ステータス': 'order_status', 'MRP管理者': 'mrp_controller',
                'MRP管理者名': 'mrp_controller_name', '品目コード': 'item_code', '品目テキスト': 'item_text',
                '台数': 'quantity', 'ＷＢＳ要素': 'wbs_element', 'DLV日付': 'completion_date', 'TECO日付': 'teco_date'
            }
            # 存在する列のみを選択してリネーム
            cols_to_use = [col for col in column_mapping.keys() if col in df.columns]
            df = df[cols_to_use].rename(columns=column_mapping)

            if 'completion_date' in df.columns:
                df['completion_date'] = pd.to_datetime(df['completion_date'], errors='coerce')
            if 'teco_date' in df.columns:
                df['teco_date'] = pd.to_datetime(df['teco_date'], errors='coerce')

            df.to_sql('zp02_records', self.conn, if_exists='replace', index=False)
            logger.info(f"{len(df)}件のZP02データをDBにロードしました。")
        except Exception as e:
            logger.error(f"ZP02ファイルの処理中にエラーが発生しました: {e}", exc_info=True)

    def process_storage_locations(self, file_path: Path):
        logger.info(f"保管場所一覧ファイルの処理を開始します: {file_path}")
        try:
            # This file seems to be consistently utf-8-sig
            df = pd.read_csv(file_path, sep='\\t', engine='python', encoding='utf-8-sig')
            column_mapping = {
                'ﾌﾟﾗﾝﾄ': 'plant', '責任部署': 'responsible_dept', '棚卸報告区分': 'inventory_report_category',
                '保管場所': 'storage_location', '保管場所名': 'storage_location_name', '工場在庫区分': 'factory_stock_category',
                '営業在庫区分': 'sales_stock_category', '工場区分': 'factory_category', '工場区分2': 'factory_category_2',
                '使用不可区分': 'unusable_category', '棚番チェック用': 'shelf_check_flag', '所要check': 'requirements_check'
            }
            df.rename(columns=column_mapping, inplace=True)
            df.to_sql('storage_locations', self.conn, if_exists='replace', index=False)
            logger.info(f"{len(df)}件の保管場所マスターデータをDBにロードしました。")
        except Exception as e:
            logger.error(f"保管場所一覧ファイルの処理中にエラーが発生しました: {e}", exc_info=True)

    def process_zs65(self, file_path: Path):
        logger.info(f"ZS65ファイルの処理を開始します: {file_path}")
        try:
            encoding = 'cp932' if self.mode == 'prod' else 'utf-8'
            logger.info(f"Using encoding: {encoding} for ZS65")
            df = pd.read_csv(file_path, sep='\\t', engine='python', encoding=encoding)

            # フィルタリング: プラントが'P100'のもののみ
            if 'プラント' in df.columns:
                df = df[df['プラント'] == 'P100']

            column_mapping = {
                '品目コード': 'item_code', 'プラント': 'plant', '品目テキスト': 'item_text', '保管場所': 'storage_location',
                '利用可能評価在庫': 'available_stock', '利用可能値': 'available_value', '滞留日数': 'stagnant_days'
            }
            # 存在する列のみリネーム
            df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns}, inplace=True)
            df.to_sql('zs65_records', self.conn, if_exists='replace', index=False)
            logger.info(f"{len(df)}件のZS65データをDBにロードしました。")
        except Exception as e:
            logger.error(f"ZS65ファイルの処理中にエラーが発生しました: {e}", exc_info=True)

    def clear_all_wip_stock_tables(self):
        logger.info("仕掛・在庫関連テーブルのデータをクリアします。")
        cursor = self.conn.cursor()
        try:
            tables = ['wip_details', 'zp02_records', 'zp58_records', 'storage_locations', 'zs65_records']
            for table in tables:
                cursor.execute(f"DELETE FROM {table};")
            self.conn.commit()
            logger.info("仕掛・在庫関連テーブルのクリアが完了しました。")
        except Exception as e:
            logger.error(f"テーブルクリア中にエラーが発生しました: {e}", exc_info=True)
            self.conn.rollback()

    def run_all(self, wip_details_path: Path, zp58_path: Path, zp02_path: Path, storage_locations_path: Path, zs65_path: Path):
        self.clear_all_wip_stock_tables()
        self.process_wip_details(wip_details_path)
        self.process_zp58(zp58_path)
        self.process_zp02(zp02_path)
        self.process_storage_locations(storage_locations_path)
        self.process_zs65(zs65_path)
        logger.info("すべての仕掛・在庫関連ファイルの処理が完了しました。")
