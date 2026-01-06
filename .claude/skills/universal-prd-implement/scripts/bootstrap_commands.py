#!/usr/bin/env python3
"""Install portable /prd and /implement commands into a target repo."""

import argparse
import shutil
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install universal /prd and /implement commands into a repo's .claude/commands directory.",
    )
    parser.add_argument("target", nargs="?", default=".", help="Target repo root (default: .)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing command files")
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    assets_dir = skill_root / "assets" / "commands"
    if not assets_dir.exists():
        print(f"[error] assets directory not found: {assets_dir}", file=sys.stderr)
        return 1

    target_root = Path(args.target).resolve()
    commands_dir = target_root / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    for name in ("prd.md", "implement.md"):
        src = assets_dir / name
        if not src.exists():
            print(f"[error] missing source file: {src}", file=sys.stderr)
            return 1
        dst = commands_dir / name
        if dst.exists() and not args.force:
            print(f"[skip] {dst} exists (use --force to overwrite)")
            continue
        shutil.copy2(src, dst)
        print(f"[ok] installed {dst}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
