import pandas as pd
import sqlite3
import os
from datetime import datetime

def import_data_to_sqlite():
    # ファイルパスとデータベースの設定
    txt_file_path = r'C:\Projects_workspace\02_access\テキスト\MARA_DL.csv'
    sqlite_db_path = r'C:\Projects_workspace\02_access\Database1.sqlite'
    table_name = 'MARA_DL'

    # SQLite データベースへの接続
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    # 既存のテーブルがあれば削除
    try:
        cursor.execute(f'DROP TABLE IF EXISTS {table_name}')
        conn.commit()
        print(f"テーブル '{table_name}' を削除しました。")
    except Exception as e:
        print(f"テーブル削除中にエラー: {e}")

    # ファイルの存在確認
    if not os.path.exists(txt_file_path):
        print(f"ファイルが存在しません: {txt_file_path}")
        return

    # TXTファイルの読み込み（カンマ区切りの場合）
    df = pd.read_csv(
        txt_file_path,
        delimiter=',',
        encoding='UTF-16',
        na_values=["", "NA", " "],
        dtype={'品目': str}  # 品目を文字列型として読み込む
    )

    # データフレームの列をテーブル定義に合わせる
    table_columns = {
        '品目': 'TEXT', '品目テキスト': 'TEXT', 'プラント': 'TEXT', '品目タイプコード': 'TEXT',
        '標準原価': 'REAL', '品目階層': 'TEXT', '納入予定日数': 'INTEGER', '入庫処理日数': 'INTEGER',
        'MRP_管理者': 'TEXT', 'MRP_管理者名': 'TEXT', 'メーカー名': 'TEXT', '安全重要部品': 'TEXT',
        'ROHSコード': 'TEXT', 'ROHS日付': 'TEXT', '材料費_設計予算_': 'REAL',
        '加工費_設計予算_': 'REAL', '工程': 'TEXT', 'CMコード': 'TEXT', '評価クラス': 'TEXT',
        '品目グループ': 'TEXT', '品目grpテキスト': 'TEXT', '研究室_設計室': 'TEXT', '発注点': 'INTEGER',
        '安全在庫': 'REAL', '最終入庫日': 'TEXT', '最終出庫日': 'TEXT',
        '利益センタ': 'TEXT', '調達タイプ': 'TEXT', '特殊調達タイプ': 'TEXT', '消費モード': 'TEXT',
        '逆消費期間': 'TEXT', '順消費期間': 'TEXT', '二重ＭＲＰ区分': 'TEXT', '販売ステータス': 'TEXT',
        'ＭＲＰタイプ': 'TEXT', 'タイムフェンス': 'INTEGER', 'ＭＲＰ出庫保管場所': 'TEXT',
        '棚番': 'TEXT', 'BOM': 'TEXT', '作業手順': 'TEXT', 'ロットサイズ': 'TEXT', '最小ロットサイズ': 'REAL',
        '最大ロットサイズ': 'INTEGER', '丸め数量': 'REAL', '現会計年度': 'INTEGER',
        '現期間': 'INTEGER', '格上げ区分': 'TEXT', '将来会計年度': 'INTEGER', '将来期間': 'INTEGER',
        '将来予定原価': 'REAL', '現在予定原価': 'REAL', '前回会計年度': 'INTEGER',
        '前回期間': 'INTEGER', '前回予定原価': 'REAL', '間接費グループ': 'TEXT',
        '品目登録日': 'TEXT', '日程計画余裕キー': 'INTEGER', 'プラント固有ステータス': 'TEXT',
        '営業倉庫_最終入庫日': 'TEXT', '営業倉庫_最終出庫日': 'TEXT', '原価計算ロットサイズ': 'INTEGER',
        '設計担当者ID': 'TEXT', '設計担当者名': 'TEXT', 'プラント固有開始日': 'TEXT',
        '自動購買発注': 'TEXT',
    }
    df = df[list(table_columns.keys())]

    # 欠損値を None に置き換える
    df = df.where(pd.notnull(df), None)

    # テーブルを再作成
    create_table_query = f"CREATE TABLE {table_name} ({', '.join([f'{col} {dtype}' for col, dtype in table_columns.items()])})"
    try:
        cursor.execute(create_table_query)
        conn.commit()
        print(f"テーブル '{table_name}' を再作成しました。")
    except Exception as e:
        print(f"テーブル再作成中にエラー: {e}")

    # データ挿入
    insert_query = f"INSERT INTO {table_name} ({', '.join(table_columns.keys())}) VALUES ({', '.join(['?' for _ in table_columns.keys()])})"
    batch_size = 10000
    rows = df.values.tolist()
    total_rows = len(rows)

    try:
        for i in range(0, total_rows, batch_size):
            batch = rows[i:i + batch_size]
            cursor.executemany(insert_query, batch)
            conn.commit()
            print(f"{i + len(batch)} / {total_rows} 行 挿入完了")
    except Exception as e:
        print(f"データ挿入中にエラー: {e}")

    # トランザクション外で VACUUM を実行
    conn.commit()
    conn.isolation_level = None  # autocommit モードを有効化
    try:
        cursor.execute("VACUUM")
        print("データベースを最適化しました。")
    except Exception as e:
        print(f"データベース最適化中にエラー: {e}")

    # 接続を閉じる
    conn.close()
    print("SQLite データベース接続を閉じました。")


if __name__ == "__main__":
    import_data_to_sqlite()