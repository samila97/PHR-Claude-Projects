$ApiKey    = "gLEUVfxJK3s_0CoONP4BeA"
$InputFile  = "Claude code CRM test run.csv"
$OutputFile = "Claude code CRM enriched.csv"
$FallbackFile = "needs_websearch.json"

$SkipNames = @(
    "gmail support phone number +61~800~765~948 gmail phone number",
    "test company",
    ""
)

function Get-ApolloEnrich {
    param([string]$Domain, [string]$Name)

    # Strip www. prefix from domain
    $cleanDomain = $Domain.Trim() -replace '^www\.', ''

    $params = ""
    if ($cleanDomain) {
        $params = "domain=" + [uri]::EscapeDataString($cleanDomain)
    } elseif ($Name -and $Name.Trim()) {
        $params = "name=" + [uri]::EscapeDataString($Name.Trim())
    } else {
        return $null
    }

    $url = "https://api.apollo.io/v1/organizations/enrich?$params"
    $headers = @{ "X-Api-Key" = $ApiKey; "Content-Type" = "application/json" }

    try {
        $response = Invoke-RestMethod -Uri $url -Method Get -Headers $headers -TimeoutSec 15 -ErrorAction Stop
        return $response.organization
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "    Apollo error [$statusCode]: $($_.Exception.Message.Substring(0, [Math]::Min(80, $_.Exception.Message.Length)))" -ForegroundColor Yellow
        return $null
    }
}

# Read CSV
$rows = Import-Csv -Path $InputFile
$fallbackList = @()
$count = 0

foreach ($row in $rows) {
    $count++
    $name     = $row.'Company name'.Trim()
    $domain   = $row.'Company Domain Name'.Trim()
    $industry = $row.'Industry'.Trim()
    $hcRange  = $row.'Employee Head Count'.Trim()
    $hcNum    = $row.'Number of Employees'.Trim()

    # Skip junk rows
    if ($SkipNames -contains $name.ToLower() -and -not $domain) {
        $displayName = if ($name -eq '') { '(no name)' } else { $name }
        Write-Host "[$("{0:D3}" -f $count)] SKIP   $displayName" -ForegroundColor DarkGray
        continue
    }

    $alreadyHasHC  = ($hcRange -ne "" -or ($hcNum -ne "" -and $hcNum -ne "0.0"))
    $alreadyHasInd = ($industry -ne "")

    if ($alreadyHasHC -and $alreadyHasInd) {
        Write-Host "[$("{0:D3}" -f $count)] FULL   $name" -ForegroundColor Green
        continue
    }

    $displayDomain = if ($domain -eq '') { 'none' } else { $domain }
    Write-Host "[$("{0:D3}" -f $count)] ENRICH $name (domain=$displayDomain)" -NoNewline

    $org = Get-ApolloEnrich -Domain $domain -Name $name

    $gotIndustry = $false
    $gotHC       = $false

    if ($org) {
        # Industry: check 'industry', then 'industries' array, then first keyword
        $apolloIndustry = $org.industry
        if (-not $apolloIndustry -and $org.industries -and $org.industries.Count -gt 0) {
            $apolloIndustry = $org.industries[0]
        }
        if (-not $apolloIndustry -and $org.keywords -and $org.keywords.Count -gt 0) {
            # Take first keyword that looks like an industry category (skip very generic ones)
            $skipKw = @("d2c","b2c","b2b","services","customer service","events services")
            foreach ($kw in $org.keywords) {
                if ($skipKw -notcontains $kw.ToLower()) {
                    $apolloIndustry = $kw
                    break
                }
            }
        }

        $apolloHC = $org.estimated_num_employees
        if (-not $apolloHC) { $apolloHC = $org.num_employees }

        if ($apolloIndustry -and -not $alreadyHasInd) {
            $row.'Industry' = $apolloIndustry
            $gotIndustry = $true
            Write-Host " | industry=$apolloIndustry" -NoNewline -ForegroundColor Cyan
        } elseif ($alreadyHasInd) {
            $gotIndustry = $true
            Write-Host " | industry=kept" -NoNewline
        } else {
            Write-Host " | industry=MISS" -NoNewline -ForegroundColor Red
        }

        if ($apolloHC -and -not $alreadyHasHC) {
            $row.'Number of Employees' = $apolloHC
            $gotHC = $true
            Write-Host " | hc=$apolloHC" -NoNewline -ForegroundColor Cyan
        } elseif ($alreadyHasHC) {
            $gotHC = $true
            Write-Host " | hc=kept" -NoNewline
        } else {
            Write-Host " | hc=MISS" -NoNewline -ForegroundColor Red
        }
    } else {
        if ($alreadyHasInd)  { $gotIndustry = $true; Write-Host " | industry=kept" -NoNewline }
        else                 { Write-Host " | industry=MISS" -NoNewline -ForegroundColor Red }
        if ($alreadyHasHC)   { $gotHC = $true; Write-Host " | hc=kept" -NoNewline }
        else                 { Write-Host " | hc=MISS" -NoNewline -ForegroundColor Red }
    }

    Write-Host ""

    if (-not $gotIndustry -or -not $gotHC) {
        $missing = @()
        if (-not $gotIndustry) { $missing += "industry" }
        if (-not $gotHC)       { $missing += "headcount" }
        $fallbackList += [PSCustomObject]@{
            index      = $count
            name       = $name
            domain     = $domain
            missing    = $missing -join ", "
        }
    }

    Start-Sleep -Milliseconds 400
}

# Write enriched CSV
$rows | Export-Csv -Path $OutputFile -NoTypeInformation -Encoding UTF8

# Write fallback JSON
$fallbackList | ConvertTo-Json | Set-Content -Path $FallbackFile -Encoding UTF8

Write-Host "`nDone. Saved to $OutputFile" -ForegroundColor Green
Write-Host "Companies needing web search fallback: $($fallbackList.Count)" -ForegroundColor Yellow
if ($fallbackList.Count -gt 0) {
    Write-Host "`nFallback list:"
    $fallbackList | Format-Table -AutoSize
}
