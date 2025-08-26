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

    def test_dynamic_master_creation(self):
        """
        Test that new items from production data are dynamically added to the master.
        """
        # 1. Initial master has 0 records (migrations create the table but don't seed in-memory)
        # Let's seed it with one item.
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO item_master (item_code, standard_cost) VALUES (?, ?)", ('EXISTING_ITEM', 100))
        self.conn.commit()

        # 2. Create a production dataframe with a new item
        prod_data = {
            '品目コード': ['EXISTING_ITEM', 'NEW_ITEM_1', 'NEW_ITEM_2', 'NEW_ITEM_1'],
        }
        prod_df = pd.DataFrame(prod_data)

        # 3. Run the dynamic update process
        processor = DataProcessor(self.conn)
        processor._update_dynamic_master(prod_df)

        # 4. Check the item_master table
        master_df = pd.read_sql_query("SELECT * FROM item_master", self.conn)

        # Should now have 3 items: EXISTING_ITEM, NEW_ITEM_1, NEW_ITEM_2
        self.assertEqual(len(master_df), 3)

        # Check that the new items were added
        new_item_codes = set(master_df['item_code'])
        self.assertIn('NEW_ITEM_1', new_item_codes)
        self.assertIn('NEW_ITEM_2', new_item_codes)

        # Check that the standard_cost for new items is None (NULL), which pandas reads as NaN
        new_item_1_cost = master_df[master_df['item_code'] == 'NEW_ITEM_1']['standard_cost'].iloc[0]
        self.assertTrue(pd.isna(new_item_1_cost))

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
