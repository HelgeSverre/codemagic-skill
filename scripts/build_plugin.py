#!/usr/bin/env python3
"""Build a plugin ZIP from an explicit set of distributable files."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def build(destination):
    version = json.loads((ROOT / "plugin.json").read_text())["version"]
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"codemagic-plugin-{version}.zip"
    files = [
        ROOT / name
        for name in (
            "plugin.json",
            "mcp.json",
            ".mcp.json",
            ".claude-plugin/plugin.json",
            ".codex-plugin/plugin.json",
            "LICENSE",
            "README.md",
            "CONTRIBUTING.md",
        )
    ]
    for folder in ("skills", "docs"):
        files.extend(
            p
            for p in (ROOT / folder).rglob("*")
            if p.is_file() and p.suffix in (".py", ".sh", ".md", ".yaml", ".png")
        )
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, path.relative_to(ROOT).as_posix())
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    print(build(args.output_dir))
