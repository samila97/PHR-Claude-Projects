"""
daily_run.py — Daily automated lead scoring workflow.

Steps:
  1. Pull all HubSpot contacts created today (UTC)
  2. Enrich each contact via Apollo → Google Search → Claude (fallback chain)
  3. Score each lead
  4. Write lead_score / lead_score_label / lead_score_breakdown back to HubSpot

Run:
  python daily_run.py

Env vars required (set in GitHub Actions secrets or a local .env file):
  HUBSPOT_TOKEN, APOLLO_API_KEY, GOOGLE_API_KEY, GOOGLE_CX, ANTHROPIC_API_KEY
"""

import logging
import os
import sys
import time

from dotenv import load_dotenv

from hubspot_client import HubSpotClient
from enricher import Enricher
from scorer import calculate_score

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True   # override any handlers added by imported libraries
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv()

HUBSPOT_TOKEN     = os.environ.get('HUBSPOT_TOKEN')
APOLLO_API_KEY    = os.environ.get('APOLLO_API_KEY')
GOOGLE_API_KEY    = os.environ.get('GOOGLE_API_KEY')
GOOGLE_CX         = os.environ.get('GOOGLE_CX')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

MISSING = [name for name, val in {
    'HUBSPOT_TOKEN':     HUBSPOT_TOKEN,
    'APOLLO_API_KEY':    APOLLO_API_KEY,
    'GOOGLE_API_KEY':    GOOGLE_API_KEY,
    'GOOGLE_CX':         GOOGLE_CX,
    'ANTHROPIC_API_KEY': ANTHROPIC_API_KEY,
}.items() if not val]

if MISSING:
    log.error('Missing required environment variable(s): %s', ', '.join(MISSING))
    sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info('=' * 65)
    log.info('  HubSpot Daily Lead Scoring & Enrichment Pipeline')
    log.info('=' * 65)

    hubspot  = HubSpotClient(HUBSPOT_TOKEN)
    enricher = Enricher(APOLLO_API_KEY, GOOGLE_API_KEY, GOOGLE_CX, ANTHROPIC_API_KEY)

    # Step 1 — fetch contacts created today
    log.info('[1/3] Fetching contacts created today (UTC)...')
    contacts = hubspot.get_contacts_created_today()
    log.info('      %d contact(s) found', len(contacts))

    if not contacts:
        log.info('No new contacts today — nothing to do.')
        return

    # Step 2 & 3 — enrich → score → write back
    log.info('[2/3] Enriching and scoring %d contact(s)...', len(contacts))

    success_count  = 0
    error_count    = 0
    enriched_count = 0

    for i, contact in enumerate(contacts, 1):
        contact_id = contact['id']
        props      = contact.get('properties', {})
        name = (
            f"{props.get('firstname', '')} {props.get('lastname', '')}".strip()
            or f"ID {contact_id}"
        )

        log.info('[%d/%d] %s', i, len(contacts), name)

        try:
            # Enrich missing fields
            enriched_data = enricher.enrich_contact(contact)

            if enriched_data:
                enriched_count += 1
                filled = [k for k in enriched_data if k != 'data_enriched']
                log.info('  Enriched: %s', ', '.join(filled))
                contact['properties'].update(enriched_data)

            # Score on the (now enriched) data
            score_data = calculate_score(contact)
            log.info(
                '  Score: %s → %s',
                score_data['lead_score'],
                score_data['lead_score_label']
            )

            # Build the update payload
            update_payload = {**score_data}
            if enriched_data:
                update_payload.update(enriched_data)
                update_payload['data_enriched'] = 'true'

            # Step 3 — write back to HubSpot
            hubspot.update_contact(contact_id, update_payload)
            success_count += 1

        except Exception as e:
            log.error('  FAILED for %s: %s', name, e)
            error_count += 1

        time.sleep(0.15)   # ~6–7 req/s — well within HubSpot limits

    # Summary
    log.info('[3/3] Done.')
    log.info('=' * 65)
    log.info('  Total contacts : %d', len(contacts))
    log.info('  Updated        : %d', success_count)
    log.info('  Enriched       : %d', enriched_count)
    log.info('  Errors         : %d', error_count)
    log.info('=' * 65)

    if error_count:
        sys.exit(1)   # non-zero exit lets GitHub Actions flag the run as failed


if __name__ == '__main__':
    main()
