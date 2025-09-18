import os
import sys
import pandas as pd

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.models.database import get_db_connection
from src.core.analytics import WipAnalysis, PcStockAnalysis

def verify_all_reports():
    """
    Connects to the database and verifies the output of the new/modified
    report generation methods.
    """
    print("--- Starting Final Report Verification ---")
    conn = None
    try:
        conn = get_db_connection()
        print("Database connection successful.")

        # 1. Verify WIP Details Report
        print("\n--- Verifying WIP Details Report ---")
        wip_analyzer = WipAnalysis(conn)
        wip_details_df = wip_analyzer.get_wip_details_report()
        print(f"WIP details report generated with {len(wip_details_df)} rows.")
        if "未出庫フラグ" in wip_details_df.columns and wip_details_df["未出庫フラグ"].str.contains("材料未出庫").any():
            print("WIP details verification PASSED: Found '材料未出庫' flag in the report.")
        else:
            print("WIP details verification FAILED: Did not find '材料未出庫' flag in the report.")

        # 2. Verify PC Stock Details Report
        print("\n--- Verifying PC Stock Details Report ---")
        pc_stock_analyzer = PcStockAnalysis(conn)
        pc_stock_details_df = pc_stock_analyzer.get_pc_stock_details_report()
        print(f"PC stock details report generated with {len(pc_stock_details_df)} rows.")
        if len(pc_stock_details_df) > 0 and '滞留年数' in pc_stock_details_df.columns and pd.api.types.is_integer_dtype(pc_stock_details_df['滞留年数'].dtype):
            print("PC stock details verification PASSED.")
        else:
            print("PC stock details verification FAILED.")

    except Exception as e:
        print(f"An error occurred during verification: {e}")
    finally:
        if conn:
            conn.close()
            print("\nDatabase connection closed.")
    print("--- Verification Script Finished ---")

if __name__ == "__main__":
    sys.path.insert(0, os.getcwd())
    verify_all_reports()
