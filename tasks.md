# tasks.md - タスク管理簿

プロジェクトのタスクを管理します。チェックボックス形式で進捗を追跡します。

## 現在のタスク (Current Tasks)

### P1: 分析機能の拡張
- [x] MRP管理者（内製/外注）に基づいた分析機能を追加する
- [x] 週次の生産実績レポート（明細、日別、週別）を生成する機能を実装する

### P2: ダッシュボード (UI) の実装
- [x] Streamlit の基本セットアップ (`src/app.py` を作成)
- [x] DBからデータを読み込み、Pandas DataFrameとして表示する基本ページを作成する
- [x] 生産実績サマリー（全体進捗）を表示するダッシュボードページを作成する
- [x] 品目コードや期間でデータを絞り込めるインタラクティブなフィルタ機能を追加する
- [x] エラーデータを表示する専用ページを作成する
- [x] 分析結果をExcelファイルとしてダウンロードする機能をダッシュボードに追加する

### P3: テストと品質向上
- [x] `src/core/analytics.py` の各分析機能に対する単体テストを作成する

---
## 将来の拡張機能 (バックログ)

- [x] 在庫滞留分析クラス (`InventoryAnalysis`) を実装する
- [x] 品目マスタを基準としたエラー検出機能を追加する

---

## 完了済みタスク

- [x] プロジェクトの基本構造（ディレクトリ、`__init__.py`）のセットアップ
- [x] `README.md` の作成と更新
- [x] `Pydantic` によるデータモデル (`ProductionRecord`) の定義
- [x] `data_processor.py` でのファイル読み込みと基本変換処理の実装
- [x] `database.py` でのDB接続とテーブル作成処理の実装
- [x] `main.py` での基本的なETLパイプラインの実装
- [x] `gemini.md`, `design.md`, `requirements.md`, `tasks.md` の作成
- [x] `data_processor` と `database` の動作を検証する単体・統合テスト (`tests/test_models.py`) の作成
- [x] 不正なデータ（型エラー、必須項目欠損など）を含むテストケースの追加
- [x] `src/config/settings.py` を作成し、ファイルパスやDB設定を管理する
- [x] `main.py` のDB初期化ロジックを、毎回削除するのではなく、引数で制御可能にする
- [x] `logging` 設定を `settings.py` から読み込むように変更し、ログファイルに出力する
- [x] 分析機能の基盤となる `src/core/analytics.py` を作成する
- [x] 生産実績分析クラス (`ProductionAnalytics`) を実装する (計画 vs 実績)
- [x] エラー検出クラス (`ErrorDetection`) を実装する (数量の不整合チェック)
- [x] `ErrorDetection`クラスの単体テストを作成する (`tests/test_analytics.py`)
