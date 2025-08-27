from pathlib import Path
import logging
import os

# 1. プロジェクトのルートディレクトリを基準点として設定
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# 2. 各主要ディレクトリへのパスを定義
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
REPORTS_DIR = ROOT_DIR / "reports"
SRC_DIR = ROOT_DIR / "src"
SAMPLE_DATA_DIR = DATA_DIR / "sample"

# 3. 環境設定 (開発/本番)
# 環境変数 `APP_ENV` が 'production' に設定されていれば本番、それ以外は開発とみなす
APP_ENV = os.getenv("APP_ENV", "development")

# 4. データベース関連の設定
DB_DIR = DATA_DIR / "sqlite"
DB_NAME = "production.db"
DB_PATH = DB_DIR / DB_NAME

# 5. データファイルのパス設定
if APP_ENV == "production":
    # 本番環境: ユーザー指定のネットワークパス
    # WindowsのUNCパスを表現するためにraw文字列(r"...")を使用
    DATA_FILE_PATH = Path(r"\\SAPIF01\host\MES\KANSEI_JISSEKI.txt")
    ITEM_MASTER_PATH = Path(r"\\SAPIF01\host\JOHODBDL\TEIKEI\MASTER\HINMOKU\MARA_DL.csv")
else:
    # 開発環境: プロジェクト内のサンプルデータ
    DATA_FILE_PATH = SAMPLE_DATA_DIR / "KANSEI_JISSEKI.txt"
    ITEM_MASTER_PATH = SAMPLE_DATA_DIR / "MARA_DL.csv"

# 6. ロギング設定
LOG_FILE_NAME = "app.log"
LOG_FILE_PATH = LOGS_DIR / LOG_FILE_NAME
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

# ディレクトリが存在しない場合に作成
DB_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
