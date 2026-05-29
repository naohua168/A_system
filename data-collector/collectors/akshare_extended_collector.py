"""
akshare 扩展采集器
基于 a-stock-data 项目封装的 akshare 功能子集，保留以下能力：
1. 龙虎榜席位（个股 + 全市场）
2. 限售解禁日历（历史 + 未来90天预警）
3. 行业横向对比（同花顺90行业排名）
4. 一致预期EPS
5. 东财研报（列表 + PDF下载）
6. 新闻（个股新闻/财联社快讯/全球资讯）
7. 巨潮公告
8. 基金净值（东方财富源）
"""
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)


class AkshareExtendedCollector(BaseCollector):
    """akshare 扩展数据源 — 龙虎榜/解禁/行业/研报/新闻/公告"""

    source_name = "akshare_ext"
    SUPPORTED_MARKETS = ["a_stock"]

    def __init__(self, config: dict = None):
        super().__init__(config)
        self._ak = None
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://data.eastmoney.com/",
        })

    @property
    def ak(self):
        if self._ak is None:
            import akshare as ak
            self._ak = ak
        return self._ak

    # ==========================================================
    # 龙虎榜席位（个股维度）
    # ==========================================================

    def fetch_dragon_tiger_board(self, code: str, trade_date: str,
                                  look_back: int = 30) -> dict:
        """龙虎榜数据聚合

        返回: {records: [{date, reason, net_buy, turnover}],
               seats: {buy: [{name, buy_amt, sell_amt, net}],
                       sell: [{name, buy_amt, sell_amt, net}]},
               institution: {buy_count, sell_count, net_amount}}
        """
        start = datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=look_back)
        start_str = start.strftime("%Y%m%d")
        end_str = trade_date.replace("-", "")

        records = []
        try:
            df = self.ak.stock_lhb_detail_em(start_date=start_str, end_date=end_str)
            if not df.empty:
                df_stock = df[df["代码"] == code]
                for _, row in df_stock.iterrows():
                    records.append({
                        "date": str(row.get("日期", "")),
                        "reason": row.get("解读", ""),
                        "net_buy": row.get("龙虎榜净买额", 0),
                        "turnover": row.get("换手率", 0),
                    })
        except Exception as e:
            logger.warning("龙虎榜记录查询失败 [%s]: %s", code, e)

        seats = {"buy": [], "sell": []}
        institution = {}
        if records:
            latest_date = records[0]["date"].replace("-", "")[:8]
            for flag in ["买入", "卖出"]:
                try:
                    df_detail = self.ak.stock_lhb_stock_detail_em(
                        symbol=code, date=latest_date, flag=flag
                    )
                    if not df_detail.empty:
                        for _, row in df_detail.head(5).iterrows():
                            seats[flag.replace("买入", "buy").replace("卖出", "sell")].append({
                                "name": row.get("营业部名称", ""),
                                "buy_amt": row.get("买入额", 0),
                                "sell_amt": row.get("卖出额", 0),
                                "net": row.get("净额", 0),
                            })
                except Exception as e:
                    logger.warning("龙虎榜席位查询失败 [%s/%s]: %s", code, flag, e)
            try:
                df_inst = self.ak.stock_lhb_jgmmtj_em(symbol=code)
                if not df_inst.empty:
                    row = df_inst.iloc[0]
                    institution = {
                        "buy_count": row.get("买入机构数", 0),
                        "sell_count": row.get("卖出机构数", 0),
                        "net_amount": row.get("机构净买入额", 0),
                    }
            except Exception as e:
                logger.warning("机构龙虎榜查询失败 [%s]: %s", code, e)

        return {"records": records, "seats": seats, "institution": institution}

    # ==========================================================
    # 全市场龙虎榜（东财datacenter API 直调，绕过akshare解析bug）
    # ==========================================================

    def fetch_daily_dragon_tiger(self, trade_date: str = None,
                                  min_net_buy: float = None) -> dict:
        """全市场龙虎榜

        trade_date: YYYY-MM-DD, 默认当天
        min_net_buy: 净买入下限(万元)
        """
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y-%m-%d")
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
            "columns": "ALL",
            "filter": f"(TRADE_DATE>='{trade_date}')(TRADE_DATE<='{trade_date}')",
            "pageNumber": "1", "pageSize": "500",
            "sortTypes": "-1", "sortColumns": "BILLBOARD_NET_AMT",
            "source": "WEB", "client": "WEB",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://data.eastmoney.com/",
        }
        r = self._session.get(url, params=params, headers=headers, timeout=15)
        d = r.json()
        if not d.get("success") or not d.get("result") or not d["result"].get("data"):
            return {"date": trade_date, "total_records": 0, "stocks": [],
                    "note": "无数据（非交易日或未更新）"}
        data = d["result"]["data"]
        actual_date = data[0].get("TRADE_DATE", "")[:10] if data else trade_date
        stocks = []
        for row in data:
            net_buy = (row.get("BILLBOARD_NET_AMT") or 0) / 10000
            if min_net_buy is not None and net_buy < min_net_buy:
                continue
            stocks.append({
                "code": row.get("SECURITY_CODE", ""),
                "name": row.get("SECURITY_NAME_ABBR", ""),
                "reason": row.get("EXPLANATION", ""),
                "close": row.get("CLOSE_PRICE") or 0,
                "change_pct": round(float(row.get("CHANGE_RATE") or 0), 2),
                "net_buy_wan": round(net_buy, 1),
                "buy_wan": round((row.get("BILLBOARD_BUY_AMT") or 0) / 10000, 1),
                "sell_wan": round((row.get("BILLBOARD_SELL_AMT") or 0) / 10000, 1),
                "turnover_pct": round(float(row.get("TURNOVERRATE") or 0), 2),
            })
        return {"date": actual_date, "total_records": len(stocks), "stocks": stocks}

    # ==========================================================
    # 限售解禁日历（东财 datacenter API 直调，绕过akshare解析bug）
    # ==========================================================

    def fetch_lockup_expiry(self, code: str, trade_date: str = None,
                             forward_days: int = 90) -> dict:
        """限售解禁日历

        使用东财 datacenter API 直调（替代不稳定的 akshare）

        返回: {history: [{date, type, shares, ratio}],
               upcoming: [{date, type, shares, float_ratio}]}
        """
        if not trade_date:
            trade_date = datetime.now().strftime("%Y-%m-%d")

        def _parse_row(row):
            """统一解析东财解禁API返回的行"""
            return {
                "date": str(row.get("FREE_DATE", ""))[:10],
                "type": row.get("FREE_SHARES_TYPE", row.get("LIMITED_RELEASE_TYPE_NAME", "")),
                "shares": row.get("CURRENT_FREE_SHARES", row.get("FREE_SHARES_NUM", 0)),
                "ratio": row.get("B20_ADJCHRATE", row.get("FREE_RATIO", 0)),
            }

        history = []
        try:
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": "RPT_LIFT_STAGE",
                "columns": "ALL",
                "filter": f'(SECURITY_CODE="{code}")',
                "pageNumber": "1", "pageSize": "15",
                "sortColumns": "FREE_DATE", "sortTypes": "-1",
                "source": "WEB", "client": "WEB",
            }
            r = self._session.get(url, params=params, timeout=15)
            d = r.json()
            if d.get("result") and d["result"].get("data"):
                for row in d["result"]["data"]:
                    history.append(_parse_row(row))
        except Exception as e:
            logger.warning("限售解禁历史查询失败 [%s]: %s", code, e)

        upcoming = []
        try:
            end_date = datetime.strptime(trade_date, "%Y-%m-%d") + timedelta(days=forward_days)
            end_str = end_date.strftime("%Y-%m-%d")
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": "RPT_LIFT_STAGE",
                "columns": "ALL",
                "filter": f'(SECURITY_CODE="{code}")(FREE_DATE>=\'{trade_date}\')(FREE_DATE<=\'{end_str}\')',
                "pageNumber": "1", "pageSize": "20",
                "sortColumns": "FREE_DATE", "sortTypes": "1",
                "source": "WEB", "client": "WEB",
            }
            r = self._session.get(url, params=params, timeout=15)
            d = r.json()
            if d.get("result") and d["result"].get("data"):
                for row in d["result"]["data"]:
                    parsed = _parse_row(row)
                    parsed["float_ratio"] = parsed.pop("ratio")
                    upcoming.append(parsed)
        except Exception as e:
            logger.warning("限售解禁未来查询失败 [%s]: %s", code, e)

        return {"history": history, "upcoming": upcoming}

    # ==========================================================
    # 行业横向对比
    # ==========================================================

    def fetch_industry_comparison(self, top_n: int = 20) -> dict:
        """全行业涨跌幅排名（同花顺 ~90 行业）"""
        df = self.ak.stock_board_industry_summary_ths()
        if df.empty:
            return {"top": [], "bottom": [], "total": 0}
        rows = []
        for i, row in df.iterrows():
            rows.append({
                "rank": i + 1,
                "name": row.get("板块", ""),
                "change_pct": row.get("涨跌幅", 0),
                "turnover_yi": row.get("总成交额", 0),
                "net_inflow_yi": row.get("净流入", 0) if "净流入" in df.columns else None,
                "up_count": row.get("上涨家数", 0),
                "down_count": row.get("下跌家数", 0),
                "leader": row.get("领涨股", ""),
            })
        return {"top": rows[:top_n], "bottom": rows[-top_n:], "total": len(rows)}

    # ==========================================================
    # 机构一致预期EPS
    # ==========================================================

    def fetch_consensus_eps(self, code: str) -> pd.DataFrame:
        """机构一致预期EPS

        返回: 年度, 预测机构数, 最小值, 均值, 最大值, 行业平均数
        """
        df = self.ak.stock_profit_forecast_ths(symbol=code, indicator="预测年报每股收益")
        if df.empty:
            return df
        df["code"] = code
        df["source"] = self.source_name
        return df

    # ==========================================================
    # 东财研报
    # ==========================================================

    def fetch_research_reports(self, code: str, max_pages: int = 5) -> list:
        """拉取指定股票的研报列表"""
        api = "https://reportapi.eastmoney.com/report/list"
        all_records = []
        for page in range(1, max_pages + 1):
            params = {
                "industryCode": "*", "pageSize": "100", "industry": "*",
                "rating": "*", "ratingChange": "*",
                "beginTime": "2000-01-01", "endTime": "2030-01-01",
                "pageNo": str(page), "fields": "", "qType": "0",
                "orgCode": "", "code": code, "rcode": "",
                "p": str(page), "pageNum": str(page), "pageNumber": str(page),
            }
            r = self._session.get(api, params=params, timeout=30)
            d = r.json()
            rows = d.get("data") or []
            if not rows:
                break
            all_records.extend(rows)
            if page >= (d.get("TotalPage", 1) or 1):
                break
            time.sleep(0.3)
        return all_records

    def download_report_pdf(self, record: dict, target_dir: str = "./reports") -> str:
        """下载研报PDF"""
        info_code = record.get("infoCode", "")
        if not info_code:
            return None
        date = (record.get("publishDate") or "")[:10]
        org = record.get("orgSName") or "未知"
        title = re.sub(r'[\\/:*?"<>|]', "_", record.get("title", ""))[:80]
        fname = f"{date}_{org}_{title}.pdf"
        target = Path(target_dir) / fname
        if target.exists():
            return str(target)
        url = f"https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf"
        r = requests.get(
            url,
            headers={"User-Agent": self._session.headers["User-Agent"],
                     "Referer": "https://data.eastmoney.com/"},
            timeout=60,
        )
        if r.status_code == 200 and len(r.content) >= 1024:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(r.content)
            return str(target)
        return None

    # ==========================================================
    # 新闻
    # ==========================================================

    def fetch_stock_news(self, code: str) -> pd.DataFrame:
        """个股新闻（东财源）"""
        return self.ak.stock_news_em(symbol=code)

    def fetch_cls_news(self) -> pd.DataFrame:
        """财联社快讯"""
        return self.ak.stock_info_global_cls()

    def fetch_global_news(self) -> pd.DataFrame:
        """东财全球资讯"""
        return self.ak.stock_info_global_em()

    # ==========================================================
    # 巨潮公告
    # ==========================================================

    def fetch_cninfo_filings(self, code: str) -> pd.DataFrame:
        """巨潮公告全文"""
        market = "沪市" if code.startswith("6") else ("北交所" if code.startswith("8") else "深市")
        return self.ak.stock_zh_a_disclosure_report_cninfo(symbol=code, market=market)

    # ==========================================================
    # K线数据（HTTP回退方案，当 mootdx TCP 不可用时使用）
    # ==========================================================

    def fetch_kline_http(self, code: str, freq: str = "daily",
                          days: int = 365) -> pd.DataFrame:
        """通过 akshare HTTP 获取日K线（备用方案）"""
        try:
            import akshare as ak
            suffix = {"6": "SH", "9": "SH"}.get(code[0], "SZ")
            symbol = f"{code}.{suffix}"
            df = ak.stock_zh_a_hist(symbol=symbol, period=freq,
                                     start_date="19900101", adjust="")
            if df.empty:
                return df
            if days > 0 and len(df) > days:
                df = df.tail(days)
            rename = {
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume",
                "成交额": "amount", "振幅": "amplitude",
                "涨跌幅": "change_pct", "涨跌额": "change_amount",
                "换手率": "turnover_pct",
            }
            df.rename(columns={k: v for k, v in rename.items() if k in df.columns},
                      inplace=True)
            df["code"] = code
            return df
        except Exception as e:
            raise RuntimeError(f"akshare K线采集失败 [{code}]: {e}")

    # ==========================================================
    # 基金净值
    # ==========================================================

    def fetch_fund_nav(
        self, code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取基金净值（东方财富源）
        
        从 akshare 获取单位净值和累计净值，合并返回。
        默认覆盖最近 3650 天（10年），确保有足够数据计算各周期收益。
        """
        if not start_date or not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=3650)).strftime("%Y%m%d")
        try:
            # 1. 单位净值走势（含日增长率）
            df_nav = self.ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
            if df_nav.empty:
                return df_nav
            col_map = {
                df_nav.columns[0]: "date",
                df_nav.columns[1]: "nav",
                df_nav.columns[2]: "daily_change",
            }
            df_nav.rename(columns=col_map, inplace=True)
            df_nav = df_nav[["date", "nav", "daily_change"]].copy()
            df_nav["date"] = df_nav["date"].astype(str)

            # 2. 累计净值走势
            try:
                df_acc = self.ak.fund_open_fund_info_em(symbol=code, indicator="累计净值走势")
                if not df_acc.empty:
                    acc_map = {
                        df_acc.columns[0]: "date",
                        df_acc.columns[1]: "accum_nav",
                    }
                    df_acc.rename(columns=acc_map, inplace=True)
                    df_acc = df_acc[["date", "accum_nav"]].copy()
                    df_acc["date"] = df_acc["date"].astype(str)
                    # 合并到主表
                    df_nav = df_nav.merge(df_acc, on="date", how="left")
                else:
                    df_nav["accum_nav"] = 0.0
            except Exception:
                df_nav["accum_nav"] = 0.0

            df_nav["code"] = code
            df_nav["source"] = self.source_name
            df_nav = df_nav[(df_nav["date"] >= start_date) & (df_nav["date"] <= end_date)]
            return df_nav.reset_index(drop=True)
        except Exception as e:
            raise RuntimeError(f"基金净值采集失败 [{code}]: {e}")

    def fetch_fund_holdings(self, code: str) -> pd.DataFrame:
        """获取基金前十大持仓"""
        try:
            df = self.ak.fund_portfolio_hold_detail_em(symbol=code)
            if not df.empty:
                df["code"] = code
                df["source"] = self.source_name
            return df
        except Exception as e:
            raise RuntimeError(f"基金持仓采集失败 [{code}]: {e}")

    # ==========================================================
    # 基类接口实现
    # ==========================================================

    def fetch_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        raise NotImplementedError("akshare_ext 不直接提供实时行情，请用 tencent/mootdx")

    def fetch_stock_basic(self, codes: Optional[List[str]] = None) -> pd.DataFrame:
        raise NotImplementedError("akshare_ext 不直接提供股票基本信息，请用 tencent")

    def health_check(self) -> bool:
        try:
            df = self.fetch_consensus_eps("000001")
            return not df.empty
        except Exception:
            return False
