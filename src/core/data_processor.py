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
        インスタンス化時に品目マスターを読み込んで保持する。

        :param db_conn: SQLiteデータベースへの接続オブジェクト。
        """
        self.db_conn = db_conn
        self.item_master_df = self._load_item_master()
        self.final_df = pd.DataFrame()

    def _load_item_master(self) -> pd.DataFrame:
        """品目マスターファイルを読み込む。"""
        try:
            master_df = pd.read_csv(
                settings.ITEM_MASTER_PATH,
                sep='\t',
                dtype={'品目': str, '標準原価': float}
            )
            master_df.rename(columns={'品目': 'item_code', '標準原価': 'standard_cost'}, inplace=True)
            master_df.set_index('item_code', inplace=True)
            logger.info(f"品目マスターを正常に読み込みました。{len(master_df)}件")
            return master_df
        except FileNotFoundError:
            logger.error(f"品目マスターファイルが見つかりません: {settings.ITEM_MASTER_PATH}")
            # マスターがなくても処理を続けられるように空のDataFrameを返す
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"品目マスターの読み込み中にエラーが発生しました: {e}")
            return pd.DataFrame()

    def _load_production_dataframe(self, file_path: Path) -> pd.DataFrame:
        """
        指定された生産実績ファイルを読み込み、基本的な前処理を行ってDataFrameを返す。
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

            # データ型の変換
            df['入力日時'] = pd.to_datetime(df['入力日時'], format='%Y/%m/%d %H:%M', errors='coerce')
            numeric_cols = ['指図数量', '実績数量', '累計数量', '残数量']
            for col in numeric_cols:
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
            prod_df['amount'] = 0
            return prod_df

        # Pydanticモデルのaliasに合わせてカラム名を一時的に変更
        prod_df.rename(columns={'品目コード': 'item_code'}, inplace=True)

        # マスターと結合
        enriched_df = pd.merge(
            prod_df,
            self.item_master_df,
            on='item_code',
            how='left'
        )

        # '実績数量' と 'standard_cost' を数値型に変換
        enriched_df['実績数量'] = pd.to_numeric(enriched_df['実績数量'], errors='coerce')
        enriched_df['standard_cost'] = pd.to_numeric(enriched_df['standard_cost'], errors='coerce')

        # 金額を計算 (実績数量 * 標準原価)
        enriched_df['amount'] = enriched_df['実績数量'] * enriched_df['standard_cost']

        # マスターに存在しなかった品目の処理
        missing_cost_count = enriched_df['amount'].isna().sum()
        if missing_cost_count > 0:
            missing_items = enriched_df[enriched_df['amount'].isna()]['item_code'].unique()
            logger.warning(f"{missing_cost_count}件のレコードで標準原価が見つからず、金額を0に設定しました。対象品目: {list(missing_items)}")
            enriched_df['amount'].fillna(0, inplace=True)

        # カラム名を元に戻す
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
                logging.warning(f"ファイルが空か、読み込みに失敗しました: {path}")
                return {"file": str(path), "total_rows": 0, "successful_inserts": 0, "failed_rows": 0}

            # データエンリッチメント（マスター結合と金額計算）
            enriched_df = self._enrich_data(prod_df)

            # バリデーションとDBロード
            valid_records, invalid_records = self._validate_and_transform_data(enriched_df)

            if valid_records:
                insert_production_records(self.db_conn, valid_records)
                logging.info(f"{len(valid_records)}件の有効なレコードをデータベースに挿入しました。")
            else:
                logging.warning("有効なレコードが見つからなかったため、データベースへの挿入は行われませんでした。")

            # 最終的なDFをインスタンス変数に格納
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
