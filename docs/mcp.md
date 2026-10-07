# Codemagic MCP server

`codemagic-mcp` exposes the shared Codemagic client as typed Model Context Protocol
tools. The agent host launches a local process and exchanges JSON over stdio.
There is no listening port or hosted service to deploy. It works independently
of the skills; install the skills too for workflow and signing guidance.

## Native plugin installation

Current Claude Code and Codex clients automatically load this plugin's MCP
server. Install the plugin using the [README](../README.md#install-the-plugin),
then start a new session. Claude Code also supports `/reload-plugins`.
No separate MCP registration or global Python package install is required.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first and
ensure `uvx` is on the host's PATH. The plugin runs this pinned command:

```sh
uvx --isolated --python '>=3.11' --from 'codemagic-agent-tools[mcp]==1.3.0' codemagic-mcp
```

uvx fetches and caches the package plus its MCP dependencies. It can download a
compatible Python interpreter unless that is disabled by local policy. Initial
startup needs network access; later launches reuse the cache. `--isolated`
prevents an existing global/editable uv tool from overriding the release pin.
Append `--version` to warm the environment if a first launch times out.

The portable declaration is `mcp.json` (Agent Plugins 1.0); Claude uses `.mcp.json`.
The `.codex-plugin/plugin.json` compatibility manifest adds forwarding of
credential environment variable names and `XDG_CONFIG_HOME`. No credential
values are embedded. CI validates the schema and checks that all three launchers
use the same package version. These declarations are included in the plugin ZIP.

Ask the agent to use `codemagic-setup` for missing prerequisites, connection
errors, authentication, or migration. In Claude this is
`/codemagic:codemagic-setup`. A copied skill folder does not register MCP.
Other hosts may load the portable MCP declaration; only Codex and Claude Code
have been tested here for automatic MCP startup.

Sources: [Agent Plugins MCP format](https://agent-plugins.org/specification),
[Claude plugin MCP](https://code.claude.com/docs/en/plugins/components#mcp-servers),
[Codex plugin MCP](https://learn.chatgpt.com/docs/extend/mcp#plugin-provided-mcp-servers).

## Verify and migrate

Inspect `/mcp` in Claude Code or the new session's MCP tools in Codex. Plugin
server/tool names can be prefixed by the host. Call `preview_build` using app
`aaaaaaaaaaaaaaaaaaaaaaaa`, workflow `mobile-build`, branch `feature/example`.
Expect `sent: false`; this requires no account. Then call `auth_status` to verify
credentials separately. Never start a live build merely to test installation.

For an older manually registered server, verify these checks through the
**plugin-provided** tools first. A custom old launcher may be supplying PATH or
shell-only credentials; establish that access for the new host before removal.
Remove only the old standalone entry in the client you are migrating:

```sh
claude mcp remove codemagic --scope user
codex mcp remove codemagic
```

Restart/reload and verify the bundled tools remain connected. Do not run these
commands for a skills-only or standalone-only installation. The plugin never
rewrites global host settings or removes existing registrations automatically.

## Standalone MCP and other clients

For a skills-only installation or a client without plugin MCP support, register
an uvx command directly. Configure only the client you use:

```sh
claude mcp add --scope user --transport stdio codemagic -- uvx --isolated --python '>=3.11' --from 'codemagic-agent-tools[mcp]==1.3.0' codemagic-mcp
codex mcp add codemagic -- uvx --isolated --python '>=3.11' --from 'codemagic-agent-tools[mcp]==1.3.0' codemagic-mcp
```

For standalone Codex, add variable **names**, not values, under
`[mcp_servers.codemagic]` in `~/.codex/config.toml`:

```toml
env_vars = ["CODEMAGIC_API_KEY", "CODEMAGIC_API_TOKEN", "CM_API_TOKEN", "XDG_CONFIG_HOME"]
```

Clients accepting the common `mcpServers` JSON shape can use:

```json
{
  "mcpServers": {
    "codemagic": {
      "command": "uvx",
      "args": ["--isolated", "--python", ">=3.11", "--from", "codemagic-agent-tools[mcp]==1.3.0", "codemagic-mcp"]
    }
  }
}
```

Use an absolute executable path in host settings if uvx is not on PATH. Other
clients may require a different enclosing key or environment-forwarding syntax.
Remote-only connectors need a hosted HTTP server, which this package does not
provide. The CLI remains usable without MCP or uv when Python 3.11+ is installed.

## Local development

The installed plugin always launches its pinned PyPI release. To develop changes
to the server itself, run the checkout explicitly in a separate test client:

```sh
uv sync --locked --extra mcp
uv run --locked --extra mcp codemagic-mcp
```

A host can use `uv` as the command with these arguments:

```json
["run", "--project", "/absolute/path/to/codemagic-skill", "--locked", "--extra", "mcp", "codemagic-mcp"]
```

Running the server in a terminal waits for MCP messages. The plugin ZIP also
contains the Python scripts; they can run beside each other with the MCP extra
installed. CI's `scripts/smoke_plugin_mcp.py` launches the extracted declarations
against the locally built wheel, so an unpublished release can be tested without
changing production configuration or needing credentials.

## Credentials

MCP uses the same precedence as the CLI: `CODEMAGIC_API_KEY`,
`CODEMAGIC_API_TOKEN`, `CM_API_TOKEN`, then the local token file on macOS/Linux.
Verify access using the `auth_status` tool. No tool accepts a token argument or
changes stored credentials.

Desktop apps may not inherit terminal exports. Launch the host from a shell
with the token exported, use its environment forwarding settings, or run
`uvx --isolated --python '>=3.11' --from 'codemagic-agent-tools==1.3.0' codemagic-api auth login`
in your terminal on macOS/Linux. That hidden prompt
stores a plaintext token restricted to your user (mode 0600). Windows requires
environment authentication. Do not paste tokens into chat or checked-in config.

Use saved Codemagic variable groups for signing secrets. If you pass environment
variables or workflow inputs as tool arguments, the host can record those
arguments even though this server redacts their values from results.

## Tools

| Tool | Purpose | Mutates Codemagic? |
| --- | --- | --- |
| `auth_status` | Validate credentials and show their source | No |
| `list_teams` | Discover accessible teams | No |
| `list_apps` | Find personal apps or one team's apps | No |
| `list_workflows` | Get an app's known workflows | No |
| `list_builds` | Filter builds and retain pagination metadata | No |
| `get_build` | Inspect build status/details | No |
| `get_build_actions` | Inspect steps/statuses/scripts, not raw logs | No |
| `get_build_artifacts` | List artifact metadata/URLs, without downloading | No |
| `preview_build` | Validate and redact a proposed request, offline | No |
| `start_build` | Submit a build for exactly one branch or tag | Yes |
| `cancel_build` | Cancel a build through the documented legacy API | Yes |

The server advertises read-only and mutation annotations. Hosts control their
normal approval policies; annotations are hints, not an authorization boundary.
A start can incur build costs and run publishing steps configured in the workflow.
The server never retries API requests. After a timeout or uncertain mutation,
inspect recent builds before considering another submission.

Tools return structured JSON and readable text. Errors are MCP tool errors,
not successful results containing an error string. Auth tokens, sensitive keys,
environment variables and workflow input values are redacted from API results
and build previews. Build scripts and artifact URLs can still be private.

The generic REST escape hatch stays in `codemagic-api api`; the MCP interface
exposes only the documented operations above.

## Verification

```sh
uv sync --locked --extra mcp
uv run --extra mcp python -m unittest discover -s tests -v
```

Tests cover the shared HTTP client and actual MCP calls, including stdio from an
extracted plugin in a path with spaces, current and legacy MCP handshakes,
pagination, invalid arguments, redaction, and uncertain mutation outcomes.
Build submissions and cancellation are mocked. The server uses the
[official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
