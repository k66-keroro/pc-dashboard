import unittest
import sqlite3
import pandas as pd
from pathlib import Path
import sys
import datetime
import tempfile
import shutil

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.models.migration_manager import apply_migrations
from src.core.data_processor import DataProcessor
from src.models.database import insert_production_records
from src.models.production import ProductionRecord
from src.config import settings

class TestAdvancedFeatures(unittest.TestCase):

    def setUp(self):
        """Set up an in-memory SQLite database for each test."""
        self.conn = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

        # Create a dummy master file path but don't create the file
        # This will cause the seeder in migration 002 to skip seeding.
        self.temp_dir = tempfile.mkdtemp()
        dummy_master_path = Path(self.temp_dir) / "DUMMY_MARA_DL.csv"

        # Temporarily override the settings
        self.original_item_master_path = settings.ITEM_MASTER_PATH
        settings.ITEM_MASTER_PATH = dummy_master_path

        # Run all migrations to get the latest schema
        apply_migrations(self.conn)

    def tearDown(self):
        """Close the database connection after each test."""
        self.conn.close()
        settings.ITEM_MASTER_PATH = self.original_item_master_path
        shutil.rmtree(self.temp_dir)

    def test_master_sync_logic(self):
        """
        Test that sync_master_from_csv performs a full refresh of the master data.
        """
        processor = DataProcessor(self.conn)
        cursor = self.conn.cursor()

        # 1. Sync with a first version of the master file
        master_v1_content = "品目\t標準原価\nITEM_A\t100\nITEM_B\t200\n"
        master_v1_path = Path(self.temp_dir) / "MASTER_V1.csv"
        with open(master_v1_path, 'w') as f:
            f.write(master_v1_content)

        settings.ITEM_MASTER_PATH = master_v1_path
        processor.sync_master_from_csv()

        # Check state after first sync
        master_df_v1 = pd.read_sql_query("SELECT * FROM item_master", self.conn)
        self.assertEqual(len(master_df_v1), 2)
        self.assertIn('ITEM_A', master_df_v1['item_code'].values)
        self.assertIn('ITEM_B', master_df_v1['item_code'].values)

        # 2. Sync with a second, different version of the master file
        #    - ITEM_A cost updated
        #    - ITEM_B removed
        #    - ITEM_C added
        master_v2_content = "品目\t標準原価\nITEM_A\t150\nITEM_C\t300\n"
        master_v2_path = Path(self.temp_dir) / "MASTER_V2.csv"
        with open(master_v2_path, 'w') as f:
            f.write(master_v2_content)

        settings.ITEM_MASTER_PATH = master_v2_path
        processor.sync_master_from_csv()

        # Check state after second sync (should be a full refresh)
        master_df_v2 = pd.read_sql_query("SELECT * FROM item_master ORDER BY item_code", self.conn)
        self.assertEqual(len(master_df_v2), 2)

        # ITEM_B should be gone
        self.assertNotIn('ITEM_B', master_df_v2['item_code'].values)

        # ITEM_A should be present with updated cost
        self.assertEqual(master_df_v2.loc[0, 'item_code'], 'ITEM_A')
        self.assertEqual(master_df_v2.loc[0, 'standard_cost'], 150)

        # ITEM_C should be present
        self.assertEqual(master_df_v2.loc[1, 'item_code'], 'ITEM_C')

    def test_duplicate_record_prevention(self):
        """
        Test that duplicate production records are ignored on insert.
        """
        # 1. Create some records, including a duplicate
        record_1 = ProductionRecord(plant='P100', item_code='A', item_text='A', order_number='O1', order_type='T1', mrp_controller='PC1', order_quantity=1, actual_quantity=1, cumulative_quantity=1, remaining_quantity=0, input_datetime=datetime.datetime(2025, 8, 25, 10, 0, 0), amount=100)
        record_2 = ProductionRecord(plant='P100', item_code='B', item_text='B', order_number='O2', order_type='T1', mrp_controller='PC1', order_quantity=1, actual_quantity=1, cumulative_quantity=1, remaining_quantity=0, input_datetime=datetime.datetime(2025, 8, 25, 11, 0, 0), amount=200)
        record_1_duplicate = ProductionRecord(plant='P100', item_code='A', item_text='A', order_number='O1', order_type='T1', mrp_controller='PC1', order_quantity=1, actual_quantity=1, cumulative_quantity=1, remaining_quantity=0, input_datetime=datetime.datetime(2025, 8, 25, 10, 0, 0), amount=100)

        records_to_insert = [record_1, record_2, record_1_duplicate]

        # 2. Insert them
        insert_production_records(self.conn, records_to_insert)

        # 3. Check the count in the database
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM production_records")
        count = cursor.fetchone()[0]
        # Should only be 2 records, as the duplicate was ignored
        self.assertEqual(count, 2)

        # 4. Insert the same list again
        insert_production_records(self.conn, records_to_insert)

        # 5. Check the count again
        cursor.execute("SELECT COUNT(*) FROM production_records")
        new_count = cursor.fetchone()[0]
        # Count should not have changed
        self.assertEqual(new_count, 2)

if __name__ == '__main__':
    unittest.main()
