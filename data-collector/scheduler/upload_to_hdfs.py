"""
HDFS 上传脚本（增强版）
将 data-collector 采集的 CSV 文件上传到 HDFS 指定路径（支持6种新数据源）
支持 WebHDFS (hdfs 库) 和命令行 hdfs dfs 两种模式

增强功能:
  1. 上传失败指数退避重试（3次）
  2. HDFS 连接健康检查 + 自动恢复
  3. 批量上传中断恢复（断点续传标记）
  4. 更详细的上传日志

用法:
    # 上传所有未上传的数据文件
    python upload_to_hdfs.py

    # 上传后触发 Hive MSCK REPAIR
    python upload_to_hdfs.py --repair

    # 仅列出待上传文件（不执行）
    python upload_to_hdfs.py --dry-run

    # 使用 hdfs dfs 命令模式（无 hdfs Python 库时）
    python upload_to_hdfs.py --shell
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from config import DATA_DIR, HDFS as HDFS_CFG, MAX_RETRIES, RETRY_BACKOFF_BASE

# ============================================================
# 文件类型 → HDFS 路径映射规则（支持6种新数据源）
# 通过文件名前缀识别数据类别，路由到对应 HDFS 目录
# ============================================================
FILE_ROUTING_RULES = [
    # (文件名前缀匹配, 目标子路径, 是否跳过表头)

    # ---------- 基础行情 ----------
    ("kline_",      "daily/",           True),   # 日K线
    ("realtime_",   "daily/",           True),   # 实时行情（合并存储）
    ("stock_basic_","basic/",           True),   # 股票基本信息

    # ---------- 基金 ----------
    ("fund_nav_",   "fund/nav/",        True),   # 基金净值
    ("fund_basic_", "fund/basic/",      True),   # 基金基本信息

    # ---------- 信号层（a-stock-data 新增）----------
    ("hot_reason_",     "signals/hot_reason/",    True),   # 题材归因
    ("northbound_",     "signals/northbound/",    True),   # 北向资金
    ("industry_compare_","signals/industry/",     True),   # 行业对比
    ("signals_",        "signals/stock/",         True),   # 个股综合信号

    # ---------- 资讯层（a-stock-data 迁移合并：研报+新闻+公告）----------
    ("research_reports_","info/research/",   True),   # 研报列表
    ("consensus_eps_",   "info/consensus_eps/", True), # 一致预期EPS
    ("stock_news_",      "info/stock_news/",  True),   # 个股新闻
    ("cls_news_",        "info/cls_news/",    True),   # 财联社快讯
    ("global_news_",     "info/global_news/", True),   # 全球资讯
    ("filings_",         "info/filings/",     True),   # 巨潮公告

    # ---------- 维度 ----------
    ("dim_",        "dim/",             True),   # 维度数据
]

# 已上传文件记录（避免重复上传同一文件）
UPLOAD_MARKER_DIR = Path(__file__).parent / ".uploaded"


def _exponential_backoff(attempt: int) -> float:
    """指数退避: 1s, 2s, 4s, max=30s"""
    return min(RETRY_BACKOFF_BASE * (2 ** attempt), 30.0)


class HDFSUploader:
    """HDFS 文件上传器（增强版 — 带重试和连接恢复）"""

    def __init__(self, use_shell: bool = False):
        self.use_shell = use_shell
        self.hdfs_url = HDFS_CFG["url"]
        self.hdfs_user = HDFS_CFG["user"]
        self.hdfs_base = HDFS_CFG["base_path"]

        # hdfs 库客户端（lazy init）
        self._client = None
        self._ensure_marker_dir()

    # -----------------------------------------------------------
    # HDFS 连接
    # -----------------------------------------------------------

    @property
    def client(self):
        """hdfs 库的 InsecureClient（自动降级到 shell）"""
        if self._client is None and not self.use_shell:
            try:
                from hdfs import InsecureClient
                self._client = InsecureClient(
                    self.hdfs_url,
                    user=self.hdfs_user,
                )
                logger.info("HDFS 客户端初始化成功")
            except ImportError:
                print("⚠️  hdfs 库未安装，回退到 shell 模式。执行: pip install hdfs")
                self.use_shell = True
            except Exception as e:
                logger.warning("HDFS 客户端初始化失败: %s，回退 shell 模式", e)
                self.use_shell = True
        return self._client

    def _check_hdfs_available(self) -> bool:
        """检查 HDFS 是否可达（WebHDFS 或 shell）"""
        try:
            if self.use_shell:
                result = subprocess.run(
                    ["hdfs", "dfs", "-ls", self.hdfs_base],
                    capture_output=True, text=True, timeout=10,
                )
                return result.returncode == 0
            else:
                if self.client is None:
                    return False
                self.client.list(self.hdfs_base)
                return True
        except Exception as e:
            logger.warning("HDFS 不可达: %s", e)
            return False

    # -----------------------------------------------------------
    # 文件路由
    # -----------------------------------------------------------

    def _wait_for_hdfs(self, max_retries: int = 3) -> bool:
        """等待 HDFS 恢复可达"""
        for attempt in range(max_retries):
            if self._check_hdfs_available():
                return True
            delay = _exponential_backoff(attempt)
            print(f"⏳ HDFS 不可用，{delay:.0f}s 后重试 (第{attempt+1}/{max_retries})...")
            time.sleep(delay)
        return False

    def resolve_hdfs_path(self, filename: str) -> Optional[str]:
        """根据文件名判断应上传到 HDFS 的哪个子目录"""
        for prefix, subpath, _ in FILE_ROUTING_RULES:
            if filename.startswith(prefix):
                return f"{self.hdfs_base}/{subpath}{filename}"
        logger.info("文件无匹配路由规则: %s", filename)
        return None

    def classify_file(self, filepath: str) -> Optional[dict]:
        """识别文件类型信息"""
        name = Path(filepath).name
        for prefix, subpath, skip_header in FILE_ROUTING_RULES:
            if name.startswith(prefix):
                return {
                    "name": name,
                    "local_path": filepath,
                    "hdfs_path": self.resolve_hdfs_path(name),
                    "hdfs_dir": f"{self.hdfs_base}/{subpath}",
                    "skip_header": skip_header,
                }
        logger.warning("无法识别文件类型: %s", filepath)
        return None

    # -----------------------------------------------------------
    # 扫描本地数据文件
    # -----------------------------------------------------------

    def scan_data_files(self, target_dir: Optional[str] = None) -> List[dict]:
        """扫描目录，找出所有可上传的数据文件"""
        scan_dir = Path(target_dir) if target_dir else DATA_DIR
        if not scan_dir.exists():
            print(f"⚠️  目录不存在: {scan_dir}")
            return []

        files = []
        for f in sorted(scan_dir.glob("*.csv")):
            info = self.classify_file(str(f))
            if info:
                files.append(info)
        return files

    # -----------------------------------------------------------
    # 已上传标记管理
    # -----------------------------------------------------------

    def _ensure_marker_dir(self):
        UPLOAD_MARKER_DIR.mkdir(parents=True, exist_ok=True)

    def _is_uploaded(self, filename: str) -> bool:
        marker = UPLOAD_MARKER_DIR / f"{filename}.done"
        return marker.exists()

    def _mark_uploaded(self, filename: str):
        marker = UPLOAD_MARKER_DIR / f"{filename}.done"
        marker.write_text(time.strftime("%Y-%m-%d %H:%M:%S"))

    # -----------------------------------------------------------
    # 上传方法（带重试）
    # -----------------------------------------------------------

    def upload_file(self, file_info: dict, force: bool = False) -> bool:
        """上传单个文件到 HDFS（带指数退避重试）"""
        local_path = file_info["local_path"]
        hdfs_path = file_info["hdfs_path"]
        filename = file_info["name"]

        if not force and self._is_uploaded(filename):
            return True

        local_size = os.path.getsize(local_path)
        if local_size == 0:
            print(f"⚠️  空文件，跳过: {filename}")
            return False

        # 等待 HDFS 可用
        if not self._wait_for_hdfs():
            print(f"❌ HDFS 不可达，跳过: {filename}")
            return False

        # 上传重试
        last_exc = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                if self.use_shell:
                    self._upload_shell(local_path, hdfs_path)
                else:
                    self._upload_client(local_path, hdfs_path)

                self._mark_uploaded(filename)
                print(f"✅ 上传成功: {filename}  ({self._format_size(local_size)})")
                return True

            except Exception as e:
                last_exc = e
                if attempt < MAX_RETRIES:
                    delay = _exponential_backoff(attempt)
                    print(f"⚠️  上传失败 [{filename}] (第{attempt+1}次), {delay:.0f}s 后重试: {e}")
                    time.sleep(delay)
                    # 重连
                    self._client = None
                else:
                    print(f"❌ 上传失败 [{filename}] ({MAX_RETRIES+1}次): {e}")

        return False

    def _upload_client(self, local_path: str, hdfs_path: str):
        """通过 hdfs 库上传"""
        if self.client is None:
            raise RuntimeError("HDFS 客户端未初始化")
        parent = str(Path(hdfs_path).parent)
        self.client.makedirs(parent)
        self.client.upload(hdfs_path, local_path, overwrite=True)

    def _upload_shell(self, local_path: str, hdfs_path: str):
        """通过 hdfs dfs -put 命令上传（无 hdfs 库时回退）"""
        parent = str(Path(hdfs_path).parent)
        subprocess.run(
            ["hdfs", "dfs", "-mkdir", "-p", parent],
            capture_output=True, check=False,
        )
        result = subprocess.run(
            ["hdfs", "dfs", "-put", "-f", local_path, hdfs_path],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())

    # -----------------------------------------------------------
    # Hive 表修复
    # -----------------------------------------------------------

    def run_hive_repair(self, tables: List[str] = None):
        """触发 Hive MSCK REPAIR 刷新分区元数据"""
        if not tables:
            tables = [
                "stock_analysis.stock_basic",
                "stock_analysis.stock_daily_staging",
                "stock_analysis.fund_nav",
                "stock_analysis.fund_basic",
                "stock_analysis.signal_hot_reason",
                "stock_analysis.signal_northbound",
                "stock_analysis.signal_industry",
                "stock_analysis.signal_stock",
                "stock_analysis.info_research_report",
                "stock_analysis.info_consensus_eps",
                "stock_analysis.info_stock_news",
                "stock_analysis.info_cls_news",
                "stock_analysis.info_global_news",
                "stock_analysis.info_filing",
            ]

        print(f"\n🔧 执行 Hive MSCK REPAIR: {', '.join(tables)}")
        for table in tables:
            sql = f"MSCK REPAIR TABLE {table};"
            try:
                result = subprocess.run(
                    ["beeline", "-u", "jdbc:hive2://localhost:10000",
                     "-e", sql],
                    capture_output=True, text=True, timeout=60,
                )
                if result.returncode == 0:
                    print(f"   ✅ {table} 修复完成")
                else:
                    print(f"   ⚠️  {table} 修复可能失败: {result.stderr[:100]}")
            except FileNotFoundError:
                print("   ⚠️  beeline 未安装，跳过 Hive 修复")
                break
            except subprocess.TimeoutExpired:
                print(f"   ⚠️  {table} 修复超时")
                break

    # -----------------------------------------------------------
    # 批量操作
    # -----------------------------------------------------------

    def upload_all(self, target_dir: str = None, force: bool = False,
                   dry_run: bool = False, repair: bool = False) -> int:
        """上传所有未上传的数据文件"""
        files = self.scan_data_files(target_dir)
        if not files:
            print("📭 没有发现待上传的数据文件")
            return 0

        print(f"📦 发现 {len(files)} 个数据文件")
        if dry_run:
            print("\n待上传文件列表:")
            for f in files:
                size = os.path.getsize(f["local_path"])
                print(f"   📄 {f['name']}  ({self._format_size(size)})")
                print(f"      → {f['hdfs_path']}")
            return len(files)

        success = 0
        for f in files:
            if self.upload_file(f, force=force):
                success += 1

        print(f"\n📊 上传完成: {success}/{len(files)} 成功")

        if repair and success > 0:
            self.run_hive_repair()

        return success

    # -----------------------------------------------------------
    # 工具
    # -----------------------------------------------------------

    def list_hdfs_files(self, hdfs_path: str = None) -> List[str]:
        """列出 HDFS 上的文件"""
        path = hdfs_path or self.hdfs_base
        try:
            if self.use_shell:
                result = subprocess.run(
                    ["hdfs", "dfs", "-ls", path],
                    capture_output=True, text=True, check=False,
                )
                if result.returncode == 0:
                    return [l for l in result.stdout.split("\n") if l.strip()]
                return []
            else:
                return self.client.list(path, status=False)
        except Exception as e:
            print(f"⚠️  列出 HDFS 失败: {e}")
            return []

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f}KB"
        else:
            return f"{size / 1024 / 1024:.1f}MB"


# ============================================================
# CLI 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="📤 上传采集数据到 HDFS，打通数据通道（增强版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--file", help="上传指定文件")
    parser.add_argument("--dir", help="扫描指定目录并上传所有数据文件")
    parser.add_argument("--force", action="store_true", help="强制重新上传（覆盖已上传标记）")
    parser.add_argument("--repair", action="store_true", help="上传后执行 Hive MSCK REPAIR")
    parser.add_argument("--dry-run", action="store_true", help="仅列出待上传文件，不执行上传")
    parser.add_argument("--shell", action="store_true", help="使用 hdfs dfs shell 命令（无需安装 hdfs 库）")
    parser.add_argument("--list-hdfs", nargs="?", const="", help="列出 HDFS 上的文件")
    parser.add_argument("--clear-marks", action="store_true", help="清除已上传标记")
    parser.add_argument("--retry", type=int, default=0, help="上传失败重试次数（覆盖默认值）")

    args = parser.parse_args()
    # 重试配置覆盖
    if args.retry > 0:
        global MAX_RETRIES
        MAX_RETRIES = args.retry

    uploader = HDFSUploader(use_shell=args.shell)

    if args.clear_marks:
        import shutil
        shutil.rmtree(UPLOAD_MARKER_DIR, ignore_errors=True)
        print("🗑️  已清除所有上传标记")
        return

    if args.list_hdfs is not None:
        base = args.list_hdfs or HDFS_CFG["base_path"]
        files = uploader.list_hdfs_files(base)
        print(f"\n📂 HDFS {base}:")
        for f in files:
            print(f"   {f}")
        return

    if args.file:
        info = uploader.classify_file(args.file)
        if not info:
            print(f"❌ 无法识别文件类型: {args.file}")
            return
        uploader.upload_file(info, force=args.force)
        if args.repair:
            uploader.run_hive_repair()
        return

    uploader.upload_all(
        target_dir=args.dir,
        force=args.force,
        dry_run=args.dry_run,
        repair=args.repair,
    )


if __name__ == "__main__":
    main()
