import sys
import os
import argparse
import logging
import time
from pathlib import Path
import sqlite3

from src.models.database import get_db_connection
from src.models.migration_manager import apply_migrations
from src.core.data_processor import DataProcessor
from src.core.analytics import ProductionAnalytics, ErrorDetection
from src.core.reporter import ReportGenerator
from src.config import settings
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

import datetime

def run_pipeline(conn: sqlite3.Connection, prod_data_path: Path, inventory_path: Path):
    """
    一回のデータ処理パイプラインを実行する。
    """
    logger.info("パイプライン処理を開始します。")
    try:
        processor = DataProcessor(conn)

        # 1. 生産実績データの処理
        if prod_data_path.exists():
            logger.info(f"生産実績ファイルの処理を開始: {prod_data_path}")
            prod_summary = processor.process_file_and_load_to_db(prod_data_path)
            logger.info("========== 生産実績 処理結果サマリー ==========")
            logger.info(f"  ファイル: {prod_summary.get('file')}")
            logger.info(f"  総行数: {prod_summary.get('total_rows')}")
            logger.info(f"  成功した挿入件数: {prod_summary.get('successful_inserts')}")
            logger.info(f"  失敗した行数: {prod_summary.get('failed_rows')}")
            logger.info("============================================")
        else:
            logger.warning(f"生産実績データファイルが見つかりません: {prod_data_path}")
            prod_summary = {'successful_inserts': 0}

        # 2. 在庫データの処理
        if inventory_path.exists():
            logger.info(f"在庫データファイルの処理を開始: {inventory_path}")
            inv_summary = processor.process_inventory_file_and_load_to_db(inventory_path)
            logger.info("========== 在庫データ 処理結果サマリー ==========")
            logger.info(f"  ファイル: {inv_summary.get('file')}")
            logger.info(f"  総行数: {inv_summary.get('total_rows')}")
            logger.info(f"  成功した挿入件数: {inv_summary.get('successful_inserts')}")
            logger.info(f"  失敗した行数: {inv_summary.get('failed_rows')}")
            logger.info("============================================")
        else:
            logger.warning(f"在庫データファイルが見つかりません: {inventory_path}")

        # 分析とレポート生成は、生産実績データが処理された場合のみ実行
        if prod_summary.get('successful_inserts', 0) > 0:
            # 分析とレポート生成は、処理されたデータがある場合のみ実行
            logger.info("========== 生産実績サマリー ==========")
            analytics = ProductionAnalytics(conn)
            analytics_summary = analytics.get_summary()
            if analytics_summary:
                logger.info(f"  総レコード数: {analytics_summary.get('record_count')}")
                logger.info(f"  総計画数量: {analytics_summary.get('total_order_quantity'):,}")
                logger.info(f"  総実績数量: {analytics_summary.get('total_actual_quantity'):,}")
                logger.info(f"  全体達成率: {analytics_summary.get('achievement_rate')}%")

            logger.info("========== データ整合性チェック ==========")
            error_detector = ErrorDetection(conn)
            inconsistencies = error_detector.find_quantity_inconsistencies()
            if not inconsistencies.empty:
                logger.warning(f"{len(inconsistencies)}件の数量の不整合を検出しました。")
            else:
                logger.info("数量の不整合は見つかりませんでした。")

            logger.info("========== レポート生成 ==========")
            reporter = ReportGenerator(processor.final_df)
            reporter.generate_all_reports()

        logger.info("パイプライン処理が正常に完了しました。")

    except Exception as e:
        logger.error(f"パイプライン処理中にエラーが発生しました: {e}", exc_info=True)


def main():
    """
    アプリケーションのエントリーポイント。
    引数に応じて、マスター同期または常駐サービスとしてパイプラインを実行する。
    """
    setup_logging()
    parser = argparse.ArgumentParser(description="PC製造ダッシュボードのデータ処理サービス")
    parser.add_argument('--sync-master', action='store_true', help='品目マスターCSVをデータベースに同期して終了します。')
    parser.add_argument('--prod', action='store_true', help='本番モードで実行し、ネットワークパス上のファイルを参照します。')
    parser.add_argument('--run-once', action='store_true', help='パイプラインを1回だけ実行して終了します。')
    args = parser.parse_args()

    # モードに応じてパスを設定
    if args.prod:
        logger.info("本番モードで実行します。")
        prod_data_path = settings.PROD_DATA_PATH
        master_path = settings.PROD_MASTER_PATH
        inventory_path = settings.PROD_INVENTORY_PATH
    else:
        logger.info("開発モードで実行します。")
        prod_data_path = settings.DEV_DATA_PATH
        master_path = settings.DEV_MASTER_PATH
        inventory_path = settings.DEV_INVENTORY_PATH

    logger.info(f"生産実績データソース: {prod_data_path}")
    logger.info(f"在庫データソース: {inventory_path}")
    logger.info(f"マスターソース: {master_path}")

    logger.info("PC製造ダッシュボード - バックエンドサービス v2.2 開始")

    conn = get_db_connection()
    try:
        apply_migrations(conn)
        logger.info("データベースの準備が完了しました。")

        data_processor = DataProcessor(conn)

        if args.sync_master:
            data_processor.sync_master_from_csv(master_path)
            logger.info("品目マスターの同期が完了しました。プログラムを終了します。")
            sys.exit(0)

        if args.run_once:
            logger.info("シングルランモードで実行します。")
            run_pipeline(conn, prod_data_path, inventory_path)
        else:
            logger.info("常駐サービスモードで起動します。1時間ごとにデータ処理を実行します。")
            while True:
                run_pipeline(conn, prod_data_path, inventory_path)
                logger.info("次の実行まで1時間待機します...")
                time.sleep(3600)

    except Exception as e:
        logger.critical(f"アプリケーションの起動またはマイグレーション中に致命的なエラーが発生しました: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logger.info("データベース接続を閉じました。")

if __name__ == "__main__":
    main()
