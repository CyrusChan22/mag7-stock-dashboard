# 看板第 ④ 页：Backtest 策略回测
import sys

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

sys.path.append("src")
from backtest import FEE, equal_weight_monthly, ma_crossover, summarize
from dashboard_common import MAG7, get_data, sidebar_dates

st.set_page_config(page_title="Backtest", layout="wide")
st.title("Strategy Backtests")

adj_close = get_data()
st.sidebar.header("Filters")
start, end = sidebar_dates(adj_close)
prices = adj_close.loc[start:end]


def show_table(rows):
    """回测结果表：收益类指标换成百分比"""
    table = pd.DataFrame(rows).set_index("strategy")
    for col in ["annual_return", "annual_volatility", "max_drawdown"]:
        table[col] = table[col] * 100
    table = table.rename(columns={"final_value": "Final Value ($1 start)",
                                  "annual_return": "Annual Return (%)",
                                  "annual_volatility": "Annual Volatility (%)",
                                  "max_drawdown": "Max Drawdown (%)",
                                  "sharpe": "Sharpe Ratio"})
    st.dataframe(table.round(2), width="stretch")


# ===== 回测 1：均线交叉 vs 买入持有 =====
st.header("1. Moving-Average Crossover vs Buy & Hold")
col1, col2, col3 = st.columns(3)
ticker = col1.selectbox("Ticker", list(adj_close.columns), index=list(adj_close.columns).index("SPY"))
short = col2.number_input("Short MA (days)", 5, 100, 50)
long = col3.number_input("Long MA (days)", 50, 300, 200)

price = prices[ticker].dropna()
if short >= long:
    st.warning("The short window must be shorter than the long window.")
elif len(price) <= long + 1:
    st.warning("Not enough data in this date range for the long moving average.")
else:
    strategy_equity, hold_equity, n_trades = ma_crossover(price, short, long)
    st.line_chart(pd.DataFrame({f"MA {short}/{long} ({n_trades} trades)": strategy_equity,
                                "Buy & Hold": hold_equity}))
    show_table([summarize(f"MA {short}/{long}", strategy_equity), summarize("Buy & Hold", hold_equity)])
    st.caption(f"Signals use today's close and are applied from the next day (no look-ahead bias). "
               f"Each trade costs {FEE:.1%}. 50/200 is the standard rule; tuning the windows to "
               "fit past data risks overfitting.")

# ===== 回测 2：七巨头等权 vs SPY =====
st.header("2. Equal-Weight Mag 7 (Monthly Rebalancing) vs SPY")


@st.cache_data
def run_equal_weight(start, end):
    """等权组合逐日循环比较慢，按日期区间缓存结果"""
    return equal_weight_monthly(get_data().loc[start:end], MAG7)


portfolio = run_equal_weight(start, end)
spy = prices["SPY"].loc[portfolio.index]
spy = spy / spy.iloc[0]

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(portfolio.index, portfolio, color="#eb6834", linewidth=2, label="Mag 7 equal weight")
ax.plot(spy.index, spy, color="#2a78d6", linewidth=2, label="SPY")
ax.set_yscale("log")  # 对数刻度：翻一倍的距离都一样长
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
ax.yaxis.set_minor_formatter(plt.NullFormatter())
ax.set_ylabel("Value of $1 (log scale)")
ax.legend(frameon=False)
ax.spines[["top", "right"]].set_visible(False)
st.pyplot(fig)
plt.close(fig)

show_table([summarize("Mag 7 equal weight", portfolio), summarize("SPY", spy)])
st.warning("Survivorship / selection bias: these seven stocks were chosen in hindsight because they "
           "became the biggest winners. An investor in 2015 could not have known this list, so the "
           "result shows past performance only, not a strategy that would beat the market.")
