import logging
import sys
from src.config import settings

def setup_logging():
    """
    アプリケーションのロギングを設定する。
    - コンソールとログファイルの両方に出力する。
    - 設定は settings.py から取得する。
    """
    # getLogger() でルートロガーを取得するのではなく、
    # アプリケーション固有のロガーを取得することで、他のライブラリのログに影響を与えにくくする
    # ここではルートロガーを設定する
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    # 既存のハンドラをクリアして、重複して設定されるのを防ぐ
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # フォーマッタの作成
    formatter = logging.Formatter(settings.LOG_FORMAT)

    # 1. コンソールへのハンドラ
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. ファイルへのハンドラ
    file_handler = logging.FileHandler(settings.LOG_FILE_PATH, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.info("ロギング設定が完了しました。")
