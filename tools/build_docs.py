"""Build documentation site and copy artifacts into the target output directory."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("output")


def build(output_dir: str) -> None:
    """Run make docs and copy the generated site/ directory to output_dir."""
    make_bin = shutil.which("make") or "make"
    subprocess.run([make_bin, "docs"], check=True)

    docs_src_path = Path("site")
    output_path = Path(output_dir)

    output_path.mkdir(parents=True, exist_ok=True)
    output_path.joinpath(".nojekyll").touch(exist_ok=True)

    for filename in ["llms.txt", "llms-full.txt"]:
        root_file = Path(filename)
        if root_file.exists():
            shutil.copy2(root_file, output_path / filename)

    for item in docs_src_path.iterdir():
        dest = output_path / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


def main() -> None:
    """Parse CLI arguments and build documentation output."""
    args = parser.parse_args()
    build(output_dir=args.output)


if __name__ == "__main__":
    main()
