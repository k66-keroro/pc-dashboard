import pyodbc
import os
import pandas as pd
from typing import Optional
from datetime import datetime
import re

# --------------------
# 設定
# --------------------
BLACKLIST = {"SENS", "CV", "CV-055"}
DERIVATIVE_PATTERN = re.compile(r"([STU][0-9]{1,2}|[STU][A-Z][0-9])")  # ← 1〜2桁に拡張！

Y_CODE_MAP = {
    "YAMK": "m", "YAUWM": "w", "YAWM": "w", "YBPM": "p", "YCK": "c", "YCUWM": "w",
    "YGK": "g", "YMK": "m", "YPK": "p", "YPM": "p", "YUK": "w", "YWK": "w", "YWM": "w"
}

HEAD_CM_MAP = {
    "AK": "a", "CK": "c", "DK": "d", "EK": "e", "GK": "g", "HK": "h", "IK": "i", "LK": "l",
    "MK": "m", "PK": "p", "PM": "p", "SK": "s", "UK": "w", "UWM": "w", "WK": "w", "WM": "w", "WS": "w",
    "BWM": "w"
}

# --------------------
# 関数：派生コード抽出
# --------------------
def extract_derivative(text: str) -> Optional[str]:
    if not isinstance(text, str):
        return None
    candidates = DERIVATIVE_PATTERN.findall(text.upper())
    for cand in candidates:
        if cand.upper() not in BLACKLIST:
            return cand.upper()
    return None

# --------------------
# 関数：基板番号抽出（DIMCOM対応）
# --------------------
def extract_board_number(code: str, name: str) -> Optional[str]:
    if name.startswith("DIMCOM"):
        match = re.search(r"DIMCOM\s*(?:No\.\s*)?(\d{5})", name)
        if match:
            return match.group(1)  # 正しい5桁の番号を返す
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

# --------------------
# 関数：cm_code抽出（X/Y + 汎用対応 + fallback）
# --------------------
def extract_cm_code(code: str, name: str) -> str:
    name = name.upper()
    if code.startswith("P0E"):
        return "other"
    if name.startswith("WB"):
        return "CM-W"
    elif name.startswith("DIMCOM"):
        return "CM-L"
    elif name.startswith("CV"):
        return "CM-I"
    elif name.startswith("FK"):
        return "free"
    elif name.startswith("X"):
        if name.startswith("XAMK"):
            return "CM-M"
        elif name.startswith("XUK"):
            return "CM-W"
        else:
            return "CM-" + name[1].upper()
    elif name.startswith("Y"):
        for prefix_len in [5, 4, 3]:
            prefix = name[:prefix_len]
            if prefix in Y_CODE_MAP:
                return "CM-" + Y_CODE_MAP[prefix].upper()

    match = re.match(r"([A-Z]{2,4})", name)
    if match:
        key = match.group(1)
        if key in HEAD_CM_MAP:
            return "CM-" + HEAD_CM_MAP[key].upper()

    return "other"

# --------------------
# 新しいデータを処理し登録（全件処理／上書き）
# --------------------
def rebuild_parsed_pc_master(conn):
    df_all = pd.read_sql_query("SELECT 品目, 品目テキスト FROM view_pc_master", conn)

    df_all = df_all.copy()
    df_all["cm_code"] = df_all.apply(lambda row: extract_cm_code(row["品目"], row["品目テキスト"]), axis=1)

    # cm_codeが"other"の行は他項目を空にする
    df_all["board_number"] = df_all.apply(
        lambda row: extract_board_number(row["品目"], row["品目テキスト"]) if row["cm_code"] != "other" else None,
        axis=1)
    df_all["derivative_code"] = df_all.apply(
        lambda row: extract_derivative(row["品目テキスト"]) if row["cm_code"] != "other" else None,
        axis=1)
    df_all["board_type"] = df_all.apply(
        lambda row: "派生基板" if row["derivative_code"] else "標準" if row["cm_code"] != "other" else None,
        axis=1)

    df_all["登録日"] = datetime.now().strftime("%Y-%m-%d")

    # Access DBにデータを挿入
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM parsed_pc_master")  # 既存データを削除
    for _, row in df_all.iterrows():
        cursor.execute(
            f"""
            INSERT INTO parsed_pc_master (品目, 品目テキスト, cm_code, board_number, derivative_code, board_type, 登録日)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            row["品目"], row["品目テキスト"], row["cm_code"],
            row["board_number"], row["derivative_code"], row["board_type"], row["登録日"]
        )
    conn.commit()
    print(f"parsed_pc_master テーブルを再作成しました（{len(df_all)} 件登録）。")

# --------------------
# 実行本体
# --------------------
if __name__ == "__main__":
    ACCESS_PATH = r"C:\Projects_workspace\02_access\Database1.accdb"
    CONN_STR = (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        fr"DBQ={ACCESS_PATH};"
        r"Mode=Share Deny None;"
    )

    conn = pyodbc.connect(CONN_STR)

    rebuild_parsed_pc_master(conn)
    conn.close()
