# Apply web-search-based industry + headcount updates to the enriched CSV
$InputFile  = "Claude code CRM enriched.csv"
$OutputFile = "Claude code CRM enriched.csv"  # overwrite in place

# Keyed by Record ID -> @{Industry="..."; HC="..."}
# HC = "" means don't update headcount
$updates = @{
    # Construction
    "151465923303" = @{ Industry="Construction";                         HC="400"  }  # Mamsar Group
    # Transportation
    "116928428777" = @{ Industry="Transportation/Trucking/Railroad";     HC=""     }  # United Services Akcess
    # Hospitality (resort/hotel rows that Apollo missed or had wrong data)
    "27701280048"  = @{ Industry="Hospitality";                          HC=""     }  # Marilou Resort
    "27701280027"  = @{ Industry="Hospitality";                          HC=""     }  # KEW Hotel
    "27692986244"  = @{ Industry="Hospitality";                          HC=""     }  # Tambuli Seaside (Apollo said "furniture" - wrong)
    "27701279636"  = @{ Industry="Hospitality";                          HC=""     }  # Coral Blue Oriental Villas
    "27701279615"  = @{ Industry="Hospitality";                          HC=""     }  # Chateau by the Sea
    "27539261797"  = @{ Industry="Hospitality";                          HC=""     }  # Siargao Bleu Resort
    "123720371927" = @{ Industry="Hospitality";                          HC=""     }  # Diamond WaterEdge Resort
    "123978188520" = @{ Industry="Hospitality";                          HC=""     }  # Bans Resort
    "123720371926" = @{ Industry="Hospitality";                          HC=""     }  # Boracay Holiday Resort
    "123679753977" = @{ Industry="Hospitality";                          HC=""     }  # Microtel Inn by Wyndham Boracay
    "123746667196" = @{ Industry="Health, Wellness and Fitness";         HC=""     }  # Tirta Spa Boracay
    "123731175118" = @{ Industry="Hospitality";                          HC=""     }  # Baracay Haven Suites
    "100263898813" = @{ Industry="Hospitality";                          HC=""     }  # Raffles Fairmont Makati
    "100263898814" = @{ Industry="Hospitality";                          HC=""     }  # LET X Integrated Resort (casino hotel)
    "21945718190"  = @{ Industry="Hospitality";                          HC=""     }  # Fuente Pension House
    "21945768014"  = @{ Industry="Hospitality";                          HC=""     }  # morongstarhotel.com
    "29966220134"  = @{ Industry="Hospitality";                          HC=""     }  # aquaboracay.com.ph
    # Fix Apollo keyword-based industry for Henann (luxury travel -> Hospitality)
    "100259578582" = @{ Industry="Hospitality";                          HC=""     }  # Henann Prime Beach Resort
    "100259578581" = @{ Industry="Hospitality";                          HC=""     }  # Henann Palm Beach Resort
    "100259578578" = @{ Industry="Hospitality";                          HC=""     }  # Henann Regency Resort
    "100306015985" = @{ Industry="Hospitality";                          HC=""     }  # Henann Lagoon Resort
    "100259578576" = @{ Industry="Hospitality";                          HC=""     }  # Henann Garden Resort
    "100306015982" = @{ Industry="Hospitality";                          HC=""     }  # Henann Group of Resorts
    # Automotive
    "27588216398"  = @{ Industry="Automotive";                           HC=""     }  # Hyundai Motor Philippines
    "30229260426"  = @{ Industry="Automotive";                           HC=""     }  # toyotabicutan.com.ph
    # Manufacturing - Plastics/Rubber
    "27588216348"  = @{ Industry="Plastics & Rubber Manufacturing";      HC=""     }  # SANKO PLASTICS PHILIPPINES
    "27572933774"  = @{ Industry="Plastics & Rubber Manufacturing";      HC="128"  }  # SEUNG JIN PRECISION Philippines
    "23755952922"  = @{ Industry="Plastics & Rubber Manufacturing";      HC=""     }  # F.R.P. Philippines Corporation
    # Manufacturing - Chemical/Surface Treatment
    "27572933897"  = @{ Industry="Chemicals";                            HC=""     }  # Surtec Philippines
    # Manufacturing - Electronics
    "27572933783"  = @{ Industry="Electrical/Electronic Manufacturing";  HC=""     }  # FUTABA Corporation Philippines
    "31173073057"  = @{ Industry="Electrical/Electronic Manufacturing";  HC=""     }  # Denso Ten Solutions Philippines
    # Food & Beverages
    "21684814419"  = @{ Industry="Food & Beverages";                     HC=""     }  # Epicurean Partners (Kenny Rogers Roasters)
    "221862542057" = @{ Industry="Food & Beverages";                     HC=""     }  # Creative Dishes
    "25618904095"  = @{ Industry="Food & Beverages";                     HC=""     }  # bountyagro.com.ph
    "220568212214" = @{ Industry="Food & Beverages";                     HC=""     }  # Six In One Corporation
    "152599879409" = @{ Industry="Food & Beverages";                     HC=""     }  # CERES SUMMIT CORPORATION
    "21945618189"  = @{ Industry="Food & Beverages";                     HC=""     }  # Katunyings
    "21945745558"  = @{ Industry="Food & Beverages";                     HC=""     }  # The Black Bean
    # Retail
    "238207975139" = @{ Industry="Retail";                               HC=""     }  # Cogon Commercial (hardware store)
    "21369664113"  = @{ Industry="Retail";                               HC=""     }  # Budgeting Supermarket
    "25611280923"  = @{ Industry="Retail";                               HC=""     }  # smwatsons.com
    "25619060405"  = @{ Industry="Retail";                               HC=""     }  # The SM Store
    "21983830915"  = @{ Industry="Retail";                               HC=""     }  # Metro Retail
    # Telecommunications
    "238170342084" = @{ Industry="Telecommunications";                   HC=""     }  # Jesedai Telecom
    # Healthcare / Pharmaceuticals
    "221957093092" = @{ Industry="Pharmaceuticals";                      HC="200"  }  # Justright Healthcare
    "25606579581"  = @{ Industry="Pharmaceuticals";                      HC=""     }  # mundipharma.com.ph
    "21369690752"  = @{ Industry="Hospital & Health Care";               HC=""     }  # Iloilo Mission Hospital
    "21369526851"  = @{ Industry="Hospital & Health Care";               HC=""     }  # New Sinai Medical Hospital (override Apollo "orthopedic care")
    "23774238740"  = @{ Industry="Hospital & Health Care";               HC=""     }  # mphhi.com.ph (keep Apollo hc=47)
    # Government
    "220559125225" = @{ Industry="Government Administration";            HC=""     }  # Presidential Communication Office
    "31193079040"  = @{ Industry="Government Administration";            HC=""     }  # Bureau of Jail Management (override "p/cve program")
    "22082112865"  = @{ Industry="Government Administration";            HC=""     }  # Province of Guimaras
    # Real Estate
    "32744844115"  = @{ Industry="Real Estate";                          HC=""     }  # HTLand Inc
    "96601395899"  = @{ Industry="Real Estate";                          HC=""     }  # JLL
    # Construction
    "29964835741"  = @{ Industry="Construction";                         HC=""     }  # Q-R Building Solutions
    "21945924414"  = @{ Industry="Construction";                         HC=""     }  # Ardegal
    "21945853954"  = @{ Industry="Construction";                         HC=""     }  # HG3 Construction
    # BPO / Outsourcing
    "21369713262"  = @{ Industry="Outsourcing/Offshoring";               HC=""     }  # TeleSynergy
    "31101842589"  = @{ Industry="Outsourcing/Offshoring";               HC=""     }  # Communix
    "21945869090"  = @{ Industry="Outsourcing/Offshoring";               HC=""     }  # PROBE Group
    "221855407846" = @{ Industry="Financial Services";                   HC=""     }  # Monpac Global (BPO/accounting)
    # IT & Services
    "220637488865" = @{ Industry="Information Technology & Services";    HC=""     }  # DoubleSquare Networks
    "21944619629"  = @{ Industry="Information Technology & Services";    HC=""     }  # findme.com.ph (GPS/fleet mgmt)
    "21945712913"  = @{ Industry="Information Technology & Services";    HC=""     }  # domain.ph
    "21945869077"  = @{ Industry="Information Technology & Services";    HC=""     }  # dynamic.com.ph
    "22116442167"  = @{ Industry="Internet";                             HC=""     }  # Mozcom (ISP, now closed)
    "21945869114"  = @{ Industry="Information Technology & Services";    HC=""     }  # easybiophils.com
    # Farming / Agriculture
    "220635513575" = @{ Industry="Farming";                              HC=""     }  # Musahamat Farms
    # Engineering Services
    "220633692887" = @{ Industry="Civil Engineering";                    HC=""     }  # Jadphil Inc (rail engineering)
    "220637488864" = @{ Industry="Mechanical or Industrial Engineering"; HC=""     }  # International Precision
    # Airlines
    "23825753905"  = @{ Industry="Airlines/Aviation";                    HC="6520" }  # pal.com.ph (Philippine Airlines)
    # Environmental Services
    "22563487092"  = @{ Industry="Environmental Services";               HC=""     }  # Klad Sanitation Services
    # Metal Fabrication
    "22352950291"  = @{ Industry="Metal Fabrication";                    HC=""     }  # SolarTech Steel Fabrication
    # Staffing / Recruiting
    "22344853769"  = @{ Industry="Staffing & Recruiting";                HC=""     }  # Lead Career Mover
    # Banking
    "21953865479"  = @{ Industry="Banking";                              HC=""     }  # amanahbank.gov.ph
    "21945840739"  = @{ Industry="Banking";                              HC=""     }  # chinabank.com
    # Oil & Energy
    "21945750863"  = @{ Industry="Oil & Energy";                         HC=""     }  # WTEI (Caltex distributor)
    "21945641058"  = @{ Industry="Electrical & Electronic Manufacturing";HC=""     }  # Energynet (elec/mech equipment dist)
    "21945739137"  = @{ Industry="Utilities";                            HC=""     }  # KEPCO Philippines
    "123743073984" = @{ Industry="Utilities";                            HC=""     }  # Akelco (electric cooperative)
    # Financial Services
    "21945635118"  = @{ Industry="Financial Services";                   HC=""     }  # pesoloan.ph
    "21945894448"  = @{ Industry="Financial Services";                   HC=""     }  # gdfi.ph (Global Dominion Financing)
    # Printing
    "21944619633"  = @{ Industry="Printing";                             HC=""     }  # Fongshann
    # Education
    "21945687365"  = @{ Industry="Education Management";                 HC=""     }  # JILCF Sintang Paaralan
    # Religious
    "31014014233"  = @{ Industry="Religious Institutions";               HC=""     }  # Makati Gospel Church
    # Airspeed logistics
    "21945767993"  = @{ Industry="Logistics & Supply Chain";             HC=""     }  # airspeed.com.ph
}

