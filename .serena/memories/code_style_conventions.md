# コードスタイルと慣例

## コーディング規約

### 命名規則
- **変数・関数名**: snake_case（例：`data_processor`, `get_user_name`）
- **クラス名**: PascalCase（例：`DataProcessor`, `ProductionAnalytics`）
- **定数**: UPPER_SNAKE_CASE（例：`MAX_RETRY_COUNT`, `DEFAULT_DB_PATH`）
- **モジュール名**: 小文字 + アンダースコア（例：`data_processor.py`）

### インポート順序
1. 標準ライブラリ（例：`import os`, `import datetime`）
2. サードパーティライブラリ（例：`import pandas as pd`, `import streamlit as st`）
3. ローカルモジュール（例：`from src.core import DataProcessor`）

### 型ヒント使用
- 関数の引数と戻り値に型ヒントを使用
- 例：`def process_data(df: pd.DataFrame) -> pd.DataFrame:`

### docstring規則
- 関数・クラスの説明は日本語で記述
- 複雑な処理には詳細なコメント付与
- 例：
```python
def load_and_prepare_data():
    """
    DBからデータをロードし、前処理と分析列の追加を行う。
    この関数は1時間キャッシュされ、2回目以降の実行は高速です。
    """
```

### エラーハンドリング
- try-except-finallyを適切に使用
- ログ記録によるエラー追跡
- 例：
```python
try:
    df = pd.read_sql_query("SELECT * FROM production_records", conn)
finally:
    conn.close()
```

### Streamlit固有の慣例
- キャッシュ使用：`@st.cache_data(ttl=3600)`
- レイアウト設定：`st.set_page_config(layout="wide")`
- サイドバー活用：`st.sidebar.header("表示設定")`

## プロジェクト構造パターン
- **src/**: すべてのソースコード
- **models/**: データベース関連
- **core/**: ビジネスロジック
- **utils/**: 共通ユーティリティ
- **config/**: 設定ファイル