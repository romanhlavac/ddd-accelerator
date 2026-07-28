[CmdletBinding()]
param(
    [string]$Repository = "romanhlavac/ddd-accelerator",
    [string]$ProjectOwner = "romanhlavac",
    [string]$ProjectTitle = "DDDA Platform Backlog",
    [string]$MilestoneTitle = "DDDA 0.1.0",
    [switch]$Apply,
    [switch]$SkipViews,
    [switch]$OpenProject
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ApiVersion = "2026-03-10"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$Changes = New-Object System.Collections.Generic.List[string]
$Warnings = New-Object System.Collections.Generic.List[string]
$ManualSteps = New-Object System.Collections.Generic.List[string]

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

function Write-Plan {
    param([string]$Message)
    if ($Apply) {
        Write-Host "[APPLY] $Message" -ForegroundColor Green
    }
    else {
        Write-Host "[PLAN ] $Message" -ForegroundColor Yellow
    }
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

    [pscustomobject]@{
        ExitCode = $exitCode
        Text     = $text
        Lines    = @($output)
    }
}

function Invoke-GhJson {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $result = Invoke-Gh -Arguments $Arguments
    if ([string]::IsNullOrWhiteSpace($result.Text)) {
        return $null
    }
    return ($result.Text | ConvertFrom-Json)
}

function Invoke-GhApiJsonInput {
    param(
        [Parameter(Mandatory = $true)][string]$Endpoint,
        [Parameter(Mandatory = $true)][object]$Body,
        [string]$Method = "POST",
        [switch]$GraphQL
    )

    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        $json = $Body | ConvertTo-Json -Depth 30
        [System.IO.File]::WriteAllText($tempFile, $json, $Utf8NoBom)

        if ($GraphQL) {
            $arguments = @("api", "graphql", "--input", $tempFile)
        }
        else {
            $arguments = @(
                "api",
                "--method", $Method,
                "-H", "Accept: application/vnd.github+json",
                "-H", "X-GitHub-Api-Version: $ApiVersion",
                $Endpoint,
                "--input", $tempFile
            )
        }

        return Invoke-GhJson -Arguments $arguments
    }
    finally {
        Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
    }
}

function Assert-Prerequisites {
    Write-Section "Prerequisites"

    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw "GitHub CLI 'gh' is not installed or is not on PATH. Install/update GitHub CLI and run the script again."
    }

    $version = Invoke-Gh -Arguments @("--version")
    Write-Host $version.Text

    $auth = Invoke-Gh -Arguments @("auth", "status") -AllowFailure
    if ($auth.ExitCode -ne 0) {
        throw "GitHub CLI is not authenticated. Run: gh auth login"
    }

    $help = (Invoke-Gh -Arguments @("issue", "edit", "--help")).Text
    foreach ($requiredFlag in @("--add-sub-issue", "--add-blocked-by")) {
        if ($help -notmatch [regex]::Escape($requiredFlag)) {
            throw "Installed GitHub CLI does not support $requiredFlag. Update GitHub CLI to a current version and run again."
        }
    }

    $projectProbe = Invoke-Gh -Arguments @("project", "list", "--owner", $ProjectOwner, "--limit", "1", "--format", "json") -AllowFailure
    if ($projectProbe.ExitCode -ne 0) {
        throw @"
The current GitHub CLI token cannot access Projects.
Run this once and complete the browser authorization:

    gh auth refresh -s project

Then run this script again.
Details:
$($projectProbe.Text)
"@
    }

    Write-Host "Authentication and required GitHub CLI capabilities are available." -ForegroundColor Green
}

function Get-IssueNumbers {
    param(
        [int]$IssueNumber,
        [ValidateSet("subIssues", "blockedBy", "blocking")][string]$Relationship
    )

    $json = Invoke-GhJson -Arguments @(
        "issue", "view", "$IssueNumber",
        "-R", $Repository,
        "--json", $Relationship
    )

    $values = @($json.$Relationship)
    return @($values | ForEach-Object { [int]$_.number })
}

function Ensure-SubIssues {
    param(
        [int]$Parent,
        [int[]]$Children
    )

    $current = @(Get-IssueNumbers -IssueNumber $Parent -Relationship "subIssues")
    $missing = @($Children | Where-Object { $_ -notin $current })

    if ($missing.Count -eq 0) {
        Write-Host "Parent #$Parent already has all required sub-issues."
        return
    }

    Write-Plan "Add sub-issues $($missing -join ', ') to parent #$Parent"
    if ($Apply) {
        Invoke-Gh -Arguments @(
            "issue", "edit", "$Parent",
            "-R", $Repository,
            "--add-sub-issue", ($missing -join ",")
        ) | Out-Null
        $Changes.Add("Parent #$Parent: added sub-issues $($missing -join ', ').")
    }
}

