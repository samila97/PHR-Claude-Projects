# ─────────────────────────────────────────────
# INDUSTRY SCORING  (max 35 pts)
# ─────────────────────────────────────────────
INDUSTRY_TIER1_KEYWORDS = [
    'manufacturing', 'hospitality', 'bpo', 'outsourcing',
    'business process outsourcing', 'hotel', 'hotels', 'resort'
]
INDUSTRY_TIER2_KEYWORDS = [
    'retail', 'transport', 'transportation', 'logistics',
    'supply chain', 'freight', 'shipping', 'courier'
]
INDUSTRY_TIER3_KEYWORDS = [
    'banking', 'finance', 'financial services', 'financial',
    'insurance', 'healthcare', 'health care', 'medical',
    'pharmaceutical', 'hospital', 'clinic'
]
INDUSTRY_EDUCATION_KEYWORDS = [
    'education', 'higher education', 'university', 'school',
    'college', 'academic', 'e-learning', 'edtech', 'tutoring',
    'training institution'
]

INDUSTRY_SCORE_TIER1      = 35
INDUSTRY_SCORE_TIER2      = 25
INDUSTRY_SCORE_TIER3      = 15
INDUSTRY_SCORE_OTHER      = 5
INDUSTRY_SCORE_EDUCATION  = 0

# ─────────────────────────────────────────────
# COMPANY SIZE SCORING  (max 30 pts)
# ─────────────────────────────────────────────
MIDMARKET_MIN = 200
MIDMARKET_MAX = 2000

COMPANY_SIZE_SCORE_MIDMARKET  = 30   # 200 – 2,000 employees
COMPANY_SIZE_SCORE_ENTERPRISE = 22   # 2,001+
COMPANY_SIZE_SCORE_SMB        = 8    # < 200

# ─────────────────────────────────────────────
# JOB TITLE SCORING  (max 25 pts)
# ─────────────────────────────────────────────
JOBTITLE_TIER1_KEYWORDS = [
    'chief human resource officer', 'chro',
    'chief executive officer', 'ceo',
    'chief financial officer', 'cfo',
    'chief people officer', 'cpo'
]
JOBTITLE_TIER2_KEYWORDS = [
    'hr director', 'human resources director',
    'head of hr', 'head of human resources',
    'senior hr manager', 'senior human resources manager',
    'it manager', 'information technology manager',
    'procurement manager', 'vp hr', 'vp human resources',
    'vice president hr', 'vice president human resources'
]
JOBTITLE_TIER3_KEYWORDS = [
    'hr manager', 'human resources manager',
    'recruitment manager', 'talent acquisition manager',
    'talent acquisition', 'recruiter', 'hr business partner',
    'people operations', 'people manager',
    'workforce manager', 'hr generalist'
]
JOBTITLE_NEGATIVE_KEYWORDS = [
    'student', 'intern', 'internship', 'trainee',
    'graduate student', 'undergraduate', 'apprentice'
]

JOBTITLE_SCORE_TIER1    = 25
JOBTITLE_SCORE_TIER2    = 18
JOBTITLE_SCORE_TIER3    = 12
JOBTITLE_SCORE_OTHER    = 2
JOBTITLE_SCORE_NEGATIVE = -15

# ─────────────────────────────────────────────
# CONTACT DATA QUALITY  (max 10 pts)
# ─────────────────────────────────────────────
PHONE_SCORE              = 5
CORPORATE_EMAIL_SCORE    = 5
NON_CORPORATE_EMAIL_SCORE = 2.5

NON_CORPORATE_DOMAINS = [
    'gmail.com', 'googlemail.com',
    'yahoo.com', 'ymail.com',
    'hotmail.com', 'hotmail.co.uk',
    'outlook.com', 'live.com', 'msn.com',
    'aol.com', 'icloud.com', 'me.com', 'mac.com',
    'protonmail.com', 'mail.com', 'zoho.com'
]

# ─────────────────────────────────────────────
# SCORE LABELS
# ─────────────────────────────────────────────
STRONG_FIT_MIN   = 75
POTENTIAL_FIT_MIN = 40

LABEL_STRONG_FIT   = 'Strong Fit'
LABEL_POTENTIAL_FIT = 'Potential Fit'
LABEL_WEAK_FIT      = 'Weak Fit'
