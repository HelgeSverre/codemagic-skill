# Compatibility verification

The plugin is tested at three levels: API client behavior with mocked transport,
distribution artifacts extracted into a clean directory, and actual skill use
in Claude Code and Codex. None of those checks needs a live build mutation.

## Repeatable local checks

```sh
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
uv run python scripts/validate_package.py
claude plugin validate --strict .
claude plugin validate --strict .claude-plugin/plugin.json
uv build
uv run python scripts/build_plugin.py
```

The tests run the bundled CLI after copying only the skill, and after extracting
the plugin ZIP into a path containing spaces. Synthetic IDs and `--dry-run`
verify branch selection and request construction without credentials.

## Real-client smoke test

Load the plugin in a fresh session. Ask the agent to use its installed Codemagic
skill to preview a build for app `aaaaaaaaaaaaaaaaaaaaaaaa`, workflow `mobile-build`,
and branch `feature/compatibility-check`. Require `--dry-run`, and check that it
actually executes the bundled CLI and returns `sent: false`. The request should
be POST `/api/v3/apps/aaaaaaaaaaaaaaaaaaaaaaaa/builds`, with `workflow_id` and
`branch` in the JSON body.

For Claude Code, use `claude --plugin-dir /absolute/path/to/checkout` or install
from the local marketplace. For Codex, add the checkout as a local marketplace
and install `codemagic@codemagic-tools` before starting a fresh session.

Check the client's tool-call transcript, not just its final claim. A passing
preview verifies discovery, skill-relative path resolution, Python execution,
and payload construction. It does not verify live start/cancel permissions.

## Verification record

Verified on macOS on **2026-10-07**:

| Surface | Version | Result |
| --- | --- | --- |
| Claude Code | 2.1.291 | Strict plugin/marketplace validation; local marketplace installation; skill invocation and bundled CLI dry-run passed |
| Codex CLI | 0.160.1 | Local marketplace installation; installed plugin skill discovery and bundled CLI dry-run passed |
| Python | 3.11.15 | 19 offline tests passed, including standalone skill and extracted ZIP |
| Ruff | 0.16.10 | Lint and formatting checks passed |
| Python distributions | 1.0.0 | Wheel and sdist built; isolated wheel installation and CLI invocation passed |
| Agent Plugins manifest | 1.0.0 schema | Portable manifest validated against the vendored official schema |

Both agent transcripts contained an actual command execution, not just a proposed
command. Claude invoked the namespaced Skill tool and used the local plugin's
bundled script. Codex loaded the skill from its installed marketplace cache and
ran the script in an empty environment. Both returned this result:

```json
{
  "method": "POST",
  "url": "https://codemagic.io/api/v3/apps/aaaaaaaaaaaaaaaaaaaaaaaa/builds",
  "body": {
    "workflow_id": "mobile-build",
    "branch": "feature/compatibility-check"
  },
  "sent": false
}
```

GitHub Actions separately records the Python 3.11/3.14 test matrix on macOS,
Linux, and Windows. This record does not claim that a Claude Desktop chat
connector, Codex cloud runtime, or other agent host was tested.

Authentication and read-only endpoints were verified against the official API
during initial development. Credentials and account-specific results are kept
outside the repository. No live build is required to repeat the package tests.