function Ensure-BlockedBy {
    param(
        [int]$BlockedIssue,
        [int[]]$BlockingIssues
    )

    $current = @(Get-IssueNumbers -IssueNumber $BlockedIssue -Relationship "blockedBy")
    $missing = @($BlockingIssues | Where-Object { $_ -notin $current })

    if ($missing.Count -eq 0) {
        Write-Host "Issue #$BlockedIssue already has all required dependencies."
        return
    }

    Write-Plan "Mark issue #$BlockedIssue as blocked by $($missing -join ', ')"
    if ($Apply) {
        Invoke-Gh -Arguments @(
            "issue", "edit", "$BlockedIssue",
            "-R", $Repository,
            "--add-blocked-by", ($missing -join ",")
        ) | Out-Null
        $Changes.Add("Issue #$BlockedIssue: added blocked-by dependencies $($missing -join ', ').")
    }
}

function Get-ProjectSnapshot {
    param([int]$ProjectNumber)

    $query = @'
query($login: String!, $number: Int!) {
  user(login: $login) {
    projectV2(number: $number) {
      id
      number
      title
      url
      fields(first: 100) {
        nodes {
          __typename
          ... on ProjectV2FieldCommon {
            id
            name
            dataType
          }
          ... on ProjectV2SingleSelectField {
            options {
              id
              name
            }
          }
        }
      }
      items(first: 100) {
        nodes {
          id
          content {
            __typename
            ... on Issue {
              number
              url
            }
            ... on PullRequest {
              number
              url
            }
          }
        }
      }
      views(first: 100) {
        nodes {
          number
          name
          layout
        }
      }
    }
  }
}
'@

    $payload = @{
        query = $query
        variables = @{
            login  = $ProjectOwner
            number = $ProjectNumber
        }
    }

    $result = Invoke-GhApiJsonInput -Endpoint "graphql" -Body $payload -GraphQL
    return $result.data.user.projectV2
}

function Find-Project {
    $query = @'
query($login: String!) {
  user(login: $login) {
    projectsV2(first: 100) {
      nodes {
        id
        number
        title
        url
        closed
      }
    }
  }
}
'@

    $payload = @{
        query = $query
        variables = @{ login = $ProjectOwner }
    }

    $result = Invoke-GhApiJsonInput -Endpoint "graphql" -Body $payload -GraphQL
    return @($result.data.user.projectsV2.nodes | Where-Object { $_.title -eq $ProjectTitle -and -not $_.closed }) | Select-Object -First 1
}

function Ensure-Project {
    Write-Section "GitHub Project"
    $project = Find-Project

    if (-not $project) {
        Write-Plan "Create user Project '$ProjectTitle' for $ProjectOwner"
        if (-not $Apply) {
            return $null
        }

        Invoke-Gh -Arguments @(
            "project", "create",
            "--owner", $ProjectOwner,
            "--title", $ProjectTitle,
            "--format", "json"
        ) | Out-Null
        $Changes.Add("Created Project '$ProjectTitle'.")
        $project = Find-Project
        if (-not $project) {
            throw "Project was created but could not be found afterwards."
        }
    }
    else {
        Write-Host "Found Project '$ProjectTitle' as #$($project.number)."
    }

    if ($Apply) {
        Invoke-Gh -Arguments @(
            "project", "edit", "$($project.number)",
            "--owner", $ProjectOwner,
            "--description", "Operational backlog, roadmap and release planning for the DDDA platform. Detailed requirements remain authoritative in GitHub Issues; implementation is performed through branches and pull requests.",
            "--visibility", "PUBLIC"
        ) | Out-Null

        $link = Invoke-Gh -Arguments @(
            "project", "link", "$($project.number)",
            "--owner", $ProjectOwner,
            "--repo", $Repository
        ) -AllowFailure
        if ($link.ExitCode -ne 0 -and $link.Text -notmatch "already") {
            $Warnings.Add("Project link command returned: $($link.Text)")
        }
    }

    return $project
}

