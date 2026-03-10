"""
Recall metrics utilities for comparing search results against known company lists.
"""


def normalize_company_number(num):
    """Normalize a company number for matching (strip whitespace, uppercase)."""
    if not num:
        return ''
    return str(num).strip().upper()


def compare_with_known_list(search_results, known_companies):
    """
    Compare search results against a known list of companies.

    Args:
        search_results: list of company dicts from search (must have 'company_number')
        known_companies: list of dicts with at minimum 'company_number'

    Returns:
        dict with recall metrics and lists of matched/missed companies.
    """
    # Build sets of normalized company numbers
    found_numbers = {
        normalize_company_number(c.get('company_number'))
        for c in search_results
        if c.get('company_number')
    }

    known_map = {}
    for c in known_companies:
        num = normalize_company_number(c.get('company_number'))
        if num:
            known_map[num] = c

    known_numbers = set(known_map.keys())

    # Calculate metrics
    true_positives = found_numbers & known_numbers
    false_negatives = known_numbers - found_numbers
    additional_found = found_numbers - known_numbers

    total_known = len(known_numbers)
    total_found = len(found_numbers)

    recall = len(true_positives) / total_known if total_known > 0 else 0
    precision = len(true_positives) / total_found if total_found > 0 else 0

    # Build missed companies list with available details
    missed_companies = []
    for num in sorted(false_negatives):
        entry = known_map.get(num, {})
        missed_companies.append({
            'company_number': num,
            'company_name': entry.get('company_name', ''),
        })

    return {
        'total_known': total_known,
        'total_found': total_found,
        'true_positives': len(true_positives),
        'false_negatives': len(false_negatives),
        'additional_found': len(additional_found),
        'recall': round(recall, 4),
        'precision': round(precision, 4),
        'missed_companies': missed_companies,
    }
