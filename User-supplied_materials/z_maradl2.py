import sqlite3
import pyodbc
import pandas as pd
from datetime import datetime
import os

def read_sqlite_table_to_df(sqlite_db_path, sqlite_table):
    conn = sqlite3.connect(sqlite_db_path)
    df = pd.read_sql_query(f"SELECT * FROM {sqlite_table}", conn)
    conn.close()
    return df

def row_to_sql_values(row):
    def sql_escape(val):
        if pd.isna(val):
            return "NULL"
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, datetime):
            return f"#{val.strftime('%Y-%m-%d %H:%M:%S')}#"
        val_str = str(val).replace("'", "''")
        return f"'{val_str}'"
    return f"({', '.join(sql_escape(v) for v in row)})"

def bulk_insert_to_access(access_db_path, access_table, df, column_mapping, batch_size=10000):
    # ファイルの存在を確認
    if not os.path.exists(access_db_path):
        raise FileNotFoundError(f"Access ファイルが見つかりません: {access_db_path}")

    access_conn_str = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={access_db_path};"
    conn = pyodbc.connect(access_conn_str)
    cursor = conn.cursor()

    try:
        cursor.execute(f"DROP TABLE {access_table}")
        conn.commit()
    except Exception:
        pass

    col_defs = ', '.join(f"[{col}] {dtype}" for col, dtype in column_mapping.items())
    cursor.execute(f"CREATE TABLE {access_table} ({col_defs})")
    conn.commit()

    columns_sql = ', '.join(f"[{col}]" for col in column_mapping.keys())
    total_rows = len(df)
    inserted = 0

    for i in range(0, total_rows, batch_size):
        batch = df.iloc[i:i+batch_size]
        for row in batch.itertuples(index=False):
            values_sql = row_to_sql_values(row)
            insert_sql = f"INSERT INTO {access_table} ({columns_sql}) VALUES {values_sql};"
            try:
                cursor.execute(insert_sql)
            except Exception as e:
                print(f"Error during row insert: {e}")
                break
        conn.commit()
        inserted += len(batch)
        print(f"Inserted: {inserted} / {total_rows}")

    cursor.close()
    conn.close()
    return inserted

if __name__ == "__main__":
    sqlite_db_path = r"C:\Projects_workspace\02_access\Database1.sqlite"
    access_db_path = r"C:\Projects_workspace\02_access\Database1.accdb"
    sqlite_table = "MARA_DL"
    access_table = "MARA_DL"

    # ファイルの存在を確認
    if not os.path.exists(sqlite_db_path):
        print(f"SQLite ファイルが見つかりません: {sqlite_db_path}")
        exit(1)

    df = read_sqlite_table_to_df(sqlite_db_path, sqlite_table)

    column_mapping = {col: 'TEXT' for col in df.columns}  # 必要に応じて型を調整

    print("開始...")
    try:
        count = bulk_insert_to_access(access_db_path, access_table, df, column_mapping)
        print(f"完了: {count} 件を挿入しました")
    except Exception as e:
        print(f"エラーが発生しました: {e}")