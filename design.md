# design.md - 設計書

## 1. システムアーキテクチャ

本システムは、テキストファイルベースの生産実績データを処理し、データベースに格納、最終的にWebダッシュボードで可視化するETL (Extract, Trans
form, Load) パイプラインとして設計する。

### 構成図

```
+--------------------------+
|   File System            |
| (KANSEI_JISSEKI.txt)     |
+-----------+--------------+
            |
            | 1. Extract (抽出)
            v
+-----------+--------------+
|   Python ETL Script      | (src/main.py)
| - Pandas (データ操作)    |
| - Pydantic (バリデーション)|
+-----------+--------------+
            |
            | 2. Transform & Load (変換・格納)
            v
+-----------+--------------+
|   SQLite Database        |
| (data/sqlite/production.db)|
+-----------+--------------+
            |
            | 3. Visualize (可視化)
            v
+-----------+--------------+
|   Streamlit Dashboard    |
| (Web UI)                 |
+--------------------------+
```

### コンポーネントの役割

- **Python ETL Script**: データ処理の中核。ファイルの読み込み、データクレンジング、Pydanticモデルによるバリデーション、デー
タベースへの挿入を行う。
- **SQLite Database**: 処理済みの構造化データを格納する軽量なデータベース。
- **Streamlit Dashboard**: データベースの情報を基に、各種分析結果をインタラクティブに表示するUI。

## 2. データモデル設計

### データベース

- **種類**: SQLite
- **ファイルパス**: `data/sqlite/production.db`

### テーブル: `production_records`

`src/models/production.py` の `ProductionRecord` Pydanticモデルを正規のスキーマ定義とする。

| カラム名                  | データ型 (SQLite) | 説明                       | NULL許容 |
| ------------------------- | ----------------- | -------------------------- | :
------: |
| `id`                      | INTEGER           | 主キー                     |    -
     |
| `plant`                   | TEXT              | プラント                   |    -
    |
| `storage_location`        | TEXT              | 保管場所                   |
✅    |
| `item_code`               | TEXT              | 品目コード                 |    -
   |
| `item_text`               | TEXT              | 品目テキスト               |    -
  |
| `order_number`            | TEXT              | 指図番号                   |    -
    |
| `order_type`              | TEXT              | 指図タイプ                 |    -
   |
| `mrp_controller`          | TEXT              | MRP管理者                  |    -
     |
| `order_quantity`          | INTEGER           | 指図数量                   |    -
    |
| `actual_quantity`         | INTEGER           | 実績数量                   |    -
    |
| `cumulative_quantity`     | INTEGER           | 累計数量                   |    -
    |
| `remaining_quantity`      | INTEGER           | 残数量                     |    -
     |
| `input_datetime`          | TIMESTAMP         | 入力日時                   |    -
    |
| `planned_completion_date` | DATE              | 計画完了日                 |    ✅
  |
| `wbs_element`             | TEXT              | WBS要素                    |
✅    |
| `sales_order_number`      | TEXT              | 受注伝票番号               |    ✅
 |
| `sales_order_item_number` | TEXT              | 受注明細番号               |    ✅
 |

## 3. モジュール設計

- `src/main.py`: アプリケーションのエントリーポイント。全体の処理フロー（DB初期化、データ処理実行）を制御する。
- `src/core/data_processor.py`: `DataProcessor` クラスを定義。データファイルの読み込み、Pandasによる前
処理、Pydanticによるバリデーション、DBへのロードという一連の責務を持つ。
- `src/models/database.py`: データベース接続の管理 (`get_db_connection`)、テーブル作成 (`create_ta
bles`)、データ挿入 (`insert_production_records`) といったデータベース関連の低レベルな操作をカプセル化する。
- `src/models/production.py`: `ProductionRecord` Pydanticモデルを定義。アプリケーション全体で利用す
るデータ構造を保証する。
- `src/config/settings.py` (予定): データベースパス、ファイルパス、ログ設定などの構成情報を一元管理する。
- `src/utils/` (予定): プロジェクト全体で再利用可能なヘルパー関数（日付変換、ロギング設定など）を配置する。
- `src/app.py` (予定): Streamlitダッシュボードのエントリーポイント。

## 4. UI/UX設計 (将来構想)

- **フレームワーク**: Streamlit
- **画面構成案**:
  1.  **サマリーダッシュボード**: 生産進捗の全体像（計画数、実績数、達成率）、指図タイプ別の状況などを表示。
  2.  **エラーデータビューア**: バリデーションに失敗したレコードの一覧と、そのエラー理由を表示する。
  3.  **詳細検索・分析**: 品目コードや期間などでデータをフィルタリングし、詳細を確認できる機能。
