"""
Truck Tyre Specialist Finder (Standalone)

Runs multiple search strategies against Companies House API,
combines results, enriches with PSC/directors data,
flags likely chains vs independents, and exports to Excel.

Usage:
    1. pip install requests pandas openpyxl python-dotenv
    2. Create a .env file next to this script with:
         COMPANIES_HOUSE_API_KEY=your_key_here
       Or set the environment variable directly.
    3. python truck_tyre_search.py
"""
import os
import re
import time
import logging
import requests
import pandas as pd
from dotenv import load_dotenv

# Load .env from same directory as this script
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────────────────
API_KEY = os.getenv("COMPANIES_HOUSE_API_KEY")
BASE_URL = "https://api.company-information.service.gov.uk"
ITEMS_PER_PAGE = 500
RATE_LIMIT_DELAY = 0.2
RATE_LIMIT_BACKOFF = 60

# Keywords that indicate a corporate owner (i.e. likely a chain)
CORPORATE_KEYWORDS = [
    'ltd', 'limited', 'plc', 'group', 'holdings',
    'llp', 'inc', 'corporation', 'corp', 'partners',
    'capital', 'investments', 'enterprises'
]

# Global exclude keywords — filter out companies that are clearly not truck tyre specialists
GLOBAL_EXCLUDES = [
    'car', 'bicycle', 'cycle', 'motorcycle', 'motorbike',
    'alloy', 'exhaust', 'MOT', 'garage', 'auto centre',
    'karting', 'kart', 'racing', 'golf', 'scooter',
    'wheelchair', 'pushchair', 'pram', 'buggy',
    'aircraft', 'aero', 'aviation'
]

# Keywords that indicate a truck/commercial tyre specialist (for relevance scoring)
RELEVANCE_KEYWORDS = [
    'truck', 'commercial', 'hgv', 'fleet', 'lorry',
    'van', 'trailer', 'bus', 'coach', 'heavy',
    'plant', 'industrial', 'cv '
]

# Truck-specific keywords — Searches 3 & 4 require at least one of these
# alongside "tyre/tire" to filter out generic tyre shops
TRUCK_KEYWORDS = [
    'truck', 'commercial', 'hgv', 'fleet', 'lorry',
    'van', 'trailer', 'bus', 'coach', 'heavy',
    'plant', 'industrial'
]

# Northern Ireland address indicators
NI_INDICATORS = [
    'NORTHERN IRELAND', 'BELFAST', 'ANTRIM', 'ARMAGH',
    'DERRY', 'DOWN', 'FERMANAGH', 'TYRONE', 'LISBURN', 'NEWRY'
]

# SIC code descriptions (only the ones relevant to our searches)
SIC_DESCRIPTIONS = {
    "22110": "Manufacture of rubber tyres and tubes",
    "45200": "Maintenance and repair of motor vehicles",
    "45310": "Wholesale trade of motor vehicle parts and accessories",
    "45320": "Retail trade of motor vehicle parts and accessories",
}


# ─── API Client ──────────────────────────────────────────────────────────────

