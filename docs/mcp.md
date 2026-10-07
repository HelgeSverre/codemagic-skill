# Codemagic MCP server

`codemagic-mcp` exposes the shared Codemagic client as typed Model Context Protocol
tools. The agent host launches a local process and exchanges JSON over stdio.
There is no listening port or hosted service to deploy. It works independently
of the skills; install the skills too for workflow and signing guidance.

## Install

Requires Python 3.11+ and the optional `mcp` dependencies. With uv:

```sh
uv tool install 'codemagic-agent-tools[mcp] @ git+https://github.com/HelgeSverre/codemagic-skill.git'
codemagic-mcp --help
```

This installs both `codemagic-api` and `codemagic-mcp` in an isolated environment.
Add `--upgrade` to upgrade an existing uv installation. A Git commit or tag may
be appended to the Git URL to pin a version that includes MCP support. The
existing v1.1.0 release predates MCP support. No PyPI package is needed.

For the canonical local checkout:

```sh
uv sync --locked --extra mcp
uv run --locked --extra mcp codemagic-mcp
```

Running the server in a terminal appears to wait silently: its input is MCP
messages. Let your agent launch it using the configurations below.

## Claude Code

```sh
claude mcp add --scope user --transport stdio codemagic -- codemagic-mcp
```

Restart the session, inspect `/mcp`, and ask it to call `preview_build` using
app `aaaaaaaaaaaaaaaaaaaaaaaa`, workflow `mobile-build`, branch `feature/example`.
The result must contain `sent: false`. This needs no Codemagic account.

This follows [Claude Code's stdio configuration](https://code.claude.com/docs/en/mcp).
If a desktop-launched client cannot find the executable, use its absolute path
instead of `codemagic-mcp`.

## Codex

```sh
codex mcp add codemagic -- codemagic-mcp
```

For environment authentication, add the variable names under the new entry in
`~/.codex/config.toml`, without storing their values:

```toml
[mcp_servers.codemagic]
command = "codemagic-mcp"
env_vars = ["CODEMAGIC_API_KEY", "CODEMAGIC_API_TOKEN", "CM_API_TOKEN", "XDG_CONFIG_HOME"]
```

Restart the session and make the same preview call. The CLI and desktop app
share this configuration. See the official
[MCP configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

## Other local MCP clients

For clients accepting the common `mcpServers` JSON format, merge this entry into
their MCP settings. Some clients use a different enclosing key; consult that
client's documentation.

```json
{
  "mcpServers": {
    "codemagic": {
      "command": "codemagic-mcp",
      "args": []
    }
  }
}
```

Use an absolute executable path when it is not on the host's PATH. To run a
checkout without a global installation, use `uv` as the command and arguments:

```json
["run", "--project", "/absolute/path/to/codemagic-skill", "--locked", "--extra", "mcp", "codemagic-mcp"]
```

The plugin ZIP also includes `skills/codemagic/scripts/codemagic_mcp.py`. With
the optional SDK installed, that script can run directly beside
`codemagic_api.py`; neither script needs the repository's working directory.
The plugin does not auto-enable MCP or require uv for ordinary skill use.
Remote-only chat connectors need a hosted HTTP server, which this package does
not currently provide.

## Credentials

MCP uses the same precedence as the CLI: `CODEMAGIC_API_KEY`,
`CODEMAGIC_API_TOKEN`, `CM_API_TOKEN`, then the local token file on macOS/Linux.
Verify access using the `auth_status` tool. No tool accepts a token argument or
changes stored credentials.

Desktop apps may not inherit terminal exports. Launch the host from a shell
with the token exported, use its environment forwarding settings, or run
`codemagic-api auth login` in your terminal on macOS/Linux. That hidden prompt
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
