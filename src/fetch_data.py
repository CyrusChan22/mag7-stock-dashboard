# 取数脚本：用 yfinance 下载 13 只股票的日线数据，写入本地 MySQL
# 运行方法（在项目文件夹里）：python src/fetch_data.py
# 可以反复运行：已有的数据会被更新，不会重复
import os

import pymysql
import yfinance as yf
from dotenv import load_dotenv

# 数据开始日期
START_DATE = "2015-01-01"

# 股票清单：代码 → (公司名, 分组)
STOCKS = {
    "AAPL": ("Apple Inc.", "mag7"),
    "MSFT": ("Microsoft Corporation", "mag7"),
    "NVDA": ("NVIDIA Corporation", "mag7"),
    "GOOGL": ("Alphabet Inc.", "mag7"),
    "AMZN": ("Amazon.com, Inc.", "mag7"),
    "META": ("Meta Platforms, Inc.", "mag7"),
    "TSLA": ("Tesla, Inc.", "mag7"),
    "MU": ("Micron Technology, Inc.", "memory"),
    "WDC": ("Western Digital Corporation", "memory"),
    "SNDK": ("Sandisk Corporation", "memory"),
    "SPY": ("SPDR S&P 500 ETF Trust", "benchmark"),
    "QQQ": ("Invesco QQQ Trust", "benchmark"),
    "SOXX": ("iShares Semiconductor ETF", "benchmark"),
}

# 正式上市日：这天之前的数据不要
# SNDK 从西部数据分拆，2025-02-13 至 02-21 是分拆前的预发行交易，成交稀少，不算正常行情
# ⭐⭐ 面试重点：SNDK 分拆前的预发行交易成交稀少、不是正常行情，所以从正式上市日 2025-02-24 开始取
LISTING_DATES = {
    "SNDK": "2025-02-24",
}

# yfinance 的列名 → 数据库里的列名
# ETF 会多一列 Capital Gains，这里没列出来，后面只挑这 8 列，它就被丢掉了
COLUMN_NAMES = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Volume": "volume",
    "Dividends": "dividends",
    "Stock Splits": "stock_splits",
}


# ⭐⭐⭐ 面试必背：数据库密码放在 .env 文件里，.gitignore 不上传，代码里不写死密码
def get_connection():
    """读取 .env 里的配置，连接 MySQL"""
    load_dotenv()
    conn = pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
    )
    return conn


# ⭐⭐ 面试重点：daily_prices 有外键指向 stocks，所以必须先写 stocks 表
def save_stocks(conn):
    """把股票清单写进 stocks 表（有外键，必须先写这张表）"""
    # ⭐⭐ 面试重点：用 %s 占位符而不是拼接字符串，防止 SQL 注入
    # %s 是占位符，pymysql 会把数据安全地填进去
    # ⭐⭐⭐ 面试必背：ON DUPLICATE KEY UPDATE —— 主键（stocks 表是 ticker；daily_prices 表是 ticker + 日期）已存在就更新、不存在就插入，所以脚本可以反复运行、不会重复
    # AS new 给这次要插入的值起个名字；主键已存在时，就用 new 里的值更新
    sql = """
        INSERT INTO stocks (ticker, name, category)
        VALUES (%s, %s, %s) AS new
        ON DUPLICATE KEY UPDATE name = new.name, category = new.category
    """
    rows = []
    for ticker, (name, category) in STOCKS.items():
        rows.append((ticker, name, category))

    cursor = conn.cursor()
    # ⭐ 了解：executemany 把整个元组列表批量发给数据库，比逐行 execute 快
    cursor.executemany(sql, rows)  # 一次执行多行
    # ⭐⭐ 面试重点：commit 之后数据才真正写进数据库（事务）
    conn.commit()  # 提交，数据才真正存进数据库
    print(f"stocks 表：写入 {len(rows)} 只股票")


def download_prices(ticker):
    """下载一只股票的日线数据，整理成和数据库一样的列名"""
    # ⭐⭐ 面试重点：auto_adjust=False 同时保留原始收盘价 close 和复权收盘价 adj_close；分析收益一律用 adj_close
    df = yf.Ticker(ticker).history(start=START_DATE, auto_adjust=False)
    df = df[list(COLUMN_NAMES.keys())]  # 只挑需要的 8 列
    df = df.rename(columns=COLUMN_NAMES)  # 改成数据库里的列名
    # 有正式上市日的股票，只保留上市日及之后的行
    if ticker in LISTING_DATES:
        df = df.loc[LISTING_DATES[ticker]:]
    return df


def save_prices(conn, ticker, df):
    """把一只股票的价格写进 daily_prices 表"""
    # ⭐⭐⭐ 面试必背：价格表也要更新旧行 —— 每次分红后，历史上所有 adj_close 都会重新调整，重跑时只插新日期的话旧数据就过时了
    sql = """
        INSERT INTO daily_prices
            (ticker, trade_date, open, high, low, close, adj_close,
             volume, dividends, stock_splits)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) AS new
        ON DUPLICATE KEY UPDATE
            open = new.open, high = new.high, low = new.low,
            close = new.close, adj_close = new.adj_close, volume = new.volume,
            dividends = new.dividends, stock_splits = new.stock_splits
    """
    rows = []
    for row in df.itertuples():
        # row.Index 是带时区的时间，.date() 只取日期部分
        # float()、int() 把 numpy 的数字类型转成 Python 自带的类型，pymysql 才认得
        rows.append((
            ticker,
            row.Index.date(),
            float(row.open),
            float(row.high),
            float(row.low),
            float(row.close),
            float(row.adj_close),
            int(row.volume),
            float(row.dividends),
            float(row.stock_splits),
        ))

    cursor = conn.cursor()
    cursor.executemany(sql, rows)
    conn.commit()


# ⭐⭐ 面试重点：整体四步 —— 连接数据库 → 先写 stocks → 逐只下载价格 → 写 daily_prices
def main():
    conn = get_connection()
    save_stocks(conn)

    for ticker in STOCKS:
        df = download_prices(ticker)
        save_prices(conn, ticker, df)
        print(f"{ticker:5s}：{len(df)} 行，{df.index[0].date()} 至 {df.index[-1].date()}")

    conn.close()
    print("全部完成")


# 直接运行这个文件时才执行 main()；被别的文件 import 时不执行
if __name__ == "__main__":
    main()
