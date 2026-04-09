import csv
import json
import time
import urllib.request
import urllib.parse
import urllib.error

API_KEY = "gLEUVfxJK3s_0CoONP4BeA"
INPUT_FILE = "Claude code CRM test run.csv"
OUTPUT_FILE = "Claude code CRM enriched.csv"

SKIP_NAMES = {
    "gmail support phone number +61~800~765~948 gmail phone number",
    "test company",
    "",
}

def apollo_enrich(domain=None, name=None):
    """Call Apollo organization enrich API. Returns (industry, headcount) or (None, None)."""
    params = {"api_key": API_KEY}
    if domain and domain.strip():
        params["domain"] = domain.strip()
    elif name and name.strip():
        params["name"] = name.strip()
    else:
        return None, None

    url = "https://api.apollo.io/v1/organizations/enrich?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            org = data.get("organization") or {}
            industry = org.get("industry") or None
            headcount = org.get("estimated_num_employees") or org.get("num_employees") or None
            return industry, headcount
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"    HTTP {e.code}: {body[:200]}")
        return None, None
    except Exception as e:
        print(f"    Error: {e}")
        return None, None

def main():
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    header = rows[0]
    data_rows = rows[1:]

    # Column indices (0-based)
    COL_ID       = 0
    COL_NAME     = 1
    COL_HC_RANGE = 2
    COL_HC_NUM   = 3
    COL_INDUSTRY = 4
    COL_DOMAIN   = 5

    results = []
    needs_websearch = []

    for i, row in enumerate(data_rows):
        # Pad short rows
        while len(row) < 9:
            row.append("")

        record_id  = row[COL_ID].strip()
        name       = row[COL_NAME].strip()
        domain     = row[COL_DOMAIN].strip()
        industry   = row[COL_INDUSTRY].strip()
        hc_range   = row[COL_HC_RANGE].strip()
        hc_num     = row[COL_HC_NUM].strip()

        # Skip junk
        if name.lower() in SKIP_NAMES and not domain:
            print(f"[{i+1:3}] SKIP  {name or '(no name)'}")
            results.append(row)
            continue

        # Already has both fields — still try to fill industry if missing
        already_has_hc = bool(hc_range or hc_num)
        already_has_ind = bool(industry)

        if already_has_hc and already_has_ind:
            print(f"[{i+1:3}] FULL  {name}")
            results.append(row)
            continue

        print(f"[{i+1:3}] ENRICH {name} (domain={domain or 'none'})", end=" ... ")

        new_industry, new_hc = apollo_enrich(domain=domain, name=name)

        if new_industry:
            row[COL_INDUSTRY] = new_industry
            print(f"industry={new_industry}", end=" ")
        else:
            print("industry=MISS", end=" ")

        if new_hc and not already_has_hc:
            row[COL_HC_NUM] = str(new_hc)
            print(f"hc={new_hc}", end=" ")
        elif already_has_hc:
            print("hc=kept", end=" ")
        else:
            print("hc=MISS", end=" ")

        print()

        if not new_industry or (not new_hc and not already_has_hc):
            needs_websearch.append({
                "index": i,
                "name": name,
                "domain": domain,
                "got_industry": bool(new_industry),
                "got_hc": bool(new_hc or already_has_hc),
            })

        results.append(row)
        time.sleep(0.4)  # respect rate limits

    # Write enriched CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(results)

    print(f"\nDone. Saved to {OUTPUT_FILE}")
    print(f"Companies needing web search fallback: {len(needs_websearch)}")
    if needs_websearch:
        print("\nFallback list:")
        for item in needs_websearch:
            missing = []
            if not item["got_industry"]: missing.append("industry")
            if not item["got_hc"]: missing.append("headcount")
            print(f"  [{item['index']+1:3}] {item['name']} | domain={item['domain'] or 'none'} | missing={', '.join(missing)}")

    # Save fallback list to JSON for next step
    with open("needs_websearch.json", "w") as f:
        json.dump(needs_websearch, f, indent=2)

if __name__ == "__main__":
    main()
