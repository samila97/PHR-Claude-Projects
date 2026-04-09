param(
    [switch]$Test,
    [int]$Limit = 20,
    [int]$Skip  = 0
)

$HUBSPOT_TOKEN  = "YOUR_HUBSPOT_TOKEN_HERE"
$APOLLO_KEY     = "YOUR_APOLLO_KEY_HERE"
$GOOGLE_KEY     = "YOUR_GOOGLE_KEY_HERE"
$GOOGLE_CX      = "YOUR_GOOGLE_CX_HERE"
$HS_BASE          = "https://api.hubapi.com"
$HS_HEADERS       = @{ Authorization = "Bearer $HUBSPOT_TOKEN"; "Content-Type" = "application/json" }

$IND_EDUCATION = @("education","higher education","university","school","college","academic","e-learning","edtech")
$IND_TIER1     = @("manufacturing","hospitality","bpo","outsourcing","business process outsourcing","hotel","resort")
$IND_TIER2     = @("retail","transport","transportation","logistics","supply chain","freight","shipping","courier")
$IND_TIER3     = @("banking","finance","financial services","financial","insurance","healthcare","health care","medical","pharmaceutical","hospital","clinic")

$TITLE_NEG     = @("student","intern","internship","trainee","graduate student","undergraduate","apprentice")
$TITLE_TIER1   = @("chief human resource officer","chro","chief executive officer","ceo","chief financial officer","cfo","chief people officer","cpo")
$TITLE_TIER2   = @("hr director","human resources director","head of hr","head of human resources","senior hr manager","senior human resources manager","it manager","information technology manager","procurement manager","vp hr","vp human resources","vice president hr")
$TITLE_TIER3   = @("hr manager","human resources manager","recruitment manager","talent acquisition manager","talent acquisition","recruiter","hr business partner","people operations","people manager","workforce manager","hr generalist")

$NON_CORP      = @("gmail.com","googlemail.com","yahoo.com","ymail.com","hotmail.com","hotmail.co.uk","outlook.com","live.com","msn.com","aol.com","icloud.com","me.com","mac.com","protonmail.com","mail.com","zoho.com")

function Invoke-Api {
    param($Uri, $Method = "GET", $Headers = @{}, $Body = $null, $RetryOn429 = $true)
    try {
        $p = @{ Uri = $Uri; Method = $Method; Headers = $Headers; ErrorAction = "Stop" }
        if ($Body) { $p.Body = ($Body | ConvertTo-Json -Depth 10) }
        return Invoke-RestMethod @p
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -eq 429 -and $RetryOn429) {
            Write-Host "    Rate limited - waiting 10s..." -ForegroundColor Yellow
            Start-Sleep -Seconds 10
            return Invoke-Api -Uri $Uri -Method $Method -Headers $Headers -Body $Body -RetryOn429 $false
        }
        Write-Host "    API error ($code): $_" -ForegroundColor Red
        return $null
    }
}

function Setup-Properties {
    $props = @(
        @{ name="lead_score";           label="Lead Score";           type="number"; fieldType="number";          groupName="contactinformation"; description="Calculated lead score" },
        @{ name="lead_score_label";     label="Lead Score Label";     type="string"; fieldType="text";            groupName="contactinformation"; description="Strong Fit / Potential Fit / Weak Fit" },
        @{ name="lead_score_breakdown"; label="Lead Score Breakdown"; type="string"; fieldType="textarea";        groupName="contactinformation"; description="Score detail per dimension" },
        @{ name="data_enriched";        label="Data Enriched";        type="string"; fieldType="text";            groupName="contactinformation"; description="True if enriched via Apollo/Google" },
        @{ name="enriched_employee_count"; label="Enriched Employee Count"; type="string"; fieldType="text"; groupName="contactinformation"; description="Employee count filled via Apollo/Google enrichment" }
    )
    foreach ($prop in $props) {
        try {
            Invoke-RestMethod -Uri "$HS_BASE/crm/v3/properties/contacts" -Method POST -Headers $HS_HEADERS -Body ($prop | ConvertTo-Json) -ErrorAction Stop | Out-Null
            Write-Host "  Created: $($prop.label)" -ForegroundColor Green
        } catch {
            $code = $_.Exception.Response.StatusCode.value__
            if ($code -eq 409) { Write-Host "  Exists : $($prop.label)" -ForegroundColor Gray }
            else { Write-Host "  Warning ($code): $($prop.label)" -ForegroundColor Yellow }
        }
    }
}

