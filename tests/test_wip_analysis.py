import pytest
import sqlite3
import pandas as pd
from pathlib import Path

from src.core.wip_processor import WipDataProcessor
from src.core.analytics import WipAnalysis
from src.models.migration_manager import apply_migrations

@pytest.fixture
def db_conn():
    """
    テスト用のインメモリSQLiteデータベース接続を提供するフィクスチャ。
    テストのたびに新しい空のDBが作成される。
    """
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn) # 最新のスキーマを適用
    yield conn
    conn.close()

@pytest.fixture
def sample_data_files(tmp_path):
    """
    テスト用のダミーデータファイルを作成するフィクスチャ。
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # 1. 仕掛明細データ (18列)
    # 実際のデータに合わせて、18列のテストデータを作成する
    wip_content = (
        "header\n"
        "skip\n"
        "skip\n"
        "キー\tﾌﾟﾗﾝﾄ\tMRP管理者\t工場\tライン\tﾈｯﾄﾜｰｸ/指図番号\tテキスト\t金額（国内通貨）\t品目\t初期数量\t仕掛数\t完成数量\t初期実績日付\t仕掛年齢\tCMPL\t材料\t経費\n"
        "NW\tkey1\tP100\tF1\tL1\tORD001\tItem 1\t1000\tITEM001\t10\t5\t5\t2025年8月\t1ケ月\t\t500\t500\n"
        "NW\tkey2\tP200\tF2\tL2\tORD002\tItem 2\t2000\tITEM002\t20\t20\t0\t2025年7月\t2ケ月\t\t1000\t1000\n"
        "NW\tkey3\tP100\tF1\tL1\tORD003\tItem 3\t500\tITEM003\t5\t0\t5\t2025年6月\t3ケ月\t\t250\t250\n"
    )
    wip_file = data_dir / "wip_details.csv"
    wip_file.write_text(wip_content, encoding="utf-8")

    # 2. ZP02データ (完了実績) - process_zp02で必要な列をすべて含める
    zp02_header = "MRP管理者\tMRP管理者名\t指図番号\t指図ステータス\t品目コード\t品目テキスト\t台数\tＷＢＳ要素\tDLV日付\tTECO日付\n"
    zp02_content = (
        zp02_header +
        "P100\tPC1\tORD001\tREL\tITEM001\tItem 1\t10\tWBS001\t\t\n"
        "P200\tPC2\tORD002\tREL\tITEM002\tItem 2\t20\tWBS002\t\t\n"
        "P100\tPC1\tORD003\tTECO\tITEM003\tItem 3\t5\tWBS003\t\t2025-09-01\n" # この指図は完了済み
    )
    zp02_file = data_dir / "ZP02.TXT"
    zp02_file.write_text(zp02_content, encoding="utf-8")

    # 3. ZP58データ (材料未処理)
    zp58_content = (
        "指図／ネットワーク\n"
        "ORD002\n" # 材料未処理あり
    )
    zp58_file = data_dir / "ZP58.txt"
    zp58_file.write_text(zp58_content, encoding="utf-8")

    return wip_file, zp02_file, zp58_file


def test_wip_data_processor(db_conn, sample_data_files):
    """
    WipDataProcessorがファイルを正しく読み込み、DBに格納できるかテストする。
    """
    wip_file, zp02_file, zp58_file = sample_data_files
    processor = WipDataProcessor(db_conn)

    # 処理を実行
    processor.run_all(wip_file, zp58_file, zp02_file)

    # データが正しくロードされたか確認
    wip_df = pd.read_sql_query("SELECT * FROM wip_details", db_conn)
    zp02_df = pd.read_sql_query("SELECT * FROM zp02_records", db_conn)
    zp58_df = pd.read_sql_query("SELECT * FROM zp58_records", db_conn)

    assert len(wip_df) == 3
    assert len(zp02_df) == 2
    assert len(zp58_df) == 1
    assert zp58_df.iloc[0]['order_number'] == 'ORD002'

def test_wip_analysis_summary(db_conn, sample_data_files):
    """
    WipAnalysisクラスが集計ロジックを正しく実行できるかテストする。
    """
    # 準備: テストデータをDBにロード
    wip_file, zp02_file, zp58_file = sample_data_files
    processor = WipDataProcessor(db_conn)
    processor.run_all(wip_file, zp58_file, zp02_file)

    # 分析を実行
    analyzer = WipAnalysis(db_conn)
    summary_df = analyzer.get_wip_summary_comparison()

    assert not summary_df.empty
    assert '仕掛年齢' in summary_df.columns
    assert '当初金額' in summary_df.columns
    assert '残高金額' in summary_df.columns

    # 「3ケ月」の行を確認 (ORD003, 500円, TECOなので残高は0になるはず)
    age_3_months = summary_df[summary_df['仕掛年齢'] == '3ケ月']
    assert age_3_months.iloc[0]['当初金額'] == 500
    assert age_3_months.iloc[0]['残高金額'] == 0

    # 「2ケ月」の行を確認 (ORD002, 2000円, 未完了なので残高は2000円のまま)
    age_2_months = summary_df[summary_df['仕掛年齢'] == '2ケ月']
    assert age_2_months.iloc[0]['当初金額'] == 2000
    assert age_2_months.iloc[0]['残高金額'] == 2000
