import unittest
import sqlite3
import tempfile
import os
import datetime
from pathlib import Path
import shutil

import sys
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.models.migration_manager import apply_migrations
from src.core.data_processor import DataProcessor

class TestProductionDataPipeline(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        apply_migrations(self.conn)

        self.temp_dir = tempfile.mkdtemp()
        self.master_file_path = Path(self.temp_dir) / "DUMMY_MARA_DL.csv"
        with open(self.master_file_path, 'w', encoding='utf-8') as f:
            f.write("品目\t標準原価\n")
            f.write("P001\t100\n")
            f.write(" P005 \t200\n") # Test stripping whitespace

        processor = DataProcessor(self.conn)
        processor.sync_master_from_csv(self.master_file_path)

        self.header = (
            "プラント\t保管場所\t品目コード\t品目テキスト\t指図番号\t指図タイプ\tMRP管理者\t"
            "指図数量\t実績数量\t累計数量\t残数量\t入力日時\t計画完了日\tWBS要素\t"
            "受注伝票番号\t受注明細番号\n"
        )
        self.valid_row = "P100\t1120\tP001\tTest Item 1\t50001\tZP11\tPC1\t10\t8\t8\t2\t2025/08/20 10:00\t20250825\t\t\t\n"
        self.row_non_pc = "P100\t1120\tP002\tTest Item 2\t50002\tZP11\tCC0\t20\t10\t10\t10\t2025/08/20 10:05\t20250826\t\t\t\n"
        self.row_bad_date = "P100\t1120\tP004\tTest Item 4\t50004\tZP11\tPC4\t40\t40\t40\t0\tINVALID_DATE\t2025-08-28\t\t\t\n"
        self.row_with_whitespace = "P100\t1120\t P005 \tTest Item 5\t50005\tZP11\tPC5\t50\t50\t50\t0\t2025/08/20 10:20\t20250829\t\t000345\t0010\n"

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.temp_dir)

    def test_data_processing_end_to_end(self):
        test_data = self.header + self.valid_row + self.row_non_pc + self.row_bad_date + self.row_with_whitespace

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='shift_jis') as temp_f:
            temp_f.write(test_data)
            temp_file_path = Path(temp_f.name)

        processor = DataProcessor(self.conn)
        summary = processor.process_file_and_load_to_db(temp_file_path)

        os.unlink(temp_file_path)

        # Expecting 2 valid rows: valid_row and row_with_whitespace
        # row_non_pc is filtered out by MRP filter
        # row_bad_date is dropped due to invalid date
        self.assertEqual(summary['total_rows'], 2)
        self.assertEqual(summary['successful_inserts'], 2)
        self.assertEqual(summary['failed_rows'], 0)

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM production_records")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)

        # Test that whitespace was stripped and amount was calculated
        db_record = self.conn.execute("SELECT * FROM production_records WHERE item_code = ?", ('P005',)).fetchone()
        self.assertIsNotNone(db_record)
        self.assertEqual(db_record['amount'], 50 * 200)

if __name__ == '__main__':
    unittest.main()
