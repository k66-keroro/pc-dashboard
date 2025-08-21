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
