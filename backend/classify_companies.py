"""
Truck Tyre Specialist Classifier (Standalone)

Uses DeepSeek API to research and classify companies as truck tyre specialists.
Two-phase approach: name-based screening + AI-powered online research.

Usage:
    1. pip install requests pandas openpyxl python-dotenv
    2. Create a .env file next to this script with:
         DEEPSEEK_API_KEY=your_key_here
    3. python classify_companies.py
"""
import os
import re
import json
import time
import logging
import requests
import pandas as pd
from dotenv import load_dotenv

# Load .env from same directory as this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, '.env'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

INPUT_FILE = os.path.join(SCRIPT_DIR, 'truck_tyre_specialists.xlsx')
if not os.path.exists(INPUT_FILE):
    INPUT_FILE = '/tmp/company_list_simple.txt'
OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'truck_tyre_classification_full.xlsx')
CHECKPOINT_FILE = os.path.join(SCRIPT_DIR, 'classification_checkpoint.json')

# Rate limiting
CALLS_PER_MINUTE = 20
CALL_DELAY = 60.0 / CALLS_PER_MINUTE

# ─── Phase 1: Name-based pre-screening ──────────────────────────────────────

# Strong truck tyre specialist indicators (regex)
TRUCK_TYRE_PATTERNS = [
    r'truck\s*tyre', r'truck\s*tire', r'truck\s*tyres', r'truck\s*tires',
    r'commercial\s*tyre', r'commercial\s*tire', r'commercial\s*tyres',
    r'hgv\s*tyre', r'hgv\s*tire', r'hgv\s*tyres',
    r'fleet\s*tyre', r'fleet\s*tire', r'fleet\s*tyres',
    r'lorry\s*tyre', r'lorry\s*tire', r'lorry\s*tyres',
    r'truck\s*wheel', r'commercial\s*wheel',
]

# Truck/commercial vehicle keywords
TRUCK_INDICATORS = [
    'truck', 'hgv', 'lorry', 'fleet', 'trailer',
    'bus', 'coach', 'plant', 'industrial',
]

# Tyre-related words
TYRE_WORDS = ['tyre', 'tire', 'tyres', 'tires', 'wheel', 'wheels']

# Auto-exclude patterns — clearly NOT truck tyre specialists
AUTO_EXCLUDE_PATTERNS = [
    r'\bbicycle\b', r'\bcycle\b', r'\bmotorcycle\b', r'\bmotorbike\b',
    r'\bscooter\b', r'\bkart\b', r'\bkarting\b', r'\bracing\b',
    r'\bgolf\b', r'\bwheelchair\b', r'\bpushchair\b', r'\bpram\b',
    r'\baircraft\b', r'\baero\b', r'\baviation\b',
    r'\brecycl', r'\bretread', r'\bremould',
    r'\bpuncture\s*repair\b',
]

# Generic car/consumer tyre indicators (name only has tyre + these = likely NOT truck)
CAR_INDICATORS = [
    'mobile tyre', 'mobile tire', 'part worn', 'partworn', 'part-worn',
    'alloy', '4x4', 'suv', 'performance tyre', 'budget tyre',
    'cheap tyre', 'discount tyre', 'express tyre', 'quick tyre',
    'kwik', 'fast fit', 'auto centre', 'mot ',
]

# Non-retail tyre business indicators
NON_RETAIL_INDICATORS = [
    'recycl', 'retread', 'remould', 'disposal', 'waste',
    'import', 'export', 'trading', 'manufacture', 'production',
    'rubber', 'compound', 'moulding',
]


def classify_by_name(name):
    """
    Returns (classification, confidence, method, reason) or None if needs AI research.
    """
    name_lower = name.lower()

    # 1. Auto-exclude patterns
    for pattern in AUTO_EXCLUDE_PATTERNS:
        if re.search(pattern, name_lower):
            return ('No', 'High', 'Name analysis',
                    'Company name contains excluded keyword (non-truck vehicle type)')

    # 2. Strong truck tyre specialist patterns
    for pattern in TRUCK_TYRE_PATTERNS:
        if re.search(pattern, name_lower):
            return ('Yes', 'High', 'Name analysis',
                    'Company name contains strong truck/commercial tyre indicator')

    has_truck = any(kw in name_lower for kw in TRUCK_INDICATORS)
    has_tyre = any(kw in name_lower for kw in TYRE_WORDS)

    # 3. Truck indicator + tyre word = likely specialist
    if has_truck and has_tyre:
        return ('Yes', 'Medium', 'Name analysis',
                'Company name contains both truck/commercial and tyre keywords')

    # 4. "Commercial" + tyre = likely specialist
    if 'commercial' in name_lower and has_tyre:
        return ('Yes', 'Medium', 'Name analysis',
                'Company name contains "commercial" and tyre keyword')

    # 5. Holding/investment companies
    holding_patterns = [r'\bholdings?\b', r'\binvestment', r'\bcapital\b', r'\bventure']
    is_holding = any(re.search(p, name_lower) for p in holding_patterns)
    if is_holding and not has_tyre:
        return ('No', 'Medium', 'Name analysis',
                'Appears to be a holding/investment company with no tyre indication')

    # 6. Car/consumer tyre indicators (with tyre but clearly car-focused)
    if has_tyre and not has_truck:
        for indicator in CAR_INDICATORS:
            if indicator in name_lower:
                return ('No', 'Medium', 'Name analysis',
                        f'Generic/car tyre business indicator: "{indicator}"')

    # 7. Non-retail tyre businesses
    for indicator in NON_RETAIL_INDICATORS:
        if indicator in name_lower:
            return ('No', 'Medium', 'Name analysis',
                    f'Non-retail tyre business: "{indicator}"')

    # 8. Generic "[Name] TYRES LTD" with no truck indicator → needs AI research
    return None


