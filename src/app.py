import streamlit as st
import pandas as pd
import datetime
import altair as alt

from src.models.database import get_db_connection
from src.utils.report_helpers import get_week_of_month, get_mrp_type
from src.config import settings

st.set_page_config(layout="wide", page_title="PC製造部門向けダッシュボード")

@st.cache_data
def load_and_prepare_data():
    """
    DBからデータをロードし、前処理と分析列の追加を行う。
    この関数はキャッシュされ、2回目以降の実行は高速です。
    """
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM production_records", conn)
    finally:
        conn.close()

    # --- データ型変換とクリーンアップ ---
    df['input_datetime'] = pd.to_datetime(df['input_datetime'], errors='coerce')
    df.dropna(subset=['input_datetime'], inplace=True)
    df['completion_date'] = df['input_datetime'].dt.date

    numeric_cols = ['order_quantity', 'actual_quantity', 'amount']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- 分析列の追加 ---
    # PC始まりのMRP管理者のみを対象とする
    df = df[df['mrp_controller'].str.startswith('PC', na=False)].copy()

    df['week_category'] = df['completion_date'].apply(
        lambda d: get_week_of_month(d) if pd.notna(d) else None
    )
    df['mrp_type'] = df['mrp_controller'].apply(get_mrp_type)

    return df

def get_kpi_metrics(df: pd.DataFrame):
    """指定されたDFからKPIを計算する"""
    if df.empty:
        return {'total_amount': 0, 'achievement_rate': 0, 'unique_items': 0, 'unique_orders': 0}

    total_amount = df['amount'].sum()
    total_actual = df['actual_quantity'].sum()
    total_order = df['order_quantity'].sum()
    achievement_rate = (total_actual / total_order) * 100 if total_order > 0 else 0
    unique_items = df['item_code'].nunique()
    unique_orders = df['order_number'].nunique()

    return {
        'total_amount': total_amount, 'achievement_rate': achievement_rate,
        'unique_items': unique_items, 'unique_orders': unique_orders
    }