function Set-SingleSelectOptions {
    param(
        [Parameter(Mandatory = $true)][object]$Field,
        [Parameter(Mandatory = $true)][object[]]$DesiredOptions
    )

    $existingByName = @{}
    foreach ($option in @($Field.options)) {
        $existingByName[$option.name] = $option.id
    }

    $inputOptions = @()
    foreach ($desired in $DesiredOptions) {
        $item = [ordered]@{
            name        = $desired.Name
            description = $desired.Description
            color       = $desired.Color
        }
        if ($existingByName.ContainsKey($desired.Name)) {
            $item.id = $existingByName[$desired.Name]
        }
        $inputOptions += $item
    }

    $mutation = @'
mutation($fieldId: ID!, $options: [ProjectV2SingleSelectFieldOptionInput!]!) {
  updateProjectV2Field(input: {fieldId: $fieldId, singleSelectOptions: $options}) {
    projectV2Field {
      ... on ProjectV2FieldCommon {
        id
        name
      }
    }
  }
}
'@

    $payload = @{
        query = $mutation
        variables = @{
            fieldId = $Field.id
            options = $inputOptions
        }
    }

    Invoke-GhApiJsonInput -Endpoint "graphql" -Body $payload -GraphQL | Out-Null
}

function Ensure-ProjectFields {
    param([int]$ProjectNumber)

    Write-Section "Project fields"

    $singleSelectDefinitions = @(
        @{ Name = "Status"; Options = @(
            @{ Name = "Backlog";     Color = "GRAY";   Description = "Recorded and not yet triaged." },
            @{ Name = "Discovery";   Color = "PURPLE"; Description = "Problem discovery and option analysis." },
            @{ Name = "Triaged";     Color = "BLUE";   Description = "Classified but not yet Ready." },
            @{ Name = "Ready";       Color = "GREEN";  Description = "Meets entry criteria for implementation." },
            @{ Name = "In progress"; Color = "YELLOW"; Description = "Active branch or implementation work exists." },
            @{ Name = "In review";   Color = "ORANGE"; Description = "Technical or human review is active." },
            @{ Name = "Blocked";     Color = "RED";    Description = "Cannot progress until a named condition is met." },
            @{ Name = "Done";        Color = "GREEN";  Description = "Definition of Done is satisfied." },
            @{ Name = "Cancelled";   Color = "GRAY";   Description = "Closed without implementation." }
        )},
        @{ Name = "Priority"; Options = @(
            @{ Name = "P0"; Color = "RED";    Description = "Release, safety or data-integrity blocker." },
            @{ Name = "P1"; Color = "ORANGE"; Description = "Highest active product priority." },
            @{ Name = "P2"; Color = "YELLOW"; Description = "Important planned increment." },
            @{ Name = "P3"; Color = "GRAY";   Description = "Long-term or opportunistic backlog." }
        )},
        @{ Name = "Work Package"; Options = @(
            @{ Name = "WP-08"; Color = "BLUE";   Description = "Platform lifecycle and project steering." },
            @{ Name = "WP-09"; Color = "PURPLE"; Description = "Strategy, portfolio and program lifecycle." },
            @{ Name = "WP-10"; Color = "GREEN";  Description = "Enterprise ingestion." },
            @{ Name = "WP-11"; Color = "ORANGE"; Description = "EventStorming and multi-agent orchestration." },
            @{ Name = "Other"; Color = "GRAY";   Description = "Cross-cutting governance or uncategorized work." }
        )},
        @{ Name = "Item Type"; Options = @(
            @{ Name = "GAP";            Color = "PURPLE"; Description = "Idea or discovered capability gap." },
            @{ Name = "Work Package";   Color = "BLUE";   Description = "Parent roadmap outcome." },
            @{ Name = "Change Request"; Color = "GREEN";  Description = "Concrete implementable delivery slice." },
            @{ Name = "Defect";         Color = "RED";    Description = "Incorrect existing behavior." },
            @{ Name = "Risk";           Color = "ORANGE"; Description = "Risk requiring treatment or decision." },
            @{ Name = "Enabler";        Color = "YELLOW"; Description = "Administrative or technical enabling work." }
        )},
        @{ Name = "Platform Area"; Options = @(
            @{ Name = "DOC";                 Color = "GRAY";   Description = "Documentation." },
            @{ Name = "METHODOLOGY";         Color = "PURPLE"; Description = "DDD and architecture methodology." },
            @{ Name = "TEMPLATE";            Color = "BLUE";   Description = "Templates and scaffolds." },
            @{ Name = "SCHEMA";              Color = "GREEN";  Description = "Machine-readable contracts." },
            @{ Name = "ORCHESTRATION";       Color = "ORANGE"; Description = "Runtime and workflow orchestration." },
            @{ Name = "INGESTION";           Color = "YELLOW"; Description = "Source ingestion and provenance." },
            @{ Name = "CLI";                 Color = "BLUE";   Description = "Command-line interface." },
            @{ Name = "WORKSPACE-GENERATOR"; Color = "GREEN";  Description = "Workspace creation and upgrades." },
            @{ Name = "EXAMPLE";             Color = "PURPLE"; Description = "Reference examples and fixtures." },
            @{ Name = "TESTING";             Color = "YELLOW"; Description = "Test infrastructure and evidence." },
            @{ Name = "RELEASE";             Color = "ORANGE"; Description = "Packaging, promotion and release." },
            @{ Name = "SECURITY-GOVERNANCE"; Color = "RED";    Description = "Security and governance controls." }
        )},
        @{ Name = "Impact"; Options = @(
            @{ Name = "LOW";      Color = "GRAY";   Description = "Localized low-risk change." },
            @{ Name = "MEDIUM";   Color = "YELLOW"; Description = "Material but controlled change." },
            @{ Name = "HIGH";     Color = "ORANGE"; Description = "Broad or high-risk change." },
            @{ Name = "BREAKING"; Color = "RED";    Description = "Breaking compatibility impact." }
        )},
        @{ Name = "Blocked"; Options = @(
            @{ Name = "No";  Color = "GREEN"; Description = "No active blocker." },
            @{ Name = "Yes"; Color = "RED";   Description = "A named blocker or unblock condition exists." }
        )},
        @{ Name = "Human Review"; Options = @(
            @{ Name = "Not required";  Color = "GRAY";   Description = "No special human judgment beyond normal review." },
            @{ Name = "Pending";       Color = "YELLOW"; Description = "Human review is required and not final." },
            @{ Name = "PASS";          Color = "GREEN";  Description = "Explicit human review passed." },
            @{ Name = "FAIL";          Color = "RED";    Description = "Explicit human review failed." },
            @{ Name = "Accepted risks";Color = "ORANGE"; Description = "Human decision accepted documented residual risks." }
        )}
    )

    $plainDefinitions = @(
        @{ Name = "Target Release"; Type = "TEXT" },
        @{ Name = "Start date"; Type = "DATE" },
        @{ Name = "Target date"; Type = "DATE" },
        @{ Name = "Outcome summary"; Type = "TEXT" },
        @{ Name = "Dependency"; Type = "TEXT" }
    )

    $snapshot = Get-ProjectSnapshot -ProjectNumber $ProjectNumber
    $fieldsByName = @{}
    foreach ($field in @($snapshot.fields.nodes)) {
        if ($field.name) { $fieldsByName[$field.name] = $field }
    }

    foreach ($definition in $singleSelectDefinitions) {
        if (-not $fieldsByName.ContainsKey($definition.Name)) {
            Write-Plan "Create single-select field '$($definition.Name)'"
            if ($Apply) {
                Invoke-Gh -Arguments @(
                    "project", "field-create", "$ProjectNumber",
                    "--owner", $ProjectOwner,
                    "--name", $definition.Name,
                    "--data-type", "SINGLE_SELECT",
                    "--single-select-options", (($definition.Options | ForEach-Object { $_.Name }) -join ","),
                    "--format", "json"
                ) | Out-Null
                $Changes.Add("Created Project field '$($definition.Name)'.")
            }
        }
    }

    foreach ($definition in $plainDefinitions) {
        if (-not $fieldsByName.ContainsKey($definition.Name)) {
            Write-Plan "Create $($definition.Type) field '$($definition.Name)'"
            if ($Apply) {
                Invoke-Gh -Arguments @(
                    "project", "field-create", "$ProjectNumber",
                    "--owner", $ProjectOwner,
                    "--name", $definition.Name,
                    "--data-type", $definition.Type,
                    "--format", "json"
                ) | Out-Null
                $Changes.Add("Created Project field '$($definition.Name)'.")
            }
        }
    }

    if ($Apply) {
        $snapshot = Get-ProjectSnapshot -ProjectNumber $ProjectNumber
        $fieldsByName = @{}
        foreach ($field in @($snapshot.fields.nodes)) {
            if ($field.name) { $fieldsByName[$field.name] = $field }
        }

        foreach ($definition in $singleSelectDefinitions) {
            $field = $fieldsByName[$definition.Name]
            if (-not $field) {
                throw "Project field '$($definition.Name)' is missing after creation."
            }
            Set-SingleSelectOptions -Field $field -DesiredOptions $definition.Options
        }
        $Changes.Add("Normalized all single-select field options, including Status.")
    }
}

