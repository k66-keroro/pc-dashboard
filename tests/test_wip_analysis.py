import pytest
import sqlite3
import pandas as pd
from pathlib import Path

from src.core.wip_processor import WipDataProcessor
from src.core.analytics import WipAnalysis, PcStockAnalysis
from src.models.migration_manager import apply_migrations

@pytest.fixture
def db_conn():
    """
    テスト用のインメモリSQLiteデータベース接続を提供するフィクスチャ。
    """
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)
    yield conn
    conn.close()

@pytest.fixture
def sample_data_files(tmp_path):
    """
    テスト用のダミーデータファイルを作成するフィクスチャ。
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # 1. 仕掛明細データ (17列) - processorが18列目を補完することをテスト
    wip_content = (
        "header\n" * 4 + # skip 3 rows and 1 header row
        "NW\tkey1\tP100\tF1\tL1\tORD001\tItem 1\t1,000\tITEM001\t10\t5\t5\t2025年8月\t1ケ月\t\t500\n"
        "NW\tkey2\tP200\tF2\tL2\tORD002\tItem 2\t2,000\tITEM002\t20\t20\t0\t2025年7月\t2ケ月\t\t1000\n"
        "NW\tkey3\tP100\tF1\tL1\tORD003\tItem 3\t500\tITEM003\t5\t0\t5\t2025年6月\t3ケ月\t\t250\n"
    )
    wip_file = data_dir / "wip_details.csv"
    wip_file.write_text(wip_content, encoding="cp932")

    # 2. ZP02データ
    zp02_header = "MRP管理者\tMRP管理者名\t指図番号\t指図ステータス\t品目コード\t品目テキスト\t台数\tＷＢＳ要素\tDLV日付\tTECO日付\n"
    zp02_content = (
        zp02_header +
        "P100\tPC1\tORD001\tREL\tITEM001\tItem 1\t10\tWBS001\t\t\n"
        "P200\tPC2\tORD002\tREL\tITEM002\tItem 2\t20\tWBS002\t\t\n"
        "P100\tPC1\tORD003\tTECO\tITEM003\tItem 3\t5\tWBS003\t\t2025-09-01\n"
    )
    zp02_file = data_dir / "ZP02.TXT"
    zp02_file.write_text(zp02_content, encoding="cp932")

    # 3. ZP58データ
    zp58_content = "指図／ネットワーク\nORD002\n"
    zp58_file = data_dir / "ZP58.txt"
    zp58_file.write_text(zp58_content, encoding="cp932")

    # 4. 保管場所一覧データ
    sl_header = "ﾌﾟﾗﾝﾄ\t責任部署\t棚卸報告区分\t保管場所\t保管場所名\t工場在庫区分\t営業在庫区分\t工場区分\t工場区分2\t使用不可区分\t棚番チェック用\t所要check\n"
    sl_content = (
        sl_header +
        "P100\t製造2部\t3_PC\t1120\t滋賀ＰＣ倉庫（ＡＷＣ）\tYes\tNo\t滋賀工場\t滋賀工場\t\tTrue\t1_使用可\n"
    )
    sl_file = data_dir / "storage_locations.csv"
    sl_file.write_text(sl_content, encoding="cp932")

    # 5. ZS65データ
    zs65_header = "品目コード\t保管場所\tplant\t滞留日数\t利用可能値\n"
    zs65_content = (
        zs65_header +
        "ITEM001\t1120\tP100\t500\t10000\n"
    )
    zs65_file = data_dir / "ZS65.TXT"
    zs65_file.write_text(zs65_content, encoding="cp932")

    return wip_file, zp02_file, zp58_file, sl_file, zs65_file


def test_wip_data_processor(db_conn, sample_data_files):
    wip_file, zp02_file, zp58_file, sl_file, zs65_file = sample_data_files
    processor = WipDataProcessor(db_conn)
    processor.run_all(wip_file, zp58_file, zp02_file, sl_file, zs65_file)

    wip_df = pd.read_sql_query("SELECT * FROM wip_details", db_conn)
    assert len(wip_df) == 3
    assert 'expense_cost' in wip_df.columns

def test_wip_analysis_summary(db_conn, sample_data_files):
    wip_file, zp02_file, zp58_file, sl_file, zs65_file = sample_data_files
    processor = WipDataProcessor(db_conn)
    processor.run_all(wip_file, zp58_file, zp02_file, sl_file, zs65_file)
    analyzer = WipAnalysis(db_conn)
    summary_df = analyzer.get_wip_summary_comparison()
    assert not summary_df.empty

def test_pc_stock_analysis(db_conn, sample_data_files):
    wip_file, zp02_file, zp58_file, sl_file, zs65_file = sample_data_files
    processor = WipDataProcessor(db_conn)
    processor.run_all(wip_file, zp58_file, zp02_file, sl_file, zs65_file)
    analyzer = PcStockAnalysis(db_conn)
    summary_df = analyzer.get_pc_stock_summary()
    assert not summary_df.empty
    assert summary_df.iloc[0]['金額'] == 10000
