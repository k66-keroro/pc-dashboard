import streamlit as st
import pandas as pd
import datetime

from src.models.database import get_db_connection
from src.utils.report_helpers import get_week_of_month, get_mrp_type
from src.config import settings

st.set_page_config(layout="wide", page_title="PC製造部門向けダッシュボード")

@st.cache_data
def load_data():
    """
    データベースから生産実績データを読み込み、分析用の列を追加してキャッシュする。
    """
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM production_records", conn)
    conn.close()

    # 'input_datetime'をdatetimeオブジェクトに変換
    # ISO8601形式("T"区切り)とその他の形式に柔軟に対応するため、formatを指定せずにエラーを無視する
    df['input_datetime'] = pd.to_datetime(df['input_datetime'], errors='coerce')
    # 'completion_date'を作成
    df['completion_date'] = df['input_datetime'].dt.date

    # 分析用の列を追加
    df['week_category'] = df['completion_date'].apply(
        lambda d: get_week_of_month(d) if pd.notna(d) else None
    )
    df['mrp_type'] = df['mrp_controller'].apply(get_mrp_type)

    return df

def main():
    """
    Streamlitダッシュボードのメイン関数
    """
    st.title("PC製造部門向けダッシュボード")

    df = load_data()

    if df.empty:
        st.warning("表示するデータがありません。")
        return

    # --- サイドバー ---
    st.sidebar.header("フィルタ")

    min_date = df['completion_date'].min()
    max_date = df['completion_date'].max()

    start_date, end_date = st.sidebar.date_input(
        "期間を選択",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="YYYY/MM/DD"
    )

    if not start_date or not end_date or start_date > end_date:
        st.sidebar.error("有効な期間を選択してください。")
        return

    # --- メインコンテンツ ---

    # 選択された期間でデータをフィルタリング
    filtered_df = df[
        (df['completion_date'] >= start_date) &
        (df['completion_date'] <= end_date)
    ]

    if filtered_df.empty:
        st.warning("選択された期間にデータがありません。")
        return

    # --- KPI表示 ---
    st.header("主要KPI")

    total_amount = filtered_df['amount'].sum()

    total_actual = filtered_df['actual_quantity'].sum()
    total_order = filtered_df['order_quantity'].sum()
    achievement_rate = (total_actual / total_order) * 100 if total_order > 0 else 0

    unique_items = filtered_df['item_code'].nunique()
    unique_orders = filtered_df['order_number'].nunique()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("総生産金額", f"¥{total_amount:,.0f}")
    col2.metric("全体達成率", f"{achievement_rate:.1f}%")
    col3.metric("生産品番数", f"{unique_items}")
    col4.metric("総指図数", f"{unique_orders}")

    st.divider()

    # --- グラフ表示 ---
    st.header("グラフ分析")

    col1, col2 = st.columns([2, 1]) # Make the first column wider

    with col1:
        # 時系列推移グラフ
        st.subheader("生産金額の時系列推移")
        time_series_df = filtered_df.groupby(['completion_date', 'mrp_type'])['amount'].sum().unstack().fillna(0)
        st.line_chart(time_series_df)

    with col2:
        # 内製/外注の構成比
        st.subheader("内製/外注の構成比 (金額ベース)")
        mrp_type_summary = filtered_df.groupby('mrp_type')['amount'].sum().reset_index()
        # st.altair_chart を使ってドーナツチャートを作成 (もしaltairがなければ st.bar_chart)
        try:
            import altair as alt
            chart = alt.Chart(mrp_type_summary).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="amount", type="quantitative"),
                color=alt.Color(field="mrp_type", type="nominal", title="タイプ"),
                tooltip=['mrp_type', 'amount']
            ).properties(
                title='生産構成比'
            )
            st.altair_chart(chart, use_container_width=True)
        except ImportError:
            st.bar_chart(mrp_type_summary.set_index('mrp_type'))


    # TOP10品目
    st.subheader("生産金額 TOP 10品目")
    top_10_items = filtered_df.groupby('item_text')['amount'].sum().nlargest(10).sort_values(ascending=True)
    st.bar_chart(top_10_items, horizontal=True)

    st.divider()

    st.header("生産実績データ（フィルタ後）")

    # ダウンロードボタン
    csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="CSVデータをダウンロード",
        data=csv_data,
        file_name=f"production_data_{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.csv",
        mime='text/csv',
    )

    st.dataframe(filtered_df)


if __name__ == "__main__":
    main()
