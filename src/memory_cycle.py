# 存储芯片周期分析：用阈值法找出 MU 等股票历史上的峰顶和谷底
# 只做历史统计，不做预测
# 试运行方法（在项目文件夹里）：python src/memory_cycle.py
import pandas as pd

from correlation_beta import MAG7, daily_returns, beta_table
from data_loader import load_prices, get_adj_close
from metrics import performance_table

UP = 0.50    # 从低点涨超 50%，确认那个低点是谷底
DOWN = 0.30  # 从高点跌超 30%，确认那个高点是峰顶


# ⭐⭐⭐ 面试必背：转折点只能事后确认（涨够/跌够才回头确认），所以只能描述历史，不能当交易信号
# ⭐⭐ 面试重点：两个状态交替——上行期只盯最高点，下行期只盯最低点，所以峰谷一定交替出现
def find_turning_points(price, up=UP, down=DOWN):
    """阈值法找峰顶和谷底，返回表：每行一个转折点（日期、价格、类型 peak/trough）"""
    state = None                # 当前状态：None = 刚开始还没定，"up" = 上行期，"down" = 下行期
    high = price.iloc[0]        # 目前盯着的最高价
    high_date = price.index[0]
    low = price.iloc[0]         # 目前盯着的最低价
    low_date = price.index[0]
    points = []                 # 确认出来的转折点，一个一个往里加

    for date, p in price.items():
        # 每天先更新最高价、最低价
        if p > high:
            high = p
            high_date = date
        if p < low:
            low = p
            low_date = date

        # 不在上行期，且从最低点涨超 up → 确认最低点是谷底，进入上行期
        if state != "up" and p >= low * (1 + up):
            points.append({"date": low_date, "price": low, "type": "trough"})
            state = "up"
            high = p            # 进入上行期，从今天起重新盯最高价
            high_date = date
        # 不在下行期，且从最高点跌超 down → 确认最高点是峰顶，进入下行期
        elif state != "down" and p <= high * (1 - down):
            points.append({"date": high_date, "price": high, "type": "peak"})
            state = "down"
            low = p             # 进入下行期，从今天起重新盯最低价
            low_date = date

    return pd.DataFrame(points)


# ⭐⭐ 面试重点：一轮 = 谷底 → 峰顶 → 下一个谷底；峰顶后的最大回撤就是峰顶到下一个谷底的跌幅（下跌期 low 一直记着最低价）
def cycle_table(points):
    """把转折点整理成每轮一行：上涨时长、涨幅，之后的下跌时长、跌幅
    最后一轮如果还没出现下一个谷底，下跌两列留空（NaN），表示进行中"""
    rows = []
    for i in range(len(points)):
        # 每一轮从谷底开始；开头那个“峰顶”前面没有谷底，凑不成一轮，自动跳过
        if points["type"].iloc[i] != "trough":
            continue
        # 谷底后面还没有峰顶（还在上涨里），这一轮没法算，结束
        if i + 1 >= len(points):
            break

        trough = points.iloc[i]      # 这一轮的谷底
        peak = points.iloc[i + 1]    # 紧接着的峰顶（峰谷一定交替，所以下一行就是峰顶）
        row = {
            "trough_date": trough["date"].date(),
            "trough_price": trough["price"],
            "peak_date": peak["date"].date(),
            "peak_price": peak["price"],
            "up_months": (peak["date"] - trough["date"]).days / 30.44,  # 日历天数换算成月（一个月平均 30.44 天）
            "up_return": peak["price"] / trough["price"] - 1,
            "down_months": None,     # 先留空，有下一个谷底再填
            "down_return": None,
        }
        # 峰顶后面还有谷底 → 这一轮的下跌已经结束，可以算
        if i + 2 < len(points):
            next_trough = points.iloc[i + 2]
            row["down_months"] = (next_trough["date"] - peak["date"]).days / 30.44
            row["down_return"] = next_trough["price"] / peak["price"] - 1
        rows.append(row)

    table = pd.DataFrame(rows)
    table.index = range(1, len(table) + 1)   # 行号从 1 开始，就是第几轮
    table.index.name = "cycle"
    return table


