# 导出数据快照：把 MySQL 里的价格数据存成 data/prices.csv，给线上版（Streamlit Cloud）用
# 线上服务器连不到本机的 MySQL，所以把数据做成一个文件放进仓库
# 运行方法（在项目文件夹里，MySQL 要开着）：python src/export_snapshot.py
import os

from data_loader import SNAPSHOT_PATH, load_prices

if __name__ == "__main__":
    prices = load_prices()
    prices.to_csv(SNAPSHOT_PATH, index=False)  # index=False：不把 0、1、2… 行号写进文件
    print(f"已导出 {len(prices)} 行到 {SNAPSHOT_PATH}")
    print(f"日期范围：{prices['trade_date'].min().date()} 至 {prices['trade_date'].max().date()}")
    print(f"股票数：{prices['ticker'].nunique()}")
    print(f"文件大小：{os.path.getsize(SNAPSHOT_PATH) / 1024 / 1024:.1f} MB")
