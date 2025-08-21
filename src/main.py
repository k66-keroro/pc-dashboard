import sys
import os
import argparse
import logging

# プロジェクトのルートディレクトリをPythonパスに追加
# This is now handled by setting the project root in settings.py
# and running the script from the root.
# For direct execution, we might still need a path modification.
# Let's rely on running it as a module for now.
from src.models.database import get_db_connection, create_tables
from src.core.data_processor import DataProcessor
from src.core.analytics import ProductionAnalytics
from src.config import settings
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

def main():
    """
    データ処理パイプラインを実行するメイン関数。
    """
    # 1. ロギングと引数の設定
    setup_logging()
    parser = argparse.ArgumentParser(description="PC製造ダッシュボードのデータローダー")
    parser.add_argument(
        '--clean',
        action='store_true',
        help='実行前に既存のデータベースを削除します。'
    )
    args = parser.parse_args()

    logger.info("PC製造ダッシュボード - データローダー v2.0 開始")

    # 2. データファイルの存在確認
    if not settings.DATA_FILE_PATH.exists():
        logger.error(f"データファイルが見つかりません: {settings.DATA_FILE_PATH}")
        sys.exit(1)

    # 3. DBのクリーンアップ（引数による）
    if args.clean and os.path.exists(settings.DB_PATH):
        logger.warning(f"既存のデータベースファイルを削除します: {settings.DB_PATH}")
        os.remove(settings.DB_PATH)

    conn = None
    try:
        # 4. DB接続とテーブル作成
        logger.info(f"データベースに接続しています: {settings.DB_PATH}")
        conn = get_db_connection()
        create_tables(conn)
        logger.info("データベースとテーブルの準備が完了しました。")

        # 5. データ処理の実行
        processor = DataProcessor(conn)
        summary = processor.process_and_load_file(str(settings.DATA_FILE_PATH))

        # 6. 結果のサマリーを表示
        logger.info("========== 処理結果サマリー ==========")
        logger.info(f"  ファイル: {summary.get('file')}")
        logger.info(f"  総行数: {summary.get('total_rows')}")
        logger.info(f"  成功した挿入件数: {summary.get('successful_inserts')}")
        logger.info(f"  失敗した行数: {summary.get('failed_rows')}")
        logger.info("========================================")

        if summary.get('successful_inserts', 0) > 0:
            # 7. 分析処理の実行と結果表示
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

    except Exception as e:
        logger.critical(f"パイプラインの実行中に致命的なエラーが発生しました: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logger.info("データベース接続を閉じました。")

if __name__ == "__main__":
    main()
