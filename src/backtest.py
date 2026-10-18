# 回测：① 均线交叉策略 vs 买入持有 ② 七巨头等权组合（月度再平衡）vs SPY
# 试运行方法（在项目文件夹里）：python src/backtest.py
import pandas as pd

from data_loader import load_prices, get_adj_close
from metrics import annual_return, annual_volatility, max_drawdown, sharpe_ratio

# ⭐ 了解：手续费 + 滑点统一假设 0.1%，回测不计成本会高估策略
FEE = 0.001  # 手续费 + 滑点假设：每买卖一次收成交金额的 0.1%
MAG7 = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]


# ⭐ 了解：净值曲线和价格一样是“按日期排的 Series”，所以 metrics.py 的函数可以直接复用
def summarize(name, equity):
    """把一条净值曲线（起点 = 1）算成一行指标，直接复用 metrics.py 的函数"""
    returns = equity.pct_change().dropna()
    return {
        "strategy": name,
        "final_value": equity.iloc[-1],
        "annual_return": annual_return(equity),
        "annual_volatility": annual_volatility(returns),
        "max_drawdown": max_drawdown(equity),
        "sharpe": sharpe_ratio(equity, returns),
    }


# ⭐⭐⭐ 面试必背：结论——9 个标的的均线策略年化收益全部输给买入持有（晚买晚卖，牛市里错过涨幅）；价值是躲开长熊市、多数标的回撤变小（META −77%→−38%），但 AAPL 反而更深、SPY 一样（2020 年快速暴跌躲不开）
def ma_crossover(price, short=50, long=200):
    """均线交叉：短均线在长均线上方就持有，下方就空仓（拿现金）
    返回 (策略净值, 买入持有净值, 交易次数)，两条净值都从长均线有数据的第一天开始、起点为 1"""
    ma_short = price.rolling(short).mean()
    ma_long = price.rolling(long).mean()

    # ⭐⭐ 面试重点：50 日均线上穿 200 日 = 金叉（买），下穿 = 死叉（卖）；50/200 是业界经典参数，没调参，避免过拟合
    # 信号：1 = 持有，0 = 空仓
    signal = (ma_short > ma_long).astype(int)
    # ⭐⭐⭐ 面试必背：shift(1) 防前视偏差——今天收盘才算出信号，明天才能按它持仓；去掉 shift 回测结果会虚高
    # 防止前视偏差：今天收盘才知道信号，所以只能从明天开始按信号持仓
    position = signal.shift(1)

    daily_ret = price.pct_change()
    # ⭐⭐ 面试重点：trades = 持仓变化（0→1 或 1→0）那天记 1，当天扣 0.1%
    # 持仓变化的那天（0→1 买入、1→0 卖出）扣一次手续费
    trades = position.diff().abs()
    strategy_ret = position * daily_ret - trades * FEE

    # ⭐⭐ 面试重点：起点对齐——前 199 天 200 日均线还算不出来，策略被迫空仓，从第一天比不公平
    # 从长均线第一次有值的第二天开始比较，两种方法起点相同才公平
    start = ma_long.first_valid_index()
    strategy_ret = strategy_ret.loc[start:].iloc[1:]
    hold_ret = daily_ret.loc[start:].iloc[1:]

    # ⭐⭐ 面试重点：净值 = (1 + 每天收益) 连乘；+50% 再 −50% 净值是 0.75，不是 1
    strategy_equity = (1 + strategy_ret).cumprod()  # 每天的收益连乘，得到净值曲线
    hold_equity = (1 + hold_ret).cumprod()
    n_trades = int(trades.loc[strategy_ret.index].sum())
    return strategy_equity, hold_equity, n_trades


# ⭐⭐⭐ 面试必背：七巨头 36 倍 vs SPY 4.7 倍有幸存者（选择）偏差——七只是站在 2026 年事后挑出的赢家，不能说明“买七巨头能跑赢大盘”
def equal_weight_monthly(adj_close, tickers):
    """等权组合：每月第一个交易日把总资金平均分给每只股票，月内让持仓随涨跌自然变化"""
    returns = adj_close[tickers].pct_change().dropna()

    holdings = pd.Series(1 / len(tickers), index=tickers)  # 第一天：总资金 1，平均分
    values = []
    last_month = returns.index[0].month
    for date, day_ret in returns.iterrows():
        # ⭐⭐ 面试重点：月度再平衡 = 卖掉涨多的、买入涨少的，让每只回到 1/7，控制单只权重
        # 换月了：先把总资金重新平均分配（再平衡），按调整的金额扣手续费
        if date.month != last_month:
            total = holdings.sum()
            target = pd.Series(total / len(tickers), index=tickers)
            fee = (target - holdings).abs().sum() * FEE
            holdings = target * (1 - fee / total)
            last_month = date.month
        # 当天每只股票的持仓金额按各自涨跌变化
        holdings = holdings * (1 + day_ret)
        values.append(holdings.sum())

    return pd.Series(values, index=returns.index)


# 直接运行这个文件时，打印两个回测结果
if __name__ == "__main__":
    adj_close = get_adj_close(load_prices())
    pd.set_option("display.width", 150)
    pd.set_option("display.max_columns", None)

    print("=== 回测 1：50/200 日均线交叉 vs 买入持有（手续费 0.1%）===")
    rows = []
    for ticker in ["SPY", "QQQ"] + MAG7:
        price = adj_close[ticker].dropna()
        strategy_equity, hold_equity, n_trades = ma_crossover(price)
        row_ma = summarize(f"{ticker} MA 50/200", strategy_equity)
        row_ma["trades"] = n_trades
        rows.append(row_ma)
        rows.append(summarize(f"{ticker} buy & hold", hold_equity))
    print(pd.DataFrame(rows).set_index("strategy").round(3))

    print("\n=== 回测 2：七巨头等权（月度再平衡）vs SPY ===")
    portfolio = equal_weight_monthly(adj_close, MAG7)
    spy = adj_close["SPY"].loc[portfolio.index]
    spy = spy / spy.iloc[0]  # SPY 也换算成起点 = 1 的净值
    rows = [summarize("Mag7 equal weight", portfolio), summarize("SPY", spy)]
    print(pd.DataFrame(rows).set_index("strategy").round(3))
