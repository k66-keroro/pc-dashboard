import logging
import pandas as pd
from pathlib import Path
from typing import List, Tuple, Dict, Any
import sqlite3

from pydantic import ValidationError
from src.models.production import ProductionRecord
from src.models.database import insert_production_records
from src.config import settings

logger = logging.getLogger(__name__)

class DataProcessor:
    """
    データファイルの処理、加工、データベースへのロードを担当するクラス。
    """
    def __init__(self, db_conn: sqlite3.Connection):
        """
        DataProcessorを初期化する。
        """
        self.db_conn = db_conn
        self.item_master_df = self._load_item_master_from_db()
        self.final_df = pd.DataFrame()

    def _load_item_master_from_db(self) -> pd.DataFrame:
        """品目マスターをデータベースから読み込む。"""
        try:
            query = "SELECT name FROM sqlite_master WHERE type='table' AND name='item_master';"
            cursor = self.db_conn.cursor()
            cursor.execute(query)
            if cursor.fetchone() is None:
                logger.warning("`item_master`テーブルがDBに存在しません。")
                return pd.DataFrame()

            master_df = pd.read_sql_query("SELECT item_code, standard_cost FROM item_master", self.db_conn)
            master_df.set_index('item_code', inplace=True)
            logger.info(f"DBから品目マスターを正常に読み込みました。{len(master_df)}件")
            return master_df
        except Exception as e:
            logger.error(f"DBからの品目マスター読み込み中にエラーが発生しました: {e}")
            return pd.DataFrame()

    def sync_master_from_csv(self):
        """
        CSVマスターファイルの最新の内容でデータベースを洗い替え（全置換）する。
        """
        logger.info(f"品目マスターの同期（洗い替え）を開始します: {settings.ITEM_MASTER_PATH}")
        try:
            master_df = pd.read_csv(
                settings.ITEM_MASTER_PATH,
                sep='\t',
                dtype={'品目': str, '標準原価': float}
            )
            master_df.rename(columns={'品目': 'item_code', '標準原価': 'standard_cost'}, inplace=True)

            # 品目コードの空白を除去
            if 'item_code' in master_df.columns:
                master_df['item_code'] = master_df['item_code'].str.strip()

            # CSV内に重複がある場合に備え、最後のレコードを正とする
            initial_rows = len(master_df)
            master_df.drop_duplicates(subset=['item_code'], keep='last', inplace=True)
            if initial_rows > len(master_df):
                logger.warning(f"CSVマスター内で{initial_rows - len(master_df)}件の重複を検出し、最新のデータで上書きしました。")

            cursor = self.db_conn.cursor()

            logger.info("既存の品目マスターデータを削除します...")
            cursor.execute("DELETE FROM item_master;")

            logger.info("CSVから新しい品目マスターデータを挿入します...")
            master_df.to_sql('item_master', self.db_conn, if_exists='append', index=False)

            self.db_conn.commit()
            logger.info(f"品目マスターの同期が完了しました。{len(master_df)}件のレコードを処理しました。")

            self.item_master_df = self._load_item_master_from_db()

        except FileNotFoundError:
            logger.error(f"品目マスターファイルが見つかりません: {settings.ITEM_MASTER_PATH}")
        except Exception as e:
            logger.error(f"品目マスターの同期中にエラーが発生しました: {e}", exc_info=True)


    def _load_production_dataframe(self, file_path: Path) -> pd.DataFrame:
        """
        指定された生産実績ファイルを読み込み、基本的な前処理とフィルタリングを行ってDataFrameを返す。
        """
        try:
            df = pd.read_csv(
                file_path,
                encoding='shift_jis',
                sep='\t',
                dtype=str,
                skiprows=0,
                encoding_errors='replace'
            )
            df.columns = df.columns.str.strip()
            df = df.where(pd.notna(df), None)

            # 品目コードの空白を除去
            if '品目コード' in df.columns:
                df['品目コード'] = df['品目コード'].str.strip()

            # MRP管理者が'PC'で始まるレコードのみを対象とする
            original_rows = len(df)
            if 'MRP管理者' in df.columns:
                df = df[df['MRP管理者'].str.startswith('PC', na=False)].copy()
                logger.info(f"MRP管理者フィルタを適用: {original_rows}行 -> {len(df)}行")
            else:
                logger.warning("MRP管理者カラムが見つからなかったため、フィルタをスキップします。")

            # Use original Japanese column names for conversion
            if '入力日時' in df.columns:
                # to_datetimeでパースし、NaTは除外
                df['入力日時'] = pd.to_datetime(df['入力日時'], format='%Y/%m/%d %H:%M', errors='coerce')
                df.dropna(subset=['入力日時'], inplace=True)
                # DBに保存する前に、一貫した文字列フォーマットに変換する
                df['入力日時'] = df['入力日時'].dt.strftime('%Y-%m-%d %H:%M:%S')

            numeric_cols = ['指図数量', '実績数量', '累計数量', '残数量']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            df = df.where(pd.notna(df), None)
            return df
        except FileNotFoundError:
            logger.error(f"ファイルが見つかりません: {file_path}")
            raise
        except pd.errors.EmptyDataError:
            logger.warning(f"データファイルが空です: {file_path}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"ファイルの読み込み中に予期せぬエラーが発生しました: {e}")
            raise

    def _enrich_data(self, prod_df: pd.DataFrame) -> pd.DataFrame:
        """
        生産実績データに品目マスターを結合し、金額を計算する。
        """
        if self.item_master_df.empty:
            logger.warning("品目マスターがロードされていないため、金額計算をスキップします。")
            prod_df['amount'] = 0.0
            return prod_df

        # Pydanticモデルのaliasに合わせてカラム名を一時的に変更
        prod_df.rename(columns={'品目コード': 'item_code'}, inplace=True)

        enriched_df = pd.merge(
            prod_df,
            self.item_master_df,
            on='item_code',
            how='left'
        )

        enriched_df['実績数量'] = pd.to_numeric(enriched_df['実績数量'], errors='coerce')
        enriched_df['standard_cost'] = pd.to_numeric(enriched_df['standard_cost'], errors='coerce')

        enriched_df['amount'] = enriched_df['実績数量'] * enriched_df['standard_cost']

        missing_cost_count = enriched_df['amount'].isna().sum()
        if missing_cost_count > 0:
            missing_items = enriched_df[enriched_df['amount'].isna()]['item_code'].unique()
            logger.warning(f"{missing_cost_count}件のレコードで標準原価が見つからず、金額を0に設定しました。対象品目: {list(missing_items)}")
            enriched_df['amount'].fillna(0, inplace=True)

        enriched_df.rename(columns={'item_code': '品目コード'}, inplace=True)

        return enriched_df

    def _validate_and_transform_data(self, df: pd.DataFrame) -> Tuple[List[ProductionRecord], List[Dict[str, Any]]]:
        """
        DataFrameをPydanticモデルのリストに変換し、バリデーションを行う。
        """
        valid_records: List[ProductionRecord] = []
        invalid_records: List[Dict[str, Any]] = []

        for record_dict in df.to_dict(orient='records'):
            try:
                valid_records.append(ProductionRecord(**record_dict))
            except ValidationError as e:
                logger.warning(f"バリデーションエラー: {e.errors()} | データ: {record_dict}")
                invalid_records.append({'data': record_dict, 'errors': e.errors()})

        return valid_records, invalid_records

    def process_file_and_load_to_db(self) -> dict:
        """
        データファイルを処理し、DBにロードし、最終的なDataFrameをインスタンス変数に格納する。
        """
        path = settings.DATA_FILE_PATH
        logging.info(f"ファイル処理を開始します: {path}")

        try:
            prod_df = self._load_production_dataframe(path)

            if prod_df.empty:
                logger.warning(f"ファイルが空か、読み込みに失敗しました: {path}")
                return {"file": str(path), "total_rows": 0, "successful_inserts": 0, "failed_rows": 0}

            # データエンリッチメント（マスター結合と金額計算）
            enriched_df = self._enrich_data(prod_df)

            # バリデーションとDBロード
            valid_records, invalid_records = self._validate_and_transform_data(enriched_df)

            if valid_records:
                insert_production_records(self.db_conn, valid_records)
                logger.info(f"{len(valid_records)}件の有効なレコードをデータベースに挿入しました。")
            else:
                logging.warning("有効なレコードが見つからなかったため、データベースへの挿入は行われませんでした。")

            self.final_df = enriched_df

            summary = {
                "file": str(path),
                "total_rows": len(enriched_df),
                "successful_inserts": len(valid_records),
                "failed_rows": len(invalid_records)
            }
            logging.info(f"ファイル処理が完了しました: {summary}")
            return summary

        except Exception as e:
            logger.error(f"ファイル処理中にエラーが発生しました: {path}, Error: {e}", exc_info=True)
            return {
                "file": str(path),
                "status": "failed",
                "error": str(e)
            }
