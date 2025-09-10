from pathlib import Path
import logging

# 1. --- Core Directories ---
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
REPORTS_DIR = ROOT_DIR / "reports"
SRC_DIR = ROOT_DIR / "src"
SAMPLE_DATA_DIR = DATA_DIR / "sample"

# 2. --- Database ---
DB_DIR = DATA_DIR / "sqlite"
DB_NAME = "production.db"
DB_PATH = DB_DIR / DB_NAME

# 3. --- File Paths ---
# Production paths (network drives)
PROD_DATA_PATH = Path(r"\\SAPIF01\host\MES\KANSEI_JISSEKI.txt")
PROD_MASTER_PATH = Path(r"\\SAPIF01\host\JOHODBDL\TEIKEI\MASTER\HINMOKU\MARA_DL.csv")
PROD_ZP02_PATH = Path(r"\\SAPIF01\host\ZP02\ZP02.TXT")
PROD_ZP58_PATH = Path(r"\\SAPIF01\host\ZP58\ZP58.txt")
PROD_ZS65_PATH = Path(r"\\SAPIF01\host\ZS65\ZS65.TXT")
PROD_WIP_DIR = Path(r"\\SAPIF01\全社共有\経営企画部　経理課\情ｼｽ在庫ﾃﾞｰﾀ\仕掛品")
# 保管場所一覧は固定ファイル名を想定。ユーザーからの情報に基づき、ファイル名は'保管場所一覧.csv'と仮定
PROD_STORAGE_LOCATIONS_PATH = Path(r"\\SAPIF01\host\storage_locations\保管場所一覧.csv")

# Development paths (local sample files)
DEV_DATA_PATH = SAMPLE_DATA_DIR / "KANSEI_JISSEKI.txt"
DEV_MASTER_PATH = SAMPLE_DATA_DIR / "MARA_DL.csv"
DEV_WIP_DETAILS_PATH = SAMPLE_DATA_DIR / "wip_details.csv"
DEV_ZP58_PATH = SAMPLE_DATA_DIR / "ZP58.txt"
DEV_ZP02_PATH = SAMPLE_DATA_DIR / "ZP02.TXT"
DEV_STORAGE_LOCATIONS_PATH = SAMPLE_DATA_DIR / "storage_locations.csv"
DEV_ZS65_PATH = SAMPLE_DATA_DIR / "ZS65.TXT"


# 4. --- Logging ---
LOG_FILE_NAME = "app.log"
LOG_FILE_PATH = LOGS_DIR / LOG_FILE_NAME
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

# --- Create Directories ---
# This ensures that the necessary directories exist when the application starts.
DB_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
