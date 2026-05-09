#!/usr/bin/env python3
"""
Novel Studio 启动脚本

用法：
  python start_studio.py              # 默认 0.0.0.0:8765
  python start_studio.py --port 9000  # 自定义端口
  python start_studio.py --dev        # 开发模式（热重载）
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

parser = argparse.ArgumentParser()
parser.add_argument("--host", default="0.0.0.0")
parser.add_argument("--port", type=int, default=8765)
parser.add_argument("--dev", action="store_true")
args = parser.parse_args()

(ROOT / "novel_studio/sandbox/projects").mkdir(parents=True, exist_ok=True)
(ROOT / "novel_studio/sandbox/sessions").mkdir(parents=True, exist_ok=True)
(ROOT / "novel_studio/static").mkdir(parents=True, exist_ok=True)

import uvicorn
from novel_studio.app import app

print(f"\n🎬 Novel Studio 启动中...")
print(f"   地址: http://{args.host}:{args.port}")
print(f"   按 Ctrl+C 停止\n")

uvicorn.run(
    "novel_studio.app:app",
    host=args.host,
    port=args.port,
    reload=args.dev,
    log_level="info",
)
