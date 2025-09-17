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

class WipAnalysis:
    """
    仕掛品の進捗状況を分析するクラス。
    """
    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn

    def _get_base_wip_data(self) -> pd.DataFrame:
        """
        分析の基礎となる、関連テーブルを結合した仕掛データを取得する。
        """
        query = """
        SELECT
            d.wip_age,
            d.amount_jpy,
            d.item_code,
            z02.order_status,
            CASE WHEN z58.order_number IS NOT NULL THEN 1 ELSE 0 END AS has_zp58
        FROM
            wip_details d
        LEFT JOIN
            zp02_records z02 ON d.order_number = z02.order_number
        LEFT JOIN
            zp58_records z58 ON d.order_number = z58.order_number
        WHERE
            d.mrp_controller LIKE 'P%';
        """
        return pd.read_sql_query(query, self.conn)

    def get_wip_summary_comparison(self) -> pd.DataFrame:
        """
        完了品を除外する前と後での仕掛状況を比較したサマリーを返す。
        """
        logger.info("仕掛進捗の比較サマリー分析を開始します。")
        try:
            base_df = self._get_base_wip_data()
            if base_df.empty:
                logger.warning("分析対象の仕掛データがありません。")
                return pd.DataFrame()

            # 1. 全仕掛データの集計
            total_agg = base_df.groupby('wip_age').agg(
                total_amount=('amount_jpy', 'sum'),
                total_count=('item_code', 'count')
            ).reset_index()

            # 2. 完了(TECO, DLV)を除いた仕掛データの集計
            remaining_df = base_df[
                ~base_df['order_status'].isin(['TECO', 'DLV'])
            ]
            remaining_agg = remaining_df.groupby('wip_age').agg(
                remaining_amount=('amount_jpy', 'sum'),
                remaining_count=('item_code', 'count')
            ).reset_index()

            # 3. 二つの集計結果を結合
            comparison_df = pd.merge(total_agg, remaining_agg, on='wip_age', how='left').fillna(0)

            # 列名を日本語にリネームして最終的な出力とする
            comparison_df.rename(columns={
                'wip_age': '仕掛年齢',
                'total_amount': '当初金額',
                'total_count': '当初件数',
                'remaining_amount': '残高金額',
                'remaining_count': '残高件数'
            }, inplace=True)

            logger.info("仕掛進捗の比較サマリー分析が完了しました。")
            return comparison_df

        except Exception as e:
            logger.error(f"仕掛進捗サマリーの分析中にエラーが発生しました: {e}", exc_info=True)
            return pd.DataFrame()

class PcStockAnalysis:
    """
    PC関連の在庫分析を行うクラス。
    """
    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn

    def get_pc_stock_summary(self) -> pd.DataFrame:
        """
        PC関連の在庫を集計し、滞留年数と区分ごとのサマリーを返す。
        """
        logger.info("PC在庫のサマリー分析を開始します。")
        try:
            query = """
            SELECT
                sl.responsible_dept,
                sl.inventory_report_category,
                sl.storage_location,
                sl.storage_location_name,
                zs.item_code,
                zs.item_text,
                zs.available_stock AS quantity,
                zs.available_value AS amount,
                zs.stagnant_days
            FROM
                zs65_records zs
            LEFT JOIN
                storage_locations sl ON zs.storage_location = sl.storage_location
            WHERE
                sl.inventory_report_category = '3_PC'
                AND zs.plant = 'P100'
                AND sl.factory_stock_category = 'Yes';
            """
            df = pd.read_sql_query(query, self.conn)

            if df.empty:
                logger.warning("分析対象のPC在庫データがありません。")
                return pd.DataFrame()

            # 滞留区分と滞留年数の計算
            df['stagnant_days'] = pd.to_numeric(df['stagnant_days'], errors='coerce').fillna(0)

            def assign_category(days):
                if days > 730:
                    return 'a. 2年以上'
                if days > 365:
                    return 'b. 1年以上'
                return 'c. 1年未満'

            df['category'] = df['stagnant_days'].apply(assign_category)
            df['stagnant_years'] = (df['stagnant_days'] / 365).astype(int)

            # 集計
            summary_df = df.groupby(['category', 'stagnant_years']).agg(
                total_amount=('amount', 'sum'),
                item_count=('item_code', 'count')
            ).reset_index()

            # 列名をリネーム
            summary_df.rename(columns={
                'category': '区分',
                'stagnant_years': '滞留年数',
                'total_amount': '金額',
                'item_count': '品目数'
            }, inplace=True)

            logger.info("PC在庫のサマリー分析が完了しました。")
            return summary_df.sort_values(by=['区分', '滞留年数'])

        except Exception as e:
            logger.error(f"PC在庫サマリーの分析中にエラーが発生しました: {e}", exc_info=True)
            return pd.DataFrame()
