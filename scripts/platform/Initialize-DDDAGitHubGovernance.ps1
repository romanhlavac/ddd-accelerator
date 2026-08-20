[CmdletBinding()]
param(
    [string]$ConfigPath,
    [switch]$Apply,
    [switch]$SkipViews,
    [switch]$OpenProject
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$Changes = New-Object 'System.Collections.Generic.List[string]'
$Warnings = New-Object 'System.Collections.Generic.List[string]'
$ManualSteps = New-Object 'System.Collections.Generic.List[string]'

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

function Write-Action {
    param([string]$Message)
    $prefix = if ($Apply) { "APPLY" } else { "PLAN " }
    $color = if ($Apply) { "Green" } else { "Yellow" }
    Write-Host "[$prefix] $Message" -ForegroundColor $color
}

function Invoke-Gh {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [switch]$AllowFailure
    )

    $output = & gh @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($output | ForEach-Object { "$_" }) -join "`n"

    if (($exitCode -ne 0) -and (-not $AllowFailure)) {
        throw "gh $($Arguments -join ' ') failed with exit code $exitCode.`n$text"
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        Text = $text
    }
}

function Invoke-GhJson {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $result = Invoke-Gh -Arguments $Arguments
    if ([string]::IsNullOrWhiteSpace($result.Text)) { return $null }
    return ($result.Text | ConvertFrom-Json)
}

function Invoke-GhJsonInput {
    param(
        [Parameter(Mandatory = $true)][object]$Body,
        [string]$Endpoint,
        [string]$Method = "POST",
        [switch]$GraphQL
    )

    $temp = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText(
            $temp,
            ($Body | ConvertTo-Json -Depth 40),
            $Utf8NoBom
        )

        if ($GraphQL) {
            return Invoke-GhJson -Arguments @("api", "graphql", "--input", $temp)
        }

        return Invoke-GhJson -Arguments @(
            "api",
            "--method", $Method,
            "-H", "Accept: application/vnd.github+json",
            "-H", "X-GitHub-Api-Version: $($script:Config.api_version)",
            $Endpoint,
            "--input", $temp
        )
    }
    finally {
        Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
    }
}

function Resolve-Configuration {
    if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
        $ConfigPath = Join-Path $PSScriptRoot "..\..\config\governance\github-bootstrap.json"
    }

    $resolved = Resolve-Path -LiteralPath $ConfigPath -ErrorAction Stop
    $json = [System.IO.File]::ReadAllText($resolved.Path, $Utf8NoBom)
    $script:Config = $json | ConvertFrom-Json

    if ($Config.schema_version -ne 1) {
        throw "Unsupported github-bootstrap.json schema version: $($Config.schema_version)"
    }

    return $resolved.Path
}

function Assert-Prerequisites {
    Write-Section "Prerequisites"

    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw "GitHub CLI 'gh' is not installed or is not available on PATH."
    }

    Write-Host (Invoke-Gh -Arguments @("--version")).Text

    $auth = Invoke-Gh -Arguments @("auth", "status") -AllowFailure
    if ($auth.ExitCode -ne 0) {
        throw "GitHub CLI is not authenticated. Run: gh auth login"
    }

    $help = (Invoke-Gh -Arguments @("issue", "edit", "--help")).Text
    foreach ($flag in @("--add-sub-issue", "--add-blocked-by")) {
        if ($help -notmatch [regex]::Escape($flag)) {
            throw "The installed GitHub CLI does not support $flag. Update GitHub CLI and rerun the script."
        }
    }

    $projectProbe = Invoke-Gh -Arguments @(
        "project", "list",
        "--owner", $Config.project_owner,
        "--limit", "1",
        "--format", "json"
    ) -AllowFailure

    if ($projectProbe.ExitCode -ne 0) {
        throw @"
The current GitHub CLI token cannot manage Projects.
Run this command once, complete the browser authorization, and rerun the script:

    gh auth refresh -s project

Details:
$($projectProbe.Text)
"@
    }
}

function Get-IssueRelationshipNumbers {
    param(
        [int]$Issue,
        [ValidateSet("subIssues", "blockedBy", "blocking")][string]$Relationship
    )

    $value = Invoke-GhJson -Arguments @(
        "issue", "view", "$Issue",
        "-R", $Config.repository,
        "--json", $Relationship
    )

    return @($value.$Relationship | ForEach-Object { [int]$_.number })
}