$rows = Import-Csv -Path $InputFile
$updateCount = 0

foreach ($row in $rows) {
    $id = $row.'Record ID'.Trim()
    if ($updates.ContainsKey($id)) {
        $u = $updates[$id]

        # Only update industry if it's empty or was clearly wrong (we set it explicitly)
        if ($u.Industry) {
            $row.'Industry' = $u.Industry
            $updateCount++
        }

        # Only update headcount if provided AND current value is empty/zero
        if ($u.HC -ne "") {
            $currentHC = $row.'Number of Employees'.Trim()
            if ($currentHC -eq "" -or $currentHC -eq "0.0" -or $currentHC -eq "0") {
                $row.'Number of Employees' = $u.HC
            }
        }
    }
}

$rows | Export-Csv -Path $OutputFile -NoTypeInformation -Encoding UTF8
Write-Host "Applied $updateCount industry updates. Saved to $OutputFile" -ForegroundColor Green

# Summary of final coverage
$total   = ($rows | Measure-Object).Count
$hasInd  = ($rows | Where-Object { $_.'Industry'.Trim() -ne "" } | Measure-Object).Count
$hasHC   = ($rows | Where-Object { ($_.'Number of Employees'.Trim() -ne "" -and $_.'Number of Employees'.Trim() -ne "0.0") -or $_.'Employee Head Count'.Trim() -ne "" } | Measure-Object).Count

Write-Host "`nFinal coverage:"
Write-Host "  Industry filled:  $hasInd / $total ($([math]::Round($hasInd/$total*100))%)"
Write-Host "  Headcount filled: $hasHC / $total ($([math]::Round($hasHC/$total*100))%)"

# Show still-missing
$stillMissing = $rows | Where-Object { $_.'Industry'.Trim() -eq "" }
if ($stillMissing) {
    Write-Host "`nRows still missing industry:"
    $stillMissing | Select-Object 'Record ID','Company name','Company Domain Name' | Format-Table -AutoSize
}
