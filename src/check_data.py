# 数据体检：检查数据库里的价格有没有缺失、不合理的值、异常的涨跌幅
# 运行方法（在项目文件夹里）：python src/check_data.py
# 只检查、只打印，不修改任何数据
from data_loader import get_adj_close, load_prices

# 单日涨跌超过这个幅度就列出来，人工核实是真实行情还是数据错误
BIG_MOVE = 0.20


def check_missing(prices):
    """检查 1：每一列有几个缺失值"""
    print("【1】缺失值个数（应该全是 0）")
    print(prices.isna().sum())


def check_price_logic(prices):
    """检查 2：价格是否符合常识"""
    print("\n【2】不合理的价格（应该都是 0 行）")

    # 价格必须大于 0
    bad = prices[(prices["low"] <= 0) | (prices["adj_close"] <= 0)]
    print("价格 <= 0：", len(bad), "行")

    # 最高价不能低于最低价
    bad = prices[prices["high"] < prices["low"]]
    print("最高价 < 最低价：", len(bad), "行")

    # 收盘价应该在当天最低价和最高价之间
    bad = prices[(prices["close"] > prices["high"]) | (prices["close"] < prices["low"])]
    print("收盘价不在最低价和最高价之间：", len(bad), "行")

    # 成交量为 0 说明当天可能停牌或数据缺失
    bad = prices[prices["volume"] == 0]
    print("成交量为 0：", len(bad), "行")


def check_big_moves(prices):
    """检查 3：单日涨跌幅过大的日子"""
    print(f"\n【3】单日涨跌超过 {BIG_MOVE:.0%} 的日子（需要人工核实）")

    adj_close = get_adj_close(prices)
    returns = adj_close.pct_change()  # 每只股票的日收益率 = 今天 / 昨天 - 1

    # 宽表转回长表：stack() 把每个格子变成一行（pandas 3 会保留 NaN 格子）
    returns = returns.stack()
    # NaN 和任何数比较都是 False，所以空格子不会被筛进来
    big = returns[returns.abs() > BIG_MOVE]
    big = big.sort_values()  # 从跌得最多排到涨得最多

    print("共", len(big), "次")
    for (date, ticker), r in big.items():
        print(f"  {date.date()}  {ticker:5s}  {r:+.1%}")


if __name__ == "__main__":
    prices = load_prices()
    print("共", len(prices), "行数据\n")
    check_missing(prices)
    check_price_logic(prices)
    check_big_moves(prices)
