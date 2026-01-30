"""
Filtering utilities for company data
"""
import re
from typing import List, Dict, Any


def filter_by_include_keywords(companies: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
    """
    Filter companies to include only those with matching keywords in their name.
    Case-insensitive matching.
    """
    if not keywords:
        return companies

    filtered = []
    for company in companies:
        name = company.get('company_name', '').upper()
        for keyword in keywords:
            if keyword.upper() in name:
                filtered.append(company)
                break
    return filtered


def filter_by_exclude_keywords(companies: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
    """
    Filter companies to exclude those with matching keywords in their name.
    Uses word boundary matching to avoid partial matches.
    """
    if not keywords:
        return companies

    filtered = []
    for company in companies:
        name = company.get('company_name', '').upper()
        exclude = False
        for keyword in keywords:
            # Use word boundary to match whole words only
            pattern = r'\b' + re.escape(keyword.upper()) + r'\b'
            if re.search(pattern, name):
                exclude = True
                break
        if not exclude:
            filtered.append(company)
    return filtered


def is_northern_ireland(company: Dict[str, Any]) -> bool:
    """
    Check if company is registered in Northern Ireland.
    Northern Ireland companies have company numbers starting with 'NI' or 'R0'.
    Also checks address for Northern Ireland indicators.
    """
    company_number = company.get('company_number', '')
    if company_number.startswith('NI') or company_number.startswith('R0'):
        return True

    # Check full_address field (processed company data)
    full_address = company.get('full_address', '').upper()

    # Also check individual address fields
    locality = company.get('locality', '').upper()
    region = company.get('region', '').upper()
    country = company.get('country', '').upper()

    # Combine all address parts
    address_str = f"{full_address} {locality} {region} {country}"

    ni_indicators = ['NORTHERN IRELAND', 'BELFAST', 'ANTRIM', 'ARMAGH', 'DERRY',
                     'DOWN', 'FERMANAGH', 'TYRONE', 'LISBURN', 'NEWRY']
    for indicator in ni_indicators:
        if indicator in address_str:
            return True

    return False


def filter_exclude_northern_ireland(companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter out companies registered in Northern Ireland.
    """
    return [c for c in companies if not is_northern_ireland(c)]


def filter_active_only(companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter to include only active companies.
    """
    return [c for c in companies if c.get('company_status', '').lower() == 'active']


def deduplicate_companies(companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate companies based on company_number.
    """
    seen = set()
    unique = []
    for company in companies:
        company_num = company.get('company_number')
        if company_num and company_num not in seen:
            seen.add(company_num)
            unique.append(company)
    return unique
