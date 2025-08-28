from pathlib import Path
import logging

# --- Core Directories ---
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
REPORTS_DIR = ROOT_DIR / "reports"
SRC_DIR = ROOT_DIR / "src"
SAMPLE_DATA_DIR = DATA_DIR / "sample"

# --- Database ---
DB_DIR = DATA_DIR / "sqlite"
DB_NAME = "production.db"
DB_PATH = DB_DIR / DB_NAME

# --- Logging ---
LOG_FILE_NAME = "app.log"
LOG_FILE_PATH = LOGS_DIR / LOG_FILE_NAME
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

# --- File Paths (initialized to development by default) ---
IS_PRODUCTION = False # This will be set by main.py or app.py at runtime
DATA_FILE_PATH = SAMPLE_DATA_DIR / "KANSEI_JISSEKI.txt"
ITEM_MASTER_PATH = SAMPLE_DATA_DIR / "MARA_DL.csv"

def initialize_production_paths():
    """
    Called at runtime by entry points if in production mode.
    """
    global IS_PRODUCTION, DATA_FILE_PATH, ITEM_MASTER_PATH
    IS_PRODUCTION = True
    DATA_FILE_PATH = Path(r"\\SAPIF01\host\MES\KANSEI_JISSEKI.txt")
    ITEM_MASTER_PATH = Path(r"\\SAPIF01\host\JOHODBDL\TEIKEI\MASTER\HINMOKU\MARA_DL.csv")
    logger = logging.getLogger(__name__)
    logger.info("本番モードで実行中。ネットワークパスを使用します。")

# --- Create Directories ---
DB_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
