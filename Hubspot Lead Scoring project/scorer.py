import anthropic
import config


def _classify_industry_keywords(industry):
    """Keyword-based fallback classifier. Returns a tier string."""
    val = industry.lower()
    for kw in config.INDUSTRY_EDUCATION_KEYWORDS:
        if kw in val:
            return 'Education'
    for kw in config.INDUSTRY_TIER1_KEYWORDS:
        if kw in val:
            return 'Tier1'
    for kw in config.INDUSTRY_TIER2_KEYWORDS:
        if kw in val:
            return 'Tier2'
    for kw in config.INDUSTRY_TIER3_KEYWORDS:
        if kw in val:
            return 'Tier3'
    return 'Other'


def _classify_industry_claude(industry, api_key):
    """
    Ask Claude to map a raw industry string to a scoring tier.
    Falls back to keyword matching if the API call fails.
    """
    prompt = (
        f'Classify this company industry into exactly one scoring category.\n\n'
        f'Industry: "{industry}"\n\n'
        f'Categories:\n'
        f'- Tier1: Manufacturing, Production, Food & Beverage, FMCG, Hospitality, '
        f'Hotels, Resorts, BPO, Business Process Outsourcing\n'
        f'- Tier2: Retail, E-commerce, Transportation, Logistics, Supply Chain, '
        f'Freight, Shipping, Courier\n'
        f'- Tier3: Banking, Finance, Financial Services, Insurance, Healthcare, '
        f'Medical, Pharmaceutical, Hospitals\n'
        f'- Education: Schools, Universities, Colleges, E-learning, EdTech, '
        f'Training institutions\n'
        f'- Other: Anything that does not fit the above\n\n'
        f'Respond with ONLY one word — exactly one of: Tier1, Tier2, Tier3, Education, Other'
    )
    try:
        client   = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model='claude-opus-4-6',
            max_tokens=10,
            messages=[{'role': 'user', 'content': prompt}]
        )
        result = response.content[0].text.strip()
        if result in ('Tier1', 'Tier2', 'Tier3', 'Education', 'Other'):
            return result
        # Unexpected response — fall back
        return _classify_industry_keywords(industry)
    except Exception:
        return _classify_industry_keywords(industry)


def score_industry(industry, anthropic_api_key=None):
    if not industry:
        return 0, 'Unknown (no industry)'

    tier = (
        _classify_industry_claude(industry, anthropic_api_key)
        if anthropic_api_key
        else _classify_industry_keywords(industry)
    )

    tier_map = {
        'Tier1':     (config.INDUSTRY_SCORE_TIER1,     f'Tier 1 — {industry}'),
        'Tier2':     (config.INDUSTRY_SCORE_TIER2,     f'Tier 2 — {industry}'),
        'Tier3':     (config.INDUSTRY_SCORE_TIER3,     f'Tier 3 — {industry}'),
        'Education': (config.INDUSTRY_SCORE_EDUCATION, f'Education ({industry})'),
        'Other':     (config.INDUSTRY_SCORE_OTHER,     f'Other — {industry}'),
    }
    return tier_map.get(tier, (config.INDUSTRY_SCORE_OTHER, f'Other — {industry}'))


def score_company_size(num_employees):
    if not num_employees:
        return 0, 'Unknown (no employee count)'

    try:
        count = int(str(num_employees).replace(',', '').strip())
    except (ValueError, TypeError):
        return 0, 'Unknown (unparseable count)'

    if config.MIDMARKET_MIN <= count <= config.MIDMARKET_MAX:
        return config.COMPANY_SIZE_SCORE_MIDMARKET, f'Mid-Market ({count:,} employees)'
    elif count > config.MIDMARKET_MAX:
        return config.COMPANY_SIZE_SCORE_ENTERPRISE, f'Enterprise ({count:,} employees)'
    else:
        return config.COMPANY_SIZE_SCORE_SMB, f'SMB ({count:,} employees)'


def score_job_title(title):
    if not title:
        return config.JOBTITLE_SCORE_OTHER, 'Unknown (no title)'

    val = title.lower()

    for kw in config.JOBTITLE_NEGATIVE_KEYWORDS:
        if kw in val:
            return config.JOBTITLE_SCORE_NEGATIVE, f'Negative — {title}'

    for kw in config.JOBTITLE_TIER1_KEYWORDS:
        if kw in val:
            return config.JOBTITLE_SCORE_TIER1, f'Tier 1 — {title}'

    for kw in config.JOBTITLE_TIER2_KEYWORDS:
        if kw in val:
            return config.JOBTITLE_SCORE_TIER2, f'Tier 2 — {title}'

    for kw in config.JOBTITLE_TIER3_KEYWORDS:
        if kw in val:
            return config.JOBTITLE_SCORE_TIER3, f'Tier 3 — {title}'

    return config.JOBTITLE_SCORE_OTHER, f'Other — {title}'


def score_contact_data(email, phone):
    score = 0
    parts = []

    if phone and str(phone).strip():
        score += config.PHONE_SCORE
        parts.append(f'Phone +{config.PHONE_SCORE}')

    if email and '@' in str(email):
        domain = email.split('@')[1].lower()
        if domain in config.NON_CORPORATE_DOMAINS:
            score += config.NON_CORPORATE_EMAIL_SCORE
            parts.append(f'Non-corporate email +{config.NON_CORPORATE_EMAIL_SCORE}')
        else:
            score += config.CORPORATE_EMAIL_SCORE
            parts.append(f'Corporate email +{config.CORPORATE_EMAIL_SCORE}')

    label = ', '.join(parts) if parts else 'No contact data'
    return score, label


def get_label(score):
    if score >= config.STRONG_FIT_MIN:
        return config.LABEL_STRONG_FIT
    elif score >= config.POTENTIAL_FIT_MIN:
        return config.LABEL_POTENTIAL_FIT
    return config.LABEL_WEAK_FIT


def calculate_score(contact, anthropic_api_key=None):
    props = contact.get('properties', {})

    ind_score,  ind_label  = score_industry(props.get('industry'), anthropic_api_key)
    size_score, size_label = score_company_size(props.get('numberofemployees'))
    title_score, title_label = score_job_title(props.get('jobtitle'))
    data_score, data_label = score_contact_data(props.get('email'), props.get('phone'))

    total = round(ind_score + size_score + title_score + data_score, 1)
    label = get_label(total)

    breakdown = (
        f"Industry: {ind_score} ({ind_label}) | "
        f"Company Size: {size_score} ({size_label}) | "
        f"Job Title: {title_score} ({title_label}) | "
        f"Data Quality: {data_score} ({data_label})"
    )

    return {
        'lead_score':           total,
        'lead_score_label':     label,
        'lead_score_breakdown': breakdown
    }
