# 分析图表：把前面算好的指标画成图，存进 figures/ 文件夹
# 试运行方法（在项目文件夹里）：python src/charts.py
import logging
import os

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from scipy import stats

from backtest import ma_crossover, equal_weight_monthly
from correlation_beta import MAG7, daily_returns, correlation_matrix, rolling_correlation, beta_regression
from data_loader import load_prices, get_adj_close
from memory_cycle import find_turning_points, cycle_table, current_position, risk_comparison

# 中文字体：按顺序找，Mac 用 Arial Unicode MS，Windows 用微软雅黑，Linux 用 Noto；都没有中文会显示成方框
plt.rcParams["font.family"] = ["Arial Unicode MS", "Microsoft YaHei", "Noto Sans CJK SC"]
# 备选字体在本机找不到时 matplotlib 会刷屏警告（不影响出图），把这类提示关掉
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
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


# ⭐⭐⭐ 面试必背：这张图证明收益率是肥尾——左尾真实柱子明显高于正态曲线（SPY 跌超 5% 实际 6 天，正态只预期 0.007 天）
def plot_return_histogram(adj_close, ticker):
    """日收益率直方图 + 同均值同标准差的正态分布曲线"""
    returns = adj_close[ticker].dropna().pct_change().dropna()

    # ⭐⭐ 面试重点：正态曲线用这只股票自己的均值和标准差 —— 中心和宽度对齐后，差别只剩“形状”
    # 正态曲线：用这只股票自己的均值和标准差
    x = np.linspace(returns.min(), returns.max(), 500)
    y = stats.norm.pdf(x, returns.mean(), returns.std())

    # 左右两张小图：左边看全貌，右边把左尾（大跌的日子）放大
    fig, (ax_all, ax_tail) = plt.subplots(1, 2, figsize=(14, 5.5))
    tail_end = returns.mean() - 2 * returns.std()  # 比平均低 2 个标准差以下，算“大跌”
    for ax in [ax_all, ax_tail]:
        # ⭐⭐ 面试重点：density=True 让柱子和正态曲线用同一个纵轴刻度（概率密度），才能叠在一起比
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
    # ⭐⭐ 面试重点：vmin=0、vmax=1 固定“颜色尺”，颜色深浅才能直接对应相关系数大小
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
    # ⭐⭐ 面试重点：散点图里 Beta = 直线斜率，R² = 点贴着直线的紧密程度；两张图同刻度才能直接比 MSFT 和 TSLA
    # sharex、sharey：几张小图用同一套刻度，才能直接比较
    fig, axes = plt.subplots(1, len(tickers), figsize=(7 * len(tickers), 6), sharex=True, sharey=True)
    for ax, ticker in zip(axes, tickers):
        data = returns[[ticker, market]].dropna()
        result = beta_regression(returns, ticker, market)

        # s 是点的大小，alpha 半透明：点很多时，重叠越多的地方颜色越深
        ax.scatter(data[market], data[ticker], s=6, alpha=0.3, color=BLUE)

        # ⭐ 了解：alpha_annual 是年化的，画日收益的直线要除以 252 换回“每天”
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
    # ⭐⭐ 面试重点：对数刻度 —— 纵轴上“翻一倍”的距离都一样长，36 倍和 4 倍才能放在一张图里看清
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


def plot_turning_points(price, points, ticker="MU"):
    """价格走势 + 阈值法找到的峰顶、谷底；相邻两点之间涂底色（上涨蓝、下跌橙）"""
    fig, ax = plt.subplots(figsize=(13, 6))
    for i in range(len(points) - 1):
        a, b = points.iloc[i], points.iloc[i + 1]
        color = BLUE if a["type"] == "trough" else ORANGE   # 从谷底出发 = 上涨段
        ax.axvspan(a["date"], b["date"], color=color, alpha=0.10, linewidth=0)
    ax.plot(price.index, price.values, color="#2b2b2b", linewidth=1.2)
    for _, row in points.iterrows():
        is_peak = row["type"] == "peak"
        color = BLUE if is_peak else ORANGE
        ax.scatter([row["date"]], [row["price"]], s=150, marker="*", color=color, edgecolor="white", zorder=5)
        ax.annotate(f"{row['price']:.0f}", (row["date"], row["price"]), xytext=(0, 10 if is_peak else -18),
                    textcoords="offset points", ha="center", fontsize=11, color=color)
    # 价格从 9 美元涨到 1200 美元，用对数刻度才能看清早期的周期
    ax.set_yscale("log")
    ax.set_yticks([10, 30, 100, 300, 1000])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_minor_formatter(plt.NullFormatter())
    ax.set_ylabel("复权收盘价（美元，对数刻度）")
    ax.set_title(f"{ticker} 的峰顶（蓝星）与谷底（橙星）：浅蓝底 = 上涨段，浅橙底 = 下跌段")
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, f"cycle_turning_points_{ticker}.png")


