# Compatibility verification

The plugin is tested at three levels: API client behavior with mocked transport,
distribution artifacts extracted into a clean directory, and actual skill use
in Claude Code and Codex. None of those checks needs a live build mutation.

## Repeatable local checks

```sh
uv sync --locked --extra mcp
uv run --extra mcp ruff check .
uv run --extra mcp ruff format --check .
uv run --extra mcp python -m unittest discover -s tests -v
uv run --extra mcp python scripts/validate_package.py
claude plugin validate --strict .
claude plugin validate --strict .claude-plugin/plugin.json
uv build
uv run --extra mcp python scripts/build_plugin.py
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

## MCP verification

Verified on macOS on **2026-10-07** with the MCP feature branch:

| Surface | Result |
| --- | --- |
| Official MCP Python SDK 2.3.0 (lockfile) | All 26 CLI, MCP, and distribution tests passed |
| Minimum supported SDK 2.2.0 | All seven MCP tests passed |
| Stdio protocol | Extracted plugin served 11 tools to current and legacy clients from a path containing spaces |
| Claude Code 2.1.291 | Connected and directly called `mcp__codemagic__preview_build`; returned `sent: false` |
| Codex CLI 0.160.1 | Connected and directly called `codemagic.preview_build`; returned `sent: false` |
| Installed wheel | CLI ran without the extra; MCP server loaded with the extra |
| Live Codemagic reads | MCP `auth_status` and `list_teams` succeeded using environment authentication |

The actual agent transcripts contain MCP tool calls, not CLI commands. Both
clients used synthetic app `aaaaaaaaaaaaaaaaaaaaaaaa`, workflow `mobile-build`,
and branch `feature/mcp-check`. Their requests used only `preview_build`.
No live build was started or canceled. Local transcripts and authentication
configuration are excluded from the repository.

The server was registered in both clients' user configuration for future
sessions. These checks do not establish support for hosted HTTP connectors or
Claude Desktop; installation recipes for untested hosts are examples only.
See [MCP setup](mcp.md) to repeat the tests or register the server.

## Automatic plugin MCP (1.3.0)

Verified on macOS on **2026-10-07** with uv 0.12.18:

| Surface | Result |
| --- | --- |
| Claude Code 2.1.291 | Loaded an extracted plugin through `--plugin-dir`; `plugin:codemagic:codemagic` connected and its namespaced `preview_build` returned `sent: false` |
| Codex CLI 0.160.1 | Installed the extracted plugin from a temporary local marketplace; a fresh session with only that plugin enabled called its MCP `preview_build`, returning `sent: false` |
| Package verification | All three launcher declarations ran version 1.3.0 through uvx, discovered 11 tools, passed an offline preview, and correctly reported missing authentication |
| Validation | All 26 existing tests, Ruff, strict Claude manifest validation, setup-skill validation, Agent Plugins MCP schema checks, and Twine passed |

The native client transcripts contain actual MCP calls. Codex ignored the user's
usual config during the test, so the previous standalone server could not satisfy
the request. Claude called `mcp__plugin_codemagic_codemagic__preview_build`.
Before publication, `UV_FIND_LINKS` pointed to the locally built wheel; the
temporary Codex compatibility manifest forwarded that test-only variable. The
published manifests resolve the identical version pin through PyPI and do not
forward that test variable. These checks did not start or cancel a build.

CI repeats extracted-plugin launcher checks using the built wheel and a fresh
uv cache. Real-host registration is a separate manual smoke test; CI does not
claim to run authenticated Codex or Claude sessions on every operating system.

## Terminal ownership regression (1.3.1)

Verified on macOS on **2026-10-07**:

- A custom `zsh -ic` credential launcher temporarily took the host's foreground
  terminal while loading startup files, even with piped MCP stdin/stdout.
- Changing that launcher to `zsh +m -ic` preserved terminal ownership and
  authenticated MCP access. Claude Code 2.1.292 started successfully in both
  classic and fullscreen rendering modes after the repair.
- The extracted plugin's new `with_zsh_env.sh` passed a real PTY regression test,
  checking ownership inside `.zshrc` as well as after startup. A plain `zsh -ic`
  negative control demonstrated the original takeover. The test also checked
  exports, stdin, stdout isolation, argument boundaries, and exit status.
- All three bundled MCP declarations launched the built 1.3.1 wheel through uvx,
  exposed 11 tools, and passed offline build previews.

The terminal tests run on macOS/Linux with zsh and skip Windows, where this
shell helper does not apply. The native declarations continue to launch uvx
directly. The setup skill describes repairing existing custom launchers;
package installation does not alter those user-owned files.
