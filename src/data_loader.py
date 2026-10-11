# 数据读取：从 MySQL 把价格读成 Pandas 的 DataFrame
# 之后的分析和看板都通过这里取数；以后线上版改读数据快照，也只改这个文件
# 试运行方法（在项目文件夹里）：python src/data_loader.py
import os

import pandas as pd
import pymysql
from dotenv import load_dotenv


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


def load_prices():
    """读出 daily_prices 全部数据：每只股票每天一行（长表）"""
    sql = """
        SELECT ticker, trade_date, open, high, low, close, adj_close,
               volume, dividends, stock_splits
        FROM daily_prices
        ORDER BY ticker, trade_date
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()  # 取回所有行，每行是一个元组
    conn.close()

    columns = ["ticker", "trade_date", "open", "high", "low", "close",
               "adj_close", "volume", "dividends", "stock_splits"]
    df = pd.DataFrame(rows, columns=columns)
    # MySQL 读出来的日期是 Python 的 date，转成 Pandas 的日期类型，方便按日期筛选、画图
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def get_adj_close(prices):
    """把长表转成宽表：行是日期，列是股票，值是复权收盘价"""
    wide = prices.pivot(index="trade_date", columns="ticker", values="adj_close")
    return wide


# 直接运行这个文件时，做个简单检查
if __name__ == "__main__":
    prices = load_prices()
    print("长表形状：", prices.shape)
    print(prices.dtypes)
    print(prices.head())

    adj_close = get_adj_close(prices)
    print("\n宽表形状：", adj_close.shape)
    print(adj_close.tail())
