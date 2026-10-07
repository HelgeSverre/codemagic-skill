# Agent distribution research

Research and checks dated **2026-10-07**. The objective was to find useful
distribution paths for the existing package without duplicating skills or adding
a service solely for compatibility.

The questions were: can a harness install the whole skill and its resources,
which extra packaging does it need, what can be verified locally, and where
would maintenance exceed the benefit? Primary documentation and current source
were used for the matrix below. Discovery is distinct from a successful model
invocation or authenticated API operation.

## Recommendation and evidence

Keep one `skills/` tree. The
[Agent Skills specification](https://agentskills.io/specification) includes
bundled scripts and references, so Python is a runtime prerequisite rather than
a reason to build one adapter per agent.

| Harness | Recommended distribution | Evidence and confidence |
| --- | --- | --- |
| Claude Code | Existing native plugin/marketplace | High: installed plugin and real skill execution verified; see [record](compatibility.md) |
| Codex | Existing Agent Plugin/marketplace | High: installed plugin and real skill execution verified |
| GitHub Copilot CLI | Existing root Agent Plugin | High: CLI 1.0.93-2 discovered the local plugin and skill |
| Gemini CLI | Native Git skill installer, `--path skills` | High: CLI 0.61.0 installed/discovered the skill in an isolated trusted workspace; bundled CLI version check passed |
| OpenCode | Portable skill directory | High: 1.18.30 discovered the skill through an isolated configuration directory |
| Amp | Native skill installer or portable skill directory | High: 0.0.1791173172-g3e7691 discovered both skills in a temporary workspace |
| Pi | Portable skills or Git package | High for official format documentation; runtime discovery not tested |
| Cursor | Portable skills or Agent Plugin | High for documented formats; GitHub/team marketplace root-plugin import not tested |
| Windsurf / Devin Desktop | Portable skills; legacy Windsurf paths remain documented | High for current docs; no local runtime test |
| Goose | Portable skill directory | High for official docs; no local runtime test |
| Cline | `.cline/skills/` directory | High for its documented native path; avoid an installer whose mapping is not corroborated by Cline docs |

Python 3.11+ and normal shell/file permissions are needed to run the API helper.
Authenticated operations additionally need the user's Codemagic token. Discovery
checks do not establish credential propagation, hosted-agent support, successful
builds, or native signing tools on every platform.

Version 1.3.0 adds automatic plugin MCP startup in Codex and Claude Code, plus
the portable `codemagic-setup` skill. Skills-only installers do not register MCP;
use that skill for prerequisites and host-specific registration. See
[MCP setup](mcp.md) and the [verification record](compatibility.md) for the tested
scope. The earlier discovery results below concern skills, not automatic MCP.

## Native installation recipes

**Copilot CLI** recognizes the existing root `plugin.json` and `skills/`; it can
also use the Claude marketplace catalog. No Copilot-specific manifest is needed:

```sh
copilot plugin install HelgeSverre/codemagic-skill
```

Copilot's cloud/app support is documented separately. A consuming repository can
enable a marketplace in its `.github/copilot/settings.json`; that does not imply
this project's local test covered cloud execution or cloud credentials. Sources:
[plugin reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference),
[installation](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-finding-installing),
[configuration](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference).

**Gemini CLI** can install the skills without an extension:

```sh
gemini skills install https://github.com/HelgeSverre/codemagic-skill.git --path skills
```

Use `--scope workspace` for a workspace installation. Trust that workspace before
expecting its skills to load; skill activation and execution still use Gemini's
permissions. An extension wrapper would introduce separate settings/environment
handling without improving this package's current capabilities. Sources:
[creating/installing skills](https://geminicli.com/docs/cli/creating-skills/),
[skill usage](https://geminicli.com/docs/cli/using-agent-skills/),
[workspace trust](https://geminicli.com/docs/cli/trusted-folders/).

**Amp** offers a repository installer:

```sh
amp skill add HelgeSverre/codemagic-skill --global
```

Its documented skill discovery includes `~/.config/agents/skills`,
`~/.agents/skills` and project `.agents/skills`. See
[Amp skills](https://ampcode.com/docs/customize/skills).

**Pi** documents Git packages and convention-based `skills/` discovery:

```sh
pi install git:github.com/HelgeSverre/codemagic-skill
```

This recipe is documentation-backed, not locally executed. A Pi-specific npm
package is unnecessary for this layout. See
[Pi packages](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md)
and [Pi skills](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md).

## Portable folders and multi-agent installation

Copy the **whole skill folder**, including scripts/references. Do not install
only a raw `SKILL.md` URL. Choose either a native plugin or a standalone skill in
a given client to avoid duplicate discovery.

| Harness | Documented project / user paths | Primary source |
| --- | --- | --- |
| OpenCode | `.agents/skills/` / `~/.agents/skills/`; native `~/.config/opencode/skills/` | [Skills](https://docs.opencode.ai/docs/skills/) |
| Cursor | `.cursor/skills/` / `~/.cursor/skills/`; also `.agents/skills/` equivalents | [Skills](https://cursor.com/docs/skills) |
| Pi | `.agents/skills/` / `~/.agents/skills/`; native `.pi/skills/` / `~/.pi/agent/skills/` | [Skills](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md) |
| Windsurf / Devin | `.agents/skills/` / `~/.agents/skills/`; native `.devin/skills/`; legacy `.windsurf/skills/` | [Current docs](https://docs.devin.ai/desktop/cascade/skills) |
| Goose | `.agents/skills/` / `~/.agents/skills/` | [Skills](https://github.com/aaif-goose/goose/blob/main/documentation/docs/guides/context-engineering/using-skills.md) |
| Cline | `.cline/skills/` / `~/.cline/skills/` | [Skills](https://docs.cline.bot/customization/skills) |

The [Vercel Skills CLI](https://github.com/vercel-labs/skills) already discovers
this repository layout. Use `npx skills add HelgeSverre/codemagic-skill --list`,
then select the desired skill and agent with `--skill` and `--agent`; `--global`
chooses a user installation. Avoid `--all` as the default example. Its broad
agent list is not a compatibility guarantee from this project. In particular,
the current Cline mapping to `.agents/skills` is not corroborated by Cline's
listed paths, so use Cline's native directory.

## Deliberately deferred

- **Cursor marketplace submission:** its Agent Plugin format is compatible,
  but public listing requires submission/review. GitHub/team import documents
  a Cursor marketplace manifest; root-plugin behavior needs client verification
  before adding a wrapper. See [Cursor plugins](https://prod.cursor.com/docs/plugins)
  and [plugin reference](https://prod.cursor.com/docs/reference/plugins).
- **Gemini extension / OpenCode JavaScript plugin / Pi npm package:** each adds
  metadata or behavior to maintain while their native skill support already fits.
- **MCP rewrite:** useful if a target cannot execute local scripts, but the
  researched local harnesses do not require it. Hosted runtimes need separate
  credential/network verification before a support claim.

## Signing skill decision

A general setup guide would duplicate the official
[codemagic-init](https://docs.codemagic.io/troubleshooting/codemagic-init/)
project generator and knowledge installer. We instead added `codemagic-signing`,
a focused setup/diagnosis skill with platform references.

Its value is resolving identities and failure stages: iOS API authentication
versus certificate private keys and per-target profiles; Android upload keys
versus Play distribution keys; and Gradle signing versus store/API permissions.
See its [iOS](../skills/codemagic-signing/references/ios.md) and
[Android](../skills/codemagic-signing/references/android.md) references for the
primary evidence and bounded checks. It supplies no credential-generation or
key-rotation automation. Historical vendor blogs were useful background, but
current Apple, Android, Google Play and Codemagic documentation governs the recipes.
For example, the [Android walkthrough](https://blog.codemagic.io/the-simple-guide-to-android-code-signing/)
and [iOS walkthrough](https://blog.codemagic.io/how-to-code-sign-publish-ios-apps/)
help explain the process but are not the source for current console flows.
