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
            # ユーザー提供のデータは18列。先頭3行はスキップ。
            df = pd.read_csv(file_path, sep='\\t', engine='python', skiprows=4, header=None, usecols=range(18))

            # 18個の列名を英語で定義
            df.columns = [
                'wip_type', 'wip_key', 'plant', 'mrp_controller', 'factory_name', 'line_name',
                'order_number', 'item_text', 'amount_jpy', 'item_code',
                'initial_quantity', 'wip_quantity', 'completed_quantity', 'initial_date',
                'wip_age', 'cmpl_flag', 'material_cost', 'expense_cost'
            ]

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

    def run_all(self, wip_details_path: Path, zp58_path: Path, zp02_path: Path):
        """
        すべての仕掛関連ファイルを処理する。
        """
        self.clear_wip_tables()
        self.process_wip_details(wip_details_path)
        self.process_zp58(zp58_path)
        self.process_zp02(zp02_path)
        logger.info("すべての仕掛関連ファイルの処理が完了しました。")