function Get-RecentContacts($count, $skip = 0) {
    $body = @{
        limit      = $count + $skip
        properties = @("firstname","lastname","email","phone","jobtitle","industry","numberofemployees","company","website","createdate")
        sorts      = @(@{ propertyName = "createdate"; direction = "DESCENDING" })
    }
    $resp = Invoke-Api -Uri "$HS_BASE/crm/v3/objects/contacts/search" -Method POST -Headers $HS_HEADERS -Body $body
    return $resp.results | Select-Object -Skip $skip -First $count
}

function Get-AllContacts {
    $contacts = @()
    $after    = $null
    $fields   = "firstname,lastname,email,phone,jobtitle,industry,numberofemployees,company,website,createdate"
    do {
        $uri = "$HS_BASE/crm/v3/objects/contacts?limit=100&properties=$fields"
        if ($after) { $uri += "&after=$after" }
        $resp = Invoke-Api -Uri $uri -Headers $HS_HEADERS
        if (-not $resp) { break }
        $contacts += $resp.results
        $after = $resp.paging.next.after
        Start-Sleep -Milliseconds 100
    } while ($after)
    return $contacts
}

function Update-Contact($id, $props) {
    Invoke-Api -Uri "$HS_BASE/crm/v3/objects/contacts/$id" -Method PATCH -Headers $HS_HEADERS -Body @{ properties = $props } | Out-Null
}

function Enrich-Apollo($contact) {
    $p = $contact.properties
    $payload = @{
        first_name        = if ($p.firstname) { $p.firstname } else { "" }
        last_name         = if ($p.lastname)  { $p.lastname  } else { "" }
        email             = if ($p.email)     { $p.email     } else { "" }
        organization_name = if ($p.company)   { $p.company   } else { "" }
    }
    if ($p.email -and $p.email -match "@") { $payload.domain = $p.email.Split("@")[1] }

    $resp = Invoke-Api -Uri "https://api.apollo.io/v1/people/match" -Method POST -Headers @{"Content-Type"="application/json";"Cache-Control"="no-cache";"X-Api-Key"=$APOLLO_KEY} -Body $payload
    if (-not $resp -or -not $resp.person) { return @{} }

    $person = $resp.person
    $org    = if ($person.organization) { $person.organization } else { @{} }
    $result = @{}

    if (-not $p.jobtitle          -and $person.title)                { $result.jobtitle               = $person.title }
    if (-not $p.email             -and $person.email)                { $result.email                  = $person.email }
    if (-not $p.industry          -and $org.industry)                { $result.industry               = $org.industry }
    if (-not $p.numberofemployees -and $org.estimated_num_employees) { $result.enriched_employee_count = [string]$org.estimated_num_employees }
    if (-not $p.phone) {
        $phones = $person.phone_numbers
        if ($phones -and $phones.Count -gt 0) { $result.phone = $phones[0].raw_number }
    }
    return $result
}