class CompaniesHouseAPI:
    def __init__(self):
        if not API_KEY:
            raise ValueError(
                "COMPANIES_HOUSE_API_KEY not set.\n"
                "Create a .env file with: COMPANIES_HOUSE_API_KEY=your_key\n"
                "Get a free key at: https://developer.company-information.service.gov.uk/"
            )
        self.session = requests.Session()
        self.session.auth = (API_KEY, '')

    def _make_request(self, endpoint, params=None):
        url = f"{BASE_URL}{endpoint}"
        for attempt in range(3):
            try:
                response = self.session.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 416:
                    return None
                elif response.status_code == 429:
                    logger.warning(f"Rate limited, waiting {RATE_LIMIT_BACKOFF}s...")
                    time.sleep(RATE_LIMIT_BACKOFF)
                    continue
                elif response.status_code == 404:
                    return None
                else:
                    logger.error(f"API error {response.status_code}: {response.text}")
                    if attempt < 2:
                        time.sleep(5)
                        continue
                    return None
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                if attempt < 2:
                    time.sleep(5)
                    continue
                return None
        return None

    def _process_company(self, item):
        address = item.get('registered_office_address', {})
        sic_codes = item.get('sic_codes', [])
        accounts = item.get('accounts', {})
        last_accounts = accounts.get('last_accounts', {})
        confirmation = item.get('confirmation_statement', {})
        previous_names = item.get('previous_company_names', [])

        sic_descs = [SIC_DESCRIPTIONS.get(s, s) for s in sic_codes]
        addr_parts = [address.get(k, '') for k in
                      ['address_line_1', 'address_line_2', 'locality', 'region', 'postal_code', 'country']]
        full_address = ', '.join(p for p in addr_parts if p)
        prev_names = [pn.get('name', '') for pn in previous_names if pn.get('name')]

        return {
            'company_number': item.get('company_number', ''),
            'company_name': item.get('company_name', ''),
            'company_status': item.get('company_status', ''),
            'company_type': item.get('company_type', ''),
            'date_of_creation': item.get('date_of_creation', ''),
            'date_of_cessation': item.get('date_of_cessation', ''),
            'sic_codes': ', '.join(sic_codes),
            'sic_descriptions': ', '.join(sic_descs),
            'address_line_1': address.get('address_line_1', ''),
            'address_line_2': address.get('address_line_2', ''),
            'locality': address.get('locality', ''),
            'region': address.get('region', ''),
            'postal_code': address.get('postal_code', ''),
            'country': address.get('country', ''),
            'full_address': full_address,
            'accounts_overdue': 'Yes' if accounts.get('overdue') else 'No',
            'last_accounts_date': last_accounts.get('made_up_to', ''),
            'last_accounts_type': last_accounts.get('type', ''),
            'confirmation_statement_last': confirmation.get('last_made_up_to', ''),
            'jurisdiction': item.get('jurisdiction', ''),
            'has_charges': 'Yes' if item.get('has_charges') else 'No',
            'has_insolvency_history': 'Yes' if item.get('has_insolvency_history') else 'No',
            'previous_names': '; '.join(prev_names),
            'companies_house_url': f"https://find-and-update.company-information.service.gov.uk/company/{item.get('company_number', '')}"
        }

    def search_by_sic(self, sic_code, active_only=True):
        companies = []
        start_index = 0
        while True:
            params = {'sic_codes': sic_code, 'size': ITEMS_PER_PAGE, 'start_index': start_index}
            if active_only:
                params['company_status'] = 'active'
            response = self._make_request('/advanced-search/companies', params)
            if not response:
                break
            items = response.get('items', [])
            if not items:
                break
            for item in items:
                companies.append(self._process_company(item))
            hits = response.get('hits', 0)
            start_index += len(items)
            if start_index >= hits or start_index >= 10000:
                break
            time.sleep(RATE_LIMIT_DELAY)
        logger.info(f"SIC {sic_code}: {len(companies)} companies")
        return companies

    def search_by_name(self, search_term, active_only=True):
        companies = []
        start_index = 0
        while True:
            params = {'company_name_includes': search_term, 'size': ITEMS_PER_PAGE, 'start_index': start_index}
            if active_only:
                params['company_status'] = 'active'
            response = self._make_request('/advanced-search/companies', params)
            if not response:
                break
            items = response.get('items', [])
            if not items:
                break
            for item in items:
                companies.append(self._process_company(item))
            hits = response.get('hits', 0)
            start_index += len(items)
            if start_index >= hits or start_index >= 10000:
                break
            time.sleep(RATE_LIMIT_DELAY)
        logger.info(f"Name search '{search_term}': {len(companies)} companies")
        return companies

    def get_officers(self, company_number):
        response = self._make_request(f'/company/{company_number}/officers')
        if not response:
            return {'directors_count': 0, 'directors_names': ''}
        directors = []
        for officer in response.get('items', []):
            if officer.get('resigned_on'):
                continue
            if 'director' in officer.get('officer_role', '').lower():
                name = officer.get('name', '')
                if name:
                    directors.append(name)
        return {'directors_count': len(directors), 'directors_names': '; '.join(directors)}

    def get_psc(self, company_number):
        response = self._make_request(f'/company/{company_number}/persons-with-significant-control')
        if not response:
            return {'psc_count': 0, 'psc_names': '', 'psc_control': ''}
        psc_names = []
        control_types = set()
        for psc in response.get('items', []):
            if psc.get('ceased'):
                continue
            name = psc.get('name', '')
            if not name:
                ne = psc.get('name_elements', {})
                if ne:
                    name = ' '.join(p for p in [ne.get('forename', ''), ne.get('surname', '')] if p)
            if name:
                psc_names.append(name)
            for nature in psc.get('natures_of_control', []):
                if 'ownership-of-shares-75-to-100' in nature:
                    control_types.add('75-100% shares')
                elif 'ownership-of-shares-50-to-75' in nature:
                    control_types.add('50-75% shares')
                elif 'ownership-of-shares-25-to-50' in nature:
                    control_types.add('25-50% shares')
                elif 'voting-rights' in nature:
                    control_types.add('Voting rights')
                elif 'right-to-appoint-and-remove-directors' in nature:
                    control_types.add('Appoint directors')
                elif 'significant-influence-or-control' in nature:
                    control_types.add('Significant influence')
        return {
            'psc_count': len(psc_names),
            'psc_names': '; '.join(psc_names),
            'psc_control': '; '.join(sorted(control_types))
        }

    def enrich_with_people(self, companies):
        total = len(companies)
        for i, company in enumerate(companies):
            num = company.get('company_number')
            if num:
                logger.info(f"Enriching {i+1}/{total}: {company.get('company_name', num)}")
                company.update(self.get_officers(num))
                company.update(self.get_psc(num))
                time.sleep(RATE_LIMIT_DELAY)
            else:
                company.update({'directors_count': 0, 'directors_names': '',
                                'psc_count': 0, 'psc_names': '', 'psc_control': ''})
        return companies


