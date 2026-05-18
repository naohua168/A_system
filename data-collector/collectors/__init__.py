# data-collector/collectors - 多数据源采集器模块（基于 a-stock-data 重构）
# 采用工厂模式 + 策略模式，支持动态扩展数据源
#
# 数据源清单:
#   mootdx       — 通达信TCP: K线/五档盘口/逐笔成交/财务快照/F10 (需国内IP)
#   tencent      — 腾讯财经: PE/PB/市值/换手率/涨跌停价 (不封IP)
#   ths_hot      — 同花顺热点: 当日强势股+题材归因 reason tags (零鉴权73ms)
#   ths_northbound — 同花顺北向: 北向资金实时分钟流向+自缓存历史
#   baidu        — 百度股市通: 概念板块归属+个股资金流向
#   akshare_ext  — akshare扩展: 龙虎榜/解禁/行业/研报/新闻/公告
#   information  — 资讯层: 研报+新闻+公告（从 a-stock-data 迁移合并）

from .data_source_factory import DataSourceFactory

__all__ = ["DataSourceFactory"]
