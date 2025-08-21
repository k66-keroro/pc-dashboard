from pathlib import Path
import logging

# 1. プロジェクトのルートディレクトリを基準点として設定
#    このファイル (settings.py) の2階層上がプロジェクトルート
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# 2. 各主要ディレクトリへのパスを定義
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
REPORTS_DIR = ROOT_DIR / "reports"
SRC_DIR = ROOT_DIR / "src"

# 3. データベース関連の設定
#    - DBファイルを `data/sqlite/` の中に置く
DB_DIR = DATA_DIR / "sqlite"
DB_NAME = "production.db"
DB_PATH = DB_DIR / DB_NAME

# 4. データファイルの設定
DATA_FILE_NAME = "KANSEI_JISSEKI.txt"
DATA_FILE_PATH = ROOT_DIR / DATA_FILE_NAME

# 5. ロギング設定
LOG_FILE_NAME = "app.log"
LOG_FILE_PATH = LOGS_DIR / LOG_FILE_NAME
LOG_LEVEL = logging.INFO # or "INFO" as a string if preferred
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

# ディレクトリが存在しない場合に作成
DB_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
