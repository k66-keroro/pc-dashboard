import pandas as pd
import os
import shutil

# --- 設定 ---
base_path = r'C:\Users\sem3171\pc-dashboard\User-supplied_materials'
mara_filename = 'MARA_DL.csv'
filter_filename = '8000_PC区分.txt'

mara_file = os.path.join(base_path, mara_filename)
filter_file = os.path.join(base_path, filter_filename)
output_file = mara_file  # 上書き
backup_file = mara_file + '.bak'  # バックアップ

encoding = 'utf-16'

# --- バックアップ ---
if not os.path.exists(backup_file):
    shutil.copy2(mara_file, backup_file)
    print(f"バックアップを作成しました: {backup_file}")

try:
    print("処理を開始します...")

    # 1. フィルター用品目コード読み込み
    # フィルター用品目コード読み込み（cp932のまま）
    with open(filter_file, encoding='cp932', errors='replace') as f:
        filter_codes_df = pd.read_csv(f, usecols=['品目'])
    filter_codes = set(filter_codes_df['品目'].astype(str))

    # MARA_DL.csv読み込み（utf-16で！）
    with open(mara_file, encoding='utf-16', errors='replace') as f:
        mara_df = pd.read_csv(f, low_memory=False, dtype={'品目': str}, on_bad_lines='skip')

    # 3. 絞り込み
    matched_df = mara_df[mara_df['品目'].isin(filter_codes)]
    unmatched_df = mara_df[~mara_df['品目'].isin(filter_codes)]

    # 4. アンマッチ100件サンプリング
    if len(unmatched_df) > 100:
        unmatched_sample_df = unmatched_df.sample(n=100, random_state=1)
    else:
        unmatched_sample_df = unmatched_df

    # 5. 結合
    final_df = pd.concat([matched_df, unmatched_sample_df])

    # 6. 上書き保存
    final_df.to_csv(output_file, index=False, encoding=encoding)

    print("処理が正常に完了しました！")
    print(f"元の行数: {original_count}")
    print(f"加工後の行数: {len(final_df)}")
    print(f"ファイルは '{output_file}' に保存されています。")
    print(f"バックアップ: '{backup_file}'")

except Exception as e:
    print(f"予期せぬエラーが発生しました: {e}")