def main():
    """
    Streamlitダッシュボードのメイン関数
    """
    st.title("PC製造部門向けダッシュボード")
    df = load_and_prepare_data()

    if df.empty:
        st.warning("表示するデータがありません。")
        return

    # --- サイドバー ---
    st.sidebar.header("表示設定")
    min_date = df['completion_date'].min()
    max_date = df['completion_date'].max()
    start_date, end_date = st.sidebar.date_input(
        "期間を選択", value=(min_date, max_date),
        min_value=min_date, max_value=max_date, format="YYYY/MM/DD"
    )
    agg_target = st.sidebar.radio("集計対象", ('金額', '実績数量'), horizontal=True)
    agg_column = 'amount' if agg_target == '金額' else 'actual_quantity'
    agg_label = "金額" if agg_target == '金額' else "数量"

    if not start_date or not end_date or start_date > end_date:
        st.sidebar.error("有効な期間を選択してください。")
        return

    # --- データフィルタリング ---
    filtered_df = df[(df['completion_date'] >= start_date) & (df['completion_date'] <= end_date)]
    if filtered_df.empty:
        st.warning("選択された期間にデータがありません。")
        return

    # --- KPI表示 ---
    st.header("サマリー")
    st.subheader("本日実績")
    today_df = filtered_df[filtered_df['completion_date'] == datetime.date.today()]
    today_kpis = get_kpi_metrics(today_df)
    kpi_cols = st.columns(4)
    kpi_cols[0].metric("生産金額", f"¥{today_kpis['total_amount']:,.0f}")
    kpi_cols[1].metric("達成率", f"{today_kpis['achievement_rate']:.1f}%")
    kpi_cols[2].metric("生産品番数", f"{today_kpis['unique_items']}")
    kpi_cols[3].metric("総指図数", f"{today_kpis['unique_orders']}")

    st.divider()
    st.subheader(f"期間サマリー: {start_date.strftime('%Y/%m/%d')} ~ {end_date.strftime('%Y/%m/%d')}")
    period_kpis = get_kpi_metrics(filtered_df)
    kpi_cols_period = st.columns(4)
    kpi_cols_period[0].metric("総生産金額", f"¥{period_kpis['total_amount']:,.0f}")
    kpi_cols_period[1].metric("全体達成率", f"{period_kpis['achievement_rate']:.1f}%")
    kpi_cols_period[2].metric("生産品番数", f"{period_kpis['unique_items']}")
    kpi_cols_period[3].metric("総指図数", f"{period_kpis['unique_orders']}")

    # --- タブ表示 ---
    tab_graphs, tab_daily, tab_weekly, tab_details = st.tabs(["グラフ分析", "日別レポート", "週別レポート", "明細データ"])

    with tab_graphs:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(f"{agg_label}の時系列推移")
            time_series_df = filtered_df.groupby(['completion_date', 'mrp_type'])[agg_column].sum().unstack().fillna(0)
            st.line_chart(time_series_df)
        with col2:
            st.subheader(f"内製/外注の構成比 ({agg_label}ベース)")
            mrp_type_summary = filtered_df.groupby('mrp_type')[agg_column].sum().reset_index()
            mrp_type_summary['percentage'] = (mrp_type_summary[agg_column] / mrp_type_summary[agg_column].sum())
            base = alt.Chart(mrp_type_summary).encode(
                theta=alt.Theta(field=agg_column, type="quantitative", stack=True),
                color=alt.Color(field="mrp_type", type="nominal", title="タイプ")
            )

            pie = base.mark_arc(outerRadius=120, innerRadius=70)
            text = base.mark_text(radius=140, size=14).encode(
                text=alt.Text('percentage', format='.1%')
            )

            st.altair_chart(pie + text, use_container_width=True)
        st.subheader(f"{agg_label} TOP 10品目")
        top_10_items = filtered_df.groupby('item_text')[agg_column].sum().nlargest(10).sort_values(ascending=True)
        st.bar_chart(top_10_items, horizontal=True)

    with tab_details:
        st.header("生産実績明細データ")
        display_cols = ['mrp_controller', 'completion_date', 'order_number', 'item_code', 'item_text', 'order_quantity', 'actual_quantity', 'amount', 'week_category']
        display_df = filtered_df[display_cols].rename(columns={
            'mrp_controller': 'MRP管理者', 'completion_date': '完成日', 'order_number': '指図',
            'item_code': '品目コード', 'item_text': '品目テキスト', 'order_quantity': '計画数',
            'actual_quantity': '完成数', 'amount': '金額', 'week_category': '週区分'
        })
        st.download_button(
            label="このデータをCSVでダウンロード", data=display_df.to_csv(index=False, encoding='utf-8-sig'),
            file_name=f"details_{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.csv", mime='text/csv',
        )
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    with tab_daily:
        st.header("日別サマリーレポート")
        daily_summary = filtered_df.groupby(['week_category', 'completion_date', 'mrp_controller'])[agg_column].sum().unstack(fill_value=0)
        daily_summary['日別合計'] = daily_summary.sum(axis=1)
        st.dataframe(daily_summary.style.format("{:,.0f}"), use_container_width=True)

    with tab_weekly:
        st.header("週別サマリーレポート")

        st.subheader("内製/外注別")
        weekly_summary_type = filtered_df.groupby(['week_category', 'mrp_type'])[agg_column].sum().unstack(fill_value=0)
        weekly_summary_type['合計'] = weekly_summary_type.sum(axis=1)
        st.dataframe(weekly_summary_type.style.format("{:,.0f}"), use_container_width=True)

        st.subheader("MRP管理者別")
        weekly_summary_ctrl = filtered_df.groupby(['week_category', 'mrp_controller'])[agg_column].sum().unstack(fill_value=0)
        weekly_summary_ctrl['合計'] = weekly_summary_ctrl.sum(axis=1)
        st.dataframe(weekly_summary_ctrl.style.format("{:,.0f}"), use_container_width=True)

if __name__ == "__main__":
    main()
