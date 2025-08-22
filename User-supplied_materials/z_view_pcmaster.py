import pandas as pd
import pyodbc
import numpy as np

def import_data_to_access():
    # ファイルパスとデータベースの設定
    csv_file_path = r'C:\Projects_workspace\02_access\テキスト\MARA_DL.csv'
    access_db_path = r'C:\Projects_workspace\02_access\Database1.accdb'
    table_name = 'view_pc_master'

    # Accessデータベースへの接続
    CONN_STR = f'DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={access_db_path};'
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    # 既存のテーブルがあれば削除
    try:
        cursor.execute(f'DROP TABLE {table_name}')
        conn.commit()
        print(f"テーブル '{table_name}' を削除しました。")
    except Exception as e:
        print(f"テーブル削除中にエラー: {e}")

    # CSVファイルの読み込み
    error_lines = []
    def bad_line_handler(bad_line):
        error_lines.append(bad_line)
        return None  # skip the line

    try:
        df = pd.read_csv(
            csv_file_path,
            delimiter=',',
            encoding='UTF-16',
            na_values=["", "NA", " "],
            dtype=str,  # すべての列を文字列型として読み込む
            on_bad_lines=bad_line_handler,
            engine='python'  # ← 追加
        )
    except Exception as e:
        print(f"CSVファイル読み込みエラー: {e}")
        if error_lines:
            print(f"エラー行数: {len(error_lines)}")
            for i, line in enumerate(error_lines[:10]):
                print(f"エラー行{i+1}: {line}")
        return
    if error_lines:
        print(f"スキップされたエラー行数: {len(error_lines)}")
        for i, line in enumerate(error_lines[:10]):
            print(f"エラー行{i+1}: {line}")

    # 必要な列を定義
    table_columns = {
        'プラント': 'TEXT',
        'MRP_管理者': 'TEXT',
        '調達タイプ': 'TEXT',
        '評価クラス': 'INTEGER',
        '格上げ区分': 'TEXT',
        '品目タイプコード': 'TEXT',
        '品目': 'TEXT',
        '品目テキスト': 'TEXT',
        '標準原価': 'DOUBLE',
        '現会計年度': 'INTEGER',
        '現期間': 'INTEGER',
        '研究室_設計室': 'TEXT',
        'ＭＲＰ出庫保管場所': 'TEXT',
        'MRP_管理者名': 'TEXT',
        'BOM': 'TEXT',
        '作業手順': 'TEXT',
        'ＭＲＰタイプ': 'TEXT',
        'タイムフェンス': 'INTEGER',
        '間接費グループ': 'TEXT',
        '販売ステータス': 'TEXT',
        'プラント固有ステータス': 'TEXT',
        'ロットサイズ': 'TEXT',
        '品目登録日': 'TEXT',
        '利益センタ': 'TEXT',
        '安全在庫': 'DOUBLE',
        '丸め数量': 'DOUBLE',
        '最小ロットサイズ': 'DOUBLE',
        '価格単位': 'INTEGER',
        '原価計算ロットサイズ': 'INTEGER',
        '日程計画余裕キー': 'INTEGER',
        '設計担当者ID': 'TEXT',
        '設計担当者名': 'TEXT',
        '最終入庫日': 'TEXT',
        '最終出庫日': 'TEXT',
        '製造計画担当': 'TEXT',
        'ID10_直接材料費': 'DOUBLE',
        'ID20_補助材料費': 'DOUBLE',
        'ID30_外注加工費': 'DOUBLE',
        'ID40_労務費': 'DOUBLE',
        'ID50_間接費': 'DOUBLE',
        'ID51_副資材費': 'DOUBLE',
        'ID60_経費': 'DOUBLE',
        'ID70_設備費': 'DOUBLE',
        '材料費SAP': 'DOUBLE',
        '加工費SAP': 'DOUBLE'
    }

    # 必要な列だけを抽出
    df = df[list(table_columns.keys())]

    # データのクレンジング
    df = df.replace({pd.NaT: None, np.nan: None})
    df.columns = df.columns.str.strip()  # 列名の空白を削除

    # テーブルを作成
    create_table_query = f'CREATE TABLE {table_name} ({", ".join([f"[{col}] {dtype}" for col, dtype in table_columns.items()])})'
    cursor.execute(create_table_query)
    conn.commit()
    print(f"テーブル '{table_name}' を作成しました。")

    # データのフィルタリング
    filtered_df = df[
        ((df['プラント'] == 'P100') & (df['評価クラス'] == '2120')) |
        ((df['プラント'] == 'P100') & (df['評価クラス'] == '2130') & df['品目'].str.startswith('9710') & (df['品目'] != '971030100')) 
    ]
    
    # データの挿入
    for index, row in filtered_df.iterrows():
        placeholders = ', '.join(['?'] * len(row))
        # データを挿入するSQL文
        insert_query = f"""
        INSERT INTO {table_name} (
            プラント, MRP_管理者, 調達タイプ, 評価クラス, 格上げ区分,
            品目タイプコード, 品目, 品目テキスト, 標準原価, 現会計年度,
            現期間, 研究室_設計室, MRP出庫保管場所, MRP_管理者名,
            BOM, 作業手順, MRPタイプ, タイムフェンス, 間接費グループ,
            販売ステータス, プラント固有ステータス, ロットサイズ, 品目登録日,
            利益センタ, 安全在庫, 丸め数量, 最小ロットサイズ, 価格単位,
            原価計算ロットサイズ, 日程計画余裕キー, 設計担当者ID,
            設計担当者名, 最終入庫日, 最終出庫日, 製造計画担当,
            ID10_直接材料費, ID20_補助材料費, ID30_外注加工費,
            ID40_労務費, ID50_間接費, ID51_副資材費, ID60_経費,
            ID70_設備費, 材料費SAP, 加工費SAP
        ) 
        VALUES ({placeholders})
        """
        row_data = tuple(row)
        try:
            cursor.execute(insert_query, row_data)
        except Exception as e:
            print(f"挿入エラーの詳細: {e}")
            print(f"行データ: {row_data}")
    
    conn.commit()
    print("データのインポートが完了しました。")

    # データベース接続の終了
    cursor.close()
    conn.close()

if __name__ == "__main__":
    import_data_to_access()