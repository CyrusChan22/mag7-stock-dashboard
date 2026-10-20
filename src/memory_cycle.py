# 存储芯片周期分析：用阈值法找出 MU 等股票历史上的峰顶和谷底
# 只做历史统计，不做预测
# 试运行方法（在项目文件夹里）：python src/memory_cycle.py
import pandas as pd

from data_loader import load_prices, get_adj_close

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
