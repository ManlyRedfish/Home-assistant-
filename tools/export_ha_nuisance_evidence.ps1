[CmdletBinding()]
param(
    [string]$BaseUrl,
    [string]$AccessToken,
    [datetime]$StartDate,
    [datetime]$EndDate,
    [string]$OutputFolder,
    [ValidateSet('json', 'csv', 'both')]
    [string]$Format = 'both'
)


Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-RedactedMessage {
    param(
        [string]$Message,
        [string]$Token
    )

    if ([string]::IsNullOrEmpty($Message) -or [string]::IsNullOrEmpty($Token)) {
        return $Message
    }

    return $Message.Replace($Token, '[REDACTED_TOKEN]')
}

function Invoke-HAGet {
    param(
        [string]$Uri,
        [hashtable]$Headers,
        [string]$Token
    )

    try {
        return Invoke-RestMethod -Uri $Uri -Headers $Headers -Method Get
    }
    catch {
        $safeMessage = Get-RedactedMessage -Message $_.Exception.Message -Token $Token
        throw "Home Assistant GET failed for '$Uri'. $safeMessage"
    }
}

function New-HistoryUri {
    param(
        [string]$ApiBase,
        [string]$StartIso,
        [string]$EndIso,
        [string[]]$EntityIds,
        [bool]$UseMinimalResponse
    )

    $entityParam = [uri]::EscapeDataString(($EntityIds -join ','))
    $queryParts = @(
        "end_time=$EndIso",
        "filter_entity_id=$entityParam",
        'no_attributes'
    )

    if ($UseMinimalResponse) {
        $queryParts += 'minimal_response'
    }

    return "$ApiBase/api/history/period/$StartIso?" + ($queryParts -join '&')
}

function Convert-HistoryResponseToRows {
    param(
        [object]$HistoryResponse,
        [string]$Category
    )

    $rows = @()

    if ($null -eq $HistoryResponse) {
        return $rows
    }

    foreach ($entitySeries in $HistoryResponse) {
        $seriesEntityId = $null

        foreach ($statePoint in $entitySeries) {
            if (-not [string]::IsNullOrWhiteSpace($statePoint.entity_id)) {
                $seriesEntityId = $statePoint.entity_id
            }

            $effectiveEntityId = if (-not [string]::IsNullOrWhiteSpace($statePoint.entity_id)) {
                $statePoint.entity_id
            }
            else {
                $seriesEntityId
            }

            $rows += [pscustomobject]@{
                category      = $Category
                entity_id     = $effectiveEntityId
                state         = $statePoint.state
                last_changed  = $statePoint.last_changed
                last_updated  = $statePoint.last_updated
                context_id    = $statePoint.context.id
                context_user  = $statePoint.context.user_id
                context_parent = $statePoint.context.parent_id
                attributes_json = ($statePoint.attributes | ConvertTo-Json -Depth 10 -Compress)
            }
        }
    }

    return $rows
}

function Export-Category {
    param(
        [string]$Category,
        [string[]]$EntityIds,
        [string]$StartIso,
        [string]$EndIso,
        [string]$ApiBase,
        [hashtable]$Headers,
        [string]$OutputFolder,
        [string]$Format,
        [string]$Token
    )

    $useMinimalResponse = $Format -eq 'json'
    $historyUri = New-HistoryUri -ApiBase $ApiBase -StartIso $StartIso -EndIso $EndIso -EntityIds $EntityIds -UseMinimalResponse $useMinimalResponse

    $history = Invoke-HAGet -Uri $historyUri -Headers $Headers -Token $Token

    if ($Format -in @('json', 'both')) {
        $jsonPath = Join-Path $OutputFolder "ha_history_${Category}.json"
        $history | ConvertTo-Json -Depth 20 | Out-File -FilePath $jsonPath -Encoding utf8
    }

    if ($Format -in @('csv', 'both')) {
        $rows = Convert-HistoryResponseToRows -HistoryResponse $history -Category $Category
        $csvPath = Join-Path $OutputFolder "ha_history_${Category}.csv"
        $rows | Export-Csv -Path $csvPath -NoTypeInformation -Encoding utf8
    }
}

