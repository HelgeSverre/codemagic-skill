# Contributing

The Git repository is the canonical source. Keep the API implementation at
`skills/codemagic/scripts/codemagic_api.py`; the Python package entry point and
both agent plugins use this same file. The optional MCP adapter lives beside it
in `codemagic_mcp.py` and shares authentication, HTTP handling, and build validation. The skill must remain usable when its
folder is copied on its own, without the rest of the repository.

## Local setup

```sh
uv sync --locked --extra mcp
uv run --extra mcp ruff check .
uv run --extra mcp ruff format .
uv run --extra mcp python -m unittest discover -s tests -v
uv run --extra mcp python scripts/validate_package.py
```

To develop the command globally from this checkout:

```sh
uv tool install --editable '.[mcp]'
```

For a standalone skill installation, link `skills/codemagic` into
`~/.agents/skills/codemagic` for Codex or `~/.claude/skills/codemagic` for Claude.
Do not replace an existing installation without preserving its local notes.
Plugin developers can use `claude --plugin-dir .` or add this checkout as a local
Codex marketplace.

Keep credentials and account-specific IDs out of the public skill. Local context
can live under `~/.config/codemagic-api/context.md`, which agents read only when
relevant to the requested account.

## Tests and releases

Tests mock HTTP responses and cover request contracts, credential precedence,
redaction, cancellation, pagination, and uncertain request outcomes. MCP tests also
exercise schemas, tool annotations, and stdio with current and legacy handshakes. Package
validation checks the portable manifest against the vendored Agent Plugins
schema and verifies that the two marketplace catalogs resolve to the same plugin.
Archive tests extract the plugin and run the bundled CLI from another directory.

The vendored `schemas/plugin.schema.json` is the published
[Agent Plugins 1.0 schema](https://agent-plugins.org/schemas/1.0.0/plugin.schema.json).
Refresh it deliberately when changing the manifest format, and rerun validation.

Run the real-client checks in [docs/compatibility.md](docs/compatibility.md) after
changing skill discovery, manifests, or bundled paths. Use synthetic IDs and
`--dry-run`; a live start/cancel is not needed to verify packaging.

Keep versions aligned in `pyproject.toml`, `plugin.json`,
`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and the CLI's
`VERSION` constant. Run `uv lock` after changing project metadata or dependencies.

```sh
uv build
uv run --extra mcp python scripts/build_plugin.py
```

Publish the GitHub repository or attach the plugin ZIP and Python distributions
to a release after verification. PyPI publication and official plugin-directory
submission are separate steps; neither is configured automatically.
