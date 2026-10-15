# 看板第 ② 页：Stock Deep Dive 个股深挖
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from scipy import stats

sys.path.append("src")
from correlation_beta import beta_regression, daily_returns
from dashboard_common import get_data, sidebar_dates
from metrics import distribution_table, performance_table

st.set_page_config(page_title="Stock Deep Dive", layout="wide")
st.title("Stock Deep Dive")

adj_close = get_data()

# ===== 侧边栏：选一只股票 + 日期 =====
st.sidebar.header("Filters")
tickers = [t for t in adj_close.columns if t != "SPY"]  # SPY 是比较基准，不作为可选个股
ticker = st.sidebar.selectbox("Ticker", tickers, index=tickers.index("NVDA"))
start, end = sidebar_dates(adj_close)

price = adj_close.loc[start:end, ticker].dropna()
returns = daily_returns(adj_close.loc[start:end])

# 数据不到 3 年时提醒：把很短时间的涨幅年化，会被放大得很夸张
if len(price) < 3 * 252:
    st.warning(f"{ticker} has only {len(price) / 252:.1f} years of data in this range. "
               "Annualized figures are extrapolated from a short period and can be misleading.")

# ===== 顶部四个关键数字 =====
perf = performance_table(adj_close.loc[start:end, [ticker]]).iloc[0]
beta = beta_regression(returns, ticker)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Annual Return", f"{perf['annual_return']:.1%}")
col2.metric("Annual Volatility", f"{perf['annual_volatility']:.1%}")
col3.metric("Max Drawdown", f"{perf['max_drawdown']:.1%}")
col4.metric("Beta vs SPY", f"{beta['beta']:.2f}", help=f"R² = {beta['r_squared']:.2f}")

# ===== 价格与 50/200 日均线 =====
st.subheader("Price with 50 / 200-day Moving Averages")
lines = pd.DataFrame({
    "Price": price,
    "50-day MA": price.rolling(50).mean(),
    "200-day MA": price.rolling(200).mean(),
})
st.line_chart(lines)

# ===== 回撤曲线：每天离历史最高点跌了多少 =====
st.subheader("Drawdown")
drawdown = price / price.cummax() - 1
st.area_chart(drawdown)

# ===== 收益率分布 =====
st.subheader("Daily Return Distribution vs Normal")
r = price.pct_change().dropna()
fig, ax = plt.subplots(figsize=(10, 4))
ax.hist(r, bins=100, density=True, color="#2a78d6", alpha=0.8, label="Actual daily returns")
x = np.linspace(r.min(), r.max(), 500)
ax.plot(x, stats.norm.pdf(x, r.mean(), r.std()), color="#eb6834", linewidth=2, label="Normal distribution")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
ax.legend(frameon=False)
ax.spines[["top", "right"]].set_visible(False)
st.pyplot(fig)  # 把 matplotlib 的图放进网页
plt.close(fig)  # 关掉图，避免每次刷新都多占一份内存

dist = distribution_table(adj_close.loc[start:end, [ticker]]).iloc[0]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Skewness", f"{dist['skew']:.2f}")
col2.metric("Excess Kurtosis", f"{dist['excess_kurtosis']:.2f}", help="0 for a normal distribution")
col3.metric("95% VaR (historical)", f"{dist['var_95_hist']:.2%}")
col4.metric("99% VaR (historical)", f"{dist['var_99_hist']:.2%}",
            help=f"Normal assumption gives {dist['var_99_normal']:.2%}")
