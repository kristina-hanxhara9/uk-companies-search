"""
Buying group configuration for ownership type classification.

Buying groups are voluntary trade associations of independent businesses
that group together for purchasing power. They are NOT reflected in
Companies House ownership structures, so detection requires a curated list.

To add a new buying group:
  1. Add the lowercased name fragment to KNOWN_BUYING_GROUPS
  2. The name is matched as a substring against PSC names and company names
  3. Be specific enough to avoid false positives
"""

# Known buying group entity names (lowercased).
# Matched as substrings against PSC names and company names.
KNOWN_BUYING_GROUPS = {
    # Tyre industry buying groups
    'point-s',
    'point s ',
    'tyres & wheels',
    'tyre & auto',
    'group tyre',
    'stapleton',
    'micheldever',
    'universal tyre',
    'bond international',
    '3t tyres',
    'tyre shopper',
    'protyre',
    'merityre',
    'first stop',
}

# Generic keyword phrases that indicate a buying group.
# Matched as substrings in PSC names and company names.
BUYING_GROUP_KEYWORDS = [
    'buying group',
    'purchasing group',
    'buying alliance',
    'consortium',
    'cooperative',
    'co-operative',
]
