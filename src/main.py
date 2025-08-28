import sys
import os
import argparse
import logging
import time

from src.models.database import get_db_connection
from src.models.migration_manager import apply_migrations
from src.core.data_processor import DataProcessor
from src.core.analytics import ProductionAnalytics, ErrorDetection
from src.core.reporter import ReportGenerator
from src.config import settings
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

def run_pipeline(conn):
    """
    一回のデータ処理パイプラインを実行する。
    """
    logger.info("パイプライン処理を開始します。")
    try:
        # 1. データ処理の実行
        processor = DataProcessor(conn)
        summary = processor.process_file_and_load_to_db()

        # 2. 結果のサマリーを表示
        logger.info("========== 処理結果サマリー ==========")
        logger.info(f"  ファイル: {summary.get('file')}")
        logger.info(f"  総行数: {summary.get('total_rows')}")
        logger.info(f"  成功した挿入件数: {summary.get('successful_inserts')}")
        logger.info(f"  失敗した行数: {summary.get('failed_rows')}")
        logger.info("========================================")

        if summary.get('successful_inserts', 0) > 0:
            # 3. 分析処理の実行と結果表示
            logger.info("========== 生産実績サマリー ==========")
            analytics = ProductionAnalytics(conn)
            analytics_summary = analytics.get_summary()
            if analytics_summary:
                logger.info(f"  総レコード数: {analytics_summary.get('record_count')}")
                logger.info(f"  総計画数量: {analytics_summary.get('total_order_quantity'):,}")
                logger.info(f"  総実績数量: {analytics_summary.get('total_actual_quantity'):,}")
                logger.info(f"  全体達成率: {analytics_summary.get('achievement_rate')}%")
            else:
                logger.warning("分析サマリーの生成に失敗しました。")
            logger.info("========================================")

            # 4. データ整合性チェックの実行と結果表示
            logger.info("========== データ整合性チェック ==========")
            error_detector = ErrorDetection(conn)
            inconsistencies = error_detector.find_quantity_inconsistencies()
            if not inconsistencies.empty:
                logger.warning(f"{len(inconsistencies)}件の数量の不整合を検出しました。")
                logger.warning("不整合データ:\n" + inconsistencies.to_string())
            else:
                logger.info("数量の不整合は見つかりませんでした。")
            logger.info("========================================")

            # 5. レポート生成
            logger.info("========== レポート生成 ==========")
            reporter = ReportGenerator(processor.final_df)
            reporter.generate_all_reports()
            logger.info("===================================")

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
    parser.add_argument(
        '--sync-master',
        action='store_true',
        help='品目マスターCSVをデータベースに同期して終了します。'
    )
    parser.add_argument(
        '--prod',
        action='store_true',
        help='本番モードで実行し、ネットワークパス上のファイルを参照します。'
    )
    args = parser.parse_args()

    # 本番モードの場合は、設定を本番用に切り替え
    if args.prod:
        settings.initialize_production_paths()

    logger.info("PC製造ダッシュボード - バックエンドサービス v2.1 開始")

    # DB接続とマイグレーションは最初に実行
    conn = get_db_connection()
    try:
        apply_migrations(conn)
        logger.info("データベースの準備が完了しました。")

        data_processor = DataProcessor(conn)

        if args.sync_master:
            data_processor.sync_master_from_csv()
            logger.info("品目マスターの同期が完了しました。プログラムを終了します。")
            sys.exit(0)

        # 常駐サービスとして実行
        logger.info("常駐サービスモードで起動します。1時間ごとにデータ処理を実行します。")
        while True:
            run_pipeline(conn)
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
