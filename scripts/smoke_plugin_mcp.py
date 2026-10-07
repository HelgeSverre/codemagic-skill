#!/usr/bin/env python3
"""Launch the extracted plugin's MCP declarations against a locally built wheel."""

import argparse
import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZipFile

from mcp import Client
from mcp.client.stdio import StdioServerParameters


async def verify(plugin: Path, wheel_dir: Path):
    with tempfile.TemporaryDirectory(prefix="codemagic-plugin-") as directory:
        root = Path(directory)
        extracted = root / "plugin with spaces"
        with ZipFile(plugin) as archive:
            archive.extractall(extracted)
        version = json.loads((extracted / "plugin.json").read_text())["version"]
        wheel = wheel_dir / f"codemagic_agent_tools-{version}-py3-none-any.whl"
        if not wheel.is_file():
            raise FileNotFoundError(wheel)
        # Test an unpublished release using its wheel. The production declarations
        # remain unchanged and resolve the same pinned version from PyPI.
        env = {
            "UV_FIND_LINKS": str(wheel_dir),
            "UV_CACHE_DIR": str(root / "uv-cache"),
            "XDG_CONFIG_HOME": str(root / "empty-config"),
            "CODEMAGIC_API_KEY": "",
            "CODEMAGIC_API_TOKEN": "",
            "CM_API_TOKEN": "",
        }
        for path in ("mcp.json", ".mcp.json", ".codex-plugin/plugin.json"):
            config = json.loads((extracted / path).read_text())["mcpServers"]["codemagic"]
            params = StdioServerParameters(
                command=config["command"], args=config["args"], cwd=extracted, env=env
            )
            result = subprocess.run(
                [params.command, *params.args, "--version"],
                cwd=extracted,
                env={**os.environ, **env},
                capture_output=True,
                text=True,
                check=True,
                timeout=120,
            )
            assert result.stdout.strip() == version, result.stdout
            async with Client(params, read_timeout_seconds=60) as client:
                tools = (await client.list_tools()).tools
                assert len(tools) == 11
                preview = await client.call_tool(
                    "preview_build",
                    {
                        "app_id": "a" * 24,
                        "workflow_id": "mobile-build",
                        "branch": "feature/plugin-check",
                    },
                )
                assert not preview.is_error, preview
                assert preview.structured_content["sent"] is False
                assert preview.structured_content["body"]["branch"] == "feature/plugin-check"
                auth = await client.call_tool("auth_status", {})
                assert auth.is_error, "Expected an unauthenticated, isolated server"
            print(f"{path}: version {version}, 11 tools, offline preview passed", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin", type=Path, required=True)
    parser.add_argument("--wheel-dir", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(verify(args.plugin.resolve(), args.wheel_dir.resolve()))
