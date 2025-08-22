import pandas as pd
import pyodbc
import re
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine
import os
import time
from pathlib import Path

# ----- 派生コード・基板番号・cm_code ロジック -----
BLACKLIST = {"SENS", "CV", "CV-055"}
DERIVATIVE_PATTERN = re.compile(r"([STU][0-9]{1,2}|[STU][A-Z][0-9])")

Y_CODE_MAP = {
    "YAMK": "m", "YAUWM": "w", "YAWM": "w", "YBPM": "p", "YCK": "c", "YCUWM": "w",
    "YGK": "g", "YMK": "m", "YPK": "p", "YPM": "p", "YUK": "w", "YWK": "w", "YWM": "w"
}

HEAD_CM_MAP = {
    "AK": "a", "CK": "c", "DK": "d", "EK": "e", "GK": "g", "HK": "h", "IK": "i", "LK": "l",
    "MK": "m", "PK": "p", "PM": "p", "SK": "s", "UK": "w", "UWM": "w", "WK": "w", "WM": "w", "WS": "w",
    "BWM": "w"
}

def extract_derivative(text: str) -> Optional[str]:
    if not isinstance(text, str): return None
    candidates = DERIVATIVE_PATTERN.findall(text.upper())
    for cand in candidates:
        if cand not in BLACKLIST:
            return cand
    return None

def extract_board_number(code: str, name: str) -> Optional[str]:
    if name.startswith("DIMCOM"):
        match = re.search(r"DIMCOM\s*(?:No\.\s*)?(\d{5})", name)
        if match:
            return match.group(1)
    if code.startswith("P00A"):
        return code[5:9]
    elif code.startswith("P0A"):
        return code[3:7]
    elif "-" in name:
        parts = name.split("-")
        if len(parts) > 1:
            match = re.search(r"\d{3,4}", parts[1])
            return match.group(0) if match else None
    elif re.search(r"\d{3,4}", name):
        return re.search(r"\d{3,4}", name).group(0)
    return None

def extract_cm_code(code: str, name: str) -> str:
    name = name.upper()
    if code.startswith("P0E"):
        return "other"
    if name.startswith("WB"): return "CM-W"
    if name.startswith("DIMCOM"): return "CM-L"
    if name.startswith("CV"): return "CM-I"
    if name.startswith("FK"): return "free"
    if name.startswith("X"):
        if name.startswith("XAMK"): return "CM-M"
        if name.startswith("XUK"): return "CM-W"
        return "CM-" + name[1]
    if name.startswith("Y"):
        for l in [5, 4, 3]:
            if name[:l] in Y_CODE_MAP:
                return "CM-" + Y_CODE_MAP[name[:l]].upper()
    m = re.match(r"([A-Z]{2,4})", name)
    if m and m.group(1) in HEAD_CM_MAP:
        return "CM-" + HEAD_CM_MAP[m.group(1)].upper()
    return "other"

# ----- パス設定（絶対パス使用） -----
SCRIPT_DIR = Path(__file__).parent
ACCESS_PATH = Path(r"C:\Projects_workspace\02_access\Database1.accdb")
LOG_FILE = SCRIPT_DIR / "a_everyday" / "差分登録ログ.csv"
DEBUG_LOG_FILE = SCRIPT_DIR / "debug_log.log"

# 接続文字列
CONN_STR = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    fr"DBQ={ACCESS_PATH};"
    r"Mode=Share Deny None;"
)
TABLE_NAME = "view_pc_master"
MASTER_NAME = "parsed_pc_master"

# サーバーDB設定
SERVER_DB_PATH = Path(r"\\fsdes02\Public\課共有\業務課\000_access_data\0_データ更新\900_PC_マスタ.accdb")
SERVER_CONN_STR = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    fr"DBQ={SERVER_DB_PATH};"
    r"Mode=Share Deny None;"
)

# ----- ユーティリティ関数 -----
def setup_logging():
    """ログ設定を初期化"""
    # ログディレクトリを作成
    DEBUG_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        filename=str(DEBUG_LOG_FILE),
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filemode='a',
        encoding='utf-8'
    )

