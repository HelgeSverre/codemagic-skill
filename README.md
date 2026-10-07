![Codemagic Skill — builds, workflows and artifacts for AI agents](https://raw.githubusercontent.com/HelgeSverre/codemagic-skill/main/docs/assets/header.png)

# Codemagic Skill

[![CI](https://github.com/HelgeSverre/codemagic-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/HelgeSverre/codemagic-skill/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/managed_with-uv-DE5FE9)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/badge/lint%20%26%20format-Ruff-D7FF64)](https://docs.astral.sh/ruff/)
[![Claude Code + Codex](https://img.shields.io/badge/agents-Claude_Code_%2B_Codex-F97316)](#install-the-plugin)
[![PyPI](https://img.shields.io/pypi/v/codemagic-agent-tools)](https://pypi.org/project/codemagic-agent-tools/)
[![MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/HelgeSverre/codemagic-skill/blob/main/LICENSE)

Give your coding agent the tools to operate your Codemagic builds. Find an
app, select a workflow, start a build from a branch or tag, inspect the result,
and locate its artifacts—all through the official Codemagic REST API.

Claude Code and Codex plugin installs include [MCP tools](#mcp-tools) automatically.
The host launches a version-pinned Python server through uvx, which fetches its
dependencies from PyPI on first connection. No hosted service is needed.
The bundled CLI also runs independently with **zero runtime dependencies**.

The package contains three portable skills:

- **`codemagic`** operates apps, workflows, builds and artifacts.
- **`codemagic-setup`** installs prerequisites, verifies MCP/authentication, and
  helps migrate an older manual server registration.
- **`codemagic-signing`** diagnoses iOS/Android signing and helps configure an
  existing project while preserving its signing identity. It distinguishes
  provisioning, Gradle wiring, store permissions and runtime certificate issues.

The signing skill complements the official
[codemagic-init](https://docs.codemagic.io/troubleshooting/codemagic-init/) setup
tool. It does not provision account credentials or start builds merely by loading.

> “Show the latest failed build for my app and which steps failed.”
>
> “Build the staging workflow from `feature/login`.”
>
> “Find the APK and IPA artifacts from that build.”

## Install the plugin

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and make
`uvx` available on the agent host's PATH. Use a current Codex or Claude Code client.
The first MCP connection needs network access to download the pinned package;
uv can also provide Python 3.11+ if needed. Skills-only CLI use needs Python
3.11+ and normal shell access, without uv or the MCP dependencies.

### Claude Code

```sh
claude plugin marketplace add HelgeSverre/codemagic-skill
claude plugin install codemagic@codemagic-tools
```

Start a new session (or `/reload-plugins`) and inspect `/mcp`. The plugin's
server connects automatically. Use `/codemagic:codemagic` for builds, or
`/codemagic:codemagic-setup` for setup help. For a local checkout, try
`claude --plugin-dir /path/to/codemagic-skill`.

### Codex

```sh
codex plugin marketplace add HelgeSverre/codemagic-skill
codex plugin add codemagic@codemagic-tools
```

Start a new session to load the bundled MCP tools and skills. Ask “Use Codemagic
to list my apps” or “Use codemagic-setup to check my installation.” The plugin
forwards `CODEMAGIC_API_KEY` when it is present in the host's environment.

### GitHub Copilot CLI

```sh
copilot plugin install HelgeSverre/codemagic-skill
```

The Agent Plugins manifest and `skills/` directory provide skill discovery.
Automatic MCP startup has been verified in Claude Code and Codex; other hosts
can use the setup skill and their documented MCP configuration.

### Gemini CLI

```sh
gemini skills install https://github.com/HelgeSverre/codemagic-skill.git --path skills
```

Gemini installs the skills directly; it does not need an extension wrapper.
Workspace installations also require a trusted workspace. Skill activation and
shell execution remain subject to Gemini's normal consent and permissions.

### Other agent harnesses

OpenCode, Cursor, Amp, Pi, Goose and current Windsurf/Devin support the portable
skill folder. See the [support matrix and installation recipes](https://github.com/HelgeSverre/codemagic-skill/blob/main/docs/agent-support.md)
for tested discovery results, supported paths and limitations. Cline uses its
own documented skill directory.

The Vercel Skills CLI also discovers this repository. List available skills first,
then choose a target rather than installing into every detected agent:

```sh
npx skills add HelgeSverre/codemagic-skill --list
npx skills add HelgeSverre/codemagic-skill --skill codemagic --agent amp --global
```

For signing guidance, select `--skill codemagic-signing`.

### Install only the skills

Copy a self-contained folder under `skills/` into your client's user skill
directory. This works without plugin support:

```sh
git clone https://github.com/HelgeSverre/codemagic-skill.git
mkdir -p ~/.agents/skills ~/.claude/skills
cp -R codemagic-skill/skills/codemagic ~/.agents/skills/codemagic
cp -R codemagic-skill/skills/codemagic ~/.claude/skills/codemagic
# Optional companion skill, installed independently in the same way:
cp -R codemagic-skill/skills/codemagic-signing ~/.agents/skills/codemagic-signing
```

Use either the plugin or the standalone skill in each client to avoid duplicate
entries. Codex also supports `~/.codex/skills` in installations that use that
location. For development, symlink the skill directory to keep the checkout
canonical; see [Contributing](https://github.com/HelgeSverre/codemagic-skill/blob/main/CONTRIBUTING.md).

## MCP tools

The Claude Code and Codex plugins register MCP automatically. A separate
`mcp add` or `uv tool install` is unnecessary for native plugin installations.
The bundled configuration runs:

```sh
uvx --isolated --python '>=3.11' --from 'codemagic-agent-tools[mcp]==1.3.1' codemagic-mcp
```

The host manages this process; running it directly waits for MCP messages.
Append `--version` to check prerequisites and warm the dependency cache.
If setup fails, ask your agent to use `codemagic-setup`. Authentication uses the
same `CODEMAGIC_API_KEY` or saved login as the CLI.

Tools cover authentication status, teams, apps, workflows, builds, steps,
artifacts, build previews, build starts and cancellation. Previews require no
credentials and send no requests. An enabled plugin may start MCP in each
session; a skills-only install keeps the dependency-free CLI available without
starting an MCP process.

If you previously added a standalone `codemagic` server, verify the plugin's
connection and authentication before removing that duplicate. See
[MCP setup](https://github.com/HelgeSverre/codemagic-skill/blob/main/docs/mcp.md)
for migration, other clients, local development, credentials, and verification.

If Claude suspends with `suspended (tty input)`, check an older custom zsh
credential launcher. Version 1.3.1 adds a tested wrapper and repair guidance;
updating the plugin alone cannot rewrite an existing custom launcher. Follow
the [terminal suspension fix](https://github.com/HelgeSverre/codemagic-skill/blob/main/docs/mcp.md#claude-suspends-with-suspended-tty-input)
or ask your agent to use `codemagic-setup`.

## Authentication

Create a personal API token in Codemagic under **Teams → Personal Account →
Integrations → Codemagic API → Show**. Some UI versions call this **Account
settings → API token**. The token has your account's team permissions.

Expose it as `CODEMAGIC_API_KEY` in the environment that launches your agent or
terminal. `CODEMAGIC_API_TOKEN` and `CM_API_TOKEN` are also supported, in that
order after `CODEMAGIC_API_KEY`.

For a local terminal login, install the CLI below and run:

```sh
codemagic-api auth login
codemagic-api auth status
```

The hidden prompt verifies the token before saving it. On macOS/Linux, the
fallback token file is `~/.config/codemagic-api/token` (or under
`$XDG_CONFIG_HOME`), with permissions `0600`. It is plaintext. Windows uses an
environment variable instead of token-file login. No token belongs in this repo,
plugin manifests, prompts, or shell command arguments.

## Standalone CLI

Install from PyPI with [uv](https://docs.astral.sh/uv/):

```sh
uv tool install codemagic-agent-tools
codemagic-api --help
```

Or run from a checkout without installing anything:

```sh
python3 skills/codemagic/scripts/codemagic_api.py --help
```

| Task | Command |
| --- | --- |
| List teams | `codemagic-api teams` |
| Find team apps | `codemagic-api apps --team TEAM_ID --name my-app` |
| List workflows | `codemagic-api workflows APP_ID` |
| Recent builds | `codemagic-api builds --team TEAM_ID --app APP_ID` |
| Build details | `codemagic-api build BUILD_ID` |
| Step statuses | `codemagic-api actions BUILD_ID` |
| Artifact URLs | `codemagic-api artifacts BUILD_ID` |
| Cancel a build | `codemagic-api cancel BUILD_ID` |

Start a build with the **workflow ID**, which may differ from its display name:

```sh
codemagic-api start --app APP_ID --workflow WORKFLOW_ID \
  --branch feature/login --dry-run

# Submit the same request after reviewing the preview.
codemagic-api start --app APP_ID --workflow WORKFLOW_ID \
  --branch feature/login
```

Use exactly one of `--branch` or `--tag`. `--inputs-file` and
`--environment-file` accept JSON objects for workflow inputs and environment
overrides. List commands return pagination metadata; use `--page` or `--cursor`
to fetch subsequent results. Output is JSON, with diagnostics on stderr.

For other documented JSON endpoints:

```sh
codemagic-api api GET '/teams/TEAM_ID/variable-groups'
codemagic-api api POST '/apps/APP_ID/builds' --data-file request.json --dry-run
```

Read the [API notes](https://github.com/HelgeSverre/codemagic-skill/blob/main/skills/codemagic/references/api.md) for payload formats,
version differences, and endpoint mappings.

## Behavior to know

- A selected workflow can publish to stores or testers. Starting that workflow
  runs its configured publishing steps too.
- A build request accepted with HTTP 202 is queued, not completed. Its ID may
  briefly return 404 while Codemagic creates the build.
- Requests are never retried automatically. After an uncertain build-start
  outcome, check recent builds before submitting again.
- API calls use v3, except cancellation, which still uses Codemagic's documented
  legacy endpoint.
- `actions` returns step statuses and scripts, not full raw logs. `artifacts`
  lists artifact metadata and URLs; it does not download files or create public links.
- Token values, sensitive field names, and environment/input values are redacted
  from responses. Build scripts and artifact URLs can still contain private data.

## Development and verification

```sh
uv sync --locked --extra mcp
uv run --extra mcp ruff check .
uv run --extra mcp ruff format --check .
uv run --extra mcp python -m unittest discover -s tests -v
uv run --extra mcp python scripts/validate_package.py
uv build
uv run --extra mcp python scripts/build_plugin.py
```

CI runs lint, formatting, package validation, and offline tests on macOS, Linux,
and Windows, including MCP discovery and calls over stdio. It also builds the Python wheel/sdist and distributable plugin ZIP.
It does not need a Codemagic token and never starts a real build.

The [PyPI publishing workflow](https://github.com/HelgeSverre/codemagic-skill/blob/main/docs/publishing.md)
validates Python distributions on PRs and publishes on GitHub releases using
Trusted Publishing. Git installation works independently of PyPI. For releases
available on PyPI, use
`uv tool install 'codemagic-agent-tools[mcp]'` for the CLI and MCP server, or
`uv tool install codemagic-agent-tools` for the CLI alone.

See [compatibility verification](https://github.com/HelgeSverre/codemagic-skill/blob/main/docs/compatibility.md) for the tested clients,
test boundaries, and steps to repeat the agent checks. See
[Contributing](https://github.com/HelgeSverre/codemagic-skill/blob/main/CONTRIBUTING.md) for the canonical source layout.

## License and credits

Code and documentation are [MIT licensed](https://github.com/HelgeSverre/codemagic-skill/blob/main/LICENSE). The header illustration was
AI-generated for this project using Codemagic's visual identity as inspiration.
Codemagic names, logos, and other trademarks remain the property of their
respective owners; the software license grants no trademark rights.

**Disclaimer:** This is an unofficial community project. It is not affiliated
with, endorsed by, or sponsored by Codemagic or Nevercode Ltd. Claude and Codex
are trademarks of their respective owners; this project is not endorsed by
Anthropic or OpenAI.
