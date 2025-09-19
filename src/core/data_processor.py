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
    データファイルの処理、加工、データベースへのロードを担当するクラス。
    """
    def __init__(self, db_conn: sqlite3.Connection):
        self.db_conn = db_conn
        self.final_df = pd.DataFrame()

    def _load_item_master_from_db(self) -> pd.DataFrame:
        try:
            query = "SELECT name FROM sqlite_master WHERE type='table' AND name='item_master';"
            cursor = self.db_conn.cursor()
            cursor.execute(query)
            if cursor.fetchone() is None:
                return pd.DataFrame()
            master_df = pd.read_sql_query("SELECT item_code, standard_cost FROM item_master", self.db_conn)
            master_df.set_index('item_code', inplace=True)
            return master_df
        except Exception as e:
            logger.error(f"DBからの品目マスター読み込み中にエラーが発生しました: {e}")
            return pd.DataFrame()

    def sync_master_from_csv(self, master_path: Path):
        logger.info(f"品目マスターの同期（洗い替え）を開始します: {master_path}")
        try:
            # MARA_DL.csvを読み込む。エンコードはUTF-16、セパレータは自動判別。
            # usecolsは指定せず、全列を読み込んでから処理する。
            master_df = pd.read_csv(
                master_path, sep=None, engine='python',
                encoding='utf-16'
            )

            # P100プラントでフィルタ（列が存在する場合のみ）
            if 'プラント' in master_df.columns:
                initial_count = len(master_df)
                master_df = master_df[master_df['プラント'] == 'P100'].copy()
                logger.info(f"P100プラントでフィルタリング: {initial_count}件 → {len(master_df)}件")
            else:
                logger.warning("マスターファイルに 'プラント' 列が見つからないため、フィルタリングをスキップします。")

            # 必要な列が存在するか確認
            required_cols = {'品目': 'item_code', '標準原価': 'standard_cost'}
            if not all(col in master_df.columns for col in required_cols.keys()):
                logger.error(f"マスターファイルに必要な列 {list(required_cols.keys())} がありません。")
                return

            master_df.rename(columns=required_cols, inplace=True)

            if 'item_code' in master_df.columns:
                master_df['item_code'] = master_df['item_code'].str.strip()

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
        except FileNotFoundError:
            logger.error(f"品目マスターファイルが見つかりません: {master_path}")
        except Exception as e:
            logger.error(f"品目マスターの同期中にエラーが発生しました: {e}", exc_info=True)


    def _load_production_dataframe(self, file_path: Path) -> pd.DataFrame:
        try:
            df = pd.read_csv(
                file_path, encoding='shift_jis', sep='\t',
                dtype=str, skiprows=0, encoding_errors='replace'
            )
            df.columns = df.columns.str.strip()
            df = df.where(pd.notna(df), None)

            if '品目コード' in df.columns:
                df['品目コード'] = df['品目コード'].str.strip()

            original_rows = len(df)
            if 'MRP管理者' in df.columns:
                df = df[df['MRP管理者'].str.startswith('PC', na=False)].copy()
                logger.info(f"MRP管理者フィルタを適用: {original_rows}行 -> {len(df)}行")

            if '入力日時' in df.columns:
                df['入力日時'] = pd.to_datetime(df['入力日時'], format='%Y/%m/%d %H:%M', errors='coerce')
                df.dropna(subset=['入力日時'], inplace=True)
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

    def _enrich_data(self, prod_df: pd.DataFrame, master_df: pd.DataFrame) -> pd.DataFrame:
        if master_df.empty:
            logger.warning("品目マスターが空のため、金額計算をスキップします。")
            prod_df['amount'] = 0.0
            return prod_df

        prod_df_temp = prod_df.rename(columns={'品目コード': 'item_code'})

        enriched_df = pd.merge(prod_df_temp, master_df, on='item_code', how='left')

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
        valid_records, invalid_records = [], []
        for record_dict in df.to_dict(orient='records'):
            try:
                valid_records.append(ProductionRecord(**record_dict))
            except ValidationError as e:
                logger.warning(f"バリデーションエラー: {e.errors()} | データ: {record_dict}")
                invalid_records.append({'data': record_dict, 'errors': e.errors()})
        return valid_records, invalid_records

    def process_file_and_load_to_db(self, data_path: Path) -> dict:
        logging.info(f"ファイル処理を開始します: {data_path}")
        try:
            prod_df = self._load_production_dataframe(data_path)
            if prod_df.empty:
                return {"file": str(data_path), "total_rows": 0, "successful_inserts": 0, "failed_rows": 0}

            master_df = self._load_item_master_from_db()
            enriched_df = self._enrich_data(prod_df, master_df)
            valid_records, invalid_records = self._validate_and_transform_data(enriched_df)

            if valid_records:
                insert_production_records(self.db_conn, valid_records)
                logger.info(f"{len(valid_records)}件の有効なレコードをデータベースに挿入しました。")

            self.final_df = enriched_df
            summary = {
                "file": str(data_path), "total_rows": len(enriched_df),
                "successful_inserts": len(valid_records), "failed_rows": len(invalid_records)
            }
            logging.info(f"ファイル処理が完了しました: {summary}")
            return summary
        except Exception as e:
            logger.error(f"ファイル処理中にエラーが発生しました: {data_path}, Error: {e}", exc_info=True)
            return {"file": str(data_path), "status": "failed", "error": str(e)}