# ⭐⭐⭐ 面试必背：当前这轮还没结束（下一个转折点没确认），只能说“到目前为止”跌/涨了多少，放进历史里比，不预测
def current_position(price, points, up=UP, down=DOWN):
    """当前这轮的位置：最后一个转折点之后，到今天为止的情况"""
    last = points.iloc[-1]                  # 最后一个确认的转折点
    after = price[price.index >= last["date"]]   # 从那天到今天的价格
    latest = price.iloc[-1]
    if last["type"] == "peak":
        # 最后是峰顶 → 现在在下跌期：看峰顶以来最深跌到哪、现在离峰顶多远
        deepest = after.min()
        return {
            "phase": "down",
            "since": last["date"].date(),
            "since_price": last["price"],
            "months": (price.index[-1] - last["date"]).days / 30.44,
            "latest": latest,
            "change_now": latest / last["price"] - 1,          # 今天比峰顶跌了多少
            "extreme": deepest / last["price"] - 1,            # 峰顶以来最深跌了多少
            "extreme_date": after.idxmin().date(),
            "confirm_level": deepest * (1 + up),               # 涨到这里才会确认谷底
        }
    # 最后是谷底 → 现在在上涨期：看谷底以来最高涨到哪
    highest = after.max()
    return {
        "phase": "up",
        "since": last["date"].date(),
        "since_price": last["price"],
        "months": (price.index[-1] - last["date"]).days / 30.44,
        "latest": latest,
        "change_now": latest / last["price"] - 1,
        "extreme": highest / last["price"] - 1,
        "extreme_date": after.idxmax().date(),
        "confirm_level": highest * (1 - down),                 # 跌到这里才会确认峰顶
    }


# ⭐⭐ 面试重点：复用 metrics.py 和 correlation_beta.py 的函数，波动率、回撤、Beta 都是现成的
def risk_comparison(adj_close, tickers):
    """存储股 vs 七巨头 vs 大盘：年化波动率、最大回撤、Beta（对 SPY）"""
    perf = performance_table(adj_close[tickers])
    returns = daily_returns(adj_close)
    # SPY 自己对自己回归没有意义（Beta 按定义就是 1），所以不放进回归，合并后补上
    betas = beta_table(returns, [t for t in tickers if t != "SPY"])
    table = perf[["start", "annual_volatility", "max_drawdown"]].join(betas[["beta", "r_squared"]])
    if "SPY" in table.index:
        table.loc["SPY", ["beta", "r_squared"]] = 1.0
    return table


# 直接运行这个文件时，打印 MU 的转折点和每轮统计表
if __name__ == "__main__":
    adj_close = get_adj_close(load_prices())
    mu = adj_close["MU"].dropna()

    points = find_turning_points(mu)
    print(f"MU 数据：{mu.index[0].date()} 至 {mu.index[-1].date()}，共 {len(mu)} 天")
    print(f"阈值：上涨 {UP:.0%}，下跌 {DOWN:.0%}\n")
    pd.set_option("display.width", 150)
    pd.set_option("display.max_columns", None)  # 列都显示出来，不用省略号

    print("=== 转折点 ===")
    print(points.round({"price": 2}))

    print("\n=== 每轮统计（NaN = 这一轮的下跌还在进行中）===")
    print(cycle_table(points).round(2))

    print("\n=== 当前这轮 ===")
    for key, value in current_position(mu, points).items():
        print(f"{key}: {round(value, 3) if isinstance(value, float) else value}")

    print("\n=== 风险对比（Beta 对 SPY；SNDK 2025 年才上市，样本很短）===")
    print(risk_comparison(adj_close, ["MU", "WDC", "SNDK", "SOXX"] + MAG7 + ["SPY"]).round(3))
