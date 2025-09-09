import pandas as pd
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class WipDataProcessor:
    """
    仕掛関連のデータファイルを処理し、データベースにロードするクラス。
    """
    def __init__(self, conn: sqlite3.Connection):
        """
        コンストラクタ

        :param conn: SQLiteデータベースへの接続オブジェクト
        """
        self.conn = conn

    def process_wip_details(self, file_path: Path):
        """
        仕掛明細ファイル（CSV形式）を読み込み、DBに格納する。
        """
        logger.info(f"仕掛明細ファイルの処理を開始します: {file_path}")
        try:
            # ヘッダーなしで読み込み、列数を動的にチェックして対応する
            df = pd.read_csv(file_path, sep='\\t', engine='python', skiprows=4, header=None)

            if len(df.columns) == 18:
                # 実データの場合：末尾の空列を考慮
                df.columns = [
                    'wip_type', 'wip_key', 'plant', 'mrp_controller', 'factory_name', 'line_name',
                    'order_number', 'item_text', 'amount_jpy', 'item_code',
                    'initial_quantity', 'wip_quantity', 'completed_quantity', 'initial_date',
                    'wip_age', 'cmpl_flag', 'material_cost', 'expense_cost'
                ]
            elif len(df.columns) == 17:
                # テストデータの場合
                df.columns = [
                    'wip_type', 'wip_key', 'plant', 'mrp_controller', 'factory_name', 'line_name',
                    'order_number', 'item_text', 'amount_jpy', 'item_code',
                    'initial_quantity', 'wip_quantity', 'completed_quantity', 'initial_date',
                    'wip_age', 'cmpl_flag', 'material_cost'
                ]
                df['expense_cost'] = 0 # 不足している列を追加
            else:
                raise ValueError(f"予期しない列数です: {len(df.columns)}")

            # データクレンジング
            df['amount_jpy'] = pd.to_numeric(df['amount_jpy'], errors='coerce').fillna(0)
            df['material_cost'] = pd.to_numeric(df['material_cost'], errors='coerce').fillna(0)
            df['expense_cost'] = pd.to_numeric(df['expense_cost'], errors='coerce').fillna(0)

            # データベースのUNIQUE制約に合わせて、事前に重複を除去
            subset_cols = ['wip_key', 'order_number', 'item_code']
            df.drop_duplicates(subset=subset_cols, keep='first', inplace=True)

            # データベースに挿入
            df.to_sql('wip_details', self.conn, if_exists='append', index=False)
            logger.info(f"{len(df)}件の仕掛明細データをDBにロードしました。")

        except Exception as e:
            logger.error(f"仕掛明細ファイルの処理中にエラーが発生しました: {e}", exc_info=True)

    def process_zp58(self, file_path: Path):
        """
        ZP58（材料未処理）ファイルを読み込み、DBに格納する。
        このファイルは指図番号の存在チェックにのみ使用する。
        """
        logger.info(f"ZP58ファイルの処理を開始します: {file_path}")
        try:
            df = pd.read_csv(file_path, sep='\\t', engine='python', usecols=['指図／ネットワーク'])
            df.rename(columns={'指図／ネットワーク': 'order_number'}, inplace=True)
            df.dropna(subset=['order_number'], inplace=True)
            df['order_number'] = df['order_number'].astype(str).str.strip()

            # 重複を除外
            df.drop_duplicates(inplace=True)

            # 'INSERT OR IGNORE'で挿入
            df.to_sql('zp58_records', self.conn, if_exists='append', index=False)
            logger.info(f"{len(df)}件のZP58データをDBにロードしました。")

        except Exception as e:
            logger.error(f"ZP58ファイルの処理中にエラーが発生しました: {e}", exc_info=True)

    def process_zp02(self, file_path: Path):
        """
        ZP02（完了実績）ファイルを読み込み、DBに格納する。
        """
        logger.info(f"ZP02ファイルの処理を開始します: {file_path}")
        try:
            df = pd.read_csv(file_path, sep='\\t', engine='python', encoding='utf-8')

            column_mapping = {
                '指図番号': 'order_number',
                '指図ステータス': 'order_status',
                'MRP管理者': 'mrp_controller',
                'MRP管理者名': 'mrp_controller_name',
                '品目コード': 'item_code',
                '品目テキスト': 'item_text',
                '台数': 'quantity',
                'ＷＢＳ要素': 'wbs_element',
                'DLV日付': 'completion_date',
                'TECO日付': 'teco_date'
            }
            # 必要な列のみを抽出
            df = df[list(column_mapping.keys())]
            df.rename(columns=column_mapping, inplace=True)

            # データ型変換
            df['completion_date'] = pd.to_datetime(df['completion_date'], errors='coerce')
            df['teco_date'] = pd.to_datetime(df['teco_date'], errors='coerce')

            # 'INSERT OR IGNORE'で挿入
            df.to_sql('zp02_records', self.conn, if_exists='append', index=False)
            logger.info(f"{len(df)}件のZP02データをDBにロードしました。")

        except Exception as e:
            logger.error(f"ZP02ファイルの処理中にエラーが発生しました: {e}", exc_info=True)

    def clear_wip_tables(self):
        """
        仕掛関連のテーブルをすべてクリアする。
        """
        logger.info("仕掛関連テーブルのデータをクリアします。")
        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM wip_details;")
            cursor.execute("DELETE FROM zp02_records;")
            cursor.execute("DELETE FROM zp58_records;")
            self.conn.commit()
            logger.info("仕掛関連テーブルのクリアが完了しました。")
        except Exception as e:
            logger.error(f"テーブルクリア中にエラーが発生しました: {e}", exc_info=True)
            self.conn.rollback()

    def process_storage_locations(self, file_path: Path):
        """
        保管場所一覧ファイルを読み込み、DBに格納する。
        """
        logger.info(f"保管場所一覧ファイルの処理を開始します: {file_path}")
        try:
            df = pd.read_csv(file_path, sep='\\t', engine='python')
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
        """
        ZS65（PC在庫）ファイルを読み込み、DBに格納する。
        """
        logger.info(f"ZS65ファイルの処理を開始します: {file_path}")
        try:
            df = pd.read_csv(file_path, sep='\\t', engine='python')
            # 列名を英語に変換
            column_mapping = {
                '品目コード': 'item_code', 'プラント': 'plant', '品目テキスト': 'item_text', '保管場所': 'storage_location',
                '特殊在庫区分': 'stock_type', '特殊在庫の評価': 'stock_valuation', '特殊在庫番号': 'stock_number',
                '保管場所レベルでの品目削除フラグ': 'delete_flag', 'ロット番号': 'lot_number', '基本数量単位': 'base_unit',
                '利用可能評価在庫': 'available_stock', '通貨コード': 'currency', '利用可能値': 'available_value',
                '転送中在庫（保管場所間）': 'in_transfer_stock', '積送/輸送中の値': 'in_transfer_value',
                '品質検査中在庫': 'in_inspection_stock', '品質検査値': 'in_inspection_value',
                '非利用可能ロットの全在庫合計': 'unusable_stock', '制限値': 'restricted_value',
                '保留在庫': 'blocked_stock', '保留在庫値': 'blocked_stock_value', '返品保留在庫': 'returns_stock',
                '保留返品金額': 'returns_stock_value', '販売伝票': 'sales_order_number', '販売伝票明細': 'sales_order_item',
                '棚番': 'shelf_number', '勘定科目コード': 'account_code', '勘定科目名': 'account_name',
                '品目タイプ': 'item_type', '滞留日数': 'stagnant_days', '評価クラス': 'valuation_class',
                '評価クラステキスト': 'valuation_class_text', '調達タイプ': 'procurement_type',
                '調達タイプテキスト': 'procurement_type_text', '評価減区分': 'valuation_reduction_category'
            }
            df.rename(columns=column_mapping, inplace=True)
            df.to_sql('zs65_records', self.conn, if_exists='replace', index=False)
            logger.info(f"{len(df)}件のZS65データをDBにロードしました。")
        except Exception as e:
            logger.error(f"ZS65ファイルの処理中にエラーが発生しました: {e}", exc_info=True)

    def run_all(self, wip_details_path: Path, zp58_path: Path, zp02_path: Path, storage_locations_path: Path, zs65_path: Path):
        """
        すべての仕掛関連・在庫関連ファイルを処理する。
        """
        self.clear_wip_tables()
        self.process_wip_details(wip_details_path)
        self.process_zp58(zp58_path)
        self.process_zp02(zp02_path)

        # 新しい処理を追加
        self.process_storage_locations(storage_locations_path)
        self.process_zs65(zs65_path)

        logger.info("すべての仕掛・在庫関連ファイルの処理が完了しました。")
