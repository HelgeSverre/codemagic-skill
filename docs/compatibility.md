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

## Additional harness checks

The 2026-10-07 distribution survey added these local discovery checks. They did
not install into the user's global skill directories, invoke a model, or contact
Codemagic. Sources and installation recipes are in [agent support](agent-support.md).

| Client | Version | Observed result |
| --- | --- | --- |
| GitHub Copilot CLI | 1.0.93-2 | `--plugin-dir` discovered the plugin; `skill list --json` found both bundled skills |
| Gemini CLI | 0.61.0 | Workspace-scoped skill install in an isolated Gemini home copied `codemagic` and its resources; discovery succeeded after trusting the temporary workspace; bundled CLI returned 1.0.0 |
| OpenCode | 1.18.30 | `--pure debug skill` with an isolated configuration found the canonical `codemagic` skill and parsed its instructions |
| Amp | 0.0.1791173172-g3e7691 | `amp skills list --json` in a temporary `.agents/skills` workspace found both skills as `workspace-agents` |

Pi, Cursor, Windsurf/Devin, Goose and Cline have documentation-backed recipes;
they were not executed. No additional harness has been verified here for live
API credentials, hosted operation or actual build submission.

## Signing skill behavior checks

Two independent agent evaluations used only synthetic configuration and the
new skill's platform reference. Neither had account access or mutation permission.

- **iOS extension + App Groups:** identified the missing extension profile and
  stale main profile, retained the working distribution identity, and recommended
  checking existing Apple profiles before authorized profile repair/import.
- **Android sign-in only failing from Play:** identified the missing OAuth
  package/certificate pairing for the Play app-signing key; retained the valid
  upload keystore and publishing service account.

These checks exercise diagnosis and scope decisions. They do not prove an actual
app was signed, a store accepted a new configuration, or that the skill
outperforms an agent without it. No real signing material was used.
