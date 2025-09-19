# PC-Dashboard: 1時間ごと自動データ更新の修正指示

## 🎯 **修正目標**

1時間ごとのデータ自動更新が確実に動作するよう、現在の問題を解決する

## 🔍 **現状の問題**

### 1. 常駐サービスの問題

- `python -m src.main` で起動後、コマンドプロンプトを閉じると停止してしまう
- バックグラウンドで安定稼働する仕組みが必要

### 2. 実行モードの曖昧さ

- 開発モード（ローカルファイル）と本番モード（ネットワークファイル）の使い分けが不明確
- どちらのモードで運用すべきか決まっていない

### 3. エラー処理の不備

- ネットワークファイルアクセスエラー時の対応が不十分
- ファイルが存在しない場合の処理が弱い

## 🛠️ **修正案**

### 修正1: Windowsタスクスケジューラー対応

**新ファイル作成**: `run_hourly.bat`

```batch
@echo off
cd /d "C:\Users\sem3171\pc-dashboard"
python -m src.main --single-run 2>> logs\scheduler_error.log
```

**main.pyに追加する引数**:

```python
parser.add_argument('--single-run', action='store_true', 
                   help='1回だけデータ処理を実行して終了します（スケジューラー用）')
```

**main.py の修正箇所**:

```python
# 既存の while True ループの代わりに
if args.single_run:
    run_pipeline(conn, data_path)
    logger.info("単発実行完了。プログラムを終了します。")
else:
    logger.info("常駐サービスモードで起動します。1時間ごとにデータ処理を実行します。")
    while True:
        run_pipeline(conn, data_path)
        logger.info("次の実行まで1時間待機します...")
        time.sleep(3600)
```

### 修正2: エラーハンドリング強化

**settings.pyの修正**:

```python
# ネットワークファイルの存在確認機能を追加
def check_network_file_access():
    """本番ファイルへのアクセス可能性をチェック"""
    import os
    network_files = [
        PROD_DATA_PATH,
        PROD_MASTER_PATH,
        PROD_ZP02_PATH,
        PROD_ZP58_PATH,
        PROD_ZS65_PATH
    ]
    
    accessible_files = {}
    for file_path in network_files:
        try:
            accessible_files[str(file_path)] = os.path.exists(file_path)
        except Exception as e:
            accessible_files[str(file_path)] = False
            logger.warning(f"ネットワークファイルアクセスエラー: {file_path}, エラー: {e}")
    
    return accessible_files
```

**run_pipeline()の修正**:

```python
def run_pipeline(conn: sqlite3.Connection, data_path: Path):
    """一回のデータ処理パイプラインを実行する（エラーハンドリング強化版）"""
    logger.info("パイプライン処理を開始します。")
    
    # ファイル存在チェック（最大3回リトライ）
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if data_path and data_path.exists():
                mod_time_ts = os.path.getmtime(data_path)
                mod_time = datetime.datetime.fromtimestamp(mod_time_ts)
                logger.info(f"読み込み対象ファイルの最終更新日時: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
                break
            else:
                logger.warning(f"データファイルが見つかりません: {data_path} (試行 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(30)  # 30秒待機してリトライ
                    continue
                else:
                    logger.error(f"データファイルにアクセスできませんでした: {data_path}")
                    return
        except Exception as e:
            logger.warning(f"ファイルアクセス中にエラーが発生しました: {e} (試行 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(30)
                continue
            else:
                logger.error(f"ファイルアクセスに失敗しました: {data_path}")
                return
    
    # 既存の処理を continue...
    try:
        processor = DataProcessor(conn)
        summary = processor.process_file_and_load_to_db(data_path)
        # ... 残りの処理
    except Exception as e:
        logger.error(f"パイプライン処理中にエラーが発生しました: {e}", exc_info=True)
        # エラーが発生してもサービスは継続する
```

### 修正3: 監視・ログ機能の追加

**新ファイル作成**: `src/utils/health_check.py`

