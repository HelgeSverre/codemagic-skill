---
name: codemagic-setup
description: Install or repair the Codemagic plugin's MCP connection, uv runtime, and authentication. Use for initial setup, missing Codemagic tools, or migration from a manually registered server.
---

# Set up Codemagic tools

Native Codex and Claude Code plugin installs include an MCP declaration. The
host launches `uvx` and downloads a pinned Python package on first connection.
No separate global Python package installation or `mcp add` is needed for those
plugin installs. A copied skill folder does not register MCP.

First identify the host and whether this is a native plugin, a skills-only
installation, or an existing standalone MCP server. Preserve working unrelated
configuration. For an ordinary build/status request with unavailable MCP, use
the `codemagic` skill's CLI fallback if installed; repair installation when the
user requests setup or troubleshooting.

## Runtime and connection

1. Check `uvx --version` in the environment that launches the host. If missing,
   install uv within the requested setup scope using the appropriate method in
   the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).
   Restart a desktop host after changing PATH. Python 3.11+ is required; uv can
   download a compatible interpreter when its Python-download policy allows it.
2. Warm the release's environment and check the executable:

   ```sh
   uvx --isolated --python '>=3.11' --from 'codemagic-agent-tools[mcp]==1.3.0' codemagic-mcp --version
   ```

   First launch requires network access to PyPI or a configured package mirror.
   Do not remove `--isolated`: an existing editable/global uv tool installation
   must not override the release's package. If this version has not reached PyPI,
   inspect the release's publishing status instead of changing the pin silently.
3. For native plugins, start a new Codex session or run `/reload-plugins` in
   Claude Code. Inspect the host's MCP status (`/mcp` in Claude). A plugin server
   may have a namespaced name; find its `preview_build` tool.
4. Call `preview_build` for app `aaaaaaaaaaaaaaaaaaaaaaaa`, workflow
   `mobile-build`, branch `feature/setup-check`. Expect `sent: false`. This
   verifies tools without credentials or a live build. Do not use `start_build`
   or `cancel_build` to test installation.

If uv works in a terminal but MCP fails, inspect the host's startup error and
PATH. A first download can exceed the host's timeout; warm it with the version
command above, then reconnect. Do not patch an installed plugin cache: updates
replace it. Use supported host settings or retain the CLI fallback.

## Authentication

Call MCP `auth_status` after connection. Credentials are read in this order:
`CODEMAGIC_API_KEY`, `CODEMAGIC_API_TOKEN`, `CM_API_TOKEN`, then the saved CLI
login on macOS/Linux. The native Codex manifest forwards those variable names
and `XDG_CONFIG_HOME`; the variables must exist in the host process environment.
GUI apps may not inherit an interactive shell's exports.

Reuse the user's existing credential source. Never print tokens, inspect shell
startup files to extract them, or put values in plugin manifests, tool arguments,
or chat. If the token exists only in terminal startup configuration, launch the
host from that environment or have the user run this hidden-input login in
their own terminal on macOS/Linux:

```sh
uvx --isolated --python '>=3.11' --from 'codemagic-agent-tools==1.3.0' codemagic-api auth login
```

Login validates and saves a plaintext token with mode 0600 at
`${XDG_CONFIG_HOME:-~/.config}/codemagic-api/token`. Windows uses environment
authentication. Do not ask the user to paste the token into the conversation.
Verify with `auth_status`; a successful preview alone does not establish login.

## Skills-only or standalone MCP

If the user chose a skills-only install or a client without native plugin MCP,
register the same command with that client's documented MCP settings. For a
standalone installation in Claude Code or Codex:

```sh
claude mcp add --scope user --transport stdio codemagic -- uvx --isolated --python '>=3.11' --from 'codemagic-agent-tools[mcp]==1.3.0' codemagic-mcp
codex mcp add codemagic -- uvx --isolated --python '>=3.11' --from 'codemagic-agent-tools[mcp]==1.3.0' codemagic-mcp
```

Configure only the requested host. For standalone Codex, set
`env_vars = ["CODEMAGIC_API_KEY", "CODEMAGIC_API_TOKEN", "CM_API_TOKEN", "XDG_CONFIG_HOME"]`
under `[mcp_servers.codemagic]` in its config, preserving other settings. These
are names, never credential values. Reconnect and run the same preview/auth checks.

## Migrate an older manual registration

Check both the plugin-provided and standalone server entries. Verify the plugin
server's preview and authentication before removing the old registration. If
the old entry uses a custom launcher, account for its PATH/credential handling
first. During a requested migration, remove only the identified duplicate:

```sh
claude mcp remove codemagic --scope user
codex mcp remove codemagic
```

Do not run either removal when it is the only working connection or belongs to
a different installation. Restart/reload and verify the plugin tools remain.
