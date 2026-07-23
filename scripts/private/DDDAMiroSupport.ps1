Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-DDDAIsWindows {
    return ($env:OS -eq "Windows_NT" -or $PSVersionTable.PSEdition -eq "Desktop")
}

function Get-DDDAStateRoot {
    if (Test-DDDAIsWindows) {
        if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
            throw "LOCALAPPDATA není dostupné; nelze určit lokální DDDA state adresář."
        }
        return (Join-Path $env:LOCALAPPDATA "DDDA")
    }

    if (-not [string]::IsNullOrWhiteSpace($env:XDG_STATE_HOME)) {
        return (Join-Path $env:XDG_STATE_HOME "ddda")
    }

    $homePath = [Environment]::GetFolderPath("UserProfile")
    if ([string]::IsNullOrWhiteSpace($homePath)) {
        throw "Nelze určit domovský adresář pro DDDA state."
    }
    return (Join-Path $homePath ".local/state/ddda")
}

function Get-DDDAMiroSecretPath {
    return (Join-Path (Get-DDDAStateRoot) "secrets/miro-access-token.xml")
}

function ConvertFrom-DDDASecureString {
    param([Parameter(Mandatory = $true)][Security.SecureString]$SecureValue)

    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

function Clear-DDDAMiroAccessToken {
    $secretPath = Get-DDDAMiroSecretPath
    if (Test-Path $secretPath) {
        Remove-Item -Path $secretPath -Force
    }
}

function Get-DDDAMiroAccessToken {
    param(
        [switch]$ResetToken,
        [switch]$NonInteractive
    )

    $secretPath = Get-DDDAMiroSecretPath
    $secretRoot = Split-Path -Parent $secretPath

    if ($ResetToken) {
        Clear-DDDAMiroAccessToken
    }

    if (Test-Path Env:\MIRO_ACCESS_TOKEN) {
        $token = [string]$env:MIRO_ACCESS_TOKEN
        if ([string]::IsNullOrWhiteSpace($token)) {
            throw "MIRO_ACCESS_TOKEN je nastaven, ale je prázdný."
        }

        if (Test-DDDAIsWindows) {
            New-Item -ItemType Directory -Path $secretRoot -Force | Out-Null
            $secureToken = ConvertTo-SecureString $token -AsPlainText -Force
            $secureToken | Export-Clixml -Path $secretPath
        }
        return $token
    }

    if ((Test-DDDAIsWindows) -and (Test-Path $secretPath)) {
        $secureToken = Import-Clixml -Path $secretPath
        $token = ConvertFrom-DDDASecureString -SecureValue $secureToken
        if ([string]::IsNullOrWhiteSpace($token)) {
            throw "Uložený Miro token je prázdný. Použij -ResetToken."
        }
        return $token
    }

    if ($NonInteractive) {
        throw "Miro token není dostupný. Nastav MIRO_ACCESS_TOKEN nebo spusť interaktivně bez -NonInteractive."
    }

    $secureToken = Read-Host "Vlož Miro access token" -AsSecureString
    $token = ConvertFrom-DDDASecureString -SecureValue $secureToken
    if ([string]::IsNullOrWhiteSpace($token)) {
        throw "Miro token je prázdný."
    }

    if (Test-DDDAIsWindows) {
        New-Item -ItemType Directory -Path $secretRoot -Force | Out-Null
        $secureToken | Export-Clixml -Path $secretPath
    }
    else {
        Write-Warning "Na tomto systému se token nepersistuje. Pro další běh nastav MIRO_ACCESS_TOKEN."
    }

    return $token
}

function ConvertTo-DDDAJsonUtf8Bytes {
    param([Parameter(Mandatory = $true)][object]$Body)

    $json = $Body | ConvertTo-Json -Depth 20 -Compress
    return [pscustomobject]@{
        Json = $json
        Bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    }
}

function Invoke-DDDAMiroApi {
    param(
        [Parameter(Mandatory = $true)][ValidateSet("GET", "POST", "PATCH", "DELETE")][string]$Method,
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$AccessToken,
        [object]$Body
    )

    $headers = @{ Authorization = "Bearer $AccessToken"; Accept = "application/json" }
    $json = $null

    try {
        if ($PSBoundParameters.ContainsKey("Body")) {
            $encoded = ConvertTo-DDDAJsonUtf8Bytes -Body $Body
            $json = $encoded.Json
            return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers -ContentType "application/json; charset=utf-8" -Body $encoded.Bytes
        }

        return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers
    }
    catch {
        $statusCode = $null
        $responseBody = $null

        try {
            $response = $_.Exception.Response
            if ($null -ne $response) {
                try { $statusCode = [int]$response.StatusCode } catch {}

                if ($response.PSObject.Properties["Content"] -and $null -ne $response.Content) {
                    try { $responseBody = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult() } catch {}
                }

                if ([string]::IsNullOrWhiteSpace([string]$responseBody) -and $response.PSObject.Methods["GetResponseStream"]) {
                    $stream = $response.GetResponseStream()
                    if ($null -ne $stream) {
                        $reader = New-Object System.IO.StreamReader($stream)
                        try { $responseBody = $reader.ReadToEnd() }
                        finally { $reader.Dispose() }
                    }
                }
            }
        }
        catch {
        }

        if ([string]::IsNullOrWhiteSpace([string]$responseBody)) {
            $responseBody = $_.Exception.Message
        }

        $requestInfo = ""
        if (-not [string]::IsNullOrWhiteSpace([string]$json)) {
            $requestInfo = "`nRequest body: $json"
        }

        throw ("Miro API {0} {1} selhalo. HTTP {2}. Response: {3}{4}" -f $Method, $Uri, $statusCode, $responseBody, $requestInfo)
    }
}

function Assert-DDDAMiroTokenScopes {
    param([Parameter(Mandatory = $true)][string]$AccessToken)

    $context = Invoke-DDDAMiroApi -Method GET -Uri "https://api.miro.com/v1/oauth-token" -AccessToken $AccessToken
    $contextJson = $context | ConvertTo-Json -Depth 20
    if (($contextJson -notmatch "boards:read") -or ($contextJson -notmatch "boards:write")) {
        throw "Miro token nemá požadované scopes boards:read a boards:write."
    }
    return $context
}

function Get-DDDAObjectPropertyValue {
    param(
        [object]$InputObject,
        [Parameter(Mandatory = $true)][string]$Name,
        [object]$DefaultValue = $null
    )

    if ($null -eq $InputObject) {
        return $DefaultValue
    }

    if ($InputObject -is [System.Collections.IDictionary]) {
        if ($InputObject.Contains($Name)) {
            return $InputObject[$Name]
        }
        return $DefaultValue
    }

    $property = $InputObject.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $DefaultValue
    }

    return $property.Value
}

