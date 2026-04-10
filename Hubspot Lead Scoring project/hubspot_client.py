import datetime
import time
import requests

HUBSPOT_BASE = 'https://api.hubapi.com'

CONTACT_PROPERTIES = [
    'firstname', 'lastname', 'email', 'phone',
    'jobtitle', 'industry', 'numberofemployees',
    'company', 'website', 'lead_score', 'lead_score_label'
]


class HubSpotClient:
    def __init__(self, token):
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    # ── contacts ────────────────────────────────────────────────────────────

    def get_all_contacts(self):
        """Return every contact, handling HubSpot pagination."""
        contacts, after = [], None
        while True:
            params = {'limit': 100, 'properties': ','.join(CONTACT_PROPERTIES)}
            if after:
                params['after'] = after

            resp = self._get('/crm/v3/objects/contacts', params=params)
            contacts.extend(resp.get('results', []))

            after = resp.get('paging', {}).get('next', {}).get('after')
            if not after:
                break
            time.sleep(0.1)

        return contacts

    def get_contacts_created_last_24h(self):
        """Return all contacts created in the last 24 hours (rolling window), handling pagination."""
        since_utc = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        today_ms  = int(since_utc.timestamp() * 1000)

        contacts, after = [], None
        while True:
            payload = {
                'filterGroups': [{
                    'filters': [{
                        'propertyName': 'createdate',
                        'operator': 'GTE',
                        'value': str(today_ms)
                    }]
                }],
                'properties': CONTACT_PROPERTIES,
                'limit': 100,
                'sorts': [{'propertyName': 'createdate', 'direction': 'DESCENDING'}]
            }
            if after:
                payload['after'] = after

            resp = requests.post(
                f'{HUBSPOT_BASE}/crm/v3/objects/contacts/search',
                headers=self.headers,
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            contacts.extend(data.get('results', []))

            after = data.get('paging', {}).get('next', {}).get('after')
            if not after:
                break
            time.sleep(0.1)

        return contacts

    def get_recent_contacts(self, limit=20):
        """Return the most recently created contacts, up to `limit`."""
        payload = {
            'limit': min(limit, 100),
            'properties': CONTACT_PROPERTIES,
            'sorts': [{'propertyName': 'createdate', 'direction': 'DESCENDING'}]
        }

        resp = requests.post(
            f'{HUBSPOT_BASE}/crm/v3/objects/contacts/search',
            headers=self.headers,
            json=payload
        )
        resp.raise_for_status()
        return resp.json().get('results', [])[:limit]

    def update_contact(self, contact_id, properties):
        """Patch a single contact. Retries once on 429."""
        url = f'{HUBSPOT_BASE}/crm/v3/objects/contacts/{contact_id}'
        resp = requests.patch(url, headers=self.headers, json={'properties': properties})

        if resp.status_code == 429:
            retry_after = int(resp.headers.get('Retry-After', 10))
            print(f'    Rate limited — waiting {retry_after}s...')
            time.sleep(retry_after)
            resp = requests.patch(url, headers=self.headers, json={'properties': properties})

        if not resp.ok:
            print(f'    HubSpot error body: {resp.text}')
        resp.raise_for_status()
        return resp.json()

    # ── custom properties ────────────────────────────────────────────────────

    def setup_custom_properties(self):
        """Create lead-score properties in HubSpot if they don't exist yet."""
        props = [
            {
                'name': 'lead_score',
                'label': 'Lead Score',
                'type': 'number',
                'fieldType': 'number',
                'groupName': 'contactinformation',
                'description': 'Calculated lead score (0–100) based on ICP fit'
            },
            {
                'name': 'lead_score_label',
                'label': 'Lead Score Label',
                'type': 'string',
                'fieldType': 'text',
                'groupName': 'contactinformation',
                'description': 'Strong Fit / Potential Fit / Weak Fit'
            },
            {
                'name': 'lead_score_breakdown',
                'label': 'Lead Score Breakdown',
                'type': 'string',
                'fieldType': 'textarea',
                'groupName': 'contactinformation',
                'description': 'Scoring detail per dimension'
            },
            {
                'name': 'data_enriched',
                'label': 'Data Enriched',
                'type': 'bool',
                'fieldType': 'booleancheckbox',
                'groupName': 'contactinformation',
                'description': 'True if enriched via Apollo / Google'
            }
        ]

        for prop in props:
            try:
                resp = requests.post(
                    f'{HUBSPOT_BASE}/crm/v3/properties/contacts',
                    headers=self.headers,
                    json=prop
                )
                if resp.status_code == 409:
                    print(f"  Property '{prop['label']}' already exists — skipping")
                else:
                    resp.raise_for_status()
                    print(f"  Created property: {prop['label']}")
            except requests.HTTPError as e:
                print(f"  Warning: could not create '{prop['label']}': {e}")

    # ── private helpers ──────────────────────────────────────────────────────

    def _get(self, path, params=None):
        resp = requests.get(f'{HUBSPOT_BASE}{path}', headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json()