# ─── Phase 2: DeepSeek API ───────────────────────────────────────────────────

def classify_with_deepseek(session, company_name, company_number, address=""):
    """
    Use DeepSeek API to classify a company.
    Returns (classification, confidence, what_was_checked, reason)
    """
    prompt = f"""You are classifying UK companies as truck tyre specialists.

DEFINITION: A truck tyre specialist generates more than 50% of its total turnover
from selling new tyres (including rims, complete wheels) and tyre-related services
for TRUCKS, HGVs, commercial vehicles, buses, coaches, trailers, and other
heavy/industrial vehicles — to private and corporate fleet end users.

COMPANY TO CLASSIFY:
- Name: {company_name}
- Company Number: {company_number}
- Address: {address}

Based on the company name and your knowledge of the UK tyre industry, classify this company.

RESPOND WITH EXACTLY THIS JSON (no other text):
{{"classification": "Yes" or "Maybe" or "No", "confidence": "High" or "Medium" or "Low", "what_was_checked": "What you based your classification on", "reason": "Detailed reason"}}

RULES:
- "Yes" = name/knowledge clearly indicates truck/commercial/HGV tyre specialist
- "Maybe" = could be a truck tyre specialist, needs manual verification
- "No" = clearly a generic car tyre shop, manufacturer, wholesaler, or unrelated
- Most generic "XYZ Tyres Ltd" with no truck/commercial indicator = "No" (car tyre shops)
- Companies with "fleet", "truck", "commercial", "HGV" + tyre = "Yes"
- If truly uncertain, classify as "Maybe" """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
        "temperature": 0.1,
    }

    for attempt in range(3):
        try:
            resp = session.post(DEEPSEEK_URL, json=payload, headers=headers, timeout=30)

            if resp.status_code == 429:
                wait = 30 * (attempt + 1)
                logger.warning(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue

            if resp.status_code != 200:
                logger.warning(f"API error {resp.status_code} for {company_name}: {resp.text[:200]}")
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))
                    continue
                return ('Maybe', 'Low', f'API error {resp.status_code}', resp.text[:200])

            data = resp.json()
            text = data['choices'][0]['message']['content'].strip()

            # Extract JSON
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return (
                    result.get('classification', 'Maybe'),
                    result.get('confidence', 'Low'),
                    result.get('what_was_checked', 'DeepSeek analysis'),
                    result.get('reason', 'See AI analysis')
                )
            else:
                logger.warning(f"No JSON in response for {company_name}: {text[:200]}")
                return ('Maybe', 'Low', 'Response not parseable', text[:200])

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error for {company_name}: {e}")
            if attempt < 2:
                time.sleep(2)
                continue
            return ('Maybe', 'Low', 'JSON parse error', str(e))

        except Exception as e:
            logger.warning(f"Error for {company_name} (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            return ('Maybe', 'Low', 'Error after retries', str(e)[:200])

    return ('Maybe', 'Low', 'Failed after retries', 'Could not get response')


# ─── Checkpoint management ───────────────────────────────────────────────────

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            data = json.load(f)
            logger.info(f"Loaded checkpoint with {len(data)} classified companies")
            return data
    return {}


def save_checkpoint(results):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(results, f, indent=2)


# ─── Main ────────────────────────────────────────────────────────────────────

def load_companies():
    if os.path.exists(INPUT_FILE) and INPUT_FILE.endswith('.xlsx'):
        df = pd.read_excel(INPUT_FILE)
        logger.info(f"Loaded {len(df)} companies from {INPUT_FILE}")
        return df

    tsv_file = '/tmp/company_list_simple.txt'
    if os.path.exists(tsv_file):
        df = pd.read_csv(tsv_file, sep='\t')
        logger.info(f"Loaded {len(df)} companies from {tsv_file}")
        return df

    raise FileNotFoundError(f"No company list found.")


def main():
    logger.info("=" * 60)
    logger.info("  TRUCK TYRE SPECIALIST CLASSIFIER")
    logger.info("  Phase 1: Name screening | Phase 2: DeepSeek AI")
    logger.info("=" * 60)

    df = load_companies()
    companies = df.to_dict('records')
    checkpoint = load_checkpoint()

    # Phase 1: Name-based pre-screening
    logger.info("\n--- Phase 1: Name-based pre-screening ---")
    results = {}
    needs_research = []

    for company in companies:
        num = str(company.get('company_number', ''))
        name = str(company.get('company_name', ''))
        address = str(company.get('address', company.get('full_address', '')))

        if num in checkpoint:
            results[num] = checkpoint[num]
            continue

        name_result = classify_by_name(name)
        if name_result:
            classification, confidence, method, reason = name_result
            results[num] = {
                'company_number': num,
                'company_name': name,
                'classification': classification,
                'confidence': confidence,
                'method': method,
                'what_was_checked': 'Company name keyword analysis',
                'reason': reason,
            }
        else:
            needs_research.append({
                'company_number': num,
                'company_name': name,
                'address': address if address != 'nan' else '',
            })

    already_done = len(checkpoint)
    phase1_classified = len(results) - already_done
    logger.info(f"Phase 1 classified: {phase1_classified} companies by name")
    logger.info(f"Already in checkpoint: {already_done}")
    logger.info(f"Need AI research: {len(needs_research)} companies")

    # Phase 2: DeepSeek API research
    if needs_research:
        logger.info(f"\n--- Phase 2: DeepSeek AI ({len(needs_research)} companies) ---")
        if not DEEPSEEK_API_KEY:
            logger.warning("DEEPSEEK_API_KEY not set — classifying remaining as 'Maybe (needs manual check)'")
            for company in needs_research:
                num = company['company_number']
                results[num] = {
                    'company_number': num,
                    'company_name': company['company_name'],
                    'classification': 'Maybe',
                    'confidence': 'Low',
                    'method': 'No API key — needs manual check',
                    'what_was_checked': 'Name only (no AI available)',
                    'reason': 'Generic tyre company name — could not verify online without API key',
                }
        else:
            session = requests.Session()
            total = len(needs_research)

            for i, company in enumerate(needs_research):
                num = company['company_number']
                name = company['company_name']
                address = company.get('address', '')

                logger.info(f"[{i+1}/{total}] Researching: {name}")

                classification, confidence, what_checked, reason = classify_with_deepseek(
                    session, name, num, address
                )

                results[num] = {
                    'company_number': num,
                    'company_name': name,
                    'classification': classification,
                    'confidence': confidence,
                    'method': 'AI analysis (DeepSeek)',
                    'what_was_checked': what_checked,
                    'reason': reason,
                }

                if (i + 1) % 25 == 0:
                    save_checkpoint(results)
                    logger.info(f"  Checkpoint saved ({len(results)} total)")

                time.sleep(CALL_DELAY)

            save_checkpoint(results)

    # Export to Excel
    logger.info("\n--- Exporting results ---")
    rows = []
    for company in companies:
        num = str(company.get('company_number', ''))
        if num in results:
            rows.append(results[num])
        else:
            rows.append({
                'company_number': num,
                'company_name': str(company.get('company_name', '')),
                'classification': 'Unknown',
                'confidence': 'Low',
                'method': 'Not processed',
                'what_was_checked': '',
                'reason': '',
            })

    result_df = pd.DataFrame(rows)
    columns = ['company_number', 'company_name', 'classification',
               'confidence', 'method', 'what_was_checked', 'reason']
    result_df = result_df[columns]
    result_df.to_excel(OUTPUT_FILE, index=False, engine='openpyxl')

    # Summary
    counts = result_df['classification'].value_counts()
    conf_counts = result_df['confidence'].value_counts()

    logger.info("\n" + "=" * 60)
    logger.info("  CLASSIFICATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total companies:     {len(result_df)}")
    logger.info(f"")
    logger.info(f"Classification:")
    logger.info(f"  Yes (specialist):  {counts.get('Yes', 0)}")
    logger.info(f"  Maybe (unclear):   {counts.get('Maybe', 0)}")
    logger.info(f"  No (not spec.):    {counts.get('No', 0)}")
    logger.info(f"")
    logger.info(f"Confidence:")
    logger.info(f"  High:              {conf_counts.get('High', 0)}")
    logger.info(f"  Medium:            {conf_counts.get('Medium', 0)}")
    logger.info(f"  Low:               {conf_counts.get('Low', 0)}")
    logger.info(f"\nExported to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
