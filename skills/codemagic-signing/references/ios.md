# iOS signing decisions

Checked against the linked primary sources on 2026-10-07. Recheck current docs
before changing account resources or relying on version-specific tool behavior.

## Identify the signing model

| Model | Evidence in the workflow | What it requires |
| --- | --- | --- |
| Stored Codemagic identities | `environment.ios_signing` selects type/bundle ID or explicit certificate/profile references | Matching certificate with its private key and provisioning profiles stored in Codemagic |
| Build-time CLI provisioning | `app-store-connect fetch-signing-files`, possibly with `--create` | Apple API authentication plus the separate signing-certificate private key; compatible Apple resources |
| Manual files | Protected variables/files imported into a build keychain and profile directory | Existing certificate/private key and matching profile; deliberate file lifecycle management |

Keep the project's chosen model unless the user requests a migration. A stored
identity selector does not mean the build invokes Apple's resource-creation API.
The App Store Connect `.p8` API key authenticates API calls; it does not replace
the private key associated with a code-signing certificate. A downloaded public
certificate cannot recover its missing private key. See
[stored identities](https://docs.codemagic.io/yaml-code-signing/signing-ios/) and
[CLI/manual methods](https://docs.codemagic.io/yaml-code-signing/alternative-code-signing-methods/).

## Match every target

Inspect the selected app project, build configuration and shared scheme. Record
each signable target's bundle ID, development team, signing style, profile
specifier and entitlement file, including extensions. Do not search dependencies
as though their projects were the app.

Check profile selection against that inventory. Codemagic supports selection
by `distribution_type` plus `bundle_identifier`, or explicit
`provisioning_profiles`/`certificates`; do not mix those selection modes.
Extensions require their own matching profiles. With ID matching, check the
main ID and its extension IDs; with explicit references, verify all targets
are covered. Check where `xcode-project use-profiles` runs before the archive
and whether later settings override it. See
[Codemagic signing configuration](https://docs.codemagic.io/yaml-code-signing/signing-ios/).

Choose the distribution method from the intended destination. TestFlight/App
Store uses App Store distribution; a directly installed device build needs a
compatible development, ad hoc or eligible enterprise path. App Store signing
does not make an IPA suitable for arbitrary direct installation. Ad hoc profiles
must include the intended registered devices. See Apple's
[App Store profiles](https://developer.apple.com/help/account/provisioning-profiles/create-an-app-store-provisioning-profile)
and [ad hoc profiles](https://developer.apple.com/help/account/provisioning-profiles/create-an-ad-hoc-provisioning-profile).

## Inspect and resolve mismatches

For a profile supplied by the user, macOS `security cms -D -i PROFILE` decodes
its metadata. Capture that output locally for structured parsing; do not print
the full plist. Compare the team, application identifier, expiry, certificate
fingerprints and relevant entitlements with the selected target. Report a device
count or whether a requested device is included, rather than listing UDIDs.
Decoding alone does not prove certificate trust, private-key availability or
that a final artifact passes signature verification.

For an existing IPA, inspect its app and extension bundles, embedded profiles and
public signing metadata in a temporary directory. Keep archive paths contained
there. macOS code-signing tools can verify the actual bundles; on other hosts,
state that those checks were unavailable. Static project inspection is still useful.

| Finding | Next step |
| --- | --- |
| Missing profile or wrong distribution | Match profile type, target ID and selected Codemagic reference |
| Certificate/profile mismatch | Match the profile's included certificate to the available identity; don't create a replacement blindly |
| Missing entitlement after a capability change | Check the App ID capability, regenerate the affected profile when authorized, and update the selected copy |
| Conflicting automatic/manual settings | Resolve which signing model controls the selected configuration and remove the conflicting override |
| Missing team or wrong extension identity | Correct the affected target/configuration, preserving other targets |
| Archive signs but upload fails | Investigate App Store Connect permissions, agreements and app/version state separately |

The first five mappings are grounded in
[Codemagic's iOS troubleshooting](https://docs.codemagic.io/troubleshooting/common-ios-issues/).
Apple documents that enabling capabilities invalidates affected profiles:
[capability changes](https://developer.apple.com/help/account/identifiers/enable-app-capabilities/).
Publishing has its own requirements:
[App Store Connect publishing](https://docs.codemagic.io/yaml-publishing/app-store-connect/).

If account changes are needed, distinguish an API key from a signing identity
and check the actual role and API-key type. Individual App Store Connect keys
cannot use the provisioning endpoints supported by team keys. Do not propose
certificate revocation as routine cleanup. Consult
[Apple API keys](https://developer.apple.com/documentation/appstoreconnectapi/creating-api-keys-for-app-store-connect-api)
and the official
[fetch-signing-files command](https://github.com/codemagic-ci-cd/cli-tools/blob/master/docs/app-store-connect/fetch-signing-files.md)
before an authorized resource change.
