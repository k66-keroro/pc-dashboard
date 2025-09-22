# 推奨コマンドと実行方法

## Windows環境での基本コマンド

### ディレクトリ操作
- `dir` - ファイル一覧表示（`ls`の代替）
- `cd <directory>` - ディレクトリ移動
- `cd..` - 親ディレクトリに移動
- `mkdir <directory>` - ディレクトリ作成
- `rmdir <directory>` - ディレクトリ削除

### ファイル操作
- `type <file>` - ファイル内容表示（`cat`の代替）
- `copy <source> <destination>` - ファイルコピー
- `move <source> <destination>` - ファイル移動
- `del <file>` - ファイル削除
- `findstr "<pattern>" <file>` - ファイル内検索（`grep`の代替）

## プロジェクト実行コマンド

### データ処理バッチ実行
```bash
cd C:\Users\sem3171\pc-dashboard
python src/main.py
```

### 自動データ更新（1時間毎）
```bash
run_hourly.bat
```

### Streamlitダッシュボード起動
```bash
cd C:\Users\sem3171\pc-dashboard
streamlit run src/app.py
```

### ヘルスチェック実行
```bash
python verify_reports.py
```

## Git操作
```bash
git status
git add .
git commit -m "commit message"
git push origin main
```

## Python環境管理
```bash
python -m pip install -r requirements.txt
python -m pip list
python --version
```

## ログ確認
```bash
type logs\data_processor.log
type streamlit_output.log
```

## デバッグ用コマンド
```bash
# データベース内容確認
python -c "from src.models.database import get_db_connection; import pandas as pd; conn = get_db_connection(); print(pd.read_sql('SELECT COUNT(*) FROM production_records', conn))"

# システム状態確認
python -c "from src.main import main; main()"
```