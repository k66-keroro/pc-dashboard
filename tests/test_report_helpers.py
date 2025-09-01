import unittest
import datetime
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.utils.report_helpers import get_week_of_month, get_mrp_type

class TestReportHelpers(unittest.TestCase):

    def test_get_mrp_type(self):
        """MRP管理者から内製/外注を正しく判定できるかテスト"""
        self.assertEqual(get_mrp_type('PC1'), '内製')
        self.assertEqual(get_mrp_type('PC2'), '内製')
        self.assertEqual(get_mrp_type('PC3'), '内製')
        self.assertEqual(get_mrp_type('PC4'), '外注')
        self.assertEqual(get_mrp_type('PC5'), '外注')
        self.assertEqual(get_mrp_type('PC6'), '外注')
        self.assertEqual(get_mrp_type('PC7'), 'その他')
        self.assertEqual(get_mrp_type('CC0'), 'その他')
        self.assertEqual(get_mrp_type(''), 'その他')
        self.assertEqual(get_mrp_type(None), 'その他')
        self.assertEqual(get_mrp_type('INVALID'), 'その他')

    def test_get_week_of_month(self):
        """月の週区分を正しく計算できるかテスト"""
        # User-provided examples for July 2025
        self.assertEqual(get_week_of_month(datetime.date(2025, 7, 26)), 4)
        self.assertEqual(get_week_of_month(datetime.date(2025, 7, 27)), 5)
        self.assertEqual(get_week_of_month(datetime.date(2025, 7, 28)), 5)
        self.assertEqual(get_week_of_month(datetime.date(2025, 7, 31)), 5)

        # User-provided examples for August 2025
        self.assertEqual(get_week_of_month(datetime.date(2025, 8, 1)), 1)
        self.assertEqual(get_week_of_month(datetime.date(2025, 8, 2)), 1)
        self.assertEqual(get_week_of_month(datetime.date(2025, 8, 3)), 2)
        self.assertEqual(get_week_of_month(datetime.date(2025, 8, 4)), 2)
        self.assertEqual(get_week_of_month(datetime.date(2025, 8, 9)), 2)
        self.assertEqual(get_week_of_month(datetime.date(2025, 8, 10)), 3)

        # Test another month (e.g., June 2025, where 1st is a Sunday)
        self.assertEqual(get_week_of_month(datetime.date(2025, 6, 1)), 1)
        self.assertEqual(get_week_of_month(datetime.date(2025, 6, 7)), 1)
        self.assertEqual(get_week_of_month(datetime.date(2025, 6, 8)), 2)

        # Test a month where the first Saturday is the 1st
        # December 2026, 1st is a Tuesday
        # November 2026, 1st is a Sunday
        # October 2026, 1st is a Thursday
        # September 2026, 1st is a Tuesday
        # August 2026, 1st is a Saturday
        self.assertEqual(get_week_of_month(datetime.date(2026, 8, 1)), 1)
        self.assertEqual(get_week_of_month(datetime.date(2026, 8, 2)), 2)
        self.assertEqual(get_week_of_month(datetime.date(2026, 8, 8)), 2)
        self.assertEqual(get_week_of_month(datetime.date(2026, 8, 9)), 3)

if __name__ == '__main__':
    unittest.main()