```python
import sqlite3
import datetime
from pathlib import Path
from src.config import settings
import logging

logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self):
        self.db_path = settings.DB_PATH
        
    def get_last_update_time(self):
        """最後のデータ更新時刻を取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(created_at) FROM production_records")
            result = cursor.fetchone()
            conn.close()
            return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"データベースアクセスエラー: {e}")
            return None
    
    def check_system_health(self):
        """システムの健全性をチェック"""
        health_status = {
            'timestamp': datetime.datetime.now().isoformat(),
            'database_accessible': False,
            'last_data_update': None,
            'hours_since_last_update': None,
            'network_files_accessible': {},
            'status': 'UNKNOWN'
        }
        
        try:
            # データベース接続チェック
            if self.db_path.exists():
                health_status['database_accessible'] = True
                health_status['last_data_update'] = self.get_last_update_time()
                
                if health_status['last_data_update']:
                    last_update = datetime.datetime.fromisoformat(health_status['last_data_update'])
                    now = datetime.datetime.now()
                    hours_diff = (now - last_update).total_seconds() / 3600
                    health_status['hours_since_last_update'] = round(hours_diff, 2)
            
            # ネットワークファイルアクセスチェック
            from src.config.settings import check_network_file_access
            health_status['network_files_accessible'] = check_network_file_access()
            
            # 総合ステータス判定
            if health_status['hours_since_last_update'] and health_status['hours_since_last_update'] > 2:
                health_status['status'] = 'WARNING'
            elif health_status['database_accessible']:
                health_status['status'] = 'OK'
            else:
                health_status['status'] = 'ERROR'
                
        except Exception as e:
            logger.error(f"ヘルスチェック中にエラーが発生しました: {e}")
            health_status['status'] = 'ERROR'
            
        return health_status

def main():
    """ヘルスチェック単体実行"""
    checker = HealthChecker()
    status = checker.check_system_health()
    print(f"システムステータス: {status['status']}")
    print(f"最終更新: {status['last_data_update']}")
    print(f"更新からの経過時間: {status['hours_since_last_update']}時間")
    
if __name__ == "__main__":
    main()
```

### 修正4: 新しいコマンドライン引数

**main.pyに追加**:

```python
parser.add_argument('--health-check', action='store_true', 
                   help='システムの健全性をチェックして終了します')

# メイン処理に追加
if args.health_check:
    from src.utils.health_check import HealthChecker
    checker = HealthChecker()
    status = checker.check_system_health()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    sys.exit(0)
```

## 🚀 **運用方法の提案**

### 方法1: Windowsタスクスケジューラー（推奨）

1. タスクスケジューラーで1時間ごとに `run_hourly.bat` を実行
2. 安定性が高く、システム再起動後も自動実行される

### 方法2: 常駐サービス継続

1. PowerShellで `Start-Process` を使ってバックグラウンド実行
2. 監視ツールと組み合わせて使用

## 🔧 **設定手順**

### 1. ファイルの配置

- `run_hourly.bat` をプロジェクトルートに配置
- `src/utils/health_check.py` を作成

### 2. Windowsタスクスケジューラー設定

1. タスクスケジューラーを開く
2. 「基本タスクの作成」を選択
3. 名前: "PC-Dashboard Data Update"
4. トリガー: "毎日" → 詳細設定で "1時間ごとに繰り返し"
5. 操作: `C:\Users\sem3171\pc-dashboard\run_hourly.bat`

### 3. 動作確認

```bash
# ヘルスチェック実行
python -m src.main --health-check

# 単発実行テスト  
python -m src.main --single-run
```

## 📝 **テスト項目**

- [ ] 単発実行が正常に動作する
- [ ] ヘルスチェック機能が動作する
- [ ] ネットワークファイルアクセスエラー時の挙動
- [ ] タスクスケジューラーでの自動実行
- [ ] ログファイルの出力確認

## 🎯 **期待効果**

1. **安定性向上**: システム再起動後も自動で再開
2. **監視可能**: ヘルスチェックでシステム状態を確認可能
3. **エラー耐性**: ネットワーク障害時でも適切に処理
4. **運用しやすさ**: 管理者が状況を把握しやすい

## 🔧 **追加修正項目（ダッシュボード機能改善）**

### 修正5: 金額計算の修正

**問題**: 取得単価が別プラント、集計が過大

**対応**:

```python
# データ読み込み時にプラントフィルタ追加
def load_mara_master(file_path):
    # MARA_DL.csvのエンコードUTF-16固定
    df = pd.read_csv(file_path, encoding='utf-16', sep='\t')
    
    # P100プラントでフィルタ
    df_filtered = df[df['プラント'] == 'P100']
    logger.info(f"MARA_DL.csv読み込み完了: 全{len(df)}件 → P100フィルタ後{len(df_filtered)}件")
    return df_filtered
```

### 修正6: レスポンス改善

**問題**: 繰り返し更新でパフォーマンス低下

**対応**:

```python
# エンコード固定設定を追加
ENCODING_SETTINGS = {
    'MARA_DL.csv': 'utf-16',
    'KANSEI_JISSEKI.txt': 'shift_jis',
    'ZP02.TXT': 'shift_jis',
    'ZP58.txt': 'shift_jis',
    'ZS65.TXT': 'shift_jis'
}

# キャッシュ機能の追加
@st.cache_data(ttl=3600)  # 1時間キャッシュ
def load_processed_data():
    return get_latest_data()
```

### 修正7: 仕掛進捗分析の改善

**修正内容**:

1. **仕掛年齢のソート修正**

