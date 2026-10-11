-- 建库建表：在项目文件夹里运行 mysql -u root -p < sql/schema.sql

-- 建数据库 mag7；utf8mb4 是完整的 UTF-8 编码，能存中文和各种符号
CREATE DATABASE IF NOT EXISTS mag7 DEFAULT CHARACTER SET utf8mb4;

-- 切换到 mag7 库，后面的表都建在这里
USE mag7;

-- 表 1：股票清单，每只股票一行
CREATE TABLE IF NOT EXISTS stocks (
    ticker   VARCHAR(10)  NOT NULL,   -- 股票代码，如 AAPL
    name     VARCHAR(100),            -- 公司名，如 Apple Inc.
    category VARCHAR(20),             -- 分组：mag7 / memory / benchmark
    PRIMARY KEY (ticker)
);

-- 表 2：每日价格，每只股票每个交易日一行
CREATE TABLE IF NOT EXISTS daily_prices (
    ticker       VARCHAR(10) NOT NULL,
    trade_date   DATE        NOT NULL,
    open         DOUBLE,
    high         DOUBLE,
    low          DOUBLE,
    close        DOUBLE,              -- 收盘价（已做拆股调整）
    adj_close    DOUBLE,              -- 复权收盘价（拆股 + 分红调整），算收益率用这一列
    volume       BIGINT,              -- 成交量，数值可能超过 21 亿，所以用 BIGINT
    dividends    DOUBLE,              -- 当天每股分红，平时为 0
    stock_splits DOUBLE,              -- 当天拆股比例，平时为 0
    -- 联合主键：同一只股票同一天只能有一行
    PRIMARY KEY (ticker, trade_date),
    -- 外键：ticker 必须先在 stocks 表里存在
    FOREIGN KEY (ticker) REFERENCES stocks (ticker)
);
