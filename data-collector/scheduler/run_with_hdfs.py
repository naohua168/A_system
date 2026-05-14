"""
数据采集双写管道：同时写入本地 + HDFS 冷存储
确保数据采集 → HDFS 持久化 → Hive 查询恢复全链路贯通

流程:
    run_collector.py (采集)
        │
        ├── CSV → data/raw/ (本地文件)
        │       │
        │       ├── sync_to_mysql.py → MySQL → 后端API
        │       │
        │       └── upload_to_hdfs.py → HDFS → Hive → 恢复兜底
        │
        └── HTTP源宕机时 → restore_from_hdfs.py 从Hive恢复数据

用法:
    # 全量采集 + HDFS 上传 + Hive REPAIR
    python run_with_hdfs.py --all

    # 定时全链路（每30分钟）
    python run_with_hdfs.py --loop 30

    # 仅将本地数据同步到 HDFS
    python run_with_hdfs.py --to-hdfs

    # 检查全链路状态
    python run_with_hdfs.py --status
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from scheduler.run_collector import DataCollectorRunner


class HDFSPipeline:
    """数据全链路管道（采集 + HDFS + MySQL）"""

    def __init__(self):
        self.collector = DataCollectorRunner()
        self.scripts_dir = Path(__file__).parent

    def run_python(self, script_name: str, args: list = None) -> int:
        """运行同目录下的 Python 脚本"""
        script = self.scripts_dir / script_name
        if not script.exists():
            print(f"❌ 脚本不存在: {script}")
            return -1
        cmd = [sys.executable, str(script)] + (args or [])
        result = subprocess.run(cmd, capture_output=False)
        return result.returncode

    def step_collect(self, args):
        """第1步: 数据采集"""
        print(f"\n{'='*50}")
        print(f"📡 第1步: 数据采集 [{datetime.now():%H:%M:%S}]")
        print(f"{'='*50}")

        if args.realtime:
            self.collector.collect_realtime()
        if args.kline:
            self.collector.collect_kline()
        if args.signals:
            self.collector.collect_hot_reason()
            self.collector.collect_northbound()
            self.collector.collect_industry_compare()
        if args.all:
            self.collector.collect_all()

    def step_to_hdfs(self, repair: bool = False):
        """第2步: 上传到 HDFS"""
        print(f"\n{'='*50}")
        print(f"📤 第2步: 上传到 HDFS [{datetime.now():%H:%M:%S}]")
        print(f"{'='*50}")
        upload_args = ["--force"]
        if repair:
            upload_args.append("--repair")
        return self.run_python("upload_to_hdfs.py", upload_args)

    def step_to_mysql(self):
        """第3步: 同步到 MySQL"""
        print(f"\n{'='*50}")
        print(f"🗄️  第3步: 同步到 MySQL [{datetime.now():%H:%M:%S}]")
        print(f"{'='*50}")
        return self.run_python("sync_to_mysql.py")

    def check_status(self):
        """检查全链路状态"""
        print(f"\n{'='*50}")
        print(f"🔍 全链路状态 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*50}")

        # 检查本地数据
        from config import DATA_DIR
        csv_files = list(DATA_DIR.glob("*.csv")) if DATA_DIR.exists() else []
        print(f"\n📁 本地数据: {len(csv_files)} 个CSV文件")

        # 检查 HDFS
        try:
            result = subprocess.run(
                ["hdfs", "dfs", "-ls", "/user/hadoop/stock_data/"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                dirs = [l.strip().split()[-1] for l in result.stdout.split("\n")
                        if l.strip() and l.startswith("d")]
                print(f"📂 HDFS 目录: {len(dirs)} 个")
                for d in dirs:
                    print(f"   {d}")
            else:
                print("❌ HDFS 不可达")
        except Exception as e:
            print(f"❌ HDFS 检查失败: {e}")

        # 检查 Hive
        try:
            result = subprocess.run(
                ["beeline", "-u", "jdbc:hive2://localhost:10000",
                 "-e", "USE stock_analysis; SHOW TABLES;"],
                capture_output=True, text=True, timeout=10,
            )
            tables = [l.strip() for l in result.stdout.split("\n")
                      if l.strip() and "signal_" in l.lower()]
            print(f"\n🏗️  Hive 信号层表: {len(tables)} 个")
            for t in tables:
                print(f"   {t}")
        except Exception as e:
            print(f"❌ Hive 检查失败: {e}")

        print(f"\n💡 数据恢复: python restore_from_hdfs.py --restore all")

    def run_full_pipeline(self, args):
        """执行全链路"""
        self.step_collect(args)
        if args.skip_hdfs:
            print("⏭️  跳过 HDFS 上传")
        else:
            self.step_to_hdfs(repair=args.repair)
        if args.skip_mysql:
            print("⏭️  跳过 MySQL 同步")
        else:
            self.step_to_mysql()


def main():
    parser = argparse.ArgumentParser(
        description="📦 数据采集双写管道: 本地 + HDFS + MySQL"
    )
    # 采集选项
    parser.add_argument("--all", action="store_true", help="全量采集")
    parser.add_argument("--realtime", action="store_true", help="采集实时行情")
    parser.add_argument("--kline", action="store_true", help="采集K线")
    parser.add_argument("--signals", action="store_true", help="采集信号层")
    # 管道选项
    parser.add_argument("--to-hdfs", action="store_true", help="仅将本地数据同步到HDFS")
    parser.add_argument("--skip-hdfs", action="store_true", help="跳过HDFS上传")
    parser.add_argument("--skip-mysql", action="store_true", help="跳过MySQL同步")
    parser.add_argument("--repair", action="store_true", help="上传后Hive MSCK REPAIR")
    parser.add_argument("--status", action="store_true", help="检查全链路状态")
    parser.add_argument("--loop", type=int, default=0, help="循环间隔(分钟)")

    args = parser.parse_args()
    pipe = HDFSPipeline()

    if args.status:
        pipe.check_status()
        return

    if args.to_hdfs:
        pipe.step_to_hdfs(repair=args.repair)
        return

    def run_once():
        pipe.run_full_pipeline(args)

    if args.loop > 0:
        print(f"🔄 全链路定时管道，间隔 {args.loop} 分钟")
        while True:
            run_once()
            print(f"\n⏳ 等待 {args.loop} 分钟后下一轮...\n")
            time.sleep(args.loop * 60)
    else:
        run_once()


if __name__ == "__main__":
    main()