function Ensure-Hierarchy {
    Write-Section "Native Parent/Sub-issue hierarchy"

    foreach ($relation in $Config.hierarchy) {
        $current = @(Get-IssueRelationshipNumbers -Issue $relation.parent -Relationship "subIssues")
        $missing = @($relation.children | Where-Object { [int]$_ -notin $current })
        if ($missing.Count -eq 0) {
            Write-Host "Parent #$($relation.parent) already has all required sub-issues."
            continue
        }

        Write-Action "Add sub-issues $($missing -join ', ') to parent #$($relation.parent)"
        if ($Apply) {
            Invoke-Gh -Arguments @(
                "issue", "edit", "$($relation.parent)",
                "-R", $Config.repository,
                "--add-sub-issue", ($missing -join ",")
            ) | Out-Null
            $Changes.Add("Parent #$($relation.parent): added sub-issues $($missing -join ', ').")
        }
    }
}

function Ensure-Dependencies {
    Write-Section "Native issue dependencies"

    foreach ($relation in $Config.dependencies) {
        $current = @(Get-IssueRelationshipNumbers -Issue $relation.blocked -Relationship "blockedBy")
        $missing = @($relation.blocked_by | Where-Object { [int]$_ -notin $current })
        if ($missing.Count -eq 0) {
            Write-Host "Issue #$($relation.blocked) already has all required blockers."
            continue
        }

        Write-Action "Mark #$($relation.blocked) as blocked by $($missing -join ', ')"
        if ($Apply) {
            Invoke-Gh -Arguments @(
                "issue", "edit", "$($relation.blocked)",
                "-R", $Config.repository,
                "--add-blocked-by", ($missing -join ",")
            ) | Out-Null
            $Changes.Add("Issue #$($relation.blocked): added blockers $($missing -join ', ').")
        }
    }
}

function Invoke-GraphQL {
    param(
        [Parameter(Mandatory = $true)][string]$Query,
        [Parameter(Mandatory = $true)][hashtable]$Variables
    )

    return Invoke-GhJsonInput -GraphQL -Body @{
        query = $Query
        variables = $Variables
    }
}

function Find-Project {
    $query = @'
query($login: String!) {
  user(login: $login) {
    projectsV2(first: 100) {
      nodes { id number title url closed }
    }
  }
}
'@

    $result = Invoke-GraphQL -Query $query -Variables @{ login = $Config.project_owner }
    return @($result.data.user.projectsV2.nodes | Where-Object {
        $_.title -eq $Config.project_title -and -not $_.closed
    }) | Select-Object -First 1
}

function Get-ProjectSnapshot {
    param([int]$ProjectNumber)

    $query = @'
query($login: String!, $number: Int!) {
  user(login: $login) {
    projectV2(number: $number) {
      id number title url
      fields(first: 100) {
        nodes {
          __typename
          ... on ProjectV2FieldCommon { id name dataType }
          ... on ProjectV2SingleSelectField { options { id name } }
        }
      }
      items(first: 100) {
        nodes {
          id
          content {
            __typename
            ... on Issue { number url state }
            ... on PullRequest { number url state }
          }
        }
      }
      views(first: 100) { nodes { number name layout } }
    }
  }
}
'@

    $result = Invoke-GraphQL -Query $query -Variables @{
        login = $Config.project_owner
        number = $ProjectNumber
    }
    return $result.data.user.projectV2
}

function Ensure-Project {
    Write-Section "GitHub Project"
    $project = Find-Project

    if (-not $project) {
        Write-Action "Create Project '$($Config.project_title)'"
        if (-not $Apply) { return $null }

        Invoke-Gh -Arguments @(
            "project", "create",
            "--owner", $Config.project_owner,
            "--title", $Config.project_title,
            "--format", "json"
        ) | Out-Null
        $project = Find-Project
        if (-not $project) { throw "Project creation succeeded but the Project cannot be found." }
        $Changes.Add("Created Project '$($Config.project_title)'.")
    }
    else {
        Write-Host "Found Project #$($project.number): $($project.url)"
    }

    if ($Apply) {
        Invoke-Gh -Arguments @(
            "project", "edit", "$($project.number)",
            "--owner", $Config.project_owner,
            "--description", $Config.project_description,
            "--visibility", $Config.project_visibility
        ) | Out-Null

        $link = Invoke-Gh -Arguments @(
            "project", "link", "$($project.number)",
            "--owner", $Config.project_owner,
            "--repo", $Config.repository
        ) -AllowFailure
        if ($link.ExitCode -ne 0 -and $link.Text -notmatch "already") {
            $Warnings.Add("Project link warning: $($link.Text)")
        }
    }

    return $project
}

