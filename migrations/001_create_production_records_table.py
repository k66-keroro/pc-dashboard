import sys
from pathlib import Path
import os

# プロジェクトのルートディレクトリをPythonパスに追加
# これにより、`src`パッケージを正しくインポートできる
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.models.database import get_db_connection, create_tables, DEFAULT_DB_PATH

def main():
    """
    データベースを初期化し、テーブルを作成するマイグレーションスクリプト。
    """
    print("データベースマイグレーションを開始します...")

    # 既存のデータベースファイルを削除して、クリーンな状態で開始する
    if os.path.exists(DEFAULT_DB_PATH):
        print(f"既存のデータベースファイル {DEFAULT_DB_PATH} を削除します。")
        os.remove(DEFAULT_DB_PATH)

    conn = None
    try:
        # データベース接続を取得
        conn = get_db_connection()
        print("データベース接続を確立しました。")

        # テーブルを作成
        create_tables(conn)
        print("テーブル 'production_records' とインデックスが正常に作成されました。")

        print("マイグレーションが正常に完了しました。")

    except Exception as e:
        print(f"マイグレーション中にエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()
            print("データベース接続を閉じました。")

if __name__ == "__main__":
    main()
