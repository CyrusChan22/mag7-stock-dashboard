# 表现指标与收益率分布：输入复权收盘价宽表，输出每只股票一行的指标表
# 试运行方法（在项目文件夹里）：python src/metrics.py
import numpy as np
import pandas as pd

from data_loader import load_prices, get_adj_close

TRADING_DAYS = 252  # 一年大约 252 个交易日，用来把日数据换算成年
RISK_FREE = 0.02    # 无风险利率假设 2%（2015 年至今美国短期国债的大致平均水平）


def cumulative_return(price):
    """累计收益：最后一天 / 第一天 - 1"""
    return price.iloc[-1] / price.iloc[0] - 1


# ⭐⭐ 面试重点：为什么开方不直接除（利滚利）；为什么 len-1（5 个价格只有 4 段）
def annual_return(price):
    """年化收益（复合年增长率）：把累计收益换算成“平均每年涨多少”"""
    years = (len(price) - 1) / TRADING_DAYS
    return (1 + cumulative_return(price)) ** (1 / years) - 1


# ⭐⭐⭐ 面试必背：为什么乘 √252 —— 每天独立时方差相加，一年方差 = 252 × 日方差，开根号得 √252
def annual_volatility(returns):
    """年化波动率：日收益率的标准差 × √252"""
    return returns.std() * np.sqrt(TRADING_DAYS)


# ⭐⭐⭐ 面试必背：cummax 只用截至当天的最高价，不看未来；最高点必须在最低点之前
def max_drawdown(price):
    """最大回撤：从之前的最高点算起，最多跌了百分之多少"""
    running_max = price.cummax()            # 截至每一天的历史最高价
    drawdown = price / running_max - 1      # 每一天离历史最高点跌了多少
    return drawdown.min()


# ⭐⭐⭐ 面试必背：超额收益 ÷ 波动率；局限：把上涨也当风险、假设正态、对时间段敏感
def sharpe_ratio(price, returns):
    """夏普比率：（年化收益 - 无风险利率）/ 年化波动率，即每承担一份风险换来多少超额收益"""
    return (annual_return(price) - RISK_FREE) / annual_volatility(returns)


def performance_table(adj_close):
    """表现指标表：每只股票一行"""
    rows = []
    for ticker in adj_close.columns:
        # ⭐⭐ 面试重点：为什么每只股票单独 dropna（整表 dropna 会让所有股票只剩 SNDK 上市后的数据）
        # 逐只股票去掉空值：SNDK 上市前是 NaN，不能整表 dropna
        price = adj_close[ticker].dropna()
        returns = price.pct_change().dropna()  # 第一天没有前一天价格，是 NaN
        rows.append({
            "ticker": ticker,
            "start": price.index[0].date(),
            "cumulative_return": cumulative_return(price),
            "annual_return": annual_return(price),
            "annual_volatility": annual_volatility(returns),
            "max_drawdown": max_drawdown(price),
            "sharpe": sharpe_ratio(price, returns),
        })
    return pd.DataFrame(rows).set_index("ticker")


def distribution_table(adj_close):
    """收益率分布表：偏度、峰度、VaR（历史法 vs 正态假设）"""
    rows = []
    for ticker in adj_close.columns:
        returns = adj_close[ticker].dropna().pct_change().dropna()
        rows.append({
            "ticker": ticker,
            "mean": returns.mean(),
            "std": returns.std(),
            "skew": returns.skew(),
            # ⭐⭐⭐ 面试必背：超额峰度 > 0 = 肥尾，极端涨跌比正态预测的多
            "excess_kurtosis": returns.kurt(),  # pandas 的 kurt 已经减了 3，正态分布 = 0
            # ⭐⭐⭐ 面试必背：历史 VaR vs 正态 VaR —— 99% 处历史法更差，证明正态假设低估极端亏损
            # 历史 VaR：把真实日收益从小到大排，取第 5% 的那个值
            "var_95_hist": returns.quantile(0.05),
            # 正态 VaR：假设收益是正态分布，均值 - 1.645 × 标准差
            "var_95_normal": returns.mean() - 1.645 * returns.std(),
            # 99% 再算一组：越往尾部，真实亏损比正态假设越大（肥尾）
            "var_99_hist": returns.quantile(0.01),
            "var_99_normal": returns.mean() - 2.326 * returns.std(),
        })
    return pd.DataFrame(rows).set_index("ticker")


# 直接运行这个文件时，打印两张表
if __name__ == "__main__":
    adj_close = get_adj_close(load_prices())
    pd.set_option("display.width", 150)
    pd.set_option("display.max_columns", None)  # 列都显示出来，不用省略号

    print("=== 表现指标 ===")
    print(performance_table(adj_close).round(3))

    print("\n=== 收益率分布 ===")
    print(distribution_table(adj_close).round(4))
