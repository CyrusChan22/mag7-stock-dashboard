# 分析图表：把前面算好的指标画成图，存进 figures/ 文件夹
# 试运行方法（在项目文件夹里）：python src/charts.py
import os

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from scipy import stats

from backtest import ma_crossover, equal_weight_monthly
from correlation_beta import MAG7, daily_returns, correlation_matrix, rolling_correlation, beta_regression
from data_loader import load_prices, get_adj_close

# 中文字体：Mac 自带的 Arial Unicode MS，不设的话中文会显示成方框
plt.rcParams["font.family"] = "Arial Unicode MS"
# 这个字体里没有数学负号，关掉后坐标轴的负数用普通减号显示
plt.rcParams["axes.unicode_minus"] = False
# 字号：默认 10 太小，统一放大
plt.rcParams["font.size"] = 13          # 坐标轴刻度、图例等
plt.rcParams["axes.titlesize"] = 15     # 每张小图的标题
plt.rcParams["figure.titlesize"] = 17   # 整张图的大标题

FIG_DIR = "figures"   # 图片保存的文件夹
BLUE = "#2a78d6"      # 主色：柱子、主线
ORANGE = "#eb6834"    # 对比色：正态曲线等参照线
# 热力图配色：同一种蓝从浅到深，相关性越高颜色越深
BLUES = LinearSegmentedColormap.from_list("blues", ["#f0efec", "#86b6ef", "#2a78d6", "#0d366b"])


def save(fig, filename):
    """把图存进 figures/ 文件夹，并关掉图，释放内存"""
    os.makedirs(FIG_DIR, exist_ok=True)  # 文件夹不存在就新建
    path = os.path.join(FIG_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("已保存：", path)


def plot_return_histogram(adj_close, ticker):
    """日收益率直方图 + 同均值同标准差的正态分布曲线"""
    returns = adj_close[ticker].dropna().pct_change().dropna()

    # 正态曲线：用这只股票自己的均值和标准差
    x = np.linspace(returns.min(), returns.max(), 500)
    y = stats.norm.pdf(x, returns.mean(), returns.std())

    # 左右两张小图：左边看全貌，右边把左尾（大跌的日子）放大
    fig, (ax_all, ax_tail) = plt.subplots(1, 2, figsize=(14, 5.5))
    tail_end = returns.mean() - 2 * returns.std()  # 比平均低 2 个标准差以下，算“大跌”
    for ax in [ax_all, ax_tail]:
        # density=True：柱子高度换算成“概率密度”，才能和正态曲线画在同一个刻度上
        ax.hist(returns, bins=100, density=True, color=BLUE, alpha=0.8, label="实际日收益率")
        ax.plot(x, y, color=ORANGE, linewidth=2, label="正态分布")
        ax.set_xlabel("日收益率")
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))  # 横轴显示成百分比
        ax.spines[["top", "right"]].set_visible(False)  # 去掉上边框和右边框，图更干净

    ax_all.set_title("全貌")
    ax_all.set_ylabel("概率密度")
    ax_all.legend(frameon=False, loc="upper left")

    # 右图只看左尾：横轴截到“大跌”区间，纵轴截到很小，才看得见矮柱子
    ax_tail.set_xlim(returns.min(), tail_end)
    ax_tail.set_ylim(0, stats.norm.pdf(tail_end, returns.mean(), returns.std()) * 1.5)
    ax_tail.set_title("左尾放大：大跌的日子比正态分布多")

    fig.suptitle(f"{ticker} 日收益率分布 vs 正态分布（超额峰度 {returns.kurt():.1f}）")
    save(fig, f"hist_{ticker}.png")


def plot_correlation_heatmap(returns, tickers):
    """相关系数热力图：每个格子是两只股票日收益率的相关系数，格子里写上数字"""
    corr = correlation_matrix(returns, tickers)

    fig, ax = plt.subplots(figsize=(9, 7.5))
    # imshow 把一个表格画成一格一格的颜色；vmin、vmax 固定颜色对应 0 到 1
    image = ax.imshow(corr, cmap=BLUES, vmin=0, vmax=1)

    # 横轴、纵轴都标上股票代码
    ax.set_xticks(range(len(tickers)))
    ax.set_xticklabels(tickers)
    ax.set_yticks(range(len(tickers)))
    ax.set_yticklabels(tickers)

    # 在每个格子中间写上相关系数；深色格子用白字，浅色格子用黑字，才看得清
    for i in range(len(tickers)):
        for j in range(len(tickers)):
            value = corr.iloc[i, j]
            text_color = "white" if value > 0.6 else "black"
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", color=text_color)

    fig.colorbar(image, ax=ax, label="相关系数")  # 右边的颜色条：颜色 ↔ 数值
    ax.set_title("七巨头与 SPY 日收益率相关系数（2015–2026）")
    save(fig, "correlation_heatmap.png")


