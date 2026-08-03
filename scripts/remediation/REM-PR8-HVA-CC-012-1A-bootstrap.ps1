[CmdletBinding()]
param([switch]$NoPush)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ChangeId = 'REM-PR8-HVA-CC-012.1A'
$AuthorizedBaseSha = '155ddcba7f5974eb0d3843f01466ed9a75e23f31'
$TargetBranch = 'feat/project-steering-and-documentation'
$Transport = 'chat-atomic-github-git-data-api'
$SelfRemoving = $true
$FinalFiles = [ordered]@{
    'CHANGELOG.md' = '75d3c52563b91de7c883abfe0fcc9ccc7864622c7365a35f0e2b08c4a451a3f6'
    'config/platform/development-policy.yaml' = '801754dd8dacb3e733e9b5bdd61e3ecd99c0ee2e74c671266cf8e85b1f9ba510'
    'docs/adr/0006-chat-atomic-platform-implementation.md' = '334ec2def1445e6ec88e327927144d662cceb6c423bd03ab560ae289e7972a52'
    'docs/developer-guide/chat-work-operating-model.md' = '6c1b33f4e44cdae8c3d8f1a809ab594a1349f3a240a32287ece30ae0c7c6dad8'
    'docs/developer-guide/remote-validation-broker.md' = '3c8f7b51828d83c8e63c5c9b2690b487398333b991403de7740639ab2fecb0fa'
    'knowledge/ddda-platform-development-skill.md' = 'ce3f07a46df563bf5fbdab939e7bbecead97ca92620e907d4a5ab61c42e3268a'
    'runtime/platform/tests/test_chat_work_policy.py' = 'fd7b13935f091ea5ff880dffc03f3e9f1c0df45918a7056461e241755f265e38'
}

if (-not $NoPush) { throw 'Bootstrap manifest is authorized only with -NoPush; Chat performs the guarded atomic tree update.' }
$head = (git rev-parse HEAD).Trim()
$parent = (git rev-parse HEAD^).Trim()
if ($parent -ne $AuthorizedBaseSha) { throw "Staging parent '$parent' does not match authorized base '$AuthorizedBaseSha'." }
$changed = @(git diff-tree --no-commit-id --name-only -r HEAD)
if ($changed.Count -ne 1 -or $changed[0] -ne 'scripts/remediation/REM-PR8-HVA-CC-012-1A-bootstrap.ps1') { throw 'Staging commit contains an unexpected path.' }
[pscustomobject]@{ change_id=$ChangeId; base_sha=$AuthorizedBaseSha; staging_sha=$head; target_branch=$TargetBranch; transport=$Transport; self_removing=$SelfRemoving; final_files=$FinalFiles } | ConvertTo-Json -Depth 10
