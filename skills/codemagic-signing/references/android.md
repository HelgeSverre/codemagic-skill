# Android signing decisions

Checked against the linked primary sources on 2026-10-07. Console flows and
key-upgrade rules change; use current documentation for account migrations.

## Establish identity continuity

For an existing app, determine whether it uses Play App Signing or retains its
own distribution key before recommending a keystore change.

| Evidence | Compare against |
| --- | --- |
| CI upload AAB/APK for an app enrolled in Play App Signing | Registered upload certificate |
| APK delivered by Google Play | Play app-signing certificate applicable to that distribution |
| APK distributed directly or through another store | The actual distribution certificate and the previous installed app's identity |
| Google Play API publishing failure | Publishing service-account permissions and app state, separately from signing |

With Play App Signing, the upload key and app-signing key have different roles.
Their fingerprints can legitimately differ. Losing an upload key can lead to an
upload-key reset; that does not replace Google's app-signing key. A self-managed
existing app needs continuity with its original signing identity. Do not repair
a mismatch by silently generating a fresh keystore. See
[Android app signing](https://developer.android.com/studio/publish/app-signing).

An app-signing key upgrade is a separate migration with platform-version and
certificate-registration consequences. For reset, upgrade, transfer or enrollment,
use the app's current Console state and
[Google Play's signing procedures](https://support.google.com/googleplay/android-developer/answer/9842756).

## Follow the selected variant through CI

Check the exact workflow, Gradle module, build type/flavor, application ID and
build task. Uploaded Codemagic identities are referenced under
`environment.android_signing`. The build receives `CM_KEYSTORE_PATH`,
`CM_KEYSTORE_PASSWORD`, `CM_KEY_ALIAS` and `CM_KEY_PASSWORD`; the selected Gradle
signing configuration must consume them and the release variant must select
that configuration. Uploading a keystore alone does not wire Gradle.

Adapt the existing Groovy or Kotlin DSL configuration instead of pasting a second
`android` block. Preserve deliberate local-build fallback behavior. Check that
the artifact pattern selects the intended release output, not a debug or unsigned
artifact. Stored Codemagic keystores cannot be downloaded back as a backup; an
independent private backup matters. See
[Codemagic Android signing](https://docs.codemagic.io/yaml-code-signing/signing-android/).

## Verify the appropriate artifact

Use tools already available or explain the missing prerequisite. Suggested checks:

- `keytool -list -v -keystore PATH -alias ALIAS`: inspect a user-selected keystore
  with interactive password entry. Summarize public certificate fingerprints,
  alias, entry type and validity; a certificate-only entry cannot sign.
- `apksigner verify --verbose --print-certs PATH.apk`: verify an APK and inspect
  its signer. It is not the verifier for an AAB.
- `jarsigner -verify -strict -certs PATH.aab`: inspect AAB/JAR signing. Interpret
  warnings such as self-signed certificates separately from malformed signatures;
  this does not establish Play upload eligibility or the eventual Play APK signer.
- `./gradlew signingReport`: inspect variant signing, when executing this
  repository's Gradle build logic is appropriate. It is not a passive text read.

Android's [command-line build guide](https://developer.android.com/build/building-cmdline)
distinguishes AAB and APK signing tools; the
[apksigner reference](https://developer.android.com/tools/apksigner) documents APK
verification. Use [bundletool](https://developer.android.com/tools/bundletool)
when actual APK-set generation/device testing is needed, not as proof of the
Google Play distribution certificate.

## Classify the failure

| Symptom | Evidence to check before changing keys |
| --- | --- |
| Missing keystore/alias or password failure | Selected identity reference, file existence, alias and correct secret mapping |
| Unsigned/debug-signed release | Variant's `signingConfig`, actual build task and collected artifact |
| Play reports wrong certificate | Artifact upload fingerprint versus the registered upload certificate |
| Install/update incompatibility | Package ID and distribution signer versus the installed app |
| Upload permission or version error | Publishing account access, initial app setup and versionCode |
| Sign-in/Maps works locally but fails from Play | Runtime package ID and Play app-signing fingerprint registered with the API provider |

Google Play service-account JSON authenticates publishing; it neither signs an
app nor recovers an upload key. Codemagic documents the separate permissions and
initial manual upload prerequisites in
[Google Play publishing](https://docs.codemagic.io/yaml-publishing/google-play/).

For certificate-bound APIs, select fingerprints according to where the installed
APK came from. Debug, directly distributed release and Play builds may need
different registrations. Google Android OAuth clients pair the package name
with a certificate's SHA-1 fingerprint; add the missing pairing using that
provider's supported client configuration while retaining required existing
pairings. Other services may require SHA-256 instead, so compare the same digest
type. See [Google client authentication](https://developers.google.com/android/guides/client-auth),
[Firebase's Android FAQ](https://firebase.google.com/docs/android/troubleshooting-faq),
and [Maps API restrictions](https://developers.google.com/maps/api-security-best-practices).
