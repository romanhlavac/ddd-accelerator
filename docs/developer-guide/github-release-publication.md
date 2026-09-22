# Canonical GitHub Release publication

## Terms

```text
Milestone           = declared release scope
Release candidate   = exact frozen candidate state
Tag                 = immutable Git identity of the released version
GitHub Release      = published distribution/evidence object for that tag
Canonical DDDA ZIP  = validated DDDA product package
GitHub source ZIP   = convenience source archive, not the DDDA product package
```

## Normal publication path

Publication is reached only inside an explicitly authorized non-dry-run canonical promotion, after release validation and report generation are PASS.

```text
release source SHA
→ validated canonical ZIP + SHA-256
→ portable result.json + result.md
→ annotated tag vX.Y.Z
→ GitHub Release DDDA X.Y.Z
→ upload exact assets
→ fresh server read-back of tag, Release and asset hashes
```

The published assets are named deterministically:

```text
ddda-X.Y.Z.zip
ddda-X.Y.Z-release-report.json
ddda-X.Y.Z-release-report.md
```

Automatic GitHub source archives may be visible in the Release UI. They are never canonical DDDA package evidence.

## Failure and recovery

Publication is fail closed. A tag created without its Release, a Release without all assets, an unexpected existing Release/asset, or a mismatching hash is `RECOVERY_REQUIRED`, not `PASS`.

Do not delete, replace, retag, force-push or rerun promotion heuristically. After separate recovery authorization, use the recovery command only with the original validated release source, package and reports:

```powershell
.\scripts\platform\Invoke-DDDARecoverGitHubRelease.ps1 `
  -Version X.Y.Z `
  -ReleaseSourceSha <validated-release-sha> `
  -ReleasePackagePath <validated-package.zip> `
  -ReleaseReportJsonPath <result.json> `
  -ReleaseReportMarkdownPath <result.md> `
  -ConfirmRecovery
```

Recovery finishes only after fresh tag/Release/asset read-back proves the original identities and physical package SHA-256. The tag read-back requires exactly one annotated tag-object ref and exactly one peeled commit ref for the requested tag; it uses a bounded retry only to tolerate remote visibility delay. A missing, lightweight, ambiguous or mismatching tag fails closed. Existing tags are never changed, replaced or deleted.

### Chat/Work remote recovery execution

When recovery is orchestrated remotely, the default-branch workflow `.github/workflows/controlled-release-recovery.yml` is the canonical execution surface. It is only valid after a separate human recovery authorization and is triggered by an owner-authored PR comment:

```text
/ddda recover-controlled --source-sha <40-char-frozen-sha> --version X.Y.Z --candidate-package-sha256 <64-char-sha256>
```

The workflow binds itself to the live default-branch control-plane SHA, restores the HRDR-bound exact candidate evidence, checks the candidate package hash, verifies the existing annotated tag without changing it, reconstructs the release-kind package and portable release report from the frozen source, and only then calls `Invoke-DDDARecoverGitHubRelease.ps1 -ConfirmRecovery`.

The recovery workflow is intentionally idempotent: a correct existing Release/asset is read back and retained, a missing one is created, and any identity or hash mismatch fails closed. It never creates, moves, deletes, replaces or retags the release tag, and it never merges the controlled release-source PR.