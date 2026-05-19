"""编排引擎全量测试 — 覆盖所有核心逻辑分支"""
from unittest.mock import patch, MagicMock
import json
import pytest
import pandas as pd

from engine.orchestrator import AnalysisEngine, get_engine, analyze, rank
from data.models import KLINE_COLUMN_MAP, MYSQL_TABLES, PRECOMPUTED_TABLES


class TestRankStocks:
    def test_empty(self, engine):
        with patch.object(engine.loader, "read_all_stocks", return_value=pd.DataFrame()):
            assert engine.rank_stocks() == []

    def test_no_numeric_cols(self, engine):
        with patch.object(engine.loader, "read_all_stocks",
                          return_value=pd.DataFrame({"stock_code": ["A"]})):
            assert engine.rank_stocks("x") == []

    def test_metric_fallback(self, engine):
        df = pd.DataFrame({"stock_code": ["A"], "change_percent": [1.0]})
        with patch.object(engine.loader, "read_all_stocks", return_value=df):
            r = engine.rank_stocks("nonexistent")
            assert len(r) == 1
            assert r[0]["value"] == 1.0

    def test_sorted_order(self, engine):
        df = pd.DataFrame({
            "stock_code": ["A", "B"], "stock_name": ["a", "b"],
            "change_percent": [5.0, 10.0],
        })
        with patch.object(engine.loader, "read_all_stocks", return_value=df):
            r = engine.rank_stocks("change_percent", top_n=2)
            assert r[0]["stock_code"] == "B"


class TestAnalyzeTechnical:
    def test_empty_kline(self, engine):
        assert engine._analyze_technical("000001", pd.DataFrame()) == {}

    def test_local_fallback(self, engine, sample_data):
        with patch.object(engine.loader, "read_indicators", return_value=pd.DataFrame()):
            r = engine._analyze_technical("000001", sample_data)
            assert len(r) == 5

    def test_precomputed_used(self, engine):
        mock = pd.DataFrame({"trade_date": ["2026-01-01"], "ma5": [10.5]})
        with patch.object(engine.loader, "read_indicators", return_value=mock):
            r = engine._analyze_technical("000001", pd.DataFrame())
            assert r.get("ma") is not None

    def test_local_failure(self, engine, sample_data):
        with patch.object(engine.loader, "read_indicators", return_value=pd.DataFrame()):
            with patch.object(engine, "_local_indicator", side_effect=Exception("err")):
                r = engine._analyze_technical("000001", sample_data)
                # 每个指标要么有数据要么有 error 字段
                for v in r.values():
                    if isinstance(v, dict) and "error" in v:
                        assert "err" in v["error"]

    def test_kdj_missing_cols(self):
        """KDJ缺列时返回None"""
        from engine.orchestrator import AnalysisEngine
        result = AnalysisEngine._local_indicator(
            pd.DataFrame({"high": [1], "low": [1]}), "technical.kdj", "KDJ")
        assert result is None or "K" in result.columns


class TestAnalyzeChanlun:
    def test_empty(self, engine):
        r = engine._analyze_chanlun(pd.DataFrame())
        assert "status" in r

    def test_with_data(self, engine, sample_data):
        r = engine._analyze_chanlun(sample_data)
        assert "status" in r

    def test_internal_error(self, engine, sample_data):
        """缠论内部异常被捕获"""
        with patch("engine.orchestrator.identify_fractals", side_effect=ValueError("err")):
            r = engine._analyze_chanlun(sample_data)
            assert r.get("status") == "error"


class TestAnalyzeQuantitative:
    def test_empty(self, engine):
        r = engine._analyze_quantitative(pd.DataFrame())
        assert "status" in r

    def test_with_data(self, engine, sample_data):
        r = engine._analyze_quantitative(sample_data)
        assert "status" in r

    def test_internal_error(self, engine, sample_data):
        with patch("engine.orchestrator._get_strategy_engine", side_effect=RuntimeError("err")):
            r = engine._analyze_quantitative(sample_data)
            assert r.get("status") == "error"


class TestAnalyzeStock:
    def test_cache_hit(self, engine):
        cached = json.dumps({"stock_code": "000001"})
        with patch.object(engine.loader, "_cache_get", return_value=cached):
            r = engine.analyze_stock("000001", persist=False)
            assert r["stock_code"] == "000001"

    def test_full_flow(self, engine):
        with patch.object(engine.loader, "_cache_get", return_value=None):
            with patch.object(engine.loader, "read_realtime", return_value={"stock_name": "T"}):
                with patch.object(engine.loader, "read_kline", return_value=pd.DataFrame()):
                    r = engine.analyze_stock("000001", persist=False)
                    assert r["stock_code"] == "000001"
                    assert "elapsed_ms" in r

    def test_persist_flag(self, engine):
        with patch.object(engine.loader, "_cache_get", return_value=None):
            with patch.object(engine.loader, "read_realtime", return_value={}):
                with patch.object(engine.loader, "read_kline", return_value=pd.DataFrame()):
                    with patch.object(engine.result_store, "save_multi", return_value={}):
                        r = engine.analyze_stock("000001", persist=True)
                        assert r["stock_code"] == "000001"


