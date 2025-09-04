"""
このモジュールは、生産実績データに対する分析機能を提供します。
- 生産実績分析 (計画 vs 実績)
- エラー検出
- 在庫滞留分析
などのクラスを格納します。
"""
import sqlite3
import pandas as pd
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ProductionAnalytics:
    """生産実績の分析を行うクラス"""

    def __init__(self, db_conn: sqlite3.Connection):
        """
        コンストラクタ

        :param db_conn: SQLiteデータベースへの接続オブジェクト
        """
        self.db_conn = db_conn

    def get_summary(self) -> Dict[str, Any]:
        """
        生産実績の全体サマリー（計画、実績、達成率）を計算して返す。

        :return: サマリー情報を含む辞書
        """
        try:
            df = pd.read_sql_query("SELECT order_quantity, actual_quantity FROM production_records", self.db_conn)

            if df.empty:
                return {
                    "total_order_quantity": 0,
                    "total_actual_quantity": 0,
                    "achievement_rate": 0.0,
                    "record_count": 0
                }

            total_order_quantity = df['order_quantity'].sum()
            total_actual_quantity = df['actual_quantity'].sum()

            if total_order_quantity > 0:
                achievement_rate = (total_actual_quantity / total_order_quantity) * 100
            else:
                achievement_rate = 0.0

            return {
                "total_order_quantity": int(total_order_quantity),
                "total_actual_quantity": int(total_actual_quantity),
                "achievement_rate": round(achievement_rate, 2),
                "record_count": len(df)
            }
        except Exception as e:
            logger.error(f"生産サマリーの分析中にエラーが発生しました: {e}", exc_info=True)
            return {}


class ErrorDetection:
    """
    データ内の不整合や業務ルール違反を検出するクラス。
    """

    def __init__(self, db_conn: sqlite3.Connection):
        """
        コンストラクタ

        :param db_conn: SQLiteデータベースへの接続オブジェクト
        """
        self.db_conn = db_conn

    def find_quantity_inconsistencies(self) -> pd.DataFrame:
        """
        数量の計算が一致しないレコードを検出する。
        (指図数量 - 累計数量 != 残数量)

        :return: 数量が不整合なレコードを含むDataFrame
        """
        try:
            query = """
            SELECT
                id,
                order_number,
                item_code,
                item_text,
                order_quantity,
                cumulative_quantity,
                remaining_quantity,
                (order_quantity - cumulative_quantity) AS expected_remaining
            FROM
                production_records
            WHERE
                (order_quantity - cumulative_quantity) != remaining_quantity;
            """
            df = pd.read_sql_query(query, self.db_conn)
            logger.info(f"数量の不整合チェックを実行しました。{len(df)}件のエラーを検出しました。")
            return df
        except Exception as e:
            logger.error(f"数量の不整合チェック中にエラーが発生しました: {e}", exc_info=True)
            return pd.DataFrame()

    def find_unregistered_items(self) -> pd.DataFrame:
        """
        item_masterに登録されていない品目コードを持つ生産実績レコードを検出する。

        :return: 未登録品目を含む生産実績レコードのDataFrame
        """
        try:
            query = """
            SELECT
                pr.id,
                pr.order_number,
                pr.item_code,
                pr.item_text,
                pr.input_datetime
            FROM
                production_records pr
            LEFT JOIN
                item_master im ON pr.item_code = im.item_code
            WHERE
                im.item_code IS NULL;
            """
            df = pd.read_sql_query(query, self.db_conn)
            logger.info(f"未登録品目のチェックを実行しました。{len(df)}件のエラーを検出しました。")
            return df
        except Exception as e:
            logger.error(f"未登録品目のチェック中にエラーが発生しました: {e}", exc_info=True)
            return pd.DataFrame()


class InventoryAnalysis:
    """
    在庫に関連する分析を行うクラス。
    """
    def __init__(self, db_conn: sqlite3.Connection):
        """
        コンストラクタ

        :param db_conn: SQLiteデータベースへの接続オブジェクト
        """
        self.db_conn = db_conn

    def get_stagnant_items(self, threshold_days: int) -> pd.DataFrame:
        """
        指定された日数以上、生産実績がない（動きがない）品目を特定する。

        :param threshold_days: 滞留とみなす日数（この日数を超えて動きがないものを対象とする）
        :return: 滞留している品目の情報を含むDataFrame
        """
        try:
            query = "SELECT item_code, item_text, input_datetime FROM production_records"
            df = pd.read_sql_query(query, self.db_conn)

            if df.empty:
                return pd.DataFrame()

            # データ準備
            df['input_datetime'] = pd.to_datetime(df['input_datetime'])
            df['completion_date'] = df['input_datetime'].dt.date
            df['completion_date'] = pd.to_datetime(df['completion_date'])

            # 品目ごとに最新のレコードを取得
            latest_records_idx = df.groupby('item_code')['completion_date'].idxmax()
            latest_df = df.loc[latest_records_idx].copy()

            # 今日との差分を計算
            today = pd.to_datetime(pd.Timestamp.now().date())
            latest_df['days_since_last_completion'] = (today - latest_df['completion_date']).dt.days

            # 閾値を超えるものだけをフィルタリング
            stagnant_df = latest_df[latest_df['days_since_last_completion'] > threshold_days].copy()

            # 結果をフォーマット
            stagnant_df = stagnant_df[['item_code', 'item_text', 'completion_date', 'days_since_last_completion']]
            stagnant_df.rename(columns={
                'item_code': '品目コード',
                'item_text': '品目名',
                'completion_date': '最終生産日',
                'days_since_last_completion': '経過日数'
            }, inplace=True)

            # 日付のフォーマットを 'YYYY-MM-DD' 形式の文字列に変換
            stagnant_df['最終生産日'] = stagnant_df['最終生産日'].dt.strftime('%Y-%m-%d')

            logger.info(f"滞留在庫チェックを実行しました（閾値: {threshold_days}日）。{len(stagnant_df)}件を検出しました。")
            return stagnant_df.sort_values(by='経過日数', ascending=False)

        except Exception as e:
            logger.error(f"滞留在庫の分析中にエラーが発生しました: {e}", exc_info=True)
            return pd.DataFrame()
