# タスク完了時の実行手順

## コード変更完了後の必須作業

### 1. テスト実行
```bash
# 基本動作確認
python src/main.py

# ヘルスチェック
python verify_reports.py

# Streamlitアプリ起動テスト
streamlit run src/app.py
```

### 2. データ整合性確認
```bash
# データベース状態確認
python -c "from src.models.database import get_db_connection; import pandas as pd; conn = get_db_connection(); print(pd.read_sql('SELECT COUNT(*) FROM production_records', conn))"

# 最新データ確認
python -c "from src.models.database import get_db_connection; import pandas as pd; conn = get_db_connection(); print(pd.read_sql('SELECT MAX(input_datetime) FROM production_records', conn))"
```

### 3. ログ確認
```bash
# エラーログ確認
type logs\data_processor.log | findstr "ERROR"

# 実行ログ確認  
type streamlit_output.log
```

### 4. Git操作（必要に応じて）
```bash
git status
git add .
git commit -m "feat: 日付デフォルト設定を全期間から当月に変更"
git push origin main
```

### 5. 運用環境での動作確認
```bash
# バッチ処理テスト
run_hourly.bat

# UI動作確認（ブラウザで確認）
streamlit run src/app.py
```

### 6. 設定変更内容の文書化
- claude.md ファイルに変更内容を記録
- 変更理由と影響範囲を明記
- 次回メンテナンス時の参考情報として保存

## 緊急時のロールバック手順
1. Gitコミット前なら：`git checkout -- <変更ファイル>`
2. コミット済みなら：`git revert <commit-hash>`
3. システム停止が必要な場合：Streamlitプロセス終了後、元のコードに戻す

## 問題発生時の対処
- まずログファイルを確認
- データベース接続確認
- ネットワークファイルアクセス確認
- 必要に応じてrun_hourly.batで手動データ更新