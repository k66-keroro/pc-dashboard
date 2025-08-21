import logging
import pandas as pd
from pathlib import Path
from typing import List, Tuple, Dict, Any
import sqlite3

from pydantic import ValidationError
from src.models.production import ProductionRecord
from src.models.database import insert_production_records

logger = logging.getLogger(__name__)

class DataProcessor:
    """
    データファイルの処理とデータベースへのロードを担当するクラス。
    """

    def __init__(self, db_conn: sqlite3.Connection):
        """
        DataProcessorを初期化する。

        :param db_conn: SQLiteデータベースへの接続オブジェクト。
        """
        self.db_conn = db_conn

    def _load_and_clean_dataframe(self, file_path: Path) -> pd.DataFrame:
        """
        指定されたパスからデータを読み込み、基本的な前処理を行ってDataFrameを返す。
        """
        try:
            # Shift_JISでファイルを読み込み, 全てのカラムを文字列として扱う
            df = pd.read_csv(
                file_path,
                encoding='shift_jis',
                sep='\t',
                dtype=str, # 全て文字列として読み込む
                skiprows=0,
                encoding_errors='replace'
            )

            # カラム名の前後の空白を削除
            df.columns = df.columns.str.strip()

            # pandasが生成するNaNをNoneに置換
            df = df.where(pd.notna(df), None)

            # '入力日時' (YYYY/MM/DD HH:MM)
            # errors='coerce'は不正なフォーマットをNaT (Not a Time)に変換する
            df['入力日時'] = pd.to_datetime(df['入力日時'], format='%Y/%m/%d %H:%M', errors='coerce')

            # NaTをNoneに置換
            df = df.where(pd.notna(df), None)

            return df

        except FileNotFoundError:
            logging.error(f"ファイルが見つかりません: {file_path}")
            raise
        except pd.errors.EmptyDataError:
            logging.error(f"ファイルが空です: {file_path}")
            # 空のDataFrameを返して後続処理でハンドリング
            return pd.DataFrame()
        except Exception as e:
            logging.error(f"ファイルの読み込み中に予期せぬエラーが発生しました: {e}")
            raise

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
                logging.warning(f"バリデーションエラー: {e.errors()} | データ: {record_dict}")
                invalid_records.append({'data': record_dict, 'errors': e.errors()})

        return valid_records, invalid_records

    def process_and_load_file(self, file_path: str) -> dict:
        """
        単一のデータファイルを処理し、データベースにロードする。
        """
        path = Path(file_path)
        logging.info(f"ファイル処理を開始します: {path}")

        try:
            df = self._load_and_clean_dataframe(path)

            if df.empty:
                logging.warning(f"ファイルが空か、読み込みに失敗しました: {path}")
                total_rows = 0
                try:
                    with open(path, 'r', encoding='shift_jis', errors='replace') as f:
                        num_lines = sum(1 for line in f if line.strip())
                        if num_lines > 0:
                            total_rows = num_lines -1
                except (FileNotFoundError, Exception):
                    pass

                return {"file": file_path, "total_rows": total_rows, "successful_inserts": 0, "failed_rows": total_rows}

            valid_records, invalid_records = self._validate_and_transform_data(df)

            if valid_records:
                insert_production_records(self.db_conn, valid_records)
                logging.info(f"{len(valid_records)}件の有効なレコードをデータベースに挿入しました。")
            else:
                logging.warning("有効なレコードが見つからなかったため、データベースへの挿入は行われませんでした。")

            summary = {
                "file": file_path,
                "total_rows": len(df),
                "successful_inserts": len(valid_records),
                "failed_rows": len(invalid_records)
            }
            logging.info(f"ファイル処理が完了しました: {summary}")
            return summary

        except Exception as e:
            logging.error(f"ファイル処理中にエラーが発生しました: {file_path}, Error: {e}")
            return {
                "file": file_path,
                "status": "failed",
                "error": str(e)
            }