# ─── Filters ─────────────────────────────────────────────────────────────────

def filter_include_keywords(companies, keywords):
    if not keywords:
        return companies
    filtered = []
    for c in companies:
        name = c.get('company_name', '').upper()
        if any(kw.upper() in name for kw in keywords):
            filtered.append(c)
    return filtered


def filter_exclude_keywords(companies, keywords):
    if not keywords:
        return companies
    filtered = []
    for c in companies:
        name = c.get('company_name', '').upper()
        exclude = False
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw.upper()) + r'\b', name):
                exclude = True
                break
        if not exclude:
            filtered.append(c)
    return filtered


def filter_ni(companies):
    result = []
    for c in companies:
        num = c.get('company_number', '')
        if num.startswith('NI') or num.startswith('R0'):
            continue
        addr = f"{c.get('full_address', '')} {c.get('locality', '')} {c.get('region', '')} {c.get('country', '')}".upper()
        if any(ind in addr for ind in NI_INDICATORS):
            continue
        result.append(c)
    return result


def deduplicate(companies):
    seen = set()
    unique = []
    for c in companies:
        num = c.get('company_number')
        if num and num not in seen:
            seen.add(num)
            unique.append(c)
    return unique


# ─── Chain Detection ─────────────────────────────────────────────────────────

def is_likely_chain(psc_names):
    if not psc_names or not psc_names.strip():
        return 'Unknown'
    for name in psc_names.split(';'):
        name_lower = name.strip().lower()
        if any(kw in name_lower for kw in CORPORATE_KEYWORDS):
            return 'Yes'
    return 'No'


# ─── Relevance Scoring ──────────────────────────────────────────────────────

def calc_relevance_score(company_name):
    """Score how likely a company is a truck tyre specialist (higher = more relevant)."""
    name = company_name.lower()
    return sum(1 for kw in RELEVANCE_KEYWORDS if kw in name)


# ─── Search Strategy ─────────────────────────────────────────────────────────

