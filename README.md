# Magnificent 7 Stock Analysis & Backtesting Dashboard
# 美股科技七巨头数据分析与回测看板

> 🚧 **Work in progress / 开发中**

## Overview / 项目简介

An end-to-end data analysis project on the "Magnificent 7" US tech stocks
(AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA), benchmarked against SPY and QQQ,
using daily data from January 2015 to the present.

一个端到端的数据分析项目：以美股科技七巨头（AAPL、MSFT、NVDA、GOOGL、AMZN、META、TSLA）为对象，
以 SPY、QQQ 为基准，使用 2015 年 1 月至今的日度数据。

## Planned Features / 计划功能

| English | 中文 |
|---|---|
| Performance metrics: cumulative & annualized return, volatility, max drawdown, Sharpe ratio | 表现指标：累计/年化收益、年化波动率、最大回撤、夏普比率 |
| Return distribution: histogram vs. normal, skewness/kurtosis, 95% VaR | 收益率分布：直方图对比正态分布、偏度/峰度、95% VaR |
| Correlation heatmap and 60-day rolling correlation | 相关性热力图与 60 日滚动相关 |
| CAPM regression against SPY: Beta, Alpha, R² | 对 SPY 的 CAPM 回归：Beta、Alpha、R² |
| Backtests: moving-average crossover vs. buy-and-hold; equal-weight portfolio vs. SPY | 回测：均线交叉 vs 买入持有；七巨头等权组合 vs SPY |
| Interactive multi-page Streamlit dashboard | Streamlit 多页面交互看板 |

## Tech Stack / 技术栈

Python · yfinance · MySQL (PyMySQL) · Pandas · NumPy · SciPy · Matplotlib · Streamlit

## Project Structure / 项目结构

```
mag7-stock-dashboard/
├── data/              # Data snapshot for the online version / 线上版使用的数据快照
├── src/               # Data fetching, cleaning and analysis code / 取数、清洗与分析代码
├── pages/             # Streamlit dashboard pages / 看板各页面
├── requirements.txt   # Python dependencies / 依赖库
└── .env.example       # Database config template / 数据库配置模板
```
