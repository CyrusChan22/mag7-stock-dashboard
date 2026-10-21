# 看板第 ⑤ 页：Memory Cycle 存储芯片周期
import sys

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

sys.path.append("src")
from dashboard_common import MAG7, get_data, sidebar_dates
from memory_cycle import current_position, cycle_table, find_turning_points, risk_comparison

st.set_page_config(page_title="Memory Cycle", layout="wide")
st.title("Memory-Chip Cycle")
st.caption("Are memory-chip stocks still cyclical after the AI rally? Historical statistics only, not a forecast.")

adj_close = get_data()
MEMORY = ["MU", "WDC", "SNDK"]

# ===== 侧边栏：股票、日期、两个阈值 =====
st.sidebar.header("Filters")
ticker = st.sidebar.selectbox("Ticker", MEMORY + ["SOXX"] + MAG7, index=0)
start, end = sidebar_dates(adj_close)
# ⭐⭐ 面试重点：阈值做成滑块，可以现场演示“阈值一变，轮数和结论就会变”
up = st.sidebar.slider("Rise to confirm a trough (%)", 20, 100, 50, step=5) / 100
down = st.sidebar.slider("Fall to confirm a peak (%)", 15, 60, 30, step=1) / 100

price = adj_close.loc[start:end, ticker].dropna()
points = find_turning_points(price, up, down)
if len(points) < 2:
    st.warning("No complete swing at these thresholds in this date range. Try lower thresholds or a longer period.")
    st.stop()

cycles = cycle_table(points)
current = current_position(price, points, up, down)

# ===== 顶部四个关键数字 =====
col1, col2, col3, col4 = st.columns(4)
col1.metric("Cycles found", len(cycles))
if current["phase"] == "down":
    col2.metric("Current phase", "Falling", help=f"Since the peak on {current['since']}")
    col3.metric("Deepest fall so far", f"{current['extreme']:.0%}", help=f"On {current['extreme_date']}")
    col4.metric("Price needed to confirm a trough", f"${current['confirm_level']:,.0f}",
                help=f"Latest close: ${current['latest']:,.0f}")
else:
    col2.metric("Current phase", "Rising", help=f"Since the trough on {current['since']}")
    col3.metric("Biggest rise so far", f"{current['extreme']:.0%}", help=f"On {current['extreme_date']}")
    col4.metric("Price needed to confirm a peak", f"${current['confirm_level']:,.0f}",
                help=f"Latest close: ${current['latest']:,.0f}")

# ===== 价格 + 峰谷 =====
st.subheader("Peaks and Troughs")
fig, ax = plt.subplots(figsize=(11, 4.5))
for i in range(len(points) - 1):
    a, b = points.iloc[i], points.iloc[i + 1]
    color = "#2a78d6" if a["type"] == "trough" else "#eb6834"   # 从谷底出发 = 上涨段（蓝）
    ax.axvspan(a["date"], b["date"], color=color, alpha=0.10, linewidth=0)
ax.plot(price.index, price.values, color="#2b2b2b", linewidth=1.2)
for _, row in points.iterrows():
    color = "#2a78d6" if row["type"] == "peak" else "#eb6834"
    ax.scatter([row["date"]], [row["price"]], s=120, marker="*", color=color, edgecolor="white", zorder=5)
ax.set_yscale("log")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
ax.yaxis.set_minor_formatter(plt.NullFormatter())
ax.set_ylabel("Adjusted close (log scale)")
ax.spines[["top", "right"]].set_visible(False)
st.pyplot(fig)
plt.close(fig)
st.caption("Blue star = peak, orange star = trough. Blue shading = rising leg, orange = falling leg. "
           "A turning point is only confirmed after the price has moved far enough, so the latest leg is unfinished.")

# ===== 历次周期对比表 =====
st.subheader("Cycle by Cycle")
if cycles.empty:
    st.info("No complete trough → peak cycle at these thresholds.")
else:
    table = pd.DataFrame({
        "Trough": cycles["trough_date"],
        "Peak": cycles["peak_date"],
        "Rise (x)": (cycles["peak_price"] / cycles["trough_price"]).round(1),
        "Rise (months)": cycles["up_months"].round(1),
        "Fall after peak (%)": (cycles["down_return"] * 100).round(0),
        "Fall (months)": cycles["down_months"].round(1),
    })
    st.dataframe(table, width="stretch")
    done = cycles["down_return"].dropna()
    if current["phase"] == "down" and len(done) > 0:
        st.write(f"The current fall is **{current['extreme']:.0%}** so far. "
                 f"Completed falls in this range: **{done.min():.0%}** to **{done.max():.0%}**. "
                 "Empty cells mean the fall after that peak has not ended yet.")

# ===== 风险对比：存储股 vs 七巨头 vs 大盘 =====
st.subheader("Risk: Memory Stocks vs Mag 7 vs Market")
risk = risk_comparison(adj_close.loc[start:end], MEMORY + ["SOXX"] + MAG7 + ["SPY"])
risk_show = pd.DataFrame({
    "Data from": risk["start"],
    "Annual Volatility (%)": (risk["annual_volatility"] * 100).round(1),
    "Max Drawdown (%)": (risk["max_drawdown"] * 100).round(1),
    "Beta vs SPY": risk["beta"].round(2),
    "R²": risk["r_squared"].round(2),
})
st.dataframe(risk_show, width="stretch")
st.caption("R² = share of daily moves explained by SPY. SNDK has traded only since Feb 2025, so its figures rest on a short sample.")

st.info("Limitations: only a handful of cycles, and results depend on the thresholds (try moving the sliders). "
        "Turning points are known only after the fact, so this describes history and is not a trading signal.")
