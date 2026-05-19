"""优化版 ResultStore — 批量 SQL 写入 + 合并事务"""
import json, logging
from datetime import date, timedelta, datetime as dt
from typing import Any, Dict, List, Optional

logger = logging.getLogger("analysis.result_store")


class ResultStore:
    """分析结果持久化 — 批量 INSERT + 合并事务"""

    def __init__(self, loader):
        self._loader = loader

    def _get_cursor(self):
        conn = self._loader._get_mysql()
        return conn, conn.cursor()

    # ── 批量写入（合并为单个 REPLACE ... VALUES (...), (...)）──
    def save_multi(self, asset_code: str,
                   results: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        if not results: return {}
        conn, cursor = self._get_cursor()
        today = date.today().isoformat()
        rows = []
        types = []
        for atype, rdict in results.items():
            summary = rdict.pop("_summary", "")
            result_json = json.dumps(rdict, ensure_ascii=False, default=str)
            rows.append((0, asset_code, atype, result_json, summary, today))
            types.append(atype)
        try:
            cursor.executemany(
                "REPLACE INTO analysis_result (asset_type, asset_code, analysis_type, result_json, summary, analysis_date, created_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
                rows)
            conn.commit()
            logger.info("[ResultStore] %s 批量保存 %d 类: %s", asset_code, len(types), types)
            return {t: True for t in types}
        except Exception as e:
            conn.rollback()
            logger.error("[ResultStore] 批量保存失败 %s: %s", asset_code, e)
            return {t: False for t in types}
        finally:
            cursor.close()

    # ── 单条写入（委托给 save_multi）──
    def save(self, asset_code: str, analysis_type: str,
             result_dict: Dict[str, Any], summary="", asset_type=0) -> bool:
        result = self.save_multi(asset_code, {analysis_type: {**result_dict, "_summary": summary}})
        return result.get(analysis_type, False)

    # ── 批量清理 ──
    def delete_old(self, asset_code: str, analysis_type: str, keep_days=30) -> int:
        conn, cursor = self._get_cursor()
        cutoff = (dt.now() - timedelta(days=keep_days)).isoformat()
        try:
            cursor.execute(
                "DELETE FROM analysis_result WHERE asset_code=%s AND analysis_type=%s AND analysis_date<%s",
                (asset_code, analysis_type, cutoff))
            conn.commit()
            deleted = cursor.rowcount
            if deleted: logger.info("[ResultStore] 清理 %s %s: %d条", asset_code, analysis_type, deleted)
            return deleted
        except Exception as e:
            logger.warning("[ResultStore] 清理失败: %s", e)
            return 0
        finally:
            cursor.close()

    def load_latest(self, asset_code: str, analysis_type="full") -> Optional[Dict]:
        cached = self._loader._cache_get(f"rs:{asset_code}:{analysis_type}")
        if cached:
            try: return json.loads(cached)
            except Exception: pass
        try:
            import pandas as pd
            df = pd.read_sql(
                "SELECT result_json, summary FROM analysis_result WHERE asset_code=%s AND analysis_type=%s ORDER BY analysis_date DESC LIMIT 1",
                self._loader._get_mysql(), params=(asset_code, analysis_type))
            if df.empty: return None
            result = json.loads(df.iloc[0]["result_json"])
            result["_summary"] = df.iloc[0].get("summary", "")
            self._loader._cache_set(f"rs:{asset_code}:{analysis_type}",
                json.dumps(result, ensure_ascii=False, default=str), 300)
            return result
        except Exception as e:
            logger.warning("[ResultStore] 读取失败: %s", e)
            return None
