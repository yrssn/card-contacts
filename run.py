"""在仓库根目录直接运行：python run.py [--port 8000] [--no-reload]"""
import argparse
import os
import sys
from pathlib import Path

import uvicorn

BACKEND = Path(__file__).resolve().parent / "backend"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-reload", action="store_true")
    args = parser.parse_args()
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=not args.no_reload, reload_dirs=[str(BACKEND / "app")])