def debug_file_status(file_path, label=""):
    """ファイル状態のデバッグ情報を出力"""
    try:
        file_path = Path(file_path)
        logging.debug(f"=== {label} ファイル状態確認: {file_path} ===")
        logging.debug(f"絶対パス: {file_path.absolute()}")
        logging.debug(f"存在: {file_path.exists()}")
        
        if file_path.exists():
            stat = file_path.stat()
            logging.debug(f"サイズ: {stat.st_size} bytes")
            logging.debug(f"最終更新: {datetime.fromtimestamp(stat.st_mtime)}")
            logging.debug(f"読み取り権限: {os.access(file_path, os.R_OK)}")
            logging.debug(f"書き込み権限: {os.access(file_path, os.W_OK)}")
        else:
            parent_dir = file_path.parent
            logging.debug(f"親ディレクトリ存在: {parent_dir.exists()}")
            if parent_dir.exists():
                logging.debug(f"親ディレクトリ書き込み権限: {os.access(parent_dir, os.W_OK)}")
        logging.debug("=" * 50)
    except Exception as e:
        logging.error(f"ファイル状態確認エラー ({label}): {e}")

def safe_csv_write(df, file_path, max_retries=3, retry_delay=1):
    """安全なCSV書き込み（リトライ機能付き）"""
    file_path = Path(file_path)
    
    # ディレクトリが存在しない場合は作成
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    for attempt in range(max_retries):
        try:
            logging.debug(f"CSV書き込み試行 {attempt + 1}/{max_retries}: {file_path}")
            df.to_csv(file_path, index=False, encoding="utf-8-sig")
            
            # 書き込み確認
            if file_path.exists() and file_path.stat().st_size > 0:
                last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                logging.info(f"CSV書き込み成功: {file_path} (更新日時: {last_modified})")
                return True
            else:
                logging.warning(f"CSV書き込み後にファイル確認失敗 (試行 {attempt + 1})")
                
        except (PermissionError, OSError) as e:
            logging.warning(f"CSV書き込み試行 {attempt + 1}/{max_retries} 失敗: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logging.error(f"CSV書き込み最終失敗: {e}")
                return False
        except Exception as e:
            logging.error(f"予期しないCSV書き込みエラー: {e}")
            return False
    
    return False

def check_table_exists(conn, table_name):
    """テーブルの存在確認"""
    try:
        tables = conn.cursor().tables(tableType='TABLE').fetchall()
        table_names = [table.table_name for table in tables]
        if table_name not in table_names:
            logging.error(f"テーブル '{table_name}' が存在しません。")
            return False
        return True
    except Exception as e:
        logging.error(f"テーブル確認中にエラーが発生しました: {e}")
        return False

def update_server_db():
    """サーバーDB更新処理"""
    logging.info("サーバーDB更新を開始します。")
    try:
        server_conn = pyodbc.connect(SERVER_CONN_STR)
        server_cursor = server_conn.cursor()

        insert_query = """
        INSERT INTO 8000_PC区分 (品目, 品目テキスト, a, b, c, 登録日)
        SELECT parsed_pc_master.品目, parsed_pc_master.品目テキスト, parsed_pc_master.cm_code, 
               parsed_pc_master.board_number, parsed_pc_master.derivative_code, parsed_pc_master.登録日
        FROM parsed_pc_master 
        LEFT JOIN 8000_PC区分 ON parsed_pc_master.品目 = [8000_PC区分].品目
        WHERE ((([8000_PC区分].品目) Is Null));
        """

        server_cursor.execute(insert_query)
        server_conn.commit()
        logging.info("サーバーDBにデータを追加しました。")

    except Exception as e:
        logging.error(f"サーバーDB更新中にエラーが発生しました: {e}")
    finally:
        server_cursor.close()
        server_conn.close()

# ----- メイン処理 -----
def main():
    # ログ設定
    setup_logging()
    logging.info("=== z_Parsed Pc Master Diff Logger.py の実行を開始しました ===")
    logging.info(f"スクリプトディレクトリ: {SCRIPT_DIR}")
    logging.info(f"作業ディレクトリ: {Path.cwd()}")
    
    # ファイル状態の初期確認
    debug_file_status(LOG_FILE, "初期状態")
    
    # データベース接続
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        logging.info("データベース接続成功")
    except Exception as e:
        logging.error(f"データベース接続失敗: {e}")
        return False

    try:
        # テーブル存在確認
        if not check_table_exists(conn, MASTER_NAME):
            print(f"テーブル '{MASTER_NAME}' が存在しません。処理を中断します。")
            return False

        # データを取得
        try:
            df_all = pd.read_sql(f"SELECT 品目, 品目テキスト FROM {TABLE_NAME}", conn)
            logging.info(f"全データ取得: {len(df_all)} 件")
        except Exception as e:
            logging.error(f"全データ取得エラー: {e}")
            df_all = pd.DataFrame(columns=["品目", "品目テキスト"])

        try:
            df_existing = pd.read_sql(f"SELECT 品目, 品目テキスト FROM {MASTER_NAME}", conn)
            logging.info(f"既存データ取得: {len(df_existing)} 件")
        except Exception as e:
            logging.error(f"既存データ取得エラー: {e}")
            df_existing = pd.DataFrame(columns=["品目", "品目テキスト"])

        # 差分データの生成
        logging.info("差分データの生成を開始します。")
        if not df_all.empty and not df_existing.empty:
            df_new = df_all[~df_all["品目"].isin(df_existing["品目"])]
        else:
            df_new = pd.DataFrame(columns=["品目", "品目テキスト"])
        
        logging.info(f"差分データ: {len(df_new)} 件")

        # 共通の出力用DataFrame準備
        output_columns = ["品目", "品目テキスト", "cm_code", "board_number", "derivative_code", "board_type", "登録日"]
        
        if df_new.empty:
            logging.info("差分なし（追加不要）")
            print("差分なし（追加不要）")
            
            # 空のDataFrameでもCSVを更新
            empty_df = pd.DataFrame(columns=output_columns)
            success = safe_csv_write(empty_df, LOG_FILE)
            if not success:
                logging.error("空の差分ログCSV出力に失敗しました")
            
        else:
            logging.info(f"{len(df_new)} 件の差分データを処理します。")
            
            # データ処理
            df_new = df_new.copy()
            df_new["cm_code"] = df_new.apply(lambda row: extract_cm_code(row["品目"], row["品目テキスト"]), axis=1)
            df_new["board_number"] = df_new.apply(lambda row: extract_board_number(row["品目"], row["品目テキスト"]) if row["cm_code"] != "other" else None, axis=1)
            df_new["derivative_code"] = df_new.apply(lambda row: extract_derivative(row["品目テキスト"]) if row["cm_code"] != "other" else None, axis=1)
            df_new["board_type"] = df_new.apply(lambda row: "派生基板" if row["derivative_code"] else "標準" if row["cm_code"] != "other" else None, axis=1)
            df_new["登録日"] = datetime.now().strftime("%Y-%m-%d")

            # 差分データをCSVに出力
            success = safe_csv_write(df_new, LOG_FILE)
            if not success:
                logging.error("差分ログCSV出力に失敗しました")
                return False

            # データベースへの登録
            logging.info("データベースへの登録を開始します。")
            inserted_count = 0
            for _, row in df_new.iterrows():
                try:
                    cursor.execute(
                        f"""
                        INSERT INTO {MASTER_NAME} (品目, 品目テキスト, cm_code, board_number, derivative_code, board_type, 登録日)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        row["品目"], row["品目テキスト"], row["cm_code"],
                        row["board_number"], row["derivative_code"], row["board_type"], row["登録日"]
                    )
                    inserted_count += 1
                except Exception as e:
                    logging.error(f"データベース登録エラー (品目: {row['品目']}): {e}")
            
            conn.commit()
            logging.info(f"{inserted_count} 件をデータベースに登録しました。")

        # 最終ファイル状態確認
        debug_file_status(LOG_FILE, "最終状態")

    except Exception as e:
        logging.error(f"メイン処理中にエラーが発生しました: {e}")
        return False
    finally:
        cursor.close()
        conn.close()
        logging.info("データベース接続を閉じました")

    # サーバーDB更新
    try:
        update_server_db()
    except Exception as e:
        logging.error(f"サーバーDB更新でエラーが発生しました: {e}")

    logging.info("=== z_Parsed Pc Master Diff Logger.py の実行が完了しました ===")
    return True

# スクリプト実行
if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)