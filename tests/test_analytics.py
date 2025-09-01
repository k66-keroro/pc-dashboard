import unittest
import sqlite3
import pandas as pd
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.models.database import create_tables
from src.core.analytics import ProductionAnalytics, ErrorDetection

class TestAnalytics(unittest.TestCase):

    def setUp(self):
        """Set up an in-memory SQLite database for each test."""
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        create_tables(self.conn)
        self._insert_test_data()

    def tearDown(self):
        """Close the database connection after each test."""
        self.conn.close()

    def _insert_test_data(self):
        """Insert a mix of consistent and inconsistent data for testing."""
        cursor = self.conn.cursor()

        # Consistent record
        cursor.execute("""
        INSERT INTO production_records (
            plant, item_code, item_text, order_number, order_type, mrp_controller,
            order_quantity, actual_quantity, cumulative_quantity, remaining_quantity, input_datetime
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('P100', 'ITEM001', 'Test Item 1', 'ORD001', 'ZP11', 'PC1', 100, 80, 80, 20, '2025-08-21 10:00:00'))

        # INCONSISTENT record: 100 - 50 != 40
        cursor.execute("""
        INSERT INTO production_records (
            plant, item_code, item_text, order_number, order_type, mrp_controller,
            order_quantity, actual_quantity, cumulative_quantity, remaining_quantity, input_datetime
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('P100', 'ITEM002', 'Test Item 2', 'ORD002', 'ZP11', 'PC1', 100, 50, 50, 40, '2025-08-21 11:00:00'))

        # Another consistent record
        cursor.execute("""
        INSERT INTO production_records (
            plant, item_code, item_text, order_number, order_type, mrp_controller,
            order_quantity, actual_quantity, cumulative_quantity, remaining_quantity, input_datetime
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('P100', 'ITEM003', 'Test Item 3', 'ORD003', 'ZP11', 'PC1', 50, 50, 50, 0, '2025-08-21 12:00:00'))

        self.conn.commit()

    def test_production_analytics_summary(self):
        """Test the summary method of the ProductionAnalytics class."""
        analytics = ProductionAnalytics(self.conn)
        summary = analytics.get_summary()

        self.assertEqual(summary['record_count'], 3)
        self.assertEqual(summary['total_order_quantity'], 250) # 100 + 100 + 50
        self.assertEqual(summary['total_actual_quantity'], 180) # 80 + 50 + 50
        self.assertAlmostEqual(summary['achievement_rate'], (180/250)*100)

    def test_find_quantity_inconsistencies(self):
        """Test the find_quantity_inconsistencies method of the ErrorDetection class."""
        error_detector = ErrorDetection(self.conn)
        inconsistencies_df = error_detector.find_quantity_inconsistencies()

        # We expect to find exactly one inconsistent record
        self.assertEqual(len(inconsistencies_df), 1)

        # Check if the correct record was flagged
        inconsistent_record = inconsistencies_df.iloc[0]
        self.assertEqual(inconsistent_record['order_number'], 'ORD002')
        self.assertEqual(inconsistent_record['order_quantity'], 100)
        self.assertEqual(inconsistent_record['cumulative_quantity'], 50)
        self.assertEqual(inconsistent_record['remaining_quantity'], 40)
        self.assertEqual(inconsistent_record['expected_remaining'], 50) # 100 - 50

if __name__ == '__main__':
    unittest.main()
