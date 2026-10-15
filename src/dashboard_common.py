# 看板各页面共用的部分：读数据（带缓存）、侧边栏日期筛选
import streamlit as st

from data_loader import load_prices, get_adj_close

MAG7 = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
BENCHMARKS = ["SPY", "QQQ"]


# 缓存：第一次从 MySQL 读，之后页面刷新直接用内存里的结果，不用每次都查数据库
@st.cache_data
def get_data():
    return get_adj_close(load_prices())


def sidebar_dates(adj_close):
    """侧边栏的开始、结束日期，返回字符串，方便直接用 .loc 截取"""
    start = st.sidebar.date_input("Start date", adj_close.index.min())
    end = st.sidebar.date_input("End date", adj_close.index.max())
    return str(start), str(end)