# ⭐⭐ 面试重点：当前这轮的下跌还没结束，用“至今最深”放进历史下跌里比，空心柱表示未完成
def plot_cycle_rounds(cycles, current, ticker="MU"):
    """左：每轮上涨了几倍；右：每轮之后跌了多少，最后加上当前这轮“至今最深”"""
    fig, (ax_up, ax_down) = plt.subplots(1, 2, figsize=(14, 5.5))
    labels = [f"第{i}轮\n{row.trough_date:%Y-%m}" for i, row in cycles.iterrows()]

    # 左图：涨幅用“峰顶是谷底的几倍”表示，比百分比好读
    multiples = cycles["peak_price"] / cycles["trough_price"]
    bars = ax_up.bar(labels, multiples, color=BLUE)
    for bar, m, months in zip(bars, multiples, cycles["up_months"]):
        ax_up.text(bar.get_x() + bar.get_width() / 2, m, f"{m:.1f} 倍\n{months:.0f} 个月",
                   ha="center", va="bottom", fontsize=11)
    ax_up.set_ylim(0, multiples.max() * 1.25)
    ax_up.set_ylabel("峰顶 ÷ 谷底（倍）")
    ax_up.set_title("每轮上涨：涨了几倍、用了多久")

    # 右图：已结束的轮次实心柱；当前这轮空心柱（还没结束）
    done = cycles.dropna(subset=["down_return"])
    down_labels = [f"第{i}轮" for i in done.index] + ["当前\n(至今最深)"]
    values = list(done["down_return"]) + [current["extreme"]]
    bars = ax_down.bar(down_labels, values, color=[ORANGE] * len(done) + ["white"],
                       edgecolor=[ORANGE] * len(done) + [ORANGE], linewidth=2, hatch=[""] * len(done) + ["//"])
    months_list = list(done["down_months"]) + [current["months"]]
    for bar, v, months in zip(bars, values, months_list):
        ax_down.text(bar.get_x() + bar.get_width() / 2, v, f"{v:.0%}\n{months:.1f} 个月",
                     ha="center", va="top", fontsize=11)
    ax_down.axhline(current["change_now"], color="#8a8a85", linestyle="--", linewidth=1.5,
                    label=f"今天离峰顶 {current['change_now']:.0%}")
    ax_down.set_ylim(min(values) * 1.35, 0)
    ax_down.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax_down.set_ylabel("峰顶到下一个谷底的跌幅")
    ax_down.set_title("每轮之后：跌了多少、用了多久")
    ax_down.legend(frameon=False, loc="lower left")

    for ax in [ax_up, ax_down]:
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"{ticker} 历次周期对比（阈值：涨 50% / 跌 30%）")
    save(fig, f"cycle_rounds_{ticker}.png")


def plot_risk_comparison(table, memory, mag7):
    """散点图：横轴年化波动率、纵轴最大回撤；存储股橙色、七巨头蓝色、大盘灰色"""
    fig, ax = plt.subplots(figsize=(10, 7))
    groups = [(memory, ORANGE, "存储股"), (mag7, BLUE, "七巨头"), (["SPY", "SOXX"], "#8a8a85", "大盘 / 半导体 ETF")]
    for tickers, color, name in groups:
        sub = table.loc[tickers]
        ax.scatter(sub["annual_volatility"], sub["max_drawdown"], s=110, color=color, label=name,
                   edgecolor="white", zorder=3)
        for ticker, row in sub.iterrows():
            ax.annotate(f"{ticker}  β={row['beta']:.2f}", (row["annual_volatility"], row["max_drawdown"]),
                        xytext=(8, -4), textcoords="offset points", fontsize=11)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlabel("年化波动率（越往右越颠簸）")
    ax.set_ylabel("最大回撤（越往下跌得越深）")
    ax.set_title("风险对比：2015 年至今（SNDK 从 2025-02 上市起算）")
    ax.legend(frameon=False, loc="upper right")
    ax.grid(color="#e6e6e3", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "risk_comparison.png")


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

    # 存储芯片周期
    mu = adj_close["MU"].dropna()
    points = find_turning_points(mu)
    plot_turning_points(mu, points, "MU")
    plot_cycle_rounds(cycle_table(points), current_position(mu, points), "MU")
    memory = ["MU", "WDC", "SNDK"]
    plot_risk_comparison(risk_comparison(adj_close, memory + MAG7 + ["SOXX", "SPY"]), memory, MAG7)