```python
def sort_wip_age(age_string):
    """0年1ケ月 → 0年01ケ月 形式でソート用に変換"""
    import re
    match = re.match(r'(\d+)年(\d+)ケ月', age_string)
    if match:
        years = int(match.group(1))
        months = int(match.group(2))
        return f"{years}年{months:02d}ケ月"
    return age_string

# デフォルトを仕掛年齢降順に設定
df_sorted = df.sort_values('仕掛年齢', key=lambda x: x.map(sort_wip_age), ascending=False)
```

2. **金額・件数の縦計追加**

```python
# 集計行の追加
total_row = {
    '仕掛年齢': '合計',
    '当初金額': df['当初金額'].sum(),
    '当初件数': df['当初件数'].sum(),
    '残高金額': df['残高金額'].sum(),
    '残高件数': df['残高件数'].sum()
}
df_with_total = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
```

3. **残比率の追加**

```python
# 残比率計算列の追加
df['残金額比'] = (df['残高金額'] / df['当初金額'] * 100).round(1).astype(str) + '%'
df['残件数比'] = (df['残高件数'] / df['当初件数'] * 100).round(1).astype(str) + '%'
```

### 修正8: PC関連在庫分析の改善

**修正内容**:

```python
# デフォルトを滞留年数降順に設定
df_pc_stock = df_pc_stock.sort_values('滞留年数', ascending=False)

# 区分ごとの集計を別表で表示
def create_category_summary(df):
    category_summary = df.groupby('区分').agg({
        '在庫金額': 'sum',
        '在庫件数': 'sum',
        '滞留年数': 'mean'
    }).round(2)
    
    return category_summary

# 区分別サマリー表示
st.subheader("区分別集計")
category_summary = create_category_summary(df_pc_stock)
st.dataframe(category_summary)
```

### 修正9: 期間選択機能の修正

**問題**: 期間選択が機能していない

**対応**:

```python
# 期間フィルタリング機能の修正
def apply_date_filter(df, period_selection, date_column='作成日'):
    from datetime import datetime, timedelta
    
    today = datetime.now()
    
    if period_selection == '先週':
        start_date = today - timedelta(days=today.weekday() + 7)
        end_date = today - timedelta(days=today.weekday() + 1)
    elif period_selection == '今週':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif period_selection == '先月':
        first_day_this_month = today.replace(day=1)
        end_date = first_day_this_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
    
    # DataFrame の日付フィルタリング
    df_filtered = df[
        (pd.to_datetime(df[date_column]) >= start_date) &
        (pd.to_datetime(df[date_column]) <= end_date)
    ]
    
    st.info(f"選択期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')} ({len(df_filtered)}件)")
    return df_filtered
```

### 修正10: 滞留強調表示

**修正内容**:

```python
# 滞留期間の強調表示
def highlight_aging_items(df, aging_threshold_days=365):
    """滞留期間が長いものを強調表示"""
    
    def color_aging(row):
        if row['滞留日数'] > aging_threshold_days:
            return ['background-color: #ffcccc'] * len(row)  # 赤系
        elif row['滞留日数'] > aging_threshold_days * 0.5:
            return ['background-color: #fff2cc'] * len(row)  # 黄系
        else:
            return [''] * len(row)
    
    return df.style.apply(color_aging, axis=1)

# 滞留日数でソート（降順をデフォルト）
df_sorted = df.sort_values('滞留日数', ascending=False)

# 強調表示適用
styled_df = highlight_aging_items(df_sorted)
st.dataframe(styled_df)
```

## 📊 **修正後の表示例**

### 仕掛進捗分析（修正後）

```
仕掛年齢   当初金額    当初件数   残高金額    残高件数   残金額比   残件数比
1年4ケ月   12,858      1        12,858      1        100.0%     100.0%
1年2ケ月   6,697,230   9        6,436,256   7        96.1%      77.8%
1年1ケ月   3,080       1        3,080       1        100.0%     100.0%
0年11ケ月  10,316      1        10,316      1        100.0%     100.0%
0年10ケ月  191,386     1        191,386     1        100.0%     100.0%
0年07ケ月  621,243     1        0           0        0.0%       0.0%
0年06ケ月  5,835       1        5,835       1        100.0%     100.0%
0年04ケ月  1,232,049   2        1,232,049   2        100.0%     100.0%
0年03ケ月  860,421     4        308,824     2        35.9%      50.0%
0年02ケ月  34,631,663  361      31,786,365  343      91.8%      95.0%
0年01ケ月  59,095,589  218      46,825,978  124      79.2%      56.9%
────────────────────────────────────────────────
合計       103,351,670 600      86,621,891  483      83.8%      80.5%
```

以上の修正により、1時間ごとの自動データ更新が確実に動作し、かつダッシュボードの使いやすさも大幅に向上します。