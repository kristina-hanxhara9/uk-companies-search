"""
Buying group configuration for ownership type classification.

Buying groups are voluntary trade associations of independent businesses
that group together for purchasing power. They are NOT reflected in
Companies House ownership structures, so detection requires a curated list
and keyword matching.

To add a new buying group:
  1. Add the lowercased name fragment to KNOWN_BUYING_GROUPS
  2. The name is matched as a substring against PSC names and company names
  3. Be specific enough to avoid false positives
"""

# Known buying group / purchasing cooperative entity names (lowercased).
# Matched as substrings against PSC names and company names.
# Organised by industry but the matching is universal.
KNOWN_BUYING_GROUPS = {
    # Multi-sector / general wholesale buying groups
    'buying group',
    'purchasing consortium',
    'buying alliance',

    # Construction & building supplies
    'nmbs',                     # National Merchant Buying Society
    'national merchant buying',
    'ibg ',                     # Independent Builders Group (trailing space to avoid false matches)
    'independent builders group',
    'bmc ',                     # Builders Merchants Company
    'builders merchants company',
    'h&b ',                     # H&B Buying Group (Huws Gray / Buildbase)
    'united merchants',

    # Electrical wholesale
    'fegime',                   # FEGIME UK (electrical buying group)
    'denmans',
    'electric center',
    'edmundson',

    # Plumbing & heating
    'ibn ',                     # Independent Buying Network
    'independent buying network',
    'buying network',

    # Automotive / tyre
    'point-s',
    'point s ',
    'group tyre',
    'stapleton',
    'micheldever',
    'first stop',
    'bond international',

    # Pharmacy
    'numark',
    'alphega',
    'avicenna',
    'celesio',
    'phoenix healthcare',

    # Catering & foodservice
    'caterforce',
    'country range',
    'unitas wholesale',
    'sugro',
    'confex',
    'landmark wholesale',
    'today\'s group',
    'nisa ',                    # Nisa Retail (buying group for convenience stores)
    'spar ',
    'costcutter',
    'nisa retail',
    'bestway',

    # Hardware & DIY
    'mica hardware',
    'bira ',                    # British Independent Retailers Association
    'sibling',

    # Funeral
    'saif',                     # Society of Allied & Independent Funeral Directors

    # Garden & outdoor
    'garden centre association',
    'gca ',

    # Veterinary
    'vetcel',
    'cvs group',

    # IT & technology
    'synaxon',
    'ci distribution',
}

# Generic keyword phrases that indicate a buying group.
# Matched as substrings in PSC names and company names.
BUYING_GROUP_KEYWORDS = [
    'buying group',
    'purchasing group',
    'buying alliance',
    'purchasing alliance',
    'buying consortium',
    'purchasing consortium',
    'buying cooperative',
    'buying co-operative',
    'trade buying',
    'merchant buying',
    'wholesale buying',
    'independent buying',
]
