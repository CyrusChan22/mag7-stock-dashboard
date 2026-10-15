# 看板第 ③ 页：Correlation & Beta 相关性与 Beta
import sys

import matplotlib.pyplot as plt
import streamlit as st
from matplotlib.colors import LinearSegmentedColormap

sys.path.append("src")
from correlation_beta import beta_table, correlation_matrix, daily_returns, rolling_correlation
from dashboard_common import BENCHMARKS, MAG7, get_data, sidebar_dates

st.set_page_config(page_title="Correlation & Beta", layout="wide")
st.title("Correlation & Beta")

adj_close = get_data()

st.sidebar.header("Filters")
tickers = st.sidebar.multiselect("Tickers", list(adj_close.columns), default=MAG7 + ["SPY"])
start, end = sidebar_dates(adj_close)
if len(tickers) < 2:
    st.warning("Please select at least two tickers.")
    st.stop()

returns = daily_returns(adj_close.loc[start:end])

# ===== 相关系数热力图 =====
st.subheader("Correlation of Daily Returns")
corr = correlation_matrix(returns, tickers)
blues = LinearSegmentedColormap.from_list("blues", ["#f0efec", "#86b6ef", "#2a78d6", "#0d366b"])
fig, ax = plt.subplots(figsize=(1 + 0.9 * len(tickers), 0.8 * len(tickers)))
image = ax.imshow(corr, cmap=blues, vmin=0, vmax=1)  # 颜色固定对应 0 到 1，不随数据拉伸
ax.set_xticks(range(len(tickers)))
ax.set_xticklabels(tickers, rotation=45)
ax.set_yticks(range(len(tickers)))
ax.set_yticklabels(tickers)
for i in range(len(tickers)):
    for j in range(len(tickers)):
        value = corr.iloc[i, j]
        ax.text(j, i, f"{value:.2f}", ha="center", va="center",
                color="white" if value > 0.6 else "black", fontsize=9)
fig.colorbar(image, ax=ax)
st.pyplot(fig)
plt.close(fig)
st.caption("Each cell is the correlation between two tickers' daily returns (-1 to 1).")

# ===== 滚动相关 =====
st.subheader("Rolling Correlation")
col1, col2, col3 = st.columns(3)
ticker_a = col1.selectbox("Ticker A", tickers, index=0)
ticker_b = col2.selectbox("Ticker B", tickers, index=1)
window = col3.slider("Window (trading days)", 20, 250, 60, step=10)
rolling = rolling_correlation(returns, ticker_a, ticker_b, window)
st.line_chart(rolling.rename(f"{ticker_a} vs {ticker_b}"))
st.caption(f"Full-period correlation: {returns[ticker_a].corr(returns[ticker_b]):.2f}. "
           "Correlations tend to rise during market sell-offs, when diversification is needed most.")

# ===== Beta 回归表 =====
st.subheader("CAPM Regression vs SPY")
others = [t for t in tickers if t != "SPY"]
if others:
    table = beta_table(returns, others)
    table["alpha_annual"] = table["alpha_annual"] * 100
    table = table.rename(columns={"beta": "Beta", "alpha_annual": "Alpha (annual, %)",
                                  "r_squared": "R²", "days": "Days"})
    st.dataframe(table.round(2), width="stretch")
    st.caption("Beta: how much the stock moves when SPY moves 1%. "
               "R²: share of the stock's daily variance explained by SPY.")