function Get-FieldsByName {
    param([object]$Snapshot)
    $map = @{}
    foreach ($field in @($Snapshot.fields.nodes)) {
        if ($field.name) { $map[$field.name] = $field }
    }
    return $map
}

function Set-SingleSelectOptions {
    param(
        [object]$Field,
        [object[]]$Options
    )

    $existing = @{}
    foreach ($option in @($Field.options)) { $existing[$option.name] = $option.id }

    $inputOptions = @()
    foreach ($option in $Options) {
        $item = [ordered]@{
            name = $option.name
            color = $option.color
            description = $option.description
        }
        if ($existing.ContainsKey($option.name)) { $item["id"] = $existing[$option.name] }
        $inputOptions += $item
    }

    $mutation = @'
mutation($fieldId: ID!, $options: [ProjectV2SingleSelectFieldOptionInput!]!) {
  updateProjectV2Field(input: {fieldId: $fieldId, singleSelectOptions: $options}) {
    projectV2Field { ... on ProjectV2FieldCommon { id name } }
  }
}
'@

    Invoke-GraphQL -Query $mutation -Variables @{
        fieldId = $Field.id
        options = $inputOptions
    } | Out-Null
}

function Ensure-Fields {
    param([int]$ProjectNumber)
    Write-Section "Project fields"

    $snapshot = Get-ProjectSnapshot -ProjectNumber $ProjectNumber
    $fields = Get-FieldsByName -Snapshot $snapshot

    foreach ($definition in $Config.fields) {
        if ($fields.ContainsKey($definition.name)) { continue }

        Write-Action "Create field '$($definition.name)' ($($definition.type))"
        if ($Apply) {
            $args = @(
                "project", "field-create", "$ProjectNumber",
                "--owner", $Config.project_owner,
                "--name", $definition.name,
                "--data-type", $definition.type,
                "--format", "json"
            )
            if ($definition.type -eq "SINGLE_SELECT") {
                $args += @(
                    "--single-select-options",
                    (($definition.options | ForEach-Object { $_.name }) -join ",")
                )
            }
            Invoke-Gh -Arguments $args | Out-Null
            $Changes.Add("Created Project field '$($definition.name)'.")
        }
    }

    if ($Apply) {
        $snapshot = Get-ProjectSnapshot -ProjectNumber $ProjectNumber
        $fields = Get-FieldsByName -Snapshot $snapshot
        foreach ($definition in $Config.fields | Where-Object { $_.type -eq "SINGLE_SELECT" }) {
            Set-SingleSelectOptions -Field $fields[$definition.name] -Options $definition.options
        }
        $Changes.Add("Normalized all single-select options, including Status.")
    }
}

function Get-ConfiguredItems {
    $items = New-Object 'System.Collections.Generic.List[object]'
    $base = "https://github.com/$($Config.repository)"

    foreach ($group in $Config.item_groups) {
        foreach ($number in $group.numbers) {
            $path = if ($group.kind -eq "pull") { "pull/$number" } else { "issues/$number" }
            $items.Add([pscustomobject]@{
                Url = "$base/$path"
                Kind = $group.kind
                Number = [int]$number
                Metadata = $group.metadata
            })
        }
    }
    return $items
}

function Ensure-ProjectItems {
    param([int]$ProjectNumber)
    Write-Section "Project items"

    $snapshot = Get-ProjectSnapshot -ProjectNumber $ProjectNumber
    $existing = @{}
    foreach ($item in @($snapshot.items.nodes)) {
        if ($item.content -and $item.content.url) { $existing[$item.content.url] = $item.id }
    }

    foreach ($configured in Get-ConfiguredItems) {
        if ($existing.ContainsKey($configured.Url)) { continue }

        Write-Action "Add $($configured.Url) to Project"
        if ($Apply) {
            $result = Invoke-Gh -Arguments @(
                "project", "item-add", "$ProjectNumber",
                "--owner", $Config.project_owner,
                "--url", $configured.Url,
                "--format", "json"
            ) -AllowFailure

            if ($result.ExitCode -eq 0) {
                $Changes.Add("Added $($configured.Url) to Project.")
            }
            elseif ($result.Text -notmatch "already") {
                $Warnings.Add("Project item warning for $($configured.Url): $($result.Text)")
            }
        }
    }
}

