#!/usr/bin/env python3
"""
Worker管理工具
"""

import subprocess
import sys
import time
from pathlib import Path


def start_worker(count=1, worker_id=None):
    """启动Worker"""
    cmd = [sys.executable, str(Path(__file__).parent / "table_worker.py")]

    if worker_id:
        cmd.extend(["--id", worker_id])

    if count > 1:
        cmd.extend(["--count", str(count)])

    print(f"🚀 启动Worker: {' '.join(cmd)}")
    subprocess.Popen(cmd)


def check_redis_queue():
    """检查Redis队列状态"""
    import redis
    import json

    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

        # 队列长度
        queue_len = r.llen("table_parse_queue")
        print(f"📊 Redis队列长度: {queue_len}")

        if queue_len > 0:
            # 显示队列中的任务
            tasks = r.lrange("table_parse_queue", 0, min(queue_len, 5) - 1)
            print(f"📋 队列前{len(tasks)}个任务:")
            for i, task_json in enumerate(tasks):
                try:
                    task = json.loads(task_json)
                    print(f"  {i + 1}. {task.get('job_id', 'N/A')} - {task.get('pdf_folder', 'N/A')}")
                except:
                    print(f"  {i + 1}. 无法解析任务数据")

        # 显示正在处理的任务
        keys = r.keys("table:job:*")
        print(f"\n🔍 任务状态 ({len(keys)} 个):")

        for key in keys:
            status = r.hget(key, "status")
            if status:
                job_id = key.replace("table:job:", "")
                progress = r.hget(key, "progress") or "0"
                message = r.hget(key, "message") or ""
                print(f"  {job_id[:20]}... - 状态: {status}, 进度: {progress}%, {message}")

    except Exception as e:
        print(f"❌ 检查Redis失败: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Worker管理工具')
    parser.add_argument('action', choices=['start', 'status', 'queue'],
                        help='操作: start-启动Worker, status-检查状态, queue-查看队列')
    parser.add_argument('--count', type=int, default=1, help='Worker数量')
    parser.add_argument('--id', type=str, help='Worker ID')

    args = parser.parse_args()

    if args.action == "start":
        start_worker(args.count, args.id)
    elif args.action == "status":
        # 可以扩展为检查Worker进程状态
        print("📈 Worker状态检查功能待实现")
    elif args.action == "queue":
        check_redis_queue()

