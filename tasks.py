#!/usr/bin/env python3
"""项目任务入口。

  python tasks.py pack <agent>                    打包 agents/<agent> 到 dist/
  python tasks.py predeliver <agent> [<agent>...]   单元测试 → 契约测试 → 打包
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AGENTS_DIR = ROOT / "agents"
DIST_DIR = ROOT / "dist"

# 不进入交付包的目录与文件
EXCLUDE_DIRS = {"tests", "__pycache__", ".pytest_cache", ".git", ".venv", "venv"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def _iter_package_files(agent_dir: Path):
    for path in sorted(agent_dir.rglob("*")):
        rel = path.relative_to(agent_dir)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if path.is_file() and path.suffix not in EXCLUDE_SUFFIXES:
            yield path, rel


def cmd_pack(args: argparse.Namespace) -> int:
    agent_dir = AGENTS_DIR / args.agent
    if not agent_dir.is_dir():
        print(f"[错误] 智能体不存在：{agent_dir.relative_to(ROOT)}", file=sys.stderr)
        return 1

    DIST_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = DIST_DIR / f"{args.agent}-{stamp}.zip"
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, rel in _iter_package_files(agent_dir):
            zf.write(path, Path(args.agent) / rel)
            count += 1
    print(f"已生成交付包：{out.relative_to(ROOT)}（{count} 个文件）")
    return 0


def cmd_predeliver(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(ROOT / "tools"))
    import predeliver

    return predeliver.main(args.agents)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="项目任务入口")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("pack", help="打包指定智能体到 dist/")
    p.add_argument("agent", help="智能体名称（agents/ 下的目录名）")
    p.set_defaults(func=cmd_pack)

    p = sub.add_parser("predeliver",
                       help="交付前检查：单元测试 → 契约测试 → 打包（替代 CI）")
    p.add_argument("agents", nargs="+", metavar="agent",
                   help="智能体名称（agents/ 下的目录名）")
    p.set_defaults(func=cmd_predeliver)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