function Set-ItemFieldValue {
    param(
        [string]$ProjectId,
        [string]$ItemId,
        [object]$Field,
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) { return }

    $args = @(
        "project", "item-edit",
        "--project-id", $ProjectId,
        "--id", $ItemId,
        "--field-id", $Field.id
    )

    switch ($Field.dataType) {
        "SINGLE_SELECT" {
            $option = @($Field.options | Where-Object { $_.name -eq $Value }) | Select-Object -First 1
            if (-not $option) { throw "Option '$Value' is missing in field '$($Field.name)'." }
            $args += @("--single-select-option-id", $option.id)
        }
        "TEXT" { $args += @("--text", $Value) }
        default { throw "Unsupported automated value type '$($Field.dataType)' for field '$($Field.name)'." }
    }

    Invoke-Gh -Arguments $args | Out-Null
}

function Set-InitialMetadata {
    param([int]$ProjectNumber)
    Write-Section "Initial Project metadata"

    if (-not $Apply) {
        Write-Action "Populate configured Status, Work Package, Item Type, Target Release, Blocked, Human Review and WP outcome values"
        return
    }

    $snapshot = Get-ProjectSnapshot -ProjectNumber $ProjectNumber
    $fields = Get-FieldsByName -Snapshot $snapshot
    $itemByUrl = @{}
    foreach ($item in @($snapshot.items.nodes)) {
        if ($item.content -and $item.content.url) { $itemByUrl[$item.content.url] = $item }
    }

    foreach ($configured in Get-ConfiguredItems) {
        if (-not $itemByUrl.ContainsKey($configured.Url)) {
            $Warnings.Add("Cannot set metadata because Project item is missing: $($configured.Url)")
            continue
        }

        $projectItem = $itemByUrl[$configured.Url]
        foreach ($property in $configured.Metadata.PSObject.Properties) {
            if (-not $fields.ContainsKey($property.Name)) {
                $Warnings.Add("Configured field '$($property.Name)' is not available for $($configured.Url).")
                continue
            }

            $value = [string]$property.Value
            if ($property.Name -eq "Status" -and $projectItem.content.state -in @("CLOSED", "MERGED")) {
                $value = "Done"
            }

            Set-ItemFieldValue -ProjectId $snapshot.id -ItemId $projectItem.id -Field $fields[$property.Name] -Value $value
        }
    }

    $Changes.Add("Populated initial Project metadata.")
}

function Ensure-Views {
    param([int]$ProjectNumber)
    Write-Section "Project views"

    if ($SkipViews) {
        Write-Host "View creation was skipped."
        return
    }

    $snapshot = Get-ProjectSnapshot -ProjectNumber $ProjectNumber
    $existing = @($snapshot.views.nodes | ForEach-Object { $_.name })
    $user = Invoke-GhJson -Arguments @("api", "users/$($Config.project_owner)")

    foreach ($view in $Config.views) {
        if ($view.name -in $existing) {
            Write-Host "View '$($view.name)' already exists."
            continue
        }

        Write-Action "Create $($view.layout) view '$($view.name)'"
        if ($Apply) {
            $body = [ordered]@{
                name = $view.name
                layout = $view.layout
            }
            if (-not [string]::IsNullOrWhiteSpace($view.filter)) { $body["filter"] = $view.filter }

            try {
                Invoke-GhJsonInput -Endpoint "users/$($user.id)/projectsV2/$ProjectNumber/views" -Body $body | Out-Null
                $Changes.Add("Created Project view '$($view.name)'.")
            }
            catch {
                $Warnings.Add("Could not create view '$($view.name)' automatically: $($_.Exception.Message)")
            }
        }
    }

    $ManualSteps.Add("In the Project UI, finish view-specific grouping, visible columns, sorting and Roadmap date-field selection. The API can create views but does not fully express every UI layout option.")
}

