import os
import sys
import time
from dotenv import load_dotenv

from hubspot_client import HubSpotClient
from enricher import Enricher
from scorer import calculate_score

load_dotenv()

HUBSPOT_TOKEN  = os.getenv('HUBSPOT_TOKEN')
APOLLO_API_KEY = os.getenv('APOLLO_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_CX      = os.getenv('GOOGLE_CX')

# ── mode: pass --test or --test=N to run on N most recent contacts (default 20)
TEST_MODE  = any(a.startswith('--test') for a in sys.argv[1:])
TEST_LIMIT = 20
for arg in sys.argv[1:]:
    if arg.startswith('--test='):
        try:
            TEST_LIMIT = int(arg.split('=')[1])
        except ValueError:
            pass


def main():
    print('=' * 65)
    print('  HubSpot Lead Scoring & Enrichment Pipeline')
    if TEST_MODE:
        print(f'  *** TEST MODE — {TEST_LIMIT} most recent contacts ***')
    print('=' * 65)

    hubspot  = HubSpotClient(HUBSPOT_TOKEN)
    enricher = Enricher(APOLLO_API_KEY, GOOGLE_API_KEY, GOOGLE_CX)

    # ── Step 1: create custom properties if needed ───────────────────────────
    print('\n[1/4] Setting up HubSpot custom properties...')
    hubspot.setup_custom_properties()

    # ── Step 2: fetch contacts ───────────────────────────────────────────────
    print('\n[2/4] Fetching contacts from HubSpot...')
    if TEST_MODE:
        contacts = hubspot.get_recent_contacts(limit=TEST_LIMIT)
        print(f'      {len(contacts)} most recent contact(s) fetched (test mode)')
    else:
        contacts = hubspot.get_all_contacts()
        print(f'      {len(contacts)} contact(s) found')

    if not contacts:
        print('\nNo contacts to process. Exiting.')
        return

    # ── Step 3 & 4: enrich → score → write back ──────────────────────────────
    print(f'\n[3/4] Enriching and scoring {len(contacts)} contact(s)...\n')

    success_count  = 0
    error_count    = 0
    enriched_count = 0

    for i, contact in enumerate(contacts, 1):
        contact_id = contact['id']
        props      = contact.get('properties', {})
        name       = (
            f"{props.get('firstname', '')} {props.get('lastname', '')}".strip()
            or f"(ID {contact_id})"
        )

        print(f'  [{i}/{len(contacts)}] {name}')

        try:
            # Enrich missing fields
            enriched_data = enricher.enrich_contact(contact)

            if enriched_data:
                enriched_count += 1
                filled = [k for k in enriched_data if k not in ('data_enriched',)]
                print(f'    Enriched fields : {", ".join(filled)}')
                contact['properties'].update(enriched_data)

            # Score on the (now enriched) data
            score_data = calculate_score(contact)
            print(f'    Score           : {score_data["lead_score"]} → {score_data["lead_score_label"]}')

            # Build the update payload
            update_payload = {**score_data}
            if enriched_data:
                update_payload.update(enriched_data)
                update_payload['data_enriched'] = 'true'

            hubspot.update_contact(contact_id, update_payload)
            success_count += 1

        except Exception as e:
            print(f'    ERROR: {e}')
            error_count += 1

        time.sleep(0.15)   # ~6–7 req/s — well within HubSpot limits

    # ── Summary ──────────────────────────────────────────────────────────────
    print('\n' + '=' * 65)
    print('  DONE')
    print(f'  Total contacts   : {len(contacts)}')
    print(f'  Updated          : {success_count}')
    print(f'  Enriched         : {enriched_count}')
    print(f'  Errors           : {error_count}')
    print('=' * 65)


if __name__ == '__main__':
    main()
