"""
Business size classification and chain detection utilities.

Uses Companies House accounts filing type as the primary indicator of company size,
enhanced with secondary signals (directors count, charges, company type).
"""

# Accounts type → size category mapping
# Based on UK Companies Act thresholds:
#   Micro: turnover ≤£632k, ≤10 employees
#   Small: turnover ≤£10.2m, ≤50 employees
#   Medium: turnover ≤£36m, ≤250 employees
#   Large: above medium thresholds
ACCOUNTS_TYPE_MAP = {
    'micro-entity': ('Micro', 1),
    'small': ('Small', 2),
    'total-exemption-small': ('Small', 2),
    'unaudited-abridged': ('Small', 2),
    'total-exemption-full': ('Small', 2),
    'medium': ('Medium', 3),
    'full': ('Large', 4),
    'group': ('Large (Group)', 5),
    'dormant': ('Dormant', 0),
    'audit-exemption-subsidiary': ('Subsidiary', 3),
    'filing-exemption-subsidiary': ('Subsidiary', 3),
    'initial': ('New', 0),
}

# Keywords indicating corporate (non-individual) PSC ownership
CORPORATE_KEYWORDS = [
    'ltd', 'limited', 'plc', 'group', 'holdings',
    'llp', 'inc', 'corporation', 'corp', 'partners',
    'capital', 'investments', 'enterprises',
]

# Accounts types that indicate group/chain membership
GROUP_ACCOUNTS_TYPES = {'group', 'audit-exemption-subsidiary', 'filing-exemption-subsidiary'}


def classify_business_size(company):
    """
    Classify a company's size based on accounts type and secondary signals.

    Returns dict with 'size_category' (str) and 'size_rank' (int).
    """
    accounts_type = (company.get('last_accounts_type') or '').strip().lower()

    if accounts_type in ACCOUNTS_TYPE_MAP:
        category, rank = ACCOUNTS_TYPE_MAP[accounts_type]
    else:
        category, rank = ('Unknown', -1)

    # Secondary signals: nudge upward if other indicators suggest larger size
    directors_count = company.get('directors_count', 0)
    if isinstance(directors_count, str):
        try:
            directors_count = int(directors_count)
        except (ValueError, TypeError):
            directors_count = 0

    has_charges = company.get('has_charges', '') == 'Yes'
    company_type = (company.get('company_type') or '').lower()

    # PLC companies are typically large
    if company_type == 'plc' and rank < 4:
        category, rank = ('Large', 4)

    # When accounts type is unknown, use secondary signals to estimate size
    if rank == -1:
        # Many directors suggests at least Medium
        if directors_count >= 5:
            category, rank = ('Medium', 3)
        elif directors_count >= 3 or has_charges:
            category, rank = ('Small', 2)
        elif directors_count >= 1:
            category, rank = ('Micro', 1)
    else:
        # When we have accounts type, only nudge upward
        if directors_count >= 5 and rank < 3:
            category, rank = ('Medium', 3)
        if has_charges and rank < 2:
            category, rank = ('Small', 2)

    return {'size_category': category, 'size_rank': rank}


def is_likely_chain(company):
    """
    Determine if a company is likely part of a chain/group.

    Returns 'Yes', 'No', or 'Unknown'.
    """
    accounts_type = (company.get('last_accounts_type') or '').strip().lower()

    # Group/subsidiary accounts type is a strong signal
    if accounts_type in GROUP_ACCOUNTS_TYPES:
        return 'Yes'

    # PLC is typically a larger/chain entity
    company_type = (company.get('company_type') or '').lower()
    if company_type == 'plc':
        return 'Yes'

    # Check PSC names for corporate keywords
    psc_names = company.get('psc_names', '')
    if psc_names and psc_names.strip():
        for name in psc_names.split(';'):
            name_lower = name.strip().lower()
            if any(kw in name_lower for kw in CORPORATE_KEYWORDS):
                return 'Yes'
        # PSC data present but all individuals = likely independent
        return 'No'

    # Check company name for chain indicators
    company_name = (company.get('company_name') or '').lower()
    chain_name_keywords = ['group', 'holdings', 'franchise', 'national', 'uk ']
    if any(kw in company_name for kw in chain_name_keywords):
        return 'Yes'

    # If we have accounts type and it's not a group type, lean toward No
    if accounts_type and accounts_type in ACCOUNTS_TYPE_MAP:
        return 'No'

    return 'Unknown'


def enrich_with_classification(companies):
    """
    Add size_category, size_rank, and likely_chain to each company dict.
    """
    for company in companies:
        size_info = classify_business_size(company)
        company['size_category'] = size_info['size_category']
        company['size_rank'] = size_info['size_rank']
        company['likely_chain'] = is_likely_chain(company)
    return companies
