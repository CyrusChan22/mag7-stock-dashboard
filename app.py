# 看板首页：① Overview 总览
# 运行方法（在项目文件夹里）：streamlit run app.py
import sys

import pandas as pd
import streamlit as st

sys.path.append("src")  # 让 Python 能找到 src 文件夹里的模块
from dashboard_common import MAG7, BENCHMARKS, get_data, sidebar_dates
from metrics import performance_table

st.set_page_config(page_title="Mag 7 Dashboard", layout="wide")
st.title("Magnificent 7 Stock Dashboard")
st.caption("Daily data from Yahoo Finance, 2015 to present. Prices are adjusted for splits and dividends.")

adj_close = get_data()

# ===== 侧边栏：选股票、选日期 =====
st.sidebar.header("Filters")
tickers = st.sidebar.multiselect("Tickers", list(adj_close.columns), default=MAG7 + BENCHMARKS)
start, end = sidebar_dates(adj_close)

if not tickers:
    st.warning("Please select at least one ticker.")
    st.stop()  # 没选股票就不往下画了

# 按侧边栏的选择截取数据
prices = adj_close.loc[start:end, tickers]

# ===== 表现指标表 =====
st.subheader("Performance Metrics")
table = performance_table(prices)
display = pd.DataFrame({
    "Start": table["start"],
    "Cumulative Return (%)": table["cumulative_return"] * 100,
    "Annual Return (%)": table["annual_return"] * 100,
    "Annual Volatility (%)": table["annual_volatility"] * 100,
    "Max Drawdown (%)": table["max_drawdown"] * 100,
    "Sharpe Ratio": table["sharpe"],
})
st.dataframe(display.round(2), width="stretch")  # 表格占满页面宽度
st.caption("Sharpe ratio assumes a 2% risk-free rate. "
           "Annualized figures for short histories (e.g. SNDK, listed Feb 2025) can be misleading.")

# ===== 净值曲线：每只股票都从 1 开始 =====
st.subheader("Growth of $1")
# bfill().iloc[0] 取每只股票第一个有数据的价格（SNDK 上市晚，前面是空值）
growth = prices / prices.bfill().iloc[0]
st.line_chart(growth)
