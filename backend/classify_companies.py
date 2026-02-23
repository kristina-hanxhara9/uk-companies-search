"""
Truck Tyre Specialist Classifier (Standalone)

Uses Gemini REST API with Google Search grounding to research and classify
companies as truck tyre specialists.

Usage:
    1. pip install requests pandas openpyxl python-dotenv
    2. Create a .env file next to this script with:
         GEMINI_API_KEY=your_key_here
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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

INPUT_FILE = '/tmp/company_list_simple.txt'
OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'truck_tyre_classification_full.xlsx')
CHECKPOINT_FILE = os.path.join(SCRIPT_DIR, 'classification_checkpoint.json')

# Rate limiting
CALLS_PER_MINUTE = 14  # Stay under Gemini free tier limit of 15/min
CALL_DELAY = 60.0 / CALLS_PER_MINUTE

# ─── Phase 1: Name-based pre-screening keywords ─────────────────────────────

TRUCK_TYRE_PATTERNS = [
    r'truck\s*tyre', r'truck\s*tire',
    r'commercial\s*tyre', r'commercial\s*tire',
    r'hgv\s*tyre', r'hgv\s*tire',
    r'fleet\s*tyre', r'fleet\s*tire',
    r'lorry\s*tyre', r'lorry\s*tire',
    r'truck\s*wheel',
]

TRUCK_INDICATORS = [
    'truck', 'hgv', 'lorry', 'fleet', 'trailer',
    'bus', 'coach', 'plant', 'industrial',
]

TYRE_WORDS = ['tyre', 'tire', 'tyres', 'tires', 'wheel']

AUTO_EXCLUDE_PATTERNS = [
    r'\bbicycle\b', r'\bcycle\b', r'\bmotorcycle\b', r'\bmotorbike\b',
    r'\bscooter\b', r'\bkart\b', r'\bkarting\b', r'\bracing\b',
    r'\bgolf\b', r'\bwheelchair\b', r'\bpushchair\b', r'\bpram\b',
    r'\baircraft\b', r'\baero\b', r'\baviation\b',
    r'\brecycl', r'\bretread', r'\bremould',
    r'\bpuncture\s*repair\b',
]


# ─── Phase 1: Classify by name ──────────────────────────────────────────────

def classify_by_name(name):
    """Returns (classification, confidence, method, reason) or None if needs research."""
    name_lower = name.lower()

    for pattern in AUTO_EXCLUDE_PATTERNS:
        if re.search(pattern, name_lower):
            return ('No', 'High', 'Name analysis',
                    f'Company name contains excluded keyword')

    for pattern in TRUCK_TYRE_PATTERNS:
        if re.search(pattern, name_lower):
            return ('Yes', 'High', 'Name analysis',
                    'Company name contains strong truck tyre indicator')

    has_truck = any(kw in name_lower for kw in TRUCK_INDICATORS)
    has_tyre = any(kw in name_lower for kw in TYRE_WORDS)

    if has_truck and has_tyre:
        return ('Yes', 'Medium', 'Name analysis',
                'Company name contains both truck/commercial and tyre keywords')

    if 'commercial' in name_lower and has_tyre:
        return ('Yes', 'Medium', 'Name analysis',
                'Company name contains "commercial" and tyre keyword')

    holding_patterns = [r'\bholdings?\b', r'\binvestment', r'\bcapital\b', r'\bventure']
    is_holding = any(re.search(p, name_lower) for p in holding_patterns)
    if is_holding and not has_tyre:
        return ('No', 'Medium', 'Name analysis',
                'Appears to be a holding/investment company with no tyre indication')

    return None


# ─── Phase 2: Gemini REST API + Google Search ────────────────────────────────

def classify_with_gemini(session, company_name, company_number, address=""):
    """
    Use Gemini REST API with Google Search grounding to research and classify.
    Returns (classification, confidence, what_was_checked, reason)
    """
    prompt = f"""You are classifying UK companies as truck tyre specialists.

DEFINITION: A truck tyre specialist generates more than 50% of its total turnover
from selling new tyres (including rims, complete wheels) and tyre-related services
for TRUCKS, HGVs, commercial vehicles, buses, coaches, trailers, and other
heavy/industrial vehicles — to private and corporate fleet end users.

COMPANY TO RESEARCH:
- Name: {company_name}
- Company Number: {company_number}
- Address: {address}

Search for this company online and classify it.

RESPOND WITH EXACTLY THIS JSON FORMAT (no other text):
{{
    "classification": "Yes" or "Maybe" or "No",
    "confidence": "High" or "Medium" or "Low",
    "what_was_checked": "Brief description of what you found online",
    "reason": "Why you classified them this way"
}}

GUIDELINES:
- "Yes" = clearly focuses on truck/commercial/HGV tyres
- "Maybe" = sells tyres and might include commercial, but unclear if >50% truck
- "No" = clearly a car tyre shop, manufacturer, wholesaler-only, or unrelated
- If you find their website showing truck/commercial tyre services = Yes
- If generic tyre shop with no truck focus = No
- If no info found online = classify based on company name, confidence=Low"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search_retrieval": {"dynamic_retrieval_config": {"mode": "MODE_DYNAMIC"}}}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 512}
    }

    for attempt in range(3):
        try:
            resp = session.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json=payload,
                timeout=30
            )

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
            candidates = data.get('candidates', [])
            if not candidates:
                return ('Maybe', 'Low', 'No response from Gemini', 'Empty candidates')

            text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            text = text.strip()

            # Extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return (
                    result.get('classification', 'Maybe'),
                    result.get('confidence', 'Low'),
                    result.get('what_was_checked', 'Gemini research'),
                    result.get('reason', 'See online research')
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
    if os.path.exists(INPUT_FILE):
        df = pd.read_csv(INPUT_FILE, sep='\t')
        logger.info(f"Loaded {len(df)} companies from {INPUT_FILE}")
        return df

    excel_file = os.path.join(SCRIPT_DIR, 'truck_tyre_specialists.xlsx')
    if os.path.exists(excel_file):
        df = pd.read_excel(excel_file)
        logger.info(f"Loaded {len(df)} companies from {excel_file}")
        return df

    raise FileNotFoundError(f"No company list found at {INPUT_FILE}")


def main():
    logger.info("=" * 60)
    logger.info("  TRUCK TYRE SPECIALIST CLASSIFIER")
    logger.info("  Using Gemini AI + Google Search")
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
    logger.info(f"Need online research: {len(needs_research)} companies")

    # Phase 2: Gemini API research
    if needs_research:
        logger.info(f"\n--- Phase 2: Gemini AI + Google Search ({len(needs_research)} companies) ---")
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in .env file")

        session = requests.Session()
        total = len(needs_research)

        for i, company in enumerate(needs_research):
            num = company['company_number']
            name = company['company_name']
            address = company.get('address', '')

            logger.info(f"[{i+1}/{total}] Researching: {name}")

            classification, confidence, what_checked, reason = classify_with_gemini(
                session, name, num, address
            )

            results[num] = {
                'company_number': num,
                'company_name': name,
                'classification': classification,
                'confidence': confidence,
                'method': 'Online research (Gemini + Google Search)',
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
    method_counts = result_df['method'].value_counts()

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
    logger.info(f"")
    logger.info(f"Method:")
    for method, count in method_counts.items():
        logger.info(f"  {method}: {count}")
    logger.info(f"\nExported to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
