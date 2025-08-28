import pandas as pd
import logging
from pathlib import Path

from src.utils.report_helpers import get_week_of_month
from src.config import settings

logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    分析データフレームから各種レポートを生成・出力するクラス。
    """

    def __init__(self, processed_df: pd.DataFrame):
        """
        コンストラクタ

        :param processed_df: データ処理済みのDataFrame
        """
        self.df = processed_df.copy()
        self.reports_dir = settings.REPORTS_DIR

        # レポート生成に必要な列を追加
        self._add_report_columns()

    def _add_report_columns(self):
        """
        レポート生成に必要な列（週区分など）をDataFrameに追加する。
        """
        logger.info("レポート用の列を追加しています...")
        # '入力日時'をdatetimeオブジェクトに変換
        self.df['入力日時'] = pd.to_datetime(self.df['入力日時'], errors='coerce')
        self.df.dropna(subset=['入力日時'], inplace=True)

        # '入力日時'から日付部分を抽出し、'完成日'を作成
        self.df['completion_date'] = self.df['入力日時'].dt.date

        # '週区分'を計算
        # dt.dateを適用できないNone値などがある場合を考慮
        self.df['week_category'] = self.df['completion_date'].apply(
            lambda d: get_week_of_month(d) if pd.notna(d) else None
        )
        logger.info("週区分列を追加しました。")

    def generate_all_reports(self):
        """
        すべてのレポートを生成してファイルに出力する。
        """
        logger.info("全レポートの生成を開始します。")
        self.generate_details_report()
        self.generate_daily_summary()
        self.generate_weekly_summary()
        logger.info(f"全レポートが {self.reports_dir} に出力されました。")

    def generate_details_report(self):
        """
        レポート1: 明細_抜粋
        """
        logger.info("レポート1: 明細_抜粋 を生成しています...")
        try:
            report_df = self.df[[
                'MRP管理者',
                'completion_date',
                '指図番号',
                '品目コード',
                '品目テキスト',
                '指図数量',
                '実績数量',
                'amount',
                'week_category'
            ]].copy()

            report_df.rename(columns={
                'MRP管理者': 'MRP管理者',
                'completion_date': '完成日',
                '指図番号': '指図',
                '品目コード': '品目コード',
                '品目テキスト': '品目テキスト',
                '指図数量': '計画数',
                '実績数量': '完成数',
                'amount': '金額',
                'week_category': '週区分'
            }, inplace=True)

            # 金額を整数に変換 (仕様に合わせて)
            report_df['金額'] = report_df['金額'].fillna(0).astype(int)

            output_path = self.reports_dir / "明細_抜粋.txt"
            report_df.to_csv(output_path, sep='\t', index=False, encoding='utf-8-sig')
            logger.info(f"明細_抜粋レポートが {output_path} に保存されました。")

        except Exception as e:
            logger.error(f"明細_抜粋レポートの生成中にエラーが発生しました: {e}", exc_info=True)

    def generate_daily_summary(self):
        """
        レポート2: 日別サマリー
        """
        logger.info("レポート2: 日別サマリー を生成しています...")
        try:
            # 日別、MRP管理者別に金額を集計
            daily_summary = self.df.groupby(['week_category', 'completion_date', 'MRP管理者'])['amount'].sum().reset_index()

            # MRP管理者を列にピボット
            pivot_df = daily_summary.pivot_table(
                index=['week_category', 'completion_date'],
                columns='MRP管理者',
                values='amount',
                fill_value=0
            ).reset_index()

            # 必要なPCの列をすべて存在させる
            all_pcs = [f'PC{i}' for i in range(1, 7)]
            for pc in all_pcs:
                if pc not in pivot_df.columns:
                    pivot_df[pc] = 0

            # 日別金額（合計）を計算
            pivot_df['日別金額'] = pivot_df[all_pcs].sum(axis=1)

            # '日付'列を追加
            pivot_df['日付'] = pivot_df['completion_date']

            # 仕様に合わせた列順序に並び替え
            final_columns = ['週区分', '完成日', '日付', 'PC1', 'PC2', 'PC4', 'PC5', 'PC6', '日別金額']
            # PC3は仕様にないので除外

            report_df = pivot_df.rename(columns={
                'week_category': '週区分',
                'completion_date': '完成日'
            })[final_columns]

            # 金額を整数に変換
            for col in ['PC1', 'PC2', 'PC4', 'PC5', 'PC6', '日別金額']:
                report_df[col] = report_df[col].astype(int)

            output_path = self.reports_dir / "日別サマリー.txt"
            report_df.to_csv(output_path, sep='\t', index=False, encoding='utf-8-sig')
            logger.info(f"日別サマリーレポートが {output_path} に保存されました。")

        except Exception as e:
            logger.error(f"日別サマリーレポートの生成中にエラーが発生しました: {e}", exc_info=True)

    def generate_weekly_summary(self):
        """
        レポート3: 週別サマリー
        """
        logger.info("レポート3: 週別サマリー を生成しています...")
        try:
            # 週別、MRP管理者別に金額を集計
            weekly_summary = self.df.groupby(['week_category', 'MRP管理者'])['amount'].sum().reset_index()

            # MRP管理者を列にピボット
            pivot_df = weekly_summary.pivot_table(
                index='week_category',
                columns='MRP管理者',
                values='amount',
                fill_value=0
            )

            # 必要なPCの列をすべて存在させる
            all_pcs = [f'PC{i}' for i in range(1, 7)]
            for pc in all_pcs:
                if pc not in pivot_df.columns:
                    pivot_df[pc] = 0

            # 合計列を計算
            pivot_df['合計'] = pivot_df[all_pcs].sum(axis=1)

            # 合計行を追加
            total_row = pivot_df.sum()
            total_row.name = '合計'
            pivot_df = pd.concat([pivot_df, pd.DataFrame(total_row).T])

            # 列を並び替え
            final_columns = ['PC1', 'PC2', 'PC4', 'PC5', 'PC6', '合計']
            report_df = pivot_df.rename_axis('週区分').reset_index()[['週区分'] + final_columns]

            # 金額を整数に変換
            for col in final_columns:
                report_df[col] = report_df[col].astype(int)

            output_path = self.reports_dir / "週別サマリー.txt"
            report_df.to_csv(output_path, sep='\t', index=False, encoding='utf-8-sig')
            logger.info(f"週別サマリーレポートが {output_path} に保存されました。")

        except Exception as e:
            logger.error(f"週別サマリーレポートの生成中にエラーが発生しました: {e}", exc_info=True)