function Get-DDDAAllMiroItems {
    param(
        [Parameter(Mandatory = $true)][string]$BoardId,
        [Parameter(Mandatory = $true)][string]$AccessToken
    )

    $items = @()
    $cursor = $null
    $boardSegment = [Uri]::EscapeDataString($BoardId)

    do {
        $uri = "https://api.miro.com/v2/boards/$boardSegment/items?limit=50"
        if ($cursor) {
            $uri += "&cursor=" + [Uri]::EscapeDataString([string]$cursor)
        }

        $page = Invoke-DDDAMiroApi -Method GET -Uri $uri -AccessToken $AccessToken
        $pageData = Get-DDDAObjectPropertyValue -InputObject $page -Name "data" -DefaultValue @()
        if ($pageData) {
            $items += @($pageData)
        }
        $cursor = Get-DDDAObjectPropertyValue -InputObject $page -Name "cursor"
    }
    while ($cursor)

    return $items
}

function Find-DDDAMiroItemByMarker {
    param(
        [Parameter(Mandatory = $true)][string]$BoardId,
        [Parameter(Mandatory = $true)][string]$Marker,
        [Parameter(Mandatory = $true)][string]$AccessToken
    )

    foreach ($item in @(Get-DDDAAllMiroItems -BoardId $BoardId -AccessToken $AccessToken)) {
        $data = Get-DDDAObjectPropertyValue -InputObject $item -Name "data"
        $content = Get-DDDAObjectPropertyValue -InputObject $data -Name "content" -DefaultValue ""
        if ([string]::IsNullOrWhiteSpace([string]$content)) {
            $content = Get-DDDAObjectPropertyValue -InputObject $data -Name "title" -DefaultValue ""
        }

        if ([string]$content -match [regex]::Escape($Marker)) {
            return $item
        }
    }

    return $null
}

function Assert-DDDALastExitCode {
    param([Parameter(Mandatory = $true)][string]$Operation)

    if ($LASTEXITCODE -ne 0) {
        throw ("{0} selhalo. Exit code: {1}" -f $Operation, $LASTEXITCODE)
    }
}

