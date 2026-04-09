import config


def score_industry(industry):
    if not industry:
        return 0, 'Unknown (no industry)'

    val = industry.lower()

    for kw in config.INDUSTRY_EDUCATION_KEYWORDS:
        if kw in val:
            return config.INDUSTRY_SCORE_EDUCATION, f'Education ({industry})'

    for kw in config.INDUSTRY_TIER1_KEYWORDS:
        if kw in val:
            return config.INDUSTRY_SCORE_TIER1, f'Tier 1 — {industry}'

    for kw in config.INDUSTRY_TIER2_KEYWORDS:
        if kw in val:
            return config.INDUSTRY_SCORE_TIER2, f'Tier 2 — {industry}'

    for kw in config.INDUSTRY_TIER3_KEYWORDS:
        if kw in val:
            return config.INDUSTRY_SCORE_TIER3, f'Tier 3 — {industry}'

    return config.INDUSTRY_SCORE_OTHER, f'Other — {industry}'


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


def calculate_score(contact):
    props = contact.get('properties', {})

    ind_score,  ind_label  = score_industry(props.get('industry'))
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
