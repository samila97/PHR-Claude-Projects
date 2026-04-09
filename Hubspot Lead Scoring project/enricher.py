import json
import logging
import re
import time
import requests
import anthropic

log = logging.getLogger(__name__)

FIELDS_TO_CHECK = ['jobtitle', 'industry', 'numberofemployees', 'email', 'phone']

# Claude can infer these from a company name / email domain
CLAUDE_FIELDS = {'industry', 'numberofemployees'}


class Enricher:
    def __init__(self, apollo_api_key, google_api_key, google_cx, anthropic_api_key=None):
        self.apollo_key     = apollo_api_key
        self.google_key     = google_api_key
        self.google_cx      = google_cx
        self.anthropic_key  = anthropic_api_key

    # ── public ───────────────────────────────────────────────────────────────

    def enrich_contact(self, contact):
        """
        Run the full enrichment pipeline for one contact.
        Returns a dict of {hubspot_property: value} for fields that were filled.
        """
        missing = self._missing_fields(contact)
        if not missing:
            log.info('    Enrichment: all fields present — skipping')
            return {}

        log.info('    Missing fields: %s', ', '.join(missing))
        enriched = {}

        # 1. Apollo (primary)
        apollo_data = self._apollo(contact)
        if apollo_data:
            log.info('    Apollo filled: %s', ', '.join(apollo_data))
        else:
            log.info('    Apollo: no data returned')
        enriched.update(apollo_data)

        # 2. Google Search (fallback for whatever Apollo couldn't fill)
        temp_props    = {**contact.get('properties', {}), **enriched}
        still_missing = self._missing_fields({'properties': temp_props})

        if still_missing and self.google_key and self.google_cx:
            google_data = self._google(contact, still_missing)
            if google_data:
                log.info('    Google filled: %s', ', '.join(google_data))
            else:
                log.info('    Google: no data returned')
            enriched.update(google_data)
            time.sleep(0.5)   # stay inside free-tier rate limit

        # 3. Claude (fallback for industry / employee count only)
        temp_props2    = {**contact.get('properties', {}), **enriched}
        still_missing2 = self._missing_fields({'properties': temp_props2})
        claude_targets = [f for f in still_missing2 if f in CLAUDE_FIELDS]

        if claude_targets and self.anthropic_key:
            log.info('    Claude: inferring %s...', ', '.join(claude_targets))
            claude_data = self._claude(contact, claude_targets)
            if claude_data:
                log.info('    Claude filled: %s', ', '.join(claude_data))
            else:
                log.info('    Claude: could not infer fields')
            enriched.update(claude_data)
        elif claude_targets and not self.anthropic_key:
            log.info('    Claude: skipped (no ANTHROPIC_API_KEY)')
        else:
            log.info('    Claude: not needed (industry + employees already filled)')

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

    # ── Claude ───────────────────────────────────────────────────────────────

    def _claude(self, contact, missing_fields):
        """
        Use Claude to infer industry and/or employee count from company name / domain.
        Only called when Apollo and Google both failed to fill these fields.
        """
        props   = contact.get('properties', {})
        company = props.get('company', '').strip()
        email   = props.get('email', '')
        domain  = email.split('@')[1].lower() if email and '@' in email else ''

        if not company and not domain:
            return {}

        # Build a compact context string for the prompt
        context_lines = []
        if company:
            context_lines.append(f'Company name: {company}')
        if domain:
            context_lines.append(f'Email domain: {domain}')
        context = '\n'.join(context_lines)

        # Build the JSON schema dynamically — only request fields still missing
        properties = {}
        if 'industry' in missing_fields:
            properties['industry'] = {
                'type': 'string',
                'description': 'Short industry label, e.g. Manufacturing, Retail, Banking'
            }
        if 'numberofemployees' in missing_fields:
            properties['numberofemployees'] = {
                'type': 'integer',
                'description': 'Estimated total employee count'
            }

        fields_desc = ', '.join(
            f'"{f}"' for f in ['industry', 'numberofemployees'] if f in missing_fields
        )
        prompt = (
            f'Given the following company information, respond with ONLY a JSON object '
            f'— no explanation, no markdown — inferring these fields: {fields_desc}. '
            f'Omit any field you cannot confidently infer.\n\n'
            f'{context}\n\n'
            f'Example: {{"industry": "Manufacturing", "numberofemployees": 850}}'
        )

        try:
            client   = anthropic.Anthropic(api_key=self.anthropic_key)
            response = client.messages.create(
                model='claude-opus-4-6',
                max_tokens=128,
                messages=[{'role': 'user', 'content': prompt}]
            )
            raw   = next(b.text for b in response.content if b.type == 'text').strip()
            match = re.search(r'\{.*?\}', raw, re.DOTALL)
            if not match:
                log.warning('    Claude returned no JSON: %s', raw[:120])
                return {}
            data = json.loads(match.group())
        except Exception as e:
            log.error('    Claude enrichment error: %s', e)
            return {}

        result = {}
        if 'industry' in missing_fields and data.get('industry'):
            result['industry'] = str(data['industry'])
        if 'numberofemployees' in missing_fields and data.get('numberofemployees'):
            try:
                result['numberofemployees'] = int(data['numberofemployees'])
            except (ValueError, TypeError):
                pass

        return result

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _missing_fields(contact):
        props = contact.get('properties', {})
        return [f for f in FIELDS_TO_CHECK if not (props.get(f) and str(props[f]).strip())]
