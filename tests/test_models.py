import unittest
import sqlite3
import tempfile
import os
import datetime
from pathlib import Path
import shutil

# sys.path modification to allow imports from src
import sys
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.models.production import ProductionRecord
from src.models.database import create_tables
from src.core.data_processor import DataProcessor
from src.config import settings

class TestProductionDataPipeline(unittest.TestCase):

    def setUp(self):
        """テストごとにインメモリDBとテストファイルを設定"""
        self.conn = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.conn.row_factory = sqlite3.Row
        create_tables(self.conn)

        # Create a temporary directory for user-supplied materials
        self.temp_dir = tempfile.mkdtemp()
        self.user_materials_dir = Path(self.temp_dir) / "User-supplied_materials"
        self.user_materials_dir.mkdir()

        # Create a dummy item master file
        self.master_file_path = self.user_materials_dir / "MARA_DL.csv"
        with open(self.master_file_path, 'w', encoding='utf-8') as f:
            f.write("品目\t標準原価\n")
            f.write("P001\t100\n")
            f.write("P005\t200\n")

        # Temporarily override the settings
        self.original_item_master_path = settings.ITEM_MASTER_PATH
        settings.ITEM_MASTER_PATH = self.master_file_path

        # Now instantiate the processor, which will load the dummy master
        self.processor = DataProcessor(self.conn)

        self.header = (
            "プラント\t保管場所\t品目コード\t品目テキスト\t指図番号\t指図タイプ\tMRP管理者\t"
            "指図数量\t実績数量\t累計数量\t残数量\t入力日時\t計画完了日\tWBS要素\t"
            "受注伝票番号\t受注明細番号\n"
        )
        # Test data rows
        self.valid_row = "P100\t1120\tP001\tTest Item 1\t50001\tZP11\tPC1\t10\t8\t8\t2\t2025/08/20 10:00\t20250825\t\t\t\n"
        self.row_bad_quantity = "P100\t1120\tP002\tTest Item 2\t50002\tZP11\tPC1\tBAD\t10\t10\t0\t2025/08/20 10:05\t20250826\t\t\t\n"
        self.row_missing_required = "P100\t1120\t\tTest Item 3\t50003\tZP11\tPC1\t30\t30\t30\t0\t2025/08/20 10:10\t20250827\t\t\t\n"
        self.row_bad_date = "P100\t1120\tP004\tTest Item 4\t50004\tZP11\tPC1\t40\t40\t40\t0\t2025/08/20 10:15\t2025-08-28\t\t\t\n"
        self.row_leading_zeros = "P100\t1120\tP005\tTest Item 5\t50005\tZP11\tPC1\t50\t50\t50\t0\t2025/08/20 10:20\t20250829\t\t000345\t0010\n"

    def tearDown(self):
        """テスト後にDB接続を閉じ、一時ファイルを削除"""
        self.conn.close()
        # Restore original settings
        settings.ITEM_MASTER_PATH = self.original_item_master_path
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)


    def test_clean_sap_numbers_validator(self):
        """clean_sap_numbersバリデーターを単体でテスト"""
        self.assertIsNone(ProductionRecord.clean_sap_numbers(None))
        self.assertIsNone(ProductionRecord.clean_sap_numbers(''))
        self.assertIsNone(ProductionRecord.clean_sap_numbers('   '))
        self.assertEqual(ProductionRecord.clean_sap_numbers('000123'), '123')
        self.assertEqual(ProductionRecord.clean_sap_numbers('0'), '0')
        self.assertEqual(ProductionRecord.clean_sap_numbers('000'), '0')
        self.assertEqual(ProductionRecord.clean_sap_numbers(' 123 '), '123')
        self.assertEqual(ProductionRecord.clean_sap_numbers('I-12345'), 'I-12345')

    def test_production_record_validation(self):
        """ProductionRecordモデルのバリデーションをテスト"""
        valid_data = {
            'プラント': 'P100', '保管場所': '1120', '品目コード': 'P001', '品目テキスト': 'Test Item',
            '指図番号': '50001', '指図タイプ': 'ZP11', 'MRP管理者': 'PC1', '指図数量': '10',
            '実績数量': '10', '累計数量': '10', '残数量': '0', '入力日時': datetime.datetime(2025, 8, 20, 10, 0),
            '計画完了日': '20250825', 'WBS要素': '', '受注伝票番号': '007', '受注明細番号': '0'
        }
        record = ProductionRecord(**valid_data)
        self.assertEqual(record.sales_order_number, '7')
        self.assertEqual(record.sales_order_item_number, '0')

    def test_data_processing_end_to_end(self):
        """ファイル処理からDB挿入までのエンドツーエンドテスト"""
        test_data = self.header + self.valid_row + self.row_bad_quantity + self.row_missing_required + self.row_bad_date + self.row_leading_zeros

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='shift_jis', suffix=".txt") as temp_f:
            temp_f.write(test_data)
            temp_file_path = temp_f.name

        original_data_file_path = settings.DATA_FILE_PATH
        settings.DATA_FILE_PATH = Path(temp_file_path)

        summary = self.processor.process_file_and_load_to_db()

        settings.DATA_FILE_PATH = original_data_file_path
        os.unlink(temp_file_path)

        self.assertEqual(summary['total_rows'], 5)
        self.assertEqual(summary['successful_inserts'], 2)
        self.assertEqual(summary['failed_rows'], 3)

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM production_records")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)

        # Test the newly added row with leading zeros and that amount was calculated
        cursor.execute("SELECT * FROM production_records WHERE item_code = 'P005'")
        db_record = cursor.fetchone()
        self.assertIsNotNone(db_record)
        self.assertEqual(db_record['sales_order_number'], '345')
        self.assertEqual(db_record['sales_order_item_number'], '10')
        self.assertEqual(db_record['amount'], 50 * 200) # 実績数量 * 標準原価

    def test_empty_and_header_only_file(self):
        """空のファイルやヘッダーのみのファイルを処理するテスト"""
        original_data_file_path = settings.DATA_FILE_PATH

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as empty_f:
            empty_file_path = empty_f.name

        settings.DATA_FILE_PATH = Path(empty_file_path)
        summary = self.processor.process_file_and_load_to_db()
        self.assertEqual(summary['total_rows'], 0)
        self.assertEqual(summary['failed_rows'], 0)
        self.assertEqual(summary['successful_inserts'], 0)
        os.unlink(empty_file_path)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='shift_jis') as header_f:
            header_f.write(self.header)
            header_file_path = header_f.name

        settings.DATA_FILE_PATH = Path(header_file_path)
        summary = self.processor.process_file_and_load_to_db()
        self.assertEqual(summary['total_rows'], 0)
        self.assertEqual(summary['successful_inserts'], 0)
        os.unlink(header_file_path)

        settings.DATA_FILE_PATH = original_data_file_path


if __name__ == '__main__':
    unittest.main()
