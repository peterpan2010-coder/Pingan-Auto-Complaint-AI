#!/usr/bin/env python3
"""交付前检查（替代 CI）。

对指定智能体依次运行：
  1. 单元测试   agents/<agent>/tests/unit
  2. 契约测试   agents/<agent>/tests/contract
全部通过后才调用 `python tasks.py pack <agent>` 生成交付包；任一步失败立即中止。

用法：
  python tools/predeliver.py <agent> [<agent> ...]
  python tasks.py predeliver <agent> [<agent> ...]

测试运行器：已安装 pytest 时使用 pytest，否则回退到 unittest（test_*.py）。
退出码：0 全部成功；1 测试失败或目录缺失；2 打包失败；3 参数错误。
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "agents"
TASKS_PY = ROOT / "tasks.py"

# (阶段名称, 相对于智能体目录的测试路径)，按顺序执行
STAGES = [
    ("单元测试", Path("tests") / "unit"),
    ("契约测试", Path("tests") / "contract"),
]

EXIT_OK = 0
EXIT_TEST_FAILED = 1
EXIT_PACK_FAILED = 2
EXIT_USAGE = 3


def _has_pytest() -> bool:
    return importlib.util.find_spec("pytest") is not None


def _test_command(test_dir: Path) -> list[str]:
    if _has_pytest():
        return [sys.executable, "-m", "pytest", "-q", str(test_dir)]
    return [
        sys.executable, "-m", "unittest", "discover",
        "-s", str(test_dir), "-p", "test_*.py", "-v",
    ]


def _run(cmd: list[str], cwd: Path) -> int:
    print(f"$ {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=cwd)


def run_stage(agent: str, name: str, rel_path: Path) -> bool:
    agent_dir = AGENTS_DIR / agent
    test_dir = agent_dir / rel_path
    print(f"\n==> [{agent}] {name}: {test_dir.relative_to(ROOT)}", flush=True)
    # 缺失测试目录视为失败：没有测试就不能声称“全部通过”
    if not test_dir.is_dir():
        print(f"[失败] 未找到测试目录 {test_dir.relative_to(ROOT)}", file=sys.stderr)
        return False

    start = time.monotonic()
    code = _run(_test_command(test_dir), cwd=agent_dir)
    elapsed = time.monotonic() - start
    if code != 0:
        # pytest 退出码 5 表示未收集到任何测试，同样视为失败
        print(f"[失败] {name}（退出码 {code}，{elapsed:.1f}s）", file=sys.stderr)
        return False
    print(f"[通过] {name}（{elapsed:.1f}s）")
    return True


def pack(agent: str) -> bool:
    print(f"\n==> [{agent}] 生成交付包", flush=True)
    code = _run([sys.executable, str(TASKS_PY), "pack", agent], cwd=ROOT)
    if code != 0:
        print(f"[失败] 打包（退出码 {code}）", file=sys.stderr)
        return False
    return True


def predeliver(agent: str) -> int:
    agent_dir = AGENTS_DIR / agent
    if not agent_dir.is_dir():
        print(f"[错误] 智能体不存在：{agent_dir.relative_to(ROOT)}", file=sys.stderr)
        return EXIT_USAGE

    for name, rel_path in STAGES:
        if not run_stage(agent, name, rel_path):
            print(f"\n[{agent}] 交付前检查未通过，已跳过打包。", file=sys.stderr)
            return EXIT_TEST_FAILED

    if not pack(agent):
        return EXIT_PACK_FAILED
    print(f"\n[{agent}] 交付前检查全部通过，交付包已生成。")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="交付前检查：单元测试 → 契约测试 → 打包（替代 CI）")
    parser.add_argument("agents", nargs="+", metavar="agent",
                        help="智能体名称（agents/ 下的目录名）")
    args = parser.parse_args(argv)

    for agent in args.agents:
        code = predeliver(agent)
        if code != EXIT_OK:
            return code
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
