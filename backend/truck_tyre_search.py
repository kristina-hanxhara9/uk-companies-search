"""
Truck Tyre Specialist Finder
Runs multiple search strategies, combines results, enriches with PSC data,
and flags likely chains vs independents. Exports to Excel.
"""
import sys
import os
import logging
import pandas as pd

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.companies_house import CompaniesHouseAPI
from utils.filters import (
    filter_by_include_keywords,
    filter_by_exclude_keywords,
    filter_exclude_northern_ireland,
    deduplicate_companies
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Keywords that indicate a corporate entity (i.e. likely a chain)
CORPORATE_KEYWORDS = [
    'ltd', 'limited', 'plc', 'group', 'holdings',
    'llp', 'inc', 'corporation', 'corp', 'partners',
    'capital', 'investments', 'enterprises'
]


def is_likely_chain(psc_names: str) -> str:
    """Determine if a company is likely a chain based on PSC ownership."""
    if not psc_names or not psc_names.strip():
        return 'Unknown'
    for name in psc_names.split(';'):
        name_lower = name.strip().lower()
        if any(kw in name_lower for kw in CORPORATE_KEYWORDS):
            return 'Yes'
    return 'No'


def run_search(api: CompaniesHouseAPI, label: str, sic_codes=None, include_kw=None, exclude_kw=None):
    """Run a single search strategy and return results with source label."""
    logger.info(f"--- {label} ---")
    companies = []

    if sic_codes:
        companies = api.search_by_sic_codes(sic_codes, active_only=True)
        if include_kw:
            companies = filter_by_include_keywords(companies, include_kw)
    elif include_kw:
        # Keyword-only search: search each keyword separately and combine
        for kw in include_kw:
            results = api.search_by_company_name(kw, active_only=True)
            companies.extend(results)
        companies = deduplicate_companies(companies)

    if exclude_kw:
        companies = filter_by_exclude_keywords(companies, exclude_kw)

    # Exclude Northern Ireland
    companies = filter_exclude_northern_ireland(companies)

    # Tag each company with its search source
    for c in companies:
        c['search_source'] = label

    logger.info(f"{label}: {len(companies)} companies found")
    return companies


def main():
    logger.info("=== Truck Tyre Specialist Finder ===")
    api = CompaniesHouseAPI()

    # Search 1: SIC 22110 (tyre manufacturing) + truck/tyre keywords
    s1 = run_search(api, "SIC 22110 + tyre/truck",
                    sic_codes=["22110"],
                    include_kw=["tyre", "tire", "truck"])

    # Search 2: Keywords only - truck tyre specialists
    s2 = run_search(api, "Keyword: truck/commercial/HGV tyre",
                    include_kw=["truck tyre", "truck tire", "commercial tyre",
                                "commercial tire", "HGV tyre"])

    # Search 3: SIC 45320 (retail vehicle parts) + tyre, exclude non-truck
    s3 = run_search(api, "SIC 45320 + tyre (retail)",
                    sic_codes=["45320"],
                    include_kw=["tyre", "tire"],
                    exclude_kw=["car", "bicycle", "cycle", "motorcycle", "motorbike"])

    # Search 4: SIC 45310 (wholesale vehicle parts) + tyre
    s4 = run_search(api, "SIC 45310 + tyre (wholesale)",
                    sic_codes=["45310"],
                    include_kw=["tyre", "tire"])

    # Combine all results
    all_companies = s1 + s2 + s3 + s4
    logger.info(f"Total before dedup: {len(all_companies)}")

    # For companies found in multiple searches, combine source labels
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

    # Enrich with PSC and directors data
    logger.info("Enriching with directors & PSC data (this may take a while)...")
    enriched = api.enrich_with_people_data(unique_companies)

    # Add "Likely Chain" flag
    for company in enriched:
        company['likely_chain'] = is_likely_chain(company.get('psc_names', ''))

    # Export to Excel
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'truck_tyre_specialists.xlsx')

    columns = [
        'company_name', 'company_number', 'company_status', 'likely_chain',
        'search_source', 'sic_codes', 'sic_descriptions',
        'full_address', 'locality', 'region', 'postal_code',
        'date_of_creation',
        'directors_count', 'directors_names',
        'psc_count', 'psc_names', 'psc_control',
        'companies_house_url'
    ]

    df = pd.DataFrame(enriched)
    # Reorder columns, keeping any extra columns at the end
    ordered = [c for c in columns if c in df.columns]
    extra = [c for c in df.columns if c not in columns]
    df = df[ordered + extra]

    df.to_excel(output_file, index=False, engine='openpyxl')

    # Print summary
    chain_counts = df['likely_chain'].value_counts()
    logger.info(f"\n=== RESULTS ===")
    logger.info(f"Total companies: {len(df)}")
    logger.info(f"Likely Chain:      {chain_counts.get('Yes', 0)}")
    logger.info(f"Likely Independent: {chain_counts.get('No', 0)}")
    logger.info(f"Unknown:           {chain_counts.get('Unknown', 0)}")
    logger.info(f"\nExported to: {output_file}")


if __name__ == '__main__':
    main()
