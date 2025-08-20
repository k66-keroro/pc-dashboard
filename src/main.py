import sys
from pathlib import Path
import os

# プロジェクトのルートディレクトリをPythonパスに追加
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.models.database import get_db_connection, create_tables, DEFAULT_DB_PATH
from src.core.data_processor import DataProcessor

def main():
    """
    データ処理パイプラインを実行するメイン関数。
    """
    print("PC製造ダッシュボード - データローダー v2.0")
    print("=" * 40)

    # データベースのパスとデータファイルのパスを設定
    db_path = DEFAULT_DB_PATH
    data_file_path = project_root / "KANSEI_JISSEKI.txt"

    if not data_file_path.exists():
        print(f"エラー: データファイルが見つかりません: {data_file_path}")
        sys.exit(1)

    # 既存のデータベースをクリーンアップするか選択
    if os.path.exists(db_path):
        print(f"既存のデータベースファイルが見つかりました: {db_path}")
        # 本番環境ではこのロジックをより安全なものにすべき
        # このサンプルでは、常にクリーンな状態で開始するためにファイルを削除する
        print("クリーンな状態で開始するために、既存のデータベースを削除します。")
        os.remove(db_path)

    conn = None
    try:
        # データベース接続を確立し、テーブルを作成
        print(f"データベースに接続しています: {db_path}")
        conn = get_db_connection(db_path)
        create_tables(conn)
        print("データベースとテーブルの準備が完了しました。")

        # データプロセッサを初期化してファイルを処理
        print("-" * 40)
        processor = DataProcessor(conn)
        summary = processor.process_and_load_file(str(data_file_path))

        # 結果のサマリーを表示
        print("-" * 40)
        print("処理結果サマリー:")
        print(f"  ファイル: {summary.get('file')}")
        print(f"  総行数: {summary.get('total_rows')}")
        print(f"  成功した挿入件数: {summary.get('successful_inserts')}")
        print(f"  失敗した行数: {summary.get('failed_rows')}")
        print("=" * 40)

        if summary.get('successful_inserts', 0) > 0:
            # 挿入されたデータの一部をプレビュー
            print("\nデータベースに挿入されたデータのプレビュー (最初の5件):")
            cursor = conn.cursor()
            cursor.execute("SELECT order_number, item_code, item_text, input_datetime FROM production_records LIMIT 5;")
            for row in cursor.fetchall():
                print(f"  - 指図番号: {row['order_number']}, 品目: {row['item_code']}, 入力日時: {row['input_datetime']}")

    except Exception as e:
        print(f"\nパイプラインの実行中に致命的なエラーが発生しました: {e}")
    finally:
        if conn:
            conn.close()
            print("\nデータベース接続を閉じました。")

if __name__ == "__main__":
    main()
