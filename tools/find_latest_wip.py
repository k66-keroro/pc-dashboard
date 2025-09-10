import re
import os
from pathlib import Path
import sys

# srcディレクトリをパスに追加して、設定ファイルをインポートできるようにする
# このスクリプトがtools/にあることを前提とする
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.config import settings

def find_latest_wip_file(directory: Path) -> Path:
    """
    指定されたディレクトリ内で、命名規則に一致する最新の仕掛明細ファイルを見つける。
    ファイル名の例: 202508末_仕掛明細表_WBS集約(仕掛年齢付与)_0901.xlsx
    """
    # 正規表現パターンを修正し、日付部分をより正確に捉える
    # 例: "202508末..._0901.xlsx" -> 20250901 をソートキーにする
    pattern = re.compile(r"(\d{4})\d{2}末_仕掛明細表_WBS集約\(仕掛年齢付与\)_(\d{4})\.xlsx")
    latest_file = None
    latest_timestamp = ""

    print(f"ディレクトリを検索中: {directory}")

    if not directory.is_dir():
        print(f"エラー: ディレクトリが見つかりません: {directory}", file=sys.stderr)
        return None

    for f in directory.iterdir():
        if f.is_file():
            match = pattern.match(f.name)
            if match:
                year = match.group(1)
                date_suffix = match.group(2)
                # YYYYMMDD形式のタイムスタンプを作成して比較
                timestamp_str = f"{year}{date_suffix}"

                if not latest_timestamp or timestamp_str > latest_timestamp:
                    latest_timestamp = timestamp_str
                    latest_file = f

    return latest_file

def main():
    """
    メイン関数。本番用の仕掛品ディレクトリから最新ファイルを見つけてパスを出力する。
    """
    wip_dir = settings.PROD_WIP_DIR
    latest_file = find_latest_wip_file(wip_dir)

    if latest_file:
        # Windows環境で直接コピー＆ペーストしやすいように、パスをクォートで囲む
        print(f'"{str(latest_file)}"')
    else:
        print(f"エラー: {wip_dir} 内に適切なファイルが見つかりませんでした。", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
