# 探索性脚本（10/10 第一次试用 yfinance）：下载一只股票，看看数据长什么样；正式取数见 src/fetch_data.py
import pandas as pd
import yfinance as yf

# 让 pandas 打印时把所有列显示在一行里
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)

# 创建一个股票对象，AAPL 是苹果的股票代码
aapl = yf.Ticker("AAPL")

# 下载 2015-01-01 至今的日线数据
# auto_adjust=False：同时保留原始收盘价 Close 和复权收盘价 Adj Close
df = aapl.history(start="2015-01-01", auto_adjust=False)

print("行数和列数：", df.shape)
print()
print("前 5 行：")
print(df.head())
print()
print("后 5 行：")
print(df.tail())
print()
print("每列的数据类型：")
print(df.dtypes)
print()

# 筛选出拆股的日子：Stock Splits 不为 0 的行
print("拆股的日子：")
print(df[df["Stock Splits"] > 0])
print()

# 筛选出分红的日子（除息日），只看最近 5 次
print("最近 5 次分红：")
print(df[df["Dividends"] > 0].tail())
