# PC製造部門向けダッシュボードシステム v2.0

## 概要

PC製造部門向けの実用的なダッシュボードシステムです。夜間処理で出力されるテキストファイルと日中1時間ごとの実績データを活用し、生産実績・進捗管理、マスタ不備・エラー検出、在庫滞留分析を中心とした実務に直結するWebベースダッシュボードを提供します。

## プロジェクト構造

```
pc-dashboard/
├── src/                        # ソースコード
│   ├── __init__.py
│   ├── main.py                 # メインアプリケーション
│   ├── core/                   # コア機能
│   │   ├── __init__.py
│   │   └── data_processor.py   # データ処理クラス
│   ├── config/                 # 設定管理
│   │   ├── __init__.py
│   │   └── settings.py         # 設定ファイル
│   └── utils/                  # ユーティリティ
│       └── __init__.py
├── data/                       # データディレクトリ
│   ├── current/                # 現在のデータ
│   ├── historical/             # 履歴データ
│   └── sqlite/                 # SQLiteデータベース
├── reports/                    # レポート出力
├── logs/                       # ログファイル
└── README.md               # このファイル
```

## 主要機能

### 1. データ処理機能
- **夜間処理ファイル処理**: テキストファイルの自動読み込みとデータベース保存
- **1時間ごと実績データ処理**: リアルタイムデータの処理と更新
- **データ型最適化**: 自動的なデータ型変換と最適化
- **エラーハンドリング**: 堅牢なエラー処理とログ記録

### 2. 分析機能
- **生産実績分析**: 計画vs実績の比較分析
- **エラー検出**: マスタ不備とデータ整合性チェック
- **在庫滞留分析**: 滞留期間の計算と監視

### 3. ダッシュボード機能
- **Streamlitベースの直感的UI**
- **リアルタイムデータ可視化**（1時間毎）
- **レポート生成とエクスポート**

## 使用方法

### 基本的な使用方法

```python
from src.main import ManufacturingDashboardApp

# アプリケーションを初期化
app = ManufacturingDashboardApp()

# データベースを初期化
app.initialize_database()

# ファイルを処理
result = app.process_file("data/current/production_data.csv", "night_batch")

# システム状態を確認
status = app.get_system_status()
print(f"システム状態: {status['status']}")
```

### コマンドライン実行

```bash
# アプリケーションを起動
cd pc-dashboard
python src/main.py

# ヘルスチェックを実行
python -c "from src.main import main; main()"
```

## 設定

設定は `src/config/settings.py` で管理されています：

- **データベース設定**: SQLiteデータベースのパス設定
- **ファイル処理設定**: 入力・出力ディレクトリの設定
- **ダッシュボード設定**: UI設定とテーマ
- **分析設定**: 閾値とアラート設定
- **ログ設定**: ログレベルと出力設定

## 依存関係

- **pandas**: データ処理
- **numpy**: 数値計算
- **sqlite3**: データベース操作
- **pathlib**: ファイルパス操作
- **logging**: ログ記録

## 開発状況

現在の実装状況：

- ✅ プロジェクト基盤構築
- ✅ データ処理クラス
- ✅ 設定管理システム
- ✅ エラーハンドリング
- ⏳ データモデル定義（次のタスク）
- ⏳ 分析コンポーネント
- ⏳ ダッシュボードUI

## 今後の開発予定

1. **データモデルの実装**: 生産実績、エラー
2. **分析コンポーネント**: ProductionAnalytics、ErrorDetection、InventoryAnalysis
3. **Streamlitダッシュボード**: インタラクティブなWebUI
4. **レポート機能**: Excel/PDF出力機能
5. **テスト機能**: 単体テストと統合テスト

## 既存システムとの統合

このv2.0システムは、既存のpc-production-dashboardディレクトリ内の以下のコンポーネントと統合されます：

- **既存のデータローダー**: `app/data_loader_fixed.py`との連携
- **既存のダッシュボード**: `app/dashboard.py`の機能拡張
- **データベース**: 既存の`data/sqlite/`ディレクトリの活用

## ライセンス

このプロジェクトは内部使用のために開発されています。