function Ensure-ProjectItems {
    param([int]$ProjectNumber)

    Write-Section "Project items"
    $baseUrl = "https://github.com/$Repository"
    $urls = New-Object System.Collections.Generic.List[string]
    $urls.Add("$baseUrl/pull/8")
    foreach ($number in 9..42) {
        $urls.Add("$baseUrl/issues/$number")
    }
    $urls.Add("$baseUrl/pull/43")
    $urls.Add("$baseUrl/issues/44")

    $snapshot = Get-ProjectSnapshot -ProjectNumber $ProjectNumber
    $existing = @{}
    foreach ($item in @($snapshot.items.nodes)) {
        if ($item.content -and $item.content.url) {
            $existing[$item.content.url] = $item.id
        }
    }

    foreach ($url in $urls) {
        if ($existing.ContainsKey($url)) {
            continue
        }

        Write-Plan "Add $url to Project"
        if ($Apply) {
            $result = Invoke-Gh -Arguments @(
                "project", "item-add", "$ProjectNumber",
                "--owner", $ProjectOwner,
                "--url", $url,
                "--format", "json"
            ) -AllowFailure

            if ($result.ExitCode -eq 0) {
                $Changes.Add("Added $url to Project.")
            }
            elseif ($result.Text -match "already") {
                Write-Host "Already present: $url"
            }
            else {
                $Warnings.Add("Could not add $url to Project: $($result.Text)")
            }
        }
    }
}