function Invoke-DDDAChildPowerShell {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [string[]]$Arguments = @()
    )

    $hostExe = (Get-Process -Id $PID).Path
    $hostArguments = @("-NoProfile")
    if (Test-DDDAIsWindows) {
        $hostArguments += @("-ExecutionPolicy", "Bypass")
    }
    $hostArguments += @("-File", $ScriptPath)
    $hostArguments += $Arguments

    & $hostExe @hostArguments
    Assert-DDDALastExitCode -Operation ("PowerShell skript {0}" -f $ScriptPath)
}

function Resolve-DDDAPythonCommand {
    foreach ($candidate in @("python", "py")) {
        if (-not (Get-Command $candidate -ErrorAction SilentlyContinue)) {
            continue
        }

        & $candidate --version *> $null
        if ($LASTEXITCODE -eq 0) {
            return $candidate
        }
    }

    throw "Nebyl nalezen funkční příkaz python ani py. DDDA vyžaduje Python 3.11 nebo novější."
}

function Invoke-DDDAGit {
    param(
        [Parameter(Mandatory = $true)][string]$RepositoryPath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $output = & git -C $RepositoryPath @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Git selhal v '$RepositoryPath': git $($Arguments -join ' ')`n$output"
    }
    return ($output | Out-String).Trim()
}

function Assert-DDDACleanGitRepository {
    param(
        [Parameter(Mandatory = $true)][string]$RepositoryPath,
        [Parameter(Mandatory = $true)][string]$Label
    )

    $changes = Invoke-DDDAGit -RepositoryPath $RepositoryPath -Arguments @("status", "--porcelain")
    if (-not [string]::IsNullOrWhiteSpace($changes)) {
        throw "$Label repozitář není čistý:`n$changes"
    }
}

function Get-DDDAWorkspaceProjectPath {
    param(
        [Parameter(Mandatory = $true)][string]$WorkspaceRoot,
        [Parameter(Mandatory = $true)][string]$ProjectId
    )

    $workspaceFull = [System.IO.Path]::GetFullPath($WorkspaceRoot)
    $workspaceFile = Join-Path $workspaceFull "workspace.yaml"
    if (-not (Test-Path $workspaceFile)) {
        throw "Nenalezen workspace.yaml: $workspaceFile"
    }

    $currentId = $null
    foreach ($line in Get-Content -Path $workspaceFile -Encoding UTF8) {
        if ($line -match '^\s*-\s+id:\s*(?<value>.+?)\s*$') {
            $currentId = $Matches["value"].Trim().Trim('"').Trim("'")
            continue
        }

        if ($currentId -eq $ProjectId -and $line -match '^\s+path:\s*(?<value>.+?)\s*$') {
            $relativePath = $Matches["value"].Trim().Trim('"').Trim("'")
            $projectPath = [System.IO.Path]::GetFullPath((Join-Path $workspaceFull $relativePath))
            if (-not (Test-Path $projectPath)) {
                throw "Projekt '$ProjectId' je registrován, ale cesta neexistuje: $projectPath"
            }
            return $projectPath
        }
    }

    throw "Projekt '$ProjectId' nebyl nalezen ve workspace.yaml."
}

function Get-DDDAMiroMapSnapshot {
    param([Parameter(Mandatory = $true)][string]$ProjectPath)

    $mapPath = Join-Path $ProjectPath "miro/miro-map.yaml"
    if (-not (Test-Path $mapPath)) {
        throw "Nenalezen Miro mapping: $mapPath"
    }

    $boardId = $null
    $itemIds = [System.Collections.Generic.List[string]]::new()

    foreach ($line in Get-Content -Path $mapPath -Encoding UTF8) {
        if ($line -match '^board_id:\s*(?<value>.*?)\s*$') {
            $value = $Matches["value"].Trim().Trim('"').Trim("'")
            if ($value -and $value -ne "null") {
                $boardId = $value
            }
        }
        elseif ($line -match '^\s+miro_item_id:\s*(?<value>.*?)\s*$') {
            $value = $Matches["value"].Trim().Trim('"').Trim("'")
            if ($value -and $value -ne "null") {
                $itemIds.Add($value)
            }
        }
    }

    return [pscustomobject]@{
        BoardId = $boardId
        ItemIds = @($itemIds | Sort-Object -Unique)
    }
}