function Enrich-Google($contact, $missingFields) {
    $p       = $contact.properties
    $name    = ("$($p.firstname) $($p.lastname)").Trim()
    $company = if ($p.company) { $p.company } else { "" }
    if (-not $name -and -not $company) { return @{} }

    $q    = [Uri]::EscapeDataString("`"$name`" `"$company`" job title industry employees")
    $uri  = "https://www.googleapis.com/customsearch/v1?key=$GOOGLE_KEY&cx=$GOOGLE_CX&q=$q&num=3"
    $resp = Invoke-Api -Uri $uri -Headers @{}
    if (-not $resp -or -not $resp.items) { return @{} }

    $combined = ($resp.items | ForEach-Object { "$($_.snippet) $($_.title)" }) -join " "
    $result   = @{}
    if ($missingFields -contains "numberofemployees") {
        if ($combined -match '(\d[\d,]+)\s*(employees|staff|people|workers)') {
            $result.numberofemployees = $Matches[1] -replace ",",""
        }
    }
    return $result
}

function Score-Industry($industry) {
    if (-not $industry) { return 0, "Unknown (no industry)" }
    $v = $industry.ToLower()
    foreach ($kw in $IND_EDUCATION) { if ($v -match [regex]::Escape($kw)) { return 0,  "Education ($industry)" } }
    foreach ($kw in $IND_TIER1)     { if ($v -match [regex]::Escape($kw)) { return 35, "Tier 1 - $industry" } }
    foreach ($kw in $IND_TIER2)     { if ($v -match [regex]::Escape($kw)) { return 25, "Tier 2 - $industry" } }
    foreach ($kw in $IND_TIER3)     { if ($v -match [regex]::Escape($kw)) { return 15, "Tier 3 - $industry" } }
    return 5, "Other - $industry"
}

function Score-CompanySize($numEmp) {
    if (-not $numEmp) { return 0, "Unknown (no employee count)" }
    try   { $n = [int]($numEmp -replace ",","") }
    catch { return 0, "Unknown (unparseable)" }
    if    ($n -ge 200 -and $n -le 2000) { return 30, "Mid-Market ($n employees)" }
    elseif ($n -gt 2000)                { return 22, "Enterprise ($n employees)" }
    else                                { return 8,  "SMB ($n employees)" }
}

function Score-JobTitle($title) {
    if (-not $title) { return 2, "Unknown (no title)" }
    $v = $title.ToLower()
    foreach ($kw in $TITLE_NEG)   { if ($v -match [regex]::Escape($kw)) { return -15, "Negative - $title" } }
    foreach ($kw in $TITLE_TIER1) { if ($v -match [regex]::Escape($kw)) { return 25,  "Tier 1 - $title" } }
    foreach ($kw in $TITLE_TIER2) { if ($v -match [regex]::Escape($kw)) { return 18,  "Tier 2 - $title" } }
    foreach ($kw in $TITLE_TIER3) { if ($v -match [regex]::Escape($kw)) { return 12,  "Tier 3 - $title" } }
    return 2, "Other - $title"
}

function Score-ContactData($email, $phone) {
    $score = 0; $parts = @()
    if ($phone -and $phone.Trim()) { $score += 5; $parts += "Phone +5" }
    if ($email -and $email -match "@") {
        $domain = $email.Split("@")[1].ToLower()
        if ($NON_CORP -contains $domain) { $score += 2.5; $parts += "Non-corporate email +2.5" }
        else                             { $score += 5;   $parts += "Corporate email +5" }
    }
    $label = if ($parts.Count -gt 0) { $parts -join ", " } else { "No contact data" }
    return $score, $label
}

function Get-ScoreLabel($score) {
    if ($score -ge 75) { return "Strong Fit" }
    if ($score -ge 40) { return "Potential Fit" }
    return "Weak Fit"
}

function Calculate-Score($contact) {
    $p = $contact.properties
    $empCount = if ($p.numberofemployees) { $p.numberofemployees } else { $p.enriched_employee_count }
    $indScore,   $indLabel   = Score-Industry    $p.industry
    $sizeScore,  $sizeLabel  = Score-CompanySize $empCount
    $titleScore, $titleLabel = Score-JobTitle    $p.jobtitle
    $dataScore,  $dataLabel  = Score-ContactData $p.email $p.phone
    $total    = [math]::Round($indScore + $sizeScore + $titleScore + $dataScore, 1)
    $fitLabel = Get-ScoreLabel $total
    $breakdown = "Industry: $indScore ($indLabel) | Size: $sizeScore ($sizeLabel) | Title: $titleScore ($titleLabel) | Data: $dataScore ($dataLabel)"
    return @{ lead_score = $total; lead_score_label = $fitLabel; lead_score_breakdown = $breakdown }
}

function Get-MissingFields($contact) {
    $p = $contact.properties
    $missing = @()
    foreach ($f in @("jobtitle","industry","numberofemployees","email","phone")) {
        $val = $p.$f
        if (-not $val -or $val.ToString().Trim() -eq "") { $missing += $f }
    }
    return ,$missing
}

# ============================================================
# MAIN
# ============================================================
Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  HubSpot Lead Scoring and Enrichment Pipeline" -ForegroundColor Cyan
if ($Test) { Write-Host "  *** TEST MODE - $Limit most recent contacts ***" -ForegroundColor Yellow }
Write-Host "=================================================================" -ForegroundColor Cyan

Write-Host "`n[1/4] Setting up HubSpot custom properties..."
Setup-Properties

Write-Host "`n[2/4] Fetching contacts from HubSpot..."
if ($Test) {
    $contacts = Get-RecentContacts $Limit $Skip
    $skipMsg  = if ($Skip -gt 0) { ", skipping first $Skip" } else { "" }
    Write-Host "      $($contacts.Count) contact(s) fetched (test mode$skipMsg)" -ForegroundColor Yellow
} else {
    $contacts = Get-AllContacts
    Write-Host "      $($contacts.Count) contact(s) found"
}

if (-not $contacts -or $contacts.Count -eq 0) {
    Write-Host "`nNo contacts to process. Exiting." -ForegroundColor Yellow
    exit
}

Write-Host "`n[3/4] Enriching and scoring $($contacts.Count) contact(s)...`n"

$successCount  = 0
$errorCount    = 0
$enrichedCount = 0
$total         = $contacts.Count

for ($i = 0; $i -lt $total; $i++) {
    $contact = $contacts[$i]
    $id      = $contact.id
    $p       = $contact.properties
    $name    = ("$($p.firstname) $($p.lastname)").Trim()
    if (-not $name) { $name = "(ID $id)" }

    Write-Host "  [$($i+1)/$total] $name"

    try {
        $missing      = Get-MissingFields $contact
        $enrichedData = @{}

        if ($missing.Count -gt 0) {
            Write-Host "    Missing : $($missing -join ', ')" -ForegroundColor Gray

            $apolloData = Enrich-Apollo $contact
            foreach ($k in $apolloData.Keys) { $enrichedData[$k] = $apolloData[$k] }

            $tempProps = @{}
            $p.PSObject.Properties | ForEach-Object { $tempProps[$_.Name] = $_.Value }
            foreach ($k in $enrichedData.Keys) { $tempProps[$k] = $enrichedData[$k] }
            $stillMissing = Get-MissingFields @{ properties = $tempProps }

            if ($stillMissing.Count -gt 0 -and $GOOGLE_KEY) {
                $googleData = Enrich-Google $contact $stillMissing
                foreach ($k in $googleData.Keys) { $enrichedData[$k] = $googleData[$k] }
                Start-Sleep -Milliseconds 500
            }

            if ($enrichedData.Count -gt 0) {
                $enrichedCount++
                Write-Host "    Filled  : $($enrichedData.Keys -join ', ')" -ForegroundColor Green
                foreach ($k in $enrichedData.Keys) { $p | Add-Member -NotePropertyName $k -NotePropertyValue $enrichedData[$k] -Force }
            }
        }

        $scoreData = Calculate-Score $contact
        Write-Host "    Score   : $($scoreData.lead_score) -> $($scoreData.lead_score_label)" -ForegroundColor Cyan

        $updatePayload = @{
            lead_score           = $scoreData.lead_score
            lead_score_label     = $scoreData.lead_score_label
            lead_score_breakdown = $scoreData.lead_score_breakdown
        }
        if ($enrichedData.Count -gt 0) {
            foreach ($k in $enrichedData.Keys) { $updatePayload[$k] = $enrichedData[$k] }
            $updatePayload["data_enriched"] = "true"
        }

        Update-Contact $id $updatePayload
        $successCount++

    } catch {
        Write-Host "    ERROR: $_" -ForegroundColor Red
        $errorCount++
    }

    Start-Sleep -Milliseconds 150
}

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  DONE" -ForegroundColor Green
Write-Host "  Total    : $total"
Write-Host "  Updated  : $successCount"
Write-Host "  Enriched : $enrichedCount"
Write-Host "  Errors   : $errorCount"
Write-Host "=================================================================" -ForegroundColor Cyan