function Get-ProjectField {
    param(
        [object]$Snapshot,
        [string]$Name
    )
    return @($Snapshot.fields.nodes | Where-Object { $_.name -eq $Name }) | Select-Object -First 1
}

function Set-ProjectItemValue {
    param(
        [string]$ItemId,
        [string]$ProjectId,
        [object]$Field,
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) { return }

    if ($Field.dataType -eq "SINGLE_SELECT") {
        $option = @($Field.options | Where-Object { $_.name -eq $Value }) | Select-Object -First 1
        if (-not $option) {
            throw "Option '$Value' was not found in field '$($Field.name)'."
        }
        Invoke-Gh -Arguments @(
            "project", "item-edit",
            "--id", $ItemId,
            "--project-id", $ProjectId,
            "--field-id", $Field.id,
            "--single-select-option-id", $option.id
        ) | Out-Null
    }
    elseif ($Field.dataType -eq "TEXT") {
        Invoke-Gh -Arguments @(
            "project", "item-edit",
            "--id", $ItemId,
            "--project-id", $ProjectId,
            "--field-id", $Field.id,
            "--text", $Value
        ) | Out-Null
    }
    else {
        throw "Unsupported automated field type '$($Field.dataType)' for '$($Field.name)'."
    }
}

function Set-InitialProjectMetadata {
    param([int]$ProjectNumber)

    Write-Section "Initial Project metadata"
    if (-not $Apply) {
        Write-Plan "Populate Work Package, Item Type, Status, Target Release, Blocked, Human Review and WP outcomes"
        return
    }

    $snapshot = Get-ProjectSnapshot -ProjectNumber $ProjectNumber
    $projectId = $snapshot.id
    $itemByUrl = @{}
    foreach ($item in @($snapshot.items.nodes)) {
        if ($item.content -and $item.content.url) {
            $itemByUrl[$item.content.url] = $item.id
        }
    }

    $fieldNames = @("Status", "Work Package", "Item Type", "Target Release", "Blocked", "Human Review", "Outcome summary")
    $fields = @{}
    foreach ($name in $fieldNames) {
        $field = Get-ProjectField -Snapshot $snapshot -Name $name
        if (-not $field) { throw "Required Project field '$name' is missing." }
        $fields[$name] = $field
    }

    $baseUrl = "https://github.com/$Repository"
    $metadata = New-Object System.Collections.Generic.List[object]

    $metadata.Add(@{ Url = "$baseUrl/issues/17"; Status = "Blocked";     WP = "WP-08"; Type = "Work Package"; Target = "0.1.0"; Blocked = "Yes"; Human = "Pending"; Outcome = "Reproducible platform lifecycle, G1-G8 steering and human-controlled release governance." })
    $metadata.Add(@{ Url = "$baseUrl/issues/18"; Status = "Backlog";     WP = "WP-09"; Type = "Work Package"; Target = "TBD";   Blocked = "No";  Human = "Not required"; Outcome = "Strategy, Wardley, portfolio and P0-P10 program governance linked to DDD and teams." })
    $metadata.Add(@{ Url = "$baseUrl/issues/19"; Status = "Backlog";     WP = "WP-10"; Type = "Work Package"; Target = "TBD";   Blocked = "No";  Human = "Not required"; Outcome = "Secure and auditable Office, PDF and ArchiMate ingestion with source provenance." })
    $metadata.Add(@{ Url = "$baseUrl/issues/20"; Status = "Backlog";     WP = "WP-11"; Type = "Work Package"; Target = "TBD";   Blocked = "No";  Human = "Not required"; Outcome = "Executable EventStorming and bounded multi-agent workflows with explicit human checkpoints." })

    foreach ($number in 9..15) {
        $status = if ($number -in @(13, 15)) { "In progress" } else { "Blocked" }
        $blocked = if ($number -in @(13, 15)) { "No" } else { "Yes" }
        $metadata.Add(@{ Url = "$baseUrl/issues/$number"; Status = $status; WP = "WP-08"; Type = "Change Request"; Target = "0.1.0"; Blocked = $blocked; Human = "Pending"; Outcome = "" })
    }

    foreach ($number in 21..26) {
        $metadata.Add(@{ Url = "$baseUrl/issues/$number"; Status = "Backlog"; WP = "WP-09"; Type = "Change Request"; Target = "TBD"; Blocked = "No"; Human = "Not required"; Outcome = "" })
    }
    foreach ($number in 27..33) {
        $metadata.Add(@{ Url = "$baseUrl/issues/$number"; Status = "Backlog"; WP = "WP-10"; Type = "Change Request"; Target = "TBD"; Blocked = "No"; Human = "Not required"; Outcome = "" })
    }
    foreach ($number in 34..41) {
        $metadata.Add(@{ Url = "$baseUrl/issues/$number"; Status = "Backlog"; WP = "WP-11"; Type = "Change Request"; Target = "TBD"; Blocked = "No"; Human = "Not required"; Outcome = "" })
    }

    $metadata.Add(@{ Url = "$baseUrl/pull/8";    Status = "Blocked";     WP = "WP-08"; Type = "Change Request"; Target = "0.1.0"; Blocked = "Yes"; Human = "Pending"; Outcome = "" })
    $metadata.Add(@{ Url = "$baseUrl/issues/16"; Status = "In progress"; WP = "Other"; Type = "Change Request"; Target = "TBD"; Blocked = "No"; Human = "Pending"; Outcome = "" })
    $metadata.Add(@{ Url = "$baseUrl/issues/42"; Status = "In progress"; WP = "Other"; Type = "Enabler"; Target = "TBD"; Blocked = "No"; Human = "Not required"; Outcome = "" })
    $metadata.Add(@{ Url = "$baseUrl/pull/43";   Status = "Blocked";     WP = "Other"; Type = "Change Request"; Target = "TBD"; Blocked = "Yes"; Human = "Pending"; Outcome = "" })
    $metadata.Add(@{ Url = "$baseUrl/issues/44"; Status = "Backlog";     WP = "Other"; Type = "Defect"; Target = "TBD"; Blocked = "No"; Human = "Not required"; Outcome = "" })

    foreach ($entry in $metadata) {
        if (-not $itemByUrl.ContainsKey($entry.Url)) {
            $Warnings.Add("Project item not found for metadata assignment: $($entry.Url)")
            continue
        }

        $itemId = $itemByUrl[$entry.Url]
        Set-ProjectItemValue -ItemId $itemId -ProjectId $projectId -Field $fields["Status"] -Value $entry.Status
        Set-ProjectItemValue -ItemId $itemId -ProjectId $projectId -Field $fields["Work Package"] -Value $entry.WP
        Set-ProjectItemValue -ItemId $itemId -ProjectId $projectId -Field $fields["Item Type"] -Value $entry.Type
        Set-ProjectItemValue -ItemId $itemId -ProjectId $projectId -Field $fields["Target Release"] -Value $entry.Target
        Set-ProjectItemValue -ItemId $itemId -ProjectId $projectId -Field $fields["Blocked"] -Value $entry.Blocked
        Set-ProjectItemValue -ItemId $itemId -ProjectId $projectId -Field $fields["Human Review"] -Value $entry.Human
        if ($entry.Outcome) {
            Set-ProjectItemValue -ItemId $itemId -ProjectId $projectId -Field $fields["Outcome summary"] -Value $entry.Outcome
        }
    }

    $Changes.Add("Populated initial Project metadata for Work Packages, children, PR #8, PR #43 and governance items.")
}

