# 数据读取：把价格读成 Pandas 的 DataFrame
# 本机有 MySQL 配置（.env）就读数据库；线上版没有，就读仓库里的数据快照 data/prices.csv
# 之后的分析和看板都通过这里取数，换数据来源只改这个文件
# 试运行方法（在项目文件夹里）：python src/data_loader.py
import os

import pandas as pd
import pymysql
from dotenv import load_dotenv

# 快照文件的位置：按本文件所在位置找（src/ 的上一层就是项目文件夹），从哪个文件夹运行都能找到
SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "prices.csv")


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


def load_snapshot():
    """读数据快照（线上版用）：和数据库里的表一模一样，只是存成了 CSV"""
    df = pd.read_csv(SNAPSHOT_PATH)
    df["trade_date"] = pd.to_datetime(df["trade_date"])  # CSV 里日期是文字，转成日期类型
    return df


# ⭐⭐ 面试重点：数据层自动切换——有 .env 读 MySQL，没有（线上）读 CSV 快照；返回的表格式一样，分析和看板代码都不用改
def load_prices():
    """读出全部价格数据：每只股票每天一行（长表）"""
    load_dotenv()
    if not os.getenv("MYSQL_HOST"):   # 没有数据库配置 → 说明在线上，读快照
        return load_snapshot()

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
