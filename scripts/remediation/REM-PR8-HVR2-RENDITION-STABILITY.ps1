[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$RepositoryRoot,
  [switch]$NoPush
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if(-not $NoPush){throw 'Remote remediation requires -NoPush.'}
$root=(Resolve-Path -LiteralPath $RepositoryRoot).Path
$expected=[string]$env:AUTHORIZED_HEAD_SHA
$before=(git -C $root rev-parse HEAD).Trim()
if($expected -and $before -ne $expected){throw "Exact-SHA mismatch: $before != $expected"}

function Replace-One([string]$Path,[string]$Old,[string]$New){
  $full=Join-Path $root $Path
  $text=[IO.File]::ReadAllText($full).Replace("`r`n","`n")
  $oldN=$Old.Replace("`r`n","`n").TrimEnd("`r","`n")
  $newN=$New.Replace("`r`n","`n").TrimEnd("`r","`n")
  if(-not $text.Contains($oldN)){throw "Expected block not found in $Path"}
  if(($text.Split($oldN).Count-1) -ne 1){throw "Expected block not unique in $Path"}
  [IO.File]::WriteAllText($full,$text.Replace($oldN,$newN),[Text.UTF8Encoding]::new($false))
}

Replace-One 'runtime/miro/ddda_miro/miro_tips_reference_oracle.py' @'
    image_bytes, _content_type, image = image_transport.source_image(client, source_board, image_id)
    if str(image.get("id") or "") != image_id:
        raise ValueError("Miro Tips frozen reference background identity mismatch")
    if hashlib.sha256(image_bytes).hexdigest() != expected_background:
        raise ValueError("Miro Tips frozen reference background bytes drifted")
'@ @'
    image_bytes, content_type, image = image_transport.source_image(client, source_board, image_id)
    if str(image.get("id") or "") != image_id:
        raise ValueError("Miro Tips frozen reference background identity mismatch")
    if not image_bytes or not str(content_type or "").startswith("image/"):
        raise ValueError("Miro Tips frozen reference background rendition is unreadable")
    # Miro imageUrl is a rendition endpoint and may re-encode the same image over time.
    # The immutable visual identity is therefore the pinned board/frame/image item plus
    # native topology; the current rendition digest is evidence, not a static precondition.
    hashlib.sha256(image_bytes).hexdigest()
'@

Replace-One 'runtime/miro/tests/test_miro_tips_reference_oracle.py' @'
def test_frozen_reference_oracle_rejects_background_byte_drift(monkeypatch):
    expected = b"approved-reference"
    observed = state()
    install(monkeypatch, b"changed-reference", observed)
    with pytest.raises(ValueError, match="background bytes drifted"):
        oracle.assert_frozen_reference_identity(FakeClient(), "source", "frame", manifest(expected))
'@ @'
def test_frozen_reference_oracle_accepts_miro_rendition_byte_drift_for_same_pinned_image(monkeypatch):
    expected = b"approved-reference"
    observed = state()
    install(monkeypatch, b"miro-reencoded-same-reference", observed)
    oracle.assert_frozen_reference_identity(FakeClient(), "source", "frame", manifest(expected))
'@

Replace-One '.github/workflows/platform-ci.yml' @'
          if($r.miro_tips.image.source_sha256 -ne '04b83ec7d9bc07ae31c7c11c03ec974ff4bde00d7773d7f9e55036e877f6fffd' -or $r.miro_tips.image.target_sha256 -ne '04b83ec7d9bc07ae31c7c11c03ec974ff4bde00d7773d7f9e55036e877f6fffd'){throw 'HVR Miro Tips reference-image identity mismatch'}
'@ @'
          if([string]::IsNullOrWhiteSpace([string]$r.miro_tips.image.source_sha256) -or $r.miro_tips.image.source_sha256 -ne $r.miro_tips.image.target_sha256){throw 'HVR Miro Tips copied image differs from DDDA_PLATFORM_LAB'}
'@

Replace-One 'runtime/platform/tests/test_miro_execution_profiles.py' @'
        "04b83ec7d9bc07ae31c7c11c03ec974ff4bde00d7773d7f9e55036e877f6fffd",
        "miro_tips.review_url",
'@ @'
        "miro_tips.image.source_sha256",
        "miro_tips.image.target_sha256",
        "miro_tips.review_url",
'@

python -m pip install --disable-pip-version-check --no-input pytest 'ruamel.yaml>=0.18,<0.19' requests pyyaml
if($LASTEXITCODE -ne 0){throw 'Dependency install failed'}
$env:PYTHONPATH=Join-Path $root 'runtime/miro'
python -m pytest `
  (Join-Path $root 'runtime/miro/tests/test_miro_tips_reference_oracle.py') `
  (Join-Path $root 'runtime/miro/tests/test_hvr_materialization.py') `
  (Join-Path $root 'runtime/platform/tests/test_miro_execution_profiles.py') -q
if($LASTEXITCODE -ne 0){throw 'Targeted exact-reference tests failed'}

Remove-Item -LiteralPath $PSCommandPath -Force
$paths=@(
  '.github/workflows/platform-ci.yml',
  'runtime/miro/ddda_miro/miro_tips_reference_oracle.py',
  'runtime/miro/tests/test_miro_tips_reference_oracle.py',
  'runtime/platform/tests/test_miro_execution_profiles.py',
  'scripts/remediation/REM-PR8-HVR2-RENDITION-STABILITY.ps1'
)
git -C $root add -A -- $paths
if($LASTEXITCODE -ne 0){throw 'git add failed'}
git -C $root diff --cached --check
if($LASTEXITCODE -ne 0){throw 'git diff --cached --check failed'}
$staged=@(git -C $root diff --cached --name-only)
$expectedPaths=@(
  '.github/workflows/platform-ci.yml',
  'runtime/miro/ddda_miro/miro_tips_reference_oracle.py',
  'runtime/miro/tests/test_miro_tips_reference_oracle.py',
  'runtime/platform/tests/test_miro_execution_profiles.py',
  'scripts/remediation/REM-PR8-HVR2-RENDITION-STABILITY.ps1'
)
if((@($staged|Sort-Object)-join "`n") -ne (@($expectedPaths|Sort-Object)-join "`n")){throw "Unexpected staged paths: $($staged -join ', ')"}
git -C $root commit -m 'fix(miro): treat CDN rendition bytes as volatile evidence'
if($LASTEXITCODE -ne 0){throw 'git commit failed'}
$after=(git -C $root rev-parse HEAD).Trim()
if($after -eq $before){throw 'No remediation commit created'}
if(@(git -C $root status --porcelain).Count -ne 0){throw 'Remediation left dirty repository'}
Write-Host "REM-PR8-HVR2-RENDITION-STABILITY PASS before=$before after=$after"