def run_search(api, label, sic_codes=None, include_kw=None, exclude_kw=None, require_truck_kw=False):
    logger.info(f"\n--- {label} ---")
    companies = []

    if sic_codes:
        for sic in sic_codes:
            companies.extend(api.search_by_sic(sic))
        companies = deduplicate(companies)
        if include_kw:
            companies = filter_include_keywords(companies, include_kw)
    elif include_kw:
        for kw in include_kw:
            companies.extend(api.search_by_name(kw))
        companies = deduplicate(companies)

    # Require at least one truck keyword in company name (for SIC-based searches)
    if require_truck_kw:
        companies = filter_include_keywords(companies, TRUCK_KEYWORDS)

    # Apply search-specific excludes
    if exclude_kw:
        companies = filter_exclude_keywords(companies, exclude_kw)

    # Apply global excludes to all searches
    companies = filter_exclude_keywords(companies, GLOBAL_EXCLUDES)

    companies = filter_ni(companies)

    for c in companies:
        c['search_source'] = label

    logger.info(f"{label}: {len(companies)} companies found")
    return companies


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 60)
    logger.info("  TRUCK TYRE SPECIALIST FINDER")
    logger.info("=" * 60)

    api = CompaniesHouseAPI()

    # Search 1: SIC 22110 (tyre manufacturing) + truck/tyre keywords
    s1 = run_search(api, "SIC 22110 + tyre/truck",
                    sic_codes=["22110"],
                    include_kw=["tyre", "tire", "truck"])

    # Search 2: Keywords only - truck tyre specialists
    s2 = run_search(api, "Keyword: truck/commercial/HGV tyre",
                    include_kw=["truck tyre", "truck tire", "commercial tyre",
                                "commercial tire", "HGV tyre"])

    # Search 3: SIC 45320 (retail vehicle parts) + tyre + must have truck keyword
    s3 = run_search(api, "SIC 45320 + tyre + truck keyword (retail)",
                    sic_codes=["45320"],
                    include_kw=["tyre", "tire"],
                    exclude_kw=["car", "bicycle", "cycle", "motorcycle", "motorbike"],
                    require_truck_kw=True)

    # Search 4: SIC 45310 (wholesale vehicle parts) + tyre + must have truck keyword
    s4 = run_search(api, "SIC 45310 + tyre + truck keyword (wholesale)",
                    sic_codes=["45310"],
                    include_kw=["tyre", "tire"],
                    require_truck_kw=True)

    # Combine all results, merge search_source for duplicates
    all_companies = s1 + s2 + s3 + s4
    logger.info(f"\nTotal before dedup: {len(all_companies)}")

    source_map = {}
    for c in all_companies:
        num = c['company_number']
        if num in source_map:
            existing = source_map[num]['search_source']
            new_source = c['search_source']
            if new_source not in existing:
                source_map[num]['search_source'] = f"{existing}; {new_source}"
        else:
            source_map[num] = c

    unique_companies = list(source_map.values())
    logger.info(f"After dedup: {len(unique_companies)} unique companies")

    if not unique_companies:
        logger.warning("No companies found. Check your API key and search criteria.")
        return

    # Enrich with PSC & directors data
    logger.info(f"\nFetching directors & PSC data for {len(unique_companies)} companies...")
    logger.info("(This may take a while due to API rate limits)\n")
    enriched = api.enrich_with_people(unique_companies)

    # Add chain flag and relevance score
    for company in enriched:
        company['likely_chain'] = is_likely_chain(company.get('psc_names', ''))
        company['relevance_score'] = calc_relevance_score(company.get('company_name', ''))

    # Export to Excel
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'truck_tyre_specialists.xlsx')

    columns = [
        'company_name', 'company_number', 'company_status',
        'relevance_score', 'likely_chain',
        'search_source', 'sic_codes', 'sic_descriptions',
        'full_address', 'locality', 'region', 'postal_code',
        'date_of_creation',
        'directors_count', 'directors_names',
        'psc_count', 'psc_names', 'psc_control',
        'companies_house_url'
    ]

    df = pd.DataFrame(enriched)
    ordered = [c for c in columns if c in df.columns]
    extra = [c for c in df.columns if c not in columns]
    df = df[ordered + extra]

    # Sort by relevance score (highest first), then company name
    df = df.sort_values(['relevance_score', 'company_name'], ascending=[False, True])

    df.to_excel(output_file, index=False, engine='openpyxl')

    # Summary
    chain_counts = df['likely_chain'].value_counts()
    high_relevance = len(df[df['relevance_score'] >= 2])
    medium_relevance = len(df[df['relevance_score'] == 1])
    low_relevance = len(df[df['relevance_score'] == 0])
    logger.info("\n" + "=" * 60)
    logger.info("  RESULTS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total companies:    {len(df)}")
    logger.info(f"")
    logger.info(f"Relevance Score:")
    logger.info(f"  High (2+):        {high_relevance}  <-- review these first")
    logger.info(f"  Medium (1):       {medium_relevance}")
    logger.info(f"  Low (0):          {low_relevance}")
    logger.info(f"")
    logger.info(f"Chain Detection:")
    logger.info(f"  Likely Chain:     {chain_counts.get('Yes', 0)}")
    logger.info(f"  Independent:      {chain_counts.get('No', 0)}")
    logger.info(f"  Unknown:          {chain_counts.get('Unknown', 0)}")
    logger.info(f"\nExported to: {output_file}")


if __name__ == '__main__':
    main()