function Ensure-ProjectViews {
    param([int]$ProjectNumber)

    Write-Section "Project views"
    if ($SkipViews) {
        Write-Host "View creation skipped by parameter."
        return
    }

    $snapshot = Get-ProjectSnapshot -ProjectNumber $ProjectNumber
    $existingNames = @($snapshot.views.nodes | ForEach-Object { $_.name })

    $views = @(
        @{ Name = "Work Packages";            Layout = "table";   Filter = 'Item Type:"Work Package"' },
        @{ Name = "WP hierarchy";             Layout = "table";   Filter = "" },
        @{ Name = "Delivery board";           Layout = "board";   Filter = "" },
        @{ Name = "Roadmap by Work Package";  Layout = "roadmap"; Filter = "-status:Cancelled" },
        @{ Name = "Release scope";            Layout = "table";   Filter = '-Target Release:TBD' },
        @{ Name = "Blocked and P0";           Layout = "table";   Filter = "Blocked:Yes" },
        @{ Name = "Human review queue";       Layout = "table";   Filter = 'Human Review:Pending' },
        @{ Name = "Ready without owner";      Layout = "table";   Filter = "status:Ready no:assignee" },
        @{ Name = "Recently completed";       Layout = "table";   Filter = "status:Done" }
    )

    $user = Invoke-GhJson -Arguments @("api", "users/$ProjectOwner")
    $userId = $user.id

    foreach ($view in $views) {
        if ($view.Name -in $existingNames) {
            Write-Host "View '$($view.Name)' already exists."
            continue
        }

        Write-Plan "Create $($view.Layout) view '$($view.Name)'"
        if ($Apply) {
            $body = [ordered]@{
                name   = $view.Name
                layout = $view.Layout
            }
            if ($view.Filter) { $body.filter = $view.Filter }

            try {
                Invoke-GhApiJsonInput -Endpoint "users/$userId/projectsV2/$ProjectNumber/views" -Body $body | Out-Null
                $Changes.Add("Created Project view '$($view.Name)'.")
            }
            catch {
                $Warnings.Add("Could not create view '$($view.Name)' automatically: $($_.Exception.Message)")
            }
        }
    }

    $ManualSteps.Add("In the Project UI, configure grouping, visible columns and Roadmap date fields for the created views; the current public API creates views but does not fully express all UI grouping/sorting settings.")
}

