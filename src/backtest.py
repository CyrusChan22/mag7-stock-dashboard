# 回测：① 均线交叉策略 vs 买入持有 ② 七巨头等权组合（月度再平衡）vs SPY
# 试运行方法（在项目文件夹里）：python src/backtest.py
import pandas as pd

from data_loader import load_prices, get_adj_close
from metrics import annual_return, annual_volatility, max_drawdown, sharpe_ratio

FEE = 0.001  # 手续费 + 滑点假设：每买卖一次收成交金额的 0.1%
MAG7 = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]


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


def ma_crossover(price, short=50, long=200):
    """均线交叉：短均线在长均线上方就持有，下方就空仓（拿现金）
    返回 (策略净值, 买入持有净值, 交易次数)，两条净值都从长均线有数据的第一天开始、起点为 1"""
    ma_short = price.rolling(short).mean()
    ma_long = price.rolling(long).mean()

    # 信号：1 = 持有，0 = 空仓
    signal = (ma_short > ma_long).astype(int)
    # 防止前视偏差：今天收盘才知道信号，所以只能从明天开始按信号持仓
    position = signal.shift(1)

    daily_ret = price.pct_change()
    # 持仓变化的那天（0→1 买入、1→0 卖出）扣一次手续费
    trades = position.diff().abs()
    strategy_ret = position * daily_ret - trades * FEE

    # 从长均线第一次有值的第二天开始比较，两种方法起点相同才公平
    start = ma_long.first_valid_index()
    strategy_ret = strategy_ret.loc[start:].iloc[1:]
    hold_ret = daily_ret.loc[start:].iloc[1:]

    strategy_equity = (1 + strategy_ret).cumprod()  # 每天的收益连乘，得到净值曲线
    hold_equity = (1 + hold_ret).cumprod()
    n_trades = int(trades.loc[strategy_ret.index].sum())
    return strategy_equity, hold_equity, n_trades


def equal_weight_monthly(adj_close, tickers):
    """等权组合：每月第一个交易日把总资金平均分给每只股票，月内让持仓随涨跌自然变化"""
    returns = adj_close[tickers].pct_change().dropna()

    holdings = pd.Series(1 / len(tickers), index=tickers)  # 第一天：总资金 1，平均分
    values = []
    last_month = returns.index[0].month
    for date, day_ret in returns.iterrows():
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
