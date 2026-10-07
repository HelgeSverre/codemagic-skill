# Contributing

The Git repository is the canonical source. Keep the API implementation at
`skills/codemagic/scripts/codemagic_api.py`; the Python package entry point and
both agent plugins use this same file. The optional MCP adapter lives beside it
in `codemagic_mcp.py` and shares authentication, HTTP handling, and build
validation. The skill must remain usable when its folder is copied on its own,
without the rest of the repository.

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
exercise schemas, tool annotations, and stdio with current and legacy handshakes.
Package validation checks the portable manifest against the vendored Agent Plugins
schemas and verifies that the two marketplace catalogs resolve to the same plugin.
Archive tests extract the plugin and run the bundled CLI from another directory.
The package CI job also runs every bundled MCP launcher against the built wheel
using an isolated uv cache and an extracted path containing spaces.
On macOS/Linux with zsh available, a PTY regression test checks that the extracted
credential wrapper preserves terminal ownership during shell startup, keeps
startup output off stdout, and forwards stdin, arguments, exports, and exit status.
A plain interactive-zsh control must demonstrate the original terminal takeover.

The vendored `schemas/plugin.schema.json` and `schemas/mcp.schema.json` follow the published
[Agent Plugins 1.0 schema](https://agent-plugins.org/schemas/1.0.0/plugin.schema.json).
Refresh it deliberately when changing the manifest format, and rerun validation.

Run the real-client checks in [docs/compatibility.md](docs/compatibility.md) after
changing skill discovery, manifests, or bundled paths. Use synthetic IDs and
`--dry-run`; a live start/cancel is not needed to verify packaging.

Keep versions aligned in `pyproject.toml`, `plugin.json`,
`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, all MCP launcher pins and setup examples, and the CLI's
`VERSION` constant. Run `uv lock` after changing project metadata or dependencies.

```sh
uv build
uv run --extra mcp python scripts/build_plugin.py
```

Publish a GitHub release from `main` with a tag matching the package version
(for example, `v1.2.0`). `.github/workflows/publish.yml` validates and builds
Python distributions, then uploads them to PyPI using Trusted Publishing.
Set up the pending publisher once using the exact fields in
[Publishing](docs/publishing.md). No PyPI API token or repository secret is needed.
PRs and manual workflow runs build and validate without publishing.

Attach the plugin ZIP from the successful CI run to the GitHub release. The ZIP
is not uploaded to PyPI. Official plugin-directory submission remains separate.