class TestPersistAnalysis:
    def test_persist_all(self, engine):
        result = {
            "technical": {"ma": [{"MA5": 10}], "macd": [], "kdj": [], "rsi": [], "bollinger": []},
            "chanlun": {"status": "ok", "fractals": {"top": 1, "bottom": 1},
                        "signals": [{"type": "buy_1", "date": "2026-01-01", "price": 100,
                                      "strength": 50, "description": "t"}]},
            "quantitative": {"status": "ok", "total": 3, "signals": [], "latest": None},
        }
        engine._persist_analysis("000001", result, pd.DataFrame())

    def test_persist_empty(self, engine):
        engine._persist_analysis("000001", {}, pd.DataFrame())

    def test_build_tech_summary(self, engine):
        s = engine._build_tech_summary({"ma": [{"MA5": 10}]})
        assert len(s) > 0

    def test_build_tech_summary_empty(self, engine):
        s = engine._build_tech_summary({})
        assert "技术指标" in s


class TestBatch:
    def test_sequential(self, engine):
        with patch.object(engine.loader, "_cache_get", return_value=None):
            with patch.object(engine.loader, "read_realtime", return_value={}):
                with patch.object(engine.loader, "read_kline", return_value=pd.DataFrame()):
                    r = engine.analyze_batch(["A", "B"], parallel=False)
                    assert "A" in r and "B" in r

    def test_parallel(self, engine):
        with patch.object(engine.loader, "_cache_get", return_value=None):
            with patch.object(engine.loader, "read_realtime", return_value={}):
                with patch.object(engine.loader, "read_kline", return_value=pd.DataFrame()):
                    r = engine.analyze_batch(["A", "B"], parallel=True, max_workers=2)
                    assert "A" in r and "B" in r

    def test_single_failure(self, engine):
        with patch.object(engine.loader, "_cache_get", return_value=None):
            with patch.object(engine.loader, "read_realtime", side_effect=[{}, Exception("fail")]):
                with patch.object(engine.loader, "read_kline", return_value=pd.DataFrame()):
                    r = engine.analyze_batch(["A", "B"], parallel=False)
                    assert "error" in r.get("B", {})


class TestYearlyReturn:
    def test_local_compute(self, engine):
        df = pd.DataFrame({
            "trade_date": pd.bdate_range("2025-01-01", periods=260),
            "close": [100 + i * 0.5 for i in range(260)],
        })
        with patch.object(engine.loader, "read_precomputed_yearly", return_value=pd.DataFrame()):
            with patch.object(engine.loader, "read_kline", return_value=df):
                r = engine.get_yearly_return("000001")
                assert r is not None

    def test_insufficient_data(self, engine):
        with patch.object(engine.loader, "read_precomputed_yearly", return_value=pd.DataFrame()):
            with patch.object(engine.loader, "read_kline", return_value=pd.DataFrame()):
                assert engine.get_yearly_return("000001") is None


class TestTrend:
    def test_uptrend(self, engine):
        n = 40
        df = pd.DataFrame({"trade_date": pd.bdate_range("2025-01-01", periods=n),
                           "close": [100 + i * 2 for i in range(n)]})
        with patch.object(engine.loader, "read_kline", return_value=df):
            r = engine.get_trend("000001")
            assert r["trend"] == "UPTREND"

    def test_downtrend(self, engine):
        n = 40
        df = pd.DataFrame({"trade_date": pd.bdate_range("2025-01-01", periods=n),
                           "close": [100 - i * 2 for i in range(n)]})
        with patch.object(engine.loader, "read_kline", return_value=df):
            r = engine.get_trend("000001")
            assert r["trend"] == "DOWNTREND"

    def test_sideways(self, engine):
        n = 40
        df = pd.DataFrame({"trade_date": pd.bdate_range("2025-01-01", periods=n),
                           "close": [100] * n})
        with patch.object(engine.loader, "read_kline", return_value=df):
            r = engine.get_trend("000001")
            assert r["trend"] == "SIDEWAYS"

    def test_insufficient(self, engine):
        with patch.object(engine.loader, "read_kline", return_value=pd.DataFrame()):
            assert engine.get_trend("000001")["status"] == "insufficient_data"


class TestClose:
    def test_close(self, engine):
        with patch.object(engine.loader, "close") as m:
            engine.close()
            m.assert_called_once()


class TestConvenience:
    def test_get_engine_singleton(self):
        e1 = get_engine()
        e2 = get_engine()
        assert e1 is e2
        e1.close()

    def test_analyze(self):
        with patch("engine.orchestrator.get_engine") as mock_get:
            eng = MagicMock()
            eng.analyze_stock.return_value = {"ok": True}
            mock_get.return_value = eng
            r = analyze("000001")
            assert r["ok"] is True

    def test_rank(self):
        with patch("engine.orchestrator.get_engine") as mock_get:
            eng = MagicMock()
            eng.rank_stocks.return_value = [{"a": 1}]
            mock_get.return_value = eng
            r = rank("x", 5)
            assert len(r) == 1
            eng.rank_stocks.assert_called_with("x", 5)

    def test_analyze_with_params(self):
        with patch("engine.orchestrator.get_engine") as mock_get:
            eng = MagicMock()
            mock_get.return_value = eng
            analyze("600519", 200, False, False, False)
            eng.analyze_stock.assert_called_with("600519", 200, False, False, False)


class TestDataContracts:
    def test_kline_column_map(self):
        required = {"trade_date", "open", "high", "low", "close"}
        assert required.issubset(set(KLINE_COLUMN_MAP.values()))

    def test_precomputed_tables(self):
        assert PRECOMPUTED_TABLES["ma"] == "precomputed_ma_signal"

    def test_signal_tables(self):
        expected = ["signal_hot_reason", "signal_dragon_tiger",
                     "signal_northbound", "signal_lockup", "signal_daily_industry"]
        for t in expected:
            assert MYSQL_TABLES.get(t) == t