function Ensure-Milestone {
    Write-Section "Milestones"

    $configured = @()
    if ($Config.PSObject.Properties.Name -contains "milestones" -and @($Config.milestones).Count -gt 0) {
        $configured = @($Config.milestones)
    }
    elseif ($Config.PSObject.Properties.Name -contains "milestone" -and $Config.milestone) {
        $configured = @($Config.milestone)
    }
    else {
        throw "No milestone contract is configured."
    }

    foreach ($spec in $configured) {
        $milestones = Invoke-GhJson -Arguments @(
            "api",
            "-H", "Accept: application/vnd.github+json",
            "-H", "X-GitHub-Api-Version: $($Config.api_version)",
            "repos/$($Config.repository)/milestones?state=all&per_page=100"
        )
        $matches = @($milestones | Where-Object { $_.title -eq $spec.title })
        if ($matches.Count -gt 1) { throw "Ambiguous milestone title '$($spec.title)'." }
        $milestone = $matches | Select-Object -First 1
        if (-not $milestone) {
            Write-Action "Create Milestone '$($spec.title)'"
            if ($Apply) {
                Invoke-GhJsonInput -Endpoint "repos/$($Config.repository)/milestones" -Body @{
                    title = $spec.title
                    state = if ($spec.state) { $spec.state } else { "open" }
                    description = $spec.description
                } | Out-Null
                $Changes.Add("Created Milestone '$($spec.title)'.")
            }
        }
        Write-Action "Reconcile exact membership for Milestone '$($spec.title)' through canonical release-planning reconciler"
    }

    $ManualSteps.Add("Use Reconcile-DDDAReleasePlanning.py / the privileged backlog reconciliation workflow for exact milestone membership and stale-membership removal; do not treat this initializer as release approval.")
}

function Write-Report {
    param([object]$Project)

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $path = Join-Path (Get-Location) "ddda-github-governance-setup-$timestamp.md"
    $mode = if ($Apply) { "APPLY" } else { "PLAN" }
    $projectText = if ($Project) { "#$($Project.number) - $($Project.url)" } else { "not available in plan mode" }

    $lines = New-Object 'System.Collections.Generic.List[string]'
    $lines.Add("# DDDA GitHub governance setup report")
    $lines.Add("")
    $lines.Add("- Mode: $mode")
    $lines.Add("- Repository: $($Config.repository)")
    $lines.Add("- Project: $projectText")
    $lines.Add("- Milestone: $($Config.milestone.title)")
    $lines.Add("- Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')")
    $lines.Add("")
    $lines.Add("## Changes")
    if ($Changes.Count -eq 0) { $lines.Add("- none") } else { foreach ($item in $Changes) { $lines.Add("- $item") } }
    $lines.Add("")
    $lines.Add("## Warnings")
    if ($Warnings.Count -eq 0) { $lines.Add("- none") } else { foreach ($item in $Warnings) { $lines.Add("- $item") } }
    $lines.Add("")
    $lines.Add("## Remaining manual steps")
    if ($ManualSteps.Count -eq 0) { $lines.Add("- none") } else { foreach ($item in $ManualSteps) { $lines.Add("- $item") } }

    [System.IO.File]::WriteAllLines($path, $lines, $Utf8NoBom)
    Write-Host "Report: $path" -ForegroundColor Cyan
}

$project = $null
try {
    $resolvedConfig = Resolve-Configuration
    Write-Host "Configuration: $resolvedConfig"
    Assert-Prerequisites

    Ensure-Hierarchy
    Ensure-Dependencies
    $project = Ensure-Project

    if ($project) {
        Ensure-Fields -ProjectNumber ([int]$project.number)
        Ensure-ProjectItems -ProjectNumber ([int]$project.number)
        Set-InitialMetadata -ProjectNumber ([int]$project.number)
        Ensure-Views -ProjectNumber ([int]$project.number)
    }
    elseif (-not $Apply) {
        Write-Host "Project-dependent actions are planned but cannot be inspected until the Project exists."
    }

    Ensure-Milestone

    $ManualSteps.Add("In Project Settings > Workflows, enable only safe mechanical workflows. Do not automate Priority, dates, Milestone, Human Review PASS, gate approval, HRDR or GO/NO-GO.")
    $ManualSteps.Add("Set real Priority, Start date and Target date values only after an explicit planning decision; the automation intentionally leaves them unset.")
    $ManualSteps.Add("Verify that Milestone DDDA 0.1.0 contains PR #8 and Issues #9-#15, but not Parent WP #17, WP-09-WP-11 items or PR #43.")

    if ($OpenProject -and $Apply -and $project) {
        Invoke-Gh -Arguments @(
            "project", "view", "$($project.number)",
            "--owner", $Config.project_owner,
            "--web"
        ) | Out-Null
    }

    Write-Report -Project $project

    if ($Apply) {
        Write-Host "Automated GitHub governance setup completed." -ForegroundColor Green
    }
    else {
        Write-Host "Plan completed. Run again with -Apply to perform the changes." -ForegroundColor Yellow
    }
}
catch {
    $Warnings.Add($_.Exception.Message)
    try { Write-Report -Project $project } catch { }
    Write-Error $_
    exit 1
}