function Ensure-Milestone {
    Write-Section "Milestone"

    $milestones = Invoke-GhJson -Arguments @(
        "api",
        "-H", "Accept: application/vnd.github+json",
        "-H", "X-GitHub-Api-Version: $ApiVersion",
        "repos/$Repository/milestones?state=all&per_page=100"
    )

    $milestone = @($milestones | Where-Object { $_.title -eq $MilestoneTitle }) | Select-Object -First 1
    if (-not $milestone) {
        Write-Plan "Create Milestone '$MilestoneTitle' without a due date"
        if ($Apply) {
            $body = @{
                title       = $MilestoneTitle
                state       = "open"
                description = "First validated DDDA platform release with lifecycle and project-steering foundation. Milestone membership is release scope, not release approval."
            }
            $milestone = Invoke-GhApiJsonInput -Endpoint "repos/$Repository/milestones" -Body $body
            $Changes.Add("Created Milestone '$MilestoneTitle'.")
        }
    }
    else {
        Write-Host "Found Milestone '$MilestoneTitle' as number $($milestone.number)."
    }

    Write-Plan "Assign PR #8 and Issues #9-#15 to Milestone '$MilestoneTitle'"
    if ($Apply) {
        Invoke-Gh -Arguments @(
            "pr", "edit", "8",
            "-R", $Repository,
            "--milestone", $MilestoneTitle
        ) | Out-Null

        $issueArgs = @("issue", "edit") + @((9..15) | ForEach-Object { "$_" }) + @(
            "-R", $Repository,
            "--milestone", $MilestoneTitle
        )
        Invoke-Gh -Arguments $issueArgs | Out-Null
        $Changes.Add("Assigned PR #8 and Issues #9-#15 to Milestone '$MilestoneTitle'.")
    }
}

function Write-Report {
    param([object]$Project)

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $reportPath = Join-Path (Get-Location) "ddda-github-governance-setup-$timestamp.md"

    $mode = if ($Apply) { "APPLY" } else { "PLAN" }
    $projectText = if ($Project) { "#$($Project.number) — $($Project.url)" } else { "not created/resolved in PLAN mode" }

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# DDDA GitHub governance setup report")
    $lines.Add("")
    $lines.Add("- Mode: `$mode`")
    $lines.Add("- Repository: `$Repository`")
    $lines.Add("- Project: $projectText")
    $lines.Add("- Milestone: `$MilestoneTitle`")
    $lines.Add("- Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')")
    $lines.Add("")
    $lines.Add("## Changes")
    if ($Changes.Count -eq 0) { $lines.Add("- none") }
    else { foreach ($change in $Changes) { $lines.Add("- $change") } }
    $lines.Add("")
    $lines.Add("## Warnings")
    if ($Warnings.Count -eq 0) { $lines.Add("- none") }
    else { foreach ($warning in $Warnings) { $lines.Add("- $warning") } }
    $lines.Add("")
    $lines.Add("## Remaining manual steps")
    if ($ManualSteps.Count -eq 0) { $lines.Add("- none") }
    else { foreach ($step in $ManualSteps) { $lines.Add("- $step") } }

    [System.IO.File]::WriteAllLines($reportPath, $lines, $Utf8NoBom)
    Write-Host ""
    Write-Host "Report: $reportPath" -ForegroundColor Cyan
}

