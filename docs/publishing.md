# Publishing Python packages to PyPI

The repository uses PyPI Trusted Publishing through GitHub Actions. GitHub
provides a short-lived identity token; no PyPI API token, password, or GitHub
secret is needed. See the official
[PyPI Trusted Publishing documentation](https://docs.pypi.org/trusted-publishers/using-a-publisher/).

## One-time PyPI setup

Sign in to PyPI and open
[account Publishing settings](https://pypi.org/manage/account/publishing/).
Under **Add a new pending publisher**, choose **GitHub** and enter:

| PyPI field | Value |
| --- | --- |
| PyPI Project Name | `codemagic-agent-tools` |
| Owner | `HelgeSverre` |
| Repository name | `codemagic-skill` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

The workflow field is the filename only, not `.github/workflows/publish.yml`
and not the display name "Publish to PyPI". The owner is the GitHub owner,
not your PyPI username. Keep the environment value exactly `pypi`.

Submit **Add**. A pending publisher creates the project during the first
successful upload and becomes its normal publisher automatically; you do not
need to upload manually first. Pending publishers do not reserve project names.
See [PyPI's first-project guide](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).

If this project already exists under your PyPI account, use **Your projects →
codemagic-agent-tools → Manage → Publishing** and add the same GitHub publisher
there, without the project-name field.

## GitHub environment

The workflow refers to the repository environment named `pypi`. It is configured
under **Settings → Environments → pypi**, with deployment restricted to tags
matching `v*`. There are no repository credentials to copy into it. The
release workflow separately verifies that the tagged commit belongs to `main`
and its tag equals `v` followed by the package version.

For a fork, create that environment and tag rule, configure a publisher for your
own repository/package, and update the repository guard and package URL in
`.github/workflows/publish.yml`.

## Release process

1. Update the version in `pyproject.toml`, `plugin.json`,
   `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`,
   `.claude-plugin/marketplace.json`, all MCP launcher package pins, the setup
   skill and documentation examples, the CLI's
   `VERSION`, and the standalone distribution test. Run `uv lock`.
2. Let the PR checks pass and merge into `main`.
3. Create and **publish** a GitHub release using the matching version tag, for
   example `v1.3.1` for version `1.3.1`, targeting the merged commit on `main`.
4. Watch **Actions → Publish to PyPI**. Its build job validates manifests and
   versions, runs Ruff and offline tests, builds the wheel/sdist, checks the
   rendered-description metadata with Twine, and smoke-tests both CLI and MCP.
5. The upload job downloads only those Python distributions and publishes them
   through the `pypi` environment with OIDC and digital attestations.

Only a `release: published` event in the canonical repository can upload.
Pushing a commit or tag alone does not publish to PyPI. PR checks and **Run
workflow** build and validate only; they never obtain publishing credentials.
The manual workflow appears after the workflow file is merged into the default
branch. A release published before this workflow existed must not be retagged
just to trigger it; publish the next version instead.

Pre-releases are also published when their GitHub release is published. Use a
valid Python version such as `1.3.1rc1` and the exact matching tag `v1.3.1rc1`.
No builds run against the real Codemagic API during packaging or release tests.

The plugin ZIP belongs on the GitHub release; PyPI receives only the Python
wheel and source archive. The existing CI `distributions` artifact contains
the ZIP and Python packages. The publishing workflow's separate
`pypi-distributions` artifact contains only Python packages. Do not upload the
plugin ZIP to PyPI.

Wait for the PyPI upload and an isolated uvx version check to succeed before
announcing the release or updating installed plugins. The new plugin pins the
matching PyPI version and cannot start MCP until that version is published.
If publishing fails, repair the release workflow before promoting the plugin.

## Verify publication

After the upload succeeds, open
[the PyPI project](https://pypi.org/project/codemagic-agent-tools/) and check the
version, README, and provenance. Test from a clean environment:

```sh
uvx --isolated --python '>=3.11' --from 'codemagic-agent-tools==1.3.1' codemagic-api --version
uvx --isolated --python '>=3.11' --from 'codemagic-agent-tools[mcp]==1.3.1' codemagic-mcp --version
```

For persistent installation:

```sh
uv tool install 'codemagic-agent-tools[mcp]'
```

Use `--upgrade` with `uv tool install` for an existing uv installation. Clients
already configured to launch `codemagic-mcp` do not need another MCP registration.
The commands above work only once the package has actually been published.

## Recovering a failed upload

If authentication fails before upload, check all five Trusted Publisher fields,
especially the workflow filename and environment, then rerun the failed release
workflow. PR and manual validation runs are intentionally unable to publish.
Never paste tokens into workflow files to work around a publisher mismatch.

If files were already uploaded, inspect PyPI before retrying: package filenames
cannot be replaced, and this workflow deliberately does not skip existing files.
Do not delete and reuse a version. If you need to change an already published
distribution, bump the version and publish a new matching GitHub release.
