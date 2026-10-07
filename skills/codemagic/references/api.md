# Codemagic API notes

Verified against Codemagic's public OpenAPI v3.0 schema on 2026-10-07.

- Current API reference: https://codemagic.io/api/v3/schema
- Machine-readable schema: https://codemagic.io/api/v3/schema/openapi.json
- API overview/authentication: https://docs.codemagic.io/rest-api/codemagic-rest-api/
- Documented legacy build cancellation: https://docs.codemagic.io/rest-api/builds/
- Artifact authentication/downloads: https://docs.codemagic.io/rest-api/artifacts/

## Installed implementation

`codemagic-api` is a Python CLI. Its canonical source is bundled in this skill
at `scripts/codemagic_api.py`; it can also be installed with uv. All typed commands use
`https://codemagic.io/api/v3`, except `cancel`, which uses the documented legacy
`https://api.codemagic.io/builds/{id}/cancel` endpoint. The October schema has no
v3 cancellation endpoint. API auth uses `x-auth-token` with a personal token;
effective privileges depend on that user's team role.

| Command | Method and relative v3 path |
| --- | --- |
| `teams` | GET `/user/teams` |
| `apps` | GET `/user/apps` |
| `apps --team ID` | GET `/teams/{id}/apps` |
| `workflows APP_ID` | GET `/apps/{app_id}/workflows` |
| `builds --team ID` | GET `/teams/{id}/builds` |
| `build ID`, `artifacts ID` | GET `/builds/{id}` |
| `actions ID` | GET `/builds/{id}/actions` |
| `start --app ID ...` | POST `/apps/{id}/builds` |

Typed list commands fetch one page. Teams/apps/actions use `data`, `page_size`,
`current_page`, `total_pages`; builds use `data`, `page_size`, `cursor`.
Build lists accept `app_id`, `workflow_id`, `branch`, `tag`, and status filters.
Get-build returns `data` with `status`, `commit`, `artifacts`, and other fields.
`actions` exposes step status and scripts; it is not a raw build-log endpoint.
Use the build UI or a log artifact for full logs; do not invent a v3 log URL.

## Start payload

V3 uses snake_case fields. Do not reuse old camelCase examples from legacy docs.

```json
{
  "workflow_id": "ios-workflow",
  "branch": "feature/example",
  "labels": ["manual-test"],
  "inputs": {"run_tests": true},
  "environment": {
    "variables": {"BUILD_LABEL": "manual-test"},
    "groups": ["staging"],
    "software_versions": {"flutter": "stable"}
  }
}
```

Exactly one of `branch` or `tag` is required. Start returns HTTP 202 with
`{"data":{"id":"BUILD_ID"}}`. A subsequent GET can briefly return 404.
Build terminal statuses are `finished`, `failed`, `canceled`, `timeout`, `skipped`.
Do not report a `publishing` or `finishing` build as complete.

Requests initiated through the API select the given workflow/ref directly;
do not rely on automatic-trigger branch filters to prevent publishing.
Cancellation can return HTTP 208 when the build is already finished.
The v3 API rate limit is 5,000 requests/hour. On 429, honor the
`ratelimit-reset` header (seconds); the helper reports it without retrying.

## Other documented JSON endpoints

```sh
codemagic-api api GET '/teams/TEAM_ID/variable-groups'
codemagic-api api GET '/teams/TEAM_ID/builds?page_size=10'
codemagic-api api POST '/apps/APP_ID/builds' --data-file request.json --dry-run
```

`api` accepts GET/POST/PUT/PATCH/DELETE, JSON object bodies via `--data-file`,
and `--legacy` for documented legacy endpoints. Relative paths only; arbitrary
hosts, redirects, and traversal are rejected. It deliberately has no automatic
retry, token argument, binary downloader, or public artifact-link generator.
`--dry-run` performs no authentication or network call and redacts values.
Generic endpoints rely on the official schema for request validation.

## Research findings

No official Codemagic MCP server was found in the official docs or available
plugin search. A community MCP implementation exists:
https://github.com/todah-zg/codemagic-mcp (npm `codemagic-mcp-server`).
It also includes App Store Connect and Google Play publishing tools. It was
not installed; this tool uses the official API directly with no runtime packages.

Codemagic also publishes `codemagic-init` for installing agent knowledge:
https://docs.codemagic.io/troubleshooting/codemagic-init/ . It installs knowledge
and refreshes it periodically; it is distinct from an authenticated operations
client. It was not needed for this integration.