try {
    Assert-Prerequisites

    Write-Section "Native Parent/Sub-issue hierarchy"
    Ensure-SubIssues -Parent 17 -Children @(9, 10, 11, 12, 13, 14, 15)
    Ensure-SubIssues -Parent 18 -Children @(21, 22, 23, 24, 25, 26)
    Ensure-SubIssues -Parent 19 -Children @(27, 28, 29, 30, 31, 32, 33)
    Ensure-SubIssues -Parent 20 -Children @(34, 35, 36, 37, 38, 39, 40, 41)

    Write-Section "Native issue dependencies"
    Ensure-BlockedBy -BlockedIssue 14 -BlockingIssues @(13)
    Ensure-BlockedBy -BlockedIssue 12 -BlockingIssues @(14)
    Ensure-BlockedBy -BlockedIssue 11 -BlockingIssues @(12)
    Ensure-BlockedBy -BlockedIssue 10 -BlockingIssues @(11)
    Ensure-BlockedBy -BlockedIssue 9  -BlockingIssues @(10)

    Ensure-BlockedBy -BlockedIssue 23 -BlockingIssues @(21, 22)
    Ensure-BlockedBy -BlockedIssue 24 -BlockingIssues @(22, 23)
    Ensure-BlockedBy -BlockedIssue 25 -BlockingIssues @(21, 24)
    Ensure-BlockedBy -BlockedIssue 26 -BlockingIssues @(25)

    Ensure-BlockedBy -BlockedIssue 28 -BlockingIssues @(27, 31)
    Ensure-BlockedBy -BlockedIssue 29 -BlockingIssues @(27, 31)
    Ensure-BlockedBy -BlockedIssue 30 -BlockingIssues @(27, 31)
    Ensure-BlockedBy -BlockedIssue 32 -BlockingIssues @(27)
    Ensure-BlockedBy -BlockedIssue 33 -BlockingIssues @(28, 29, 30, 31, 32)

    Ensure-BlockedBy -BlockedIssue 35 -BlockingIssues @(34)
    Ensure-BlockedBy -BlockedIssue 37 -BlockingIssues @(36)
    Ensure-BlockedBy -BlockedIssue 38 -BlockingIssues @(37)
    Ensure-BlockedBy -BlockedIssue 39 -BlockingIssues @(36, 37, 38)
    Ensure-BlockedBy -BlockedIssue 40 -BlockingIssues @(37, 38, 39)
    Ensure-BlockedBy -BlockedIssue 41 -BlockingIssues @(35, 40)

    $project = Ensure-Project
    if ($project) {
        Ensure-ProjectFields -ProjectNumber ([int]$project.number)
        Ensure-ProjectItems -ProjectNumber ([int]$project.number)
        Set-InitialProjectMetadata -ProjectNumber ([int]$project.number)
        Ensure-ProjectViews -ProjectNumber ([int]$project.number)
    }
    elseif (-not $Apply) {
        Write-Host "Project-dependent actions are listed but not executed in PLAN mode because the Project does not yet exist."
    }

    Ensure-Milestone

    $ManualSteps.Add("In Project Settings > Workflows, enable only safe mechanical status workflows. Do not automate Priority, dates, Milestone, Human Review PASS, gate approval or GO/NO-GO.")
    $ManualSteps.Add("Review and set real Priority, Start date and Target date values only after an explicit planning decision; this script intentionally leaves them unset.")
    $ManualSteps.Add("Verify the Milestone contains PR #8 and Issues #9-#15, but not Parent WP #17, WP-09-WP-11 items or PR #43.")

    if ($OpenProject -and $Apply -and $project) {
        Invoke-Gh -Arguments @("project", "view", "$($project.number)", "--owner", $ProjectOwner, "--web") | Out-Null
    }

    Write-Report -Project $project

    if (-not $Apply) {
        Write-Host ""
        Write-Host "PLAN completed. Run again with -Apply to perform the changes." -ForegroundColor Yellow
    }
    else {
        Write-Host ""
        Write-Host "Automated GitHub governance setup completed." -ForegroundColor Green
    }
}
catch {
    $Warnings.Add($_.Exception.Message)
    Write-Error $_
    try { Write-Report -Project $null } catch { }
    exit 1
}