def plot_rolling_correlation(returns, ticker_a, ticker_b, window=60):
    """滚动相关折线图：每天用过去 60 个交易日算一次相关系数"""
    rolling = rolling_correlation(returns, ticker_a, ticker_b, window)
    overall = returns[ticker_a].corr(returns[ticker_b])  # 全期只算一个数，作参照线

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(rolling.index, rolling, color=BLUE, linewidth=1.5, label=f"{window} 日滚动相关")
    # axhline：画一条横线
    ax.axhline(overall, color=ORANGE, linewidth=2, linestyle="--", label=f"全期相关 {overall:.2f}")
    ax.axhline(0, color="gray", linewidth=1)  # 0 线：低于它就是负相关

    ax.set_ylim(-0.5, 1)
    ax.set_ylabel("相关系数")
    ax.set_title(f"{ticker_a} 与 {ticker_b} 的 {window} 日滚动相关")
    ax.legend(frameon=False, loc="lower left")
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, f"rolling_corr_{ticker_a}_{ticker_b}.png")


def plot_beta_scatter(returns, tickers, market="SPY"):
    """Beta 回归散点图：每个点是一天，横轴大盘收益、纵轴个股收益，再画上回归直线"""
    # sharex、sharey：几张小图用同一套刻度，才能直接比较
    fig, axes = plt.subplots(1, len(tickers), figsize=(7 * len(tickers), 6), sharex=True, sharey=True)
    for ax, ticker in zip(axes, tickers):
        data = returns[[ticker, market]].dropna()
        result = beta_regression(returns, ticker, market)

        # s 是点的大小，alpha 半透明：点很多时，重叠越多的地方颜色越深
        ax.scatter(data[market], data[ticker], s=6, alpha=0.3, color=BLUE)

        # 回归直线：y = alpha + beta × x，alpha 要换回“每天”的单位
        x = np.linspace(data[market].min(), data[market].max(), 100)
        y = result["alpha_annual"] / 252 + result["beta"] * x
        ax.plot(x, y, color=ORANGE, linewidth=2,
                label=f"Beta = {result['beta']:.2f}，R² = {result['r_squared']:.2f}")

        ax.set_title(f"{ticker} vs {market}")
        ax.set_xlabel(f"{market} 日收益率")
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        ax.legend(frameon=False, loc="upper left")
        ax.spines[["top", "right"]].set_visible(False)

    axes[0].set_ylabel("个股日收益率")
    fig.suptitle("Beta 回归：个股日收益率 vs 大盘日收益率")
    save(fig, "beta_scatter.png")


def plot_backtest_equity(adj_close):
    """两个回测的净值曲线：左边均线交叉 vs 买入持有（SPY），右边七巨头等权 vs SPY"""
    fig, (ax_ma, ax_ew) = plt.subplots(1, 2, figsize=(16, 6))

    # 左图：SPY 均线交叉 vs 买入持有
    strategy_equity, hold_equity, n_trades = ma_crossover(adj_close["SPY"].dropna())
    ax_ma.plot(hold_equity.index, hold_equity, color=BLUE, linewidth=2, label="买入持有")
    ax_ma.plot(strategy_equity.index, strategy_equity, color=ORANGE, linewidth=2,
               label=f"50/200 均线交叉（交易 {n_trades} 次）")
    ax_ma.set_title("回测 1：SPY 均线交叉 vs 买入持有")

    # 右图：七巨头等权（月度再平衡）vs SPY
    portfolio = equal_weight_monthly(adj_close, MAG7)
    spy = adj_close["SPY"].loc[portfolio.index]
    spy = spy / spy.iloc[0]  # 换算成起点 = 1 的净值
    ax_ew.plot(portfolio.index, portfolio, color=ORANGE, linewidth=2, label="七巨头等权（月度再平衡）")
    ax_ew.plot(spy.index, spy, color=BLUE, linewidth=2, label="SPY")  # SPY 两张图都用蓝色，颜色跟着标的走
    # 对数刻度：涨 1 倍的距离都一样长，36 倍和 4 倍才能放在一张图里看清
    ax_ew.set_yscale("log")
    ax_ew.set_yticks([1, 2, 5, 10, 20, 40])  # 刻度直接写成倍数，不用 10 的几次方
    ax_ew.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
    ax_ew.yaxis.set_minor_formatter(plt.NullFormatter())  # 不显示中间的小刻度文字
    ax_ew.set_title("回测 2：七巨头等权 vs SPY（对数刻度）")

    for ax in [ax_ma, ax_ew]:
        ax.set_ylabel("净值（起点 = 1）")
        ax.legend(frameon=False, loc="upper left")
        ax.spines[["top", "right"]].set_visible(False)
    save(fig, "backtest_equity.png")


# 直接运行这个文件时，把图都画出来
if __name__ == "__main__":
    adj_close = get_adj_close(load_prices())
    for ticker in ["SPY", "NVDA"]:
        plot_return_histogram(adj_close, ticker)

    returns = daily_returns(adj_close)
    plot_correlation_heatmap(returns, MAG7 + ["SPY"])
    plot_rolling_correlation(returns, "AAPL", "MSFT")
    plot_beta_scatter(returns, ["MSFT", "TSLA"])
    plot_backtest_equity(adj_close)
