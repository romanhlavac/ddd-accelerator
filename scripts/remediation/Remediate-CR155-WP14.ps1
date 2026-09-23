[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$RepositoryRoot,[switch]$NoPush)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Set-Location (Resolve-Path $RepositoryRoot)
$initialHead=(git rev-parse HEAD).Trim()

python scripts/remediation/Remediate-CR155-WP14.py
if($LASTEXITCODE -ne 0){throw 'CR155 transformation failed'}

python -m pytest -q runtime/platform/tests/test_project_backlog_delivery_governance.py runtime/platform/tests/test_project_backlog_presentation_governance.py
if($LASTEXITCODE -ne 0){throw 'CR155 governance regression suite failed'}

git add -- config/governance/backlog-policy.yaml config/governance/github-bootstrap.json docs/roadmap/README.md docs/roadmap/backlog-index.md docs/roadmap/work-packages/WP-14-multi-model-workbench-git-sync.md runtime/platform/tests/test_project_backlog_delivery_governance.py
if($LASTEXITCODE -ne 0){throw 'git add failed'}
git rm -f -- scripts/remediation/Remediate-CR155-WP14.ps1 scripts/remediation/Remediate-CR155-WP14.py
if($LASTEXITCODE -ne 0){throw 'staging cleanup failed'}
git diff --cached --check
if($LASTEXITCODE -ne 0){throw 'git diff --cached --check failed'}

git -c user.name='DDDA Remediation Bot' -c user.email='ddda-remediation@users.noreply.github.com' commit -m 'fix(governance): materialize WP-14 backlog contract (#155)'
if($LASTEXITCODE -ne 0){throw 'remediation commit failed'}
$newHead=(git rev-parse HEAD).Trim()
if($newHead -eq $initialHead){throw 'remediation produced no commit'}
$status=@(git status --porcelain)
if($LASTEXITCODE -ne 0 -or $status.Count -ne 0){throw "working tree not clean: $($status -join '; ')"}