function Invoke-HaNuisanceEvidenceExport {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseUrl,
        [Parameter(Mandatory = $true)]
        [string]$AccessToken,
        [Parameter(Mandatory = $true)]
        [datetime]$StartDate,
        [Parameter(Mandatory = $true)]
        [datetime]$EndDate,
        [Parameter(Mandatory = $true)]
        [string]$OutputFolder,
        [ValidateSet('json', 'csv', 'both')]
        [string]$Format = 'both'
    )

    $normalizedBase = $BaseUrl.TrimEnd('/')
    $apiBase = $normalizedBase

    if ($StartDate -ge $EndDate) {
        throw 'StartDate must be earlier than EndDate.'
    }

    $headers = @{ Authorization = "Bearer $AccessToken" }

    $startUtc = $StartDate.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    $endUtc = $EndDate.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')

    New-Item -ItemType Directory -Path $OutputFolder -Force | Out-Null

    $automationEntities = @(
        'automation.v8_3_hvac_transition_log',
        'automation.v8_samsung_auto_guardrail',
        'automation.v7_5_ghost_assassin',
        'automation.v9_sleep_priority_interlock'
    )

    $climateEntities = @(
        'climate.living_room_air',
        'climate.master_bedroom_air',
        'climate.lincoln_air',
        'climate.lilly_air'
    )

    $timerEntities = @(
        'timer.lr_compressor_cooldown',
        'timer.master_compressor_cooldown',
        'timer.lincoln_compressor_cooldown',
        'timer.lilly_compressor_cooldown'
    )

    $stateUri = "$apiBase/api/states"
    $allStates = Invoke-HAGet -Uri $stateUri -Headers $headers -Token $AccessToken
    $shadeEntities = @($allStates | Where-Object { $_.entity_id -like 'cover.*shade*' } | ForEach-Object { $_.entity_id })

    $manifest = [pscustomobject]@{
        generated_utc = (Get-Date).ToUniversalTime().ToString('o')
        start_utc = $startUtc
        end_utc = $endUtc
        base_url = $normalizedBase
        categories = [pscustomobject]@{
            climates = $climateEntities
            automations = $automationEntities
            timers = $timerEntities
            shades = $shadeEntities
        }
        notes = @(
            'Read-only API usage: GET /api/states, GET /api/history/period, GET /api/logbook',
            'No POST/PUT/PATCH/DELETE requests are used by this script.'
        )
    }
    $manifest | ConvertTo-Json -Depth 10 | Out-File -FilePath (Join-Path $OutputFolder 'ha_export_manifest.json') -Encoding utf8

    Export-Category -Category 'climates' -EntityIds $climateEntities -StartIso $startUtc -EndIso $endUtc -ApiBase $apiBase -Headers $headers -OutputFolder $OutputFolder -Format $Format -Token $AccessToken
    Export-Category -Category 'automations' -EntityIds $automationEntities -StartIso $startUtc -EndIso $endUtc -ApiBase $apiBase -Headers $headers -OutputFolder $OutputFolder -Format $Format -Token $AccessToken
    Export-Category -Category 'timers' -EntityIds $timerEntities -StartIso $startUtc -EndIso $endUtc -ApiBase $apiBase -Headers $headers -OutputFolder $OutputFolder -Format $Format -Token $AccessToken

    $logbookUri = "$apiBase/api/logbook/$startUtc?end_time=$endUtc"
    $logbook = Invoke-HAGet -Uri $logbookUri -Headers $headers -Token $AccessToken
    $logbook | ConvertTo-Json -Depth 20 | Out-File -FilePath (Join-Path $OutputFolder 'ha_logbook.json') -Encoding utf8

    Write-Host "Export complete. Output folder: $OutputFolder"
    Write-Host "Shade entities discovered: $($shadeEntities.Count)"
}

if ($MyInvocation.InvocationName -ne '.') {
    Invoke-HaNuisanceEvidenceExport @PSBoundParameters
}
