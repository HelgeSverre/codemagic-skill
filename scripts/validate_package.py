#!/usr/bin/env python3
"""Validate plugin metadata, skill paths, and release version consistency."""

import json
import re
import tomllib
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]


def validate():
    manifest = json.loads((ROOT / "plugin.json").read_text())
    schema = json.loads((ROOT / "schemas/plugin.schema.json").read_text())
    jsonschema.validate(manifest, schema)
    claude = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    source = (ROOT / "skills/codemagic/scripts/codemagic_api.py").read_text()
    version = re.search(r'^VERSION = "([^"]+)"', source, re.M).group(1)
    assert version == project["version"] == manifest["version"] == claude["version"]
    assert manifest["name"] == claude["name"] == "codemagic"
    assert {k: v for k, v in manifest.items() if k != "$schema"} == claude
    codex = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
    assert {k: v for k, v in codex.items() if k != "mcpServers"} == claude
    portable_mcp = json.loads((ROOT / "mcp.json").read_text())
    mcp_schema = json.loads((ROOT / "schemas/mcp.schema.json").read_text())
    jsonschema.validate(portable_mcp, mcp_schema)
    claude_mcp = json.loads((ROOT / ".mcp.json").read_text())
    expected_server = {
        "command": "uvx",
        "args": [
            "--isolated",
            "--python",
            ">=3.11",
            "--from",
            f"codemagic-agent-tools[mcp]=={version}",
            "codemagic-mcp",
        ],
    }
    assert portable_mcp["mcpServers"] == {"codemagic": {"type": "stdio", **expected_server}}
    assert claude_mcp == {"mcpServers": {"codemagic": expected_server}}
    assert codex["mcpServers"] == {
        "codemagic": {
            **expected_server,
            "env_vars": [
                "CODEMAGIC_API_KEY",
                "CODEMAGIC_API_TOKEN",
                "CM_API_TOKEN",
                "XDG_CONFIG_HOME",
            ],
        }
    }
    for name in (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"):
        catalog = json.loads((ROOT / name).read_text())
        assert catalog["name"] == "codemagic-tools"
        for plugin in catalog["plugins"]:
            location = plugin["source"]
            if isinstance(location, dict):
                assert location["source"] == "local"
                location = location["path"]
            assert (ROOT / location).resolve() == ROOT
            assert plugin["name"] == manifest["name"]
            assert plugin.get("version", version) == version
    for skill in sorted((ROOT / "skills").iterdir()):
        if not skill.is_dir():
            continue
        text = (skill / "SKILL.md").read_text()
        metadata = yaml.safe_load(text.split("---", 2)[1])
        assert metadata["name"] == skill.name and metadata["description"]
        for link in re.findall(r"\]\((references/[^)]+)\)", text):
            assert (skill / link).is_file(), f"Missing skill reference: {link}"
    for path in (ROOT / "skills").rglob("*"):
        if path.is_file() and path.suffix in (".md", ".py", ".sh", ".yaml"):
            contents = path.read_text()
            assert "/Users/" not in contents, f"Machine-specific path in {path}"
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        assert isinstance(yaml.safe_load(path.read_text()), dict)
    assert (ROOT / "docs/assets/header.png").is_file()
    print(f"Plugin, marketplaces, skill, and version {version}: valid")


if __name__ == "__main__":
    validate()
