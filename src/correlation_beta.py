# 相关性与 Beta 回归：股票之间同涨同跌的程度，以及个股对大盘（SPY）的敏感度
# 试运行方法（在项目文件夹里）：python src/correlation_beta.py
import pandas as pd
from scipy import stats

from data_loader import load_prices, get_adj_close

TRADING_DAYS = 252
MAG7 = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]


def daily_returns(adj_close):
    """宽表的日收益率：每列一只股票"""
    return adj_close.pct_change()


# ⭐⭐⭐ 面试必背：相关系数 −1 到 1；七巨头之间普遍正相关 → 同时买七只，分散风险的效果有限（以运行结果为准）
def correlation_matrix(returns, tickers):
    """相关系数矩阵：两两之间日收益率的相关系数，-1 到 1
    pandas 的 corr 对每一对股票只用两者都有数据的日子，所以 SNDK 的 NaN 不影响其他股票"""
    return returns[tickers].corr()


# ⭐⭐ 面试重点：滚动窗口 = 每天只用过去 60 天算一次，看相关性随时间变化（危机时相关性会升高）
def rolling_correlation(returns, ticker_a, ticker_b, window=60):
    """滚动相关：每天都用“过去 60 个交易日”算一次相关系数，看相关性怎么随时间变化"""
    return returns[ticker_a].rolling(window).corr(returns[ticker_b])


# ⭐⭐⭐ 面试必背：CAPM 回归 —— Beta = 斜率（大盘涨 1% 个股涨多少），Alpha = 截距，R² = 被大盘解释的比例
def beta_regression(returns, ticker, market="SPY"):
    """CAPM 回归：个股日收益 = Alpha + Beta × 大盘日收益 + 误差"""
    # ⭐⭐ 面试重点：只保留两者都有数据的日子，回归要求 x 和 y 一一对应
    data = returns[[ticker, market]].dropna()
    result = stats.linregress(data[market], data[ticker])  # 自变量 x 是大盘，因变量 y 是个股
    return {
        "ticker": ticker,
        "beta": result.slope,                          # 斜率：大盘涨 1%，个股平均涨多少
        # ⭐⭐ 面试重点：Alpha 是日截距 × 252 换成每年；它是“大盘解释不了的收益”，事后算出来的，不代表以后还有
        "alpha_annual": result.intercept * TRADING_DAYS,  # 截距：大盘解释不了的那部分日收益，换算成每年
        "r_squared": result.rvalue ** 2,               # 个股的波动有多少比例能被大盘解释
        "days": len(data),
    }


def beta_table(returns, tickers, market="SPY"):
    """多只股票的 Beta 回归结果，每只一行"""
    rows = []
    for ticker in tickers:
        rows.append(beta_regression(returns, ticker, market))
    return pd.DataFrame(rows).set_index("ticker")


# 直接运行这个文件时，打印结果
if __name__ == "__main__":
    returns = daily_returns(get_adj_close(load_prices()))
    pd.set_option("display.width", 150)
    pd.set_option("display.max_columns", None)

    print("=== 七巨头 + SPY 相关系数矩阵 ===")
    print(correlation_matrix(returns, MAG7 + ["SPY"]).round(2))

    print("\n=== 60 日滚动相关：AAPL vs MSFT（每年最后一天）===")
    rolling = rolling_correlation(returns, "AAPL", "MSFT")
    print(rolling.groupby(rolling.index.year).last().round(2))

    print("\n=== Beta 回归（对 SPY）===")
    others = MAG7 + ["QQQ", "MU", "WDC", "SNDK", "SOXX"]
    print(beta_table(returns, others).round(3))
