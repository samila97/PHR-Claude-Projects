import re
import time
import requests

FIELDS_TO_CHECK = ['jobtitle', 'industry', 'numberofemployees', 'email', 'phone']


class Enricher:
    def __init__(self, apollo_api_key, google_api_key, google_cx):
        self.apollo_key  = apollo_api_key
        self.google_key  = google_api_key
        self.google_cx   = google_cx

    # ── public ───────────────────────────────────────────────────────────────

    def enrich_contact(self, contact):
        """
        Run the full enrichment pipeline for one contact.
        Returns a dict of {hubspot_property: value} for fields that were filled.
        """
        missing = self._missing_fields(contact)
        if not missing:
            return {}

        enriched = {}

        # 1. Apollo (primary)
        apollo_data = self._apollo(contact)
        enriched.update(apollo_data)

        # 2. Google Search (fallback for whatever Apollo couldn't fill)
        temp_props = {**contact.get('properties', {}), **enriched}
        still_missing = self._missing_fields({'properties': temp_props})

        if still_missing and self.google_key and self.google_cx:
            google_data = self._google(contact, still_missing)
            enriched.update(google_data)
            time.sleep(0.5)   # stay inside free-tier rate limit

        return enriched

    # ── Apollo ───────────────────────────────────────────────────────────────

    def _apollo(self, contact):
        props = contact.get('properties', {})

        payload = {
            'api_key':           self.apollo_key,
            'first_name':        props.get('firstname', ''),
            'last_name':         props.get('lastname', ''),
            'email':             props.get('email', ''),
            'organization_name': props.get('company', ''),
        }

        email = props.get('email', '')
        if email and '@' in email:
            payload['domain'] = email.split('@')[1]

        try:
            resp = requests.post(
                'https://api.apollo.io/v1/people/match',
                json=payload,
                headers={'Content-Type': 'application/json', 'Cache-Control': 'no-cache'},
                timeout=15
            )
            resp.raise_for_status()
            person = resp.json().get('person') or {}
        except Exception as e:
            print(f'    Apollo error: {e}')
            return {}

        if not person:
            return {}

        org     = person.get('organization') or {}
        result  = {}

        if not props.get('jobtitle') and person.get('title'):
            result['jobtitle'] = person['title']

        if not props.get('email') and person.get('email'):
            result['email'] = person['email']

        if not props.get('phone'):
            phones = person.get('phone_numbers') or []
            if phones:
                result['phone'] = phones[0].get('raw_number', '')

        if not props.get('industry') and org.get('industry'):
            result['industry'] = org['industry']

        if not props.get('numberofemployees') and org.get('estimated_num_employees'):
            result['numberofemployees'] = org['estimated_num_employees']

        return result

    # ── Google Custom Search ──────────────────────────────────────────────────

    def _google(self, contact, missing_fields):
        props   = contact.get('properties', {})
        name    = f"{props.get('firstname', '')} {props.get('lastname', '')}".strip()
        company = props.get('company', '')

        if not name and not company:
            return {}

        query = (
            f'"{name}" "{company}" '
            'job title industry employees '
            'site:linkedin.com OR site:bloomberg.com OR site:crunchbase.com'
        )

        try:
            resp = requests.get(
                'https://www.googleapis.com/customsearch/v1',
                params={'key': self.google_key, 'cx': self.google_cx, 'q': query, 'num': 3},
                timeout=10
            )
            resp.raise_for_status()
            items = resp.json().get('items', [])
        except Exception as e:
            print(f'    Google Search error: {e}')
            return {}

        if not items:
            return {}

        combined = ' '.join(
            item.get('snippet', '') + ' ' + item.get('title', '')
            for item in items
        ).lower()

        result = {}

        if 'numberofemployees' in missing_fields:
            m = re.search(r'(\d[\d,]+)\s*(?:employees|staff|people|workers)', combined)
            if m:
                result['numberofemployees'] = int(m.group(1).replace(',', ''))

        return result

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _missing_fields(contact):
        props = contact.get('properties', {})
        return [f for f in FIELDS_TO_CHECK if not (props.get(f) and str(props[f]).strip())]
