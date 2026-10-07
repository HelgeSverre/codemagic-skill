---
name: codemagic-signing
description: Set up or diagnose iOS and Android signing in an existing Codemagic project. Use for provisioning, entitlements, keystore and certificate mismatches, release-variant wiring, and distinguishing signing failures from store publishing or certificate-bound API failures.
---

# Codemagic signing

Help the user reach a correctly signed artifact while preserving an existing
app's identity. Start with project configuration and the reported failure.
This skill complements Codemagic's API/build tools; it does not require them.

## Establish the intended artifact

Infer from the repository and request before asking for missing information:

- Platform, framework, target or variant, bundle/application ID, and workflow.
- Whether this is a new app or an update to an already distributed app.
- Destination: simulator, direct device distribution, TestFlight/App Store,
  Google Play, or another Android distribution channel.
- Last successful build, current failing stage, and what changed since then.

Check whether the app uses `codemagic.yaml` or Workflow Editor. YAML instructions
do not configure Workflow Editor. Inspect the selected workflow and relevant
project files; don't migrate the project merely to apply a template.

Read only the relevant platform reference:

- [iOS signing](references/ios.md): identities, provisioning, targets,
  capabilities, and the three Codemagic signing models.
- [Android signing](references/android.md): upload versus app signing keys,
  Gradle variants, artifact verification, and runtime fingerprints.

## Diagnose before replacing credentials

Build a small evidence table connecting each target/variant, distribution
channel, configured signing identity, and observed artifact. Mark unknowns.
Do not infer success from the presence of YAML or an uploaded identity alone.

Find the first failing stage: obtaining credentials, project configuration,
archive/signing, export, store upload, or runtime API authentication. A store
permission error is not evidence of a signing-key problem. An accepted upload
does not prove that a directly distributed artifact will install.

Prefer the smallest configuration correction supported by that evidence.
Preserve working identities and local developer build paths. Explain which
checks were static, which tools actually ran, and what still requires a build
or account-side action. Don't label static inspection as a verified signed build.

## Handle credentials and account actions

Work with reference names and public certificate metadata. Do not request
private keys, keystore passwords, service-account JSON, or full provisioning
profiles in chat. A user-specified profile or artifact may be inspected locally;
summarize only necessary identifiers, expiry, entitlement names and certificate
fingerprints. Avoid dumping device UDIDs, scripts with embedded secrets, or
the full decoded profile. Use interactive password entry or an already approved
secret mechanism; passwords do not belong in command arguments.

Read-only diagnosis does not authorize creating, rotating, revoking, uploading,
or resetting credentials. When setup or repair already authorizes a specific
account action, proceed within that scope after resolving the identity and
consequences; this skill adds no repeated confirmation requirement. Ambiguous
key replacement needs the user's decision. Build and publishing operations
likewise follow the requested scope.

The separate `codemagic-api` client operates builds and documented REST endpoints;
it is not a signing-identity manager. Do not invent credential-upload endpoints.
For account operations, consult current official documentation and the actual
installed tool's help. In particular, Codemagic's
`app-store-connect fetch-signing-files --create` can create Apple resources;
it is not an inspection command.

For general first-time YAML generation, consider the official
[codemagic-init](https://docs.codemagic.io/troubleshooting/codemagic-init/).
Explain that it can write project configuration, install agent knowledge and
schedule refreshes before running it as part of an authorized setup. This skill
focuses on the identity and configuration decisions a template cannot resolve.
