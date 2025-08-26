import unittest
import pandas as pd
import datetime
from pathlib import Path
import os
import shutil
import tempfile
import sys

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.core.reporter import ReportGenerator
from src.config import settings

class TestReportGenerator(unittest.TestCase):

    def setUp(self):
        """Set up a temporary reports directory and a sample DataFrame."""
        self.temp_dir = tempfile.mkdtemp()
        self.reports_dir = Path(self.temp_dir)

        # Override the settings to use the temporary directory
        self.original_reports_dir = settings.REPORTS_DIR
        settings.REPORTS_DIR = self.reports_dir

        # Create a sample enriched DataFrame
        data = {
            'MRP管理者': ['PC1', 'PC1', 'PC2', 'PC4', 'PC1'],
            '入力日時': [
                datetime.datetime(2025, 7, 26, 10, 0), # Sat, Week 4
                datetime.datetime(2025, 7, 27, 10, 0), # Sun, Week 5
                datetime.datetime(2025, 7, 27, 11, 0), # Sun, Week 5
                datetime.datetime(2025, 8, 1, 10, 0),  # Fri, Week 1
                datetime.datetime(2025, 8, 3, 10, 0)   # Sun, Week 2
            ],
            '指図番号': ['O1', 'O2', 'O3', 'O4', 'O5'],
            '品目コード': ['A', 'B', 'A', 'C', 'B'],
            '品目テキスト': ['Item A', 'Item B', 'Item A', 'Item C', 'Item B'],
            '指図数量': [10, 20, 5, 10, 15],
            '実績数量': [10, 15, 5, 8, 15],
            'amount': [1000, 1500, 500, 800, 1500]
        }
        self.df = pd.DataFrame(data)
        self.reporter = ReportGenerator(self.df)

    def tearDown(self):
        """Clean up the temporary directory and restore settings."""
        settings.REPORTS_DIR = self.original_reports_dir
        shutil.rmtree(self.temp_dir)

    def test_generate_details_report(self):
        """Test the generation of the details report."""
        self.reporter.generate_details_report()
        report_path = self.reports_dir / "明細_抜粋.txt"
        self.assertTrue(report_path.exists())

        result_df = pd.read_csv(report_path, sep='\t')
        self.assertEqual(len(result_df), 5)
        expected_cols = ['MRP管理者', '完成日', '指図', '品目コード', '品目テキスト', '計画数', '完成数', '金額', '週区分']
        self.assertListEqual(list(result_df.columns), expected_cols)
        self.assertEqual(result_df.loc[0, '週区分'], 4)
        self.assertEqual(result_df.loc[1, '週区分'], 5)
        self.assertEqual(result_df.loc[3, '週区分'], 1)
        self.assertEqual(result_df.loc[4, '週区分'], 2)

    def test_generate_daily_summary(self):
        """Test the generation of the daily summary report."""
        self.reporter.generate_daily_summary()
        report_path = self.reports_dir / "日別サマリー.txt"
        self.assertTrue(report_path.exists())

        result_df = pd.read_csv(report_path, sep='\t')
        self.assertEqual(len(result_df), 4) # 4 unique days

        # Select rows by date to make the test robust against sorting order
        self.assertEqual(result_df[result_df['完成日'] == '2025-07-26']['日別金額'].iloc[0], 1000)
        self.assertEqual(result_df[result_df['完成日'] == '2025-07-27']['日別金額'].iloc[0], 2000)

    def test_generate_weekly_summary(self):
        """Test the generation of the weekly summary report."""
        self.reporter.generate_weekly_summary()
        report_path = self.reports_dir / "週別サマリー.txt"
        self.assertTrue(report_path.exists())

        result_df = pd.read_csv(report_path, sep='\t')
        self.assertEqual(len(result_df), 5) # 4 weeks + total row

        # Find the row for week 5 of July
        week_5_total = result_df[result_df['週区分'] == '5']['合計'].iloc[0]
        self.assertEqual(week_5_total, 2000) # 1500 + 500

        # Check the grand total row
        grand_total = result_df[result_df['週区分'] == '合計']['合計'].iloc[0]
        self.assertEqual(grand_total, self.df['amount'].sum())

if __name__ == '__main__':
    unittest.main()
