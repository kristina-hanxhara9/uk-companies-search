"""
Claude AI Classification Service
Classifies companies into Shop Types and Channels using Claude API
"""

import anthropic
import json
import logging
from typing import Dict, List, Optional, Any
from ..config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)


class ClaudeClassifier:
    """Service for classifying companies using Claude AI"""

    def __init__(self):
        if not ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY not set - AI classification will not work")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def is_available(self) -> bool:
        """Check if Claude API is configured"""
        return self.client is not None

    def _build_company_context(self, company: Dict[str, Any]) -> str:
        """Build a text description of a company for Claude to analyze"""
        parts = [
            f"Company Name: {company.get('company_name', 'Unknown')}",
            f"Company Number: {company.get('company_number', 'Unknown')}",
            f"Company Type: {company.get('company_type', 'Unknown')}",
            f"Status: {company.get('company_status', 'Unknown')}",
            f"SIC Codes: {company.get('sic_codes', 'Unknown')}",
            f"SIC Descriptions: {company.get('sic_descriptions', 'Unknown')}",
            f"Address: {company.get('full_address', 'Unknown')}",
            f"Date Created: {company.get('date_of_creation', 'Unknown')}",
        ]

        # Add directors info if available
        if company.get('directors_count'):
            parts.append(f"Directors Count: {company.get('directors_count')}")
            parts.append(f"Directors: {company.get('directors_names', 'Unknown')}")

        # Add PSC info if available
        if company.get('psc_count'):
            parts.append(f"Owners Count: {company.get('psc_count')}")
            parts.append(f"Owners: {company.get('psc_names', 'Unknown')}")

        return "\n".join(parts)

    def classify_batch(
        self,
        companies: List[Dict[str, Any]],
        channel_definitions: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Classify a batch of companies for shop type and channel.

        Args:
            companies: List of company dictionaries
            channel_definitions: User-provided channel classification rules

        Returns:
            List of companies with added classification fields
        """
        if not self.is_available():
            logger.error("Claude API not available - returning companies without classification")
            # Return companies with empty classification fields
            for company in companies:
                company['shop_type'] = 'N/A (API not configured)'
                company['channel'] = 'N/A (API not configured)'
                company['ai_confidence'] = 0
            return companies

        classified_companies = []

        # Process in batches of 10 to reduce API calls
        batch_size = 10
        for i in range(0, len(companies), batch_size):
            batch = companies[i:i + batch_size]
            logger.info(f"Classifying batch {i//batch_size + 1} of {(len(companies) + batch_size - 1)//batch_size}")

            try:
                classified_batch = self._classify_batch_internal(batch, channel_definitions)
                classified_companies.extend(classified_batch)
            except Exception as e:
                logger.error(f"Error classifying batch: {e}")
                # On error, return companies with error indication
                for company in batch:
                    company['shop_type'] = 'Error'
                    company['channel'] = 'Error'
                    company['ai_confidence'] = 0
                classified_companies.extend(batch)

        return classified_companies

    def _classify_batch_internal(
        self,
        companies: List[Dict[str, Any]],
        channel_definitions: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Internal method to classify a small batch of companies"""

        # Build the company list for the prompt
        companies_text = ""
        for idx, company in enumerate(companies):
            companies_text += f"\n--- Company {idx + 1} ---\n"
            companies_text += self._build_company_context(company)
            companies_text += "\n"

        # Build the classification prompt
        prompt = self._build_classification_prompt(companies_text, channel_definitions, len(companies))

        # Call Claude API
        message = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse the response
        response_text = message.content[0].text
        classifications = self._parse_classification_response(response_text, len(companies))

        # Add classifications to companies
        for idx, company in enumerate(companies):
            if idx < len(classifications):
                company['shop_type'] = classifications[idx].get('shop_type', 'Unknown')
                company['channel'] = classifications[idx].get('channel', 'Unknown')
                company['ai_confidence'] = classifications[idx].get('confidence', 0.5)
            else:
                company['shop_type'] = 'Unknown'
                company['channel'] = 'Unknown'
                company['ai_confidence'] = 0

        return companies

    def _build_classification_prompt(
        self,
        companies_text: str,
        channel_definitions: Optional[str],
        num_companies: int
    ) -> str:
        """Build the prompt for Claude to classify companies"""

        channel_section = ""
        if channel_definitions:
            channel_section = f"""
## Channel Definitions (provided by user):
{channel_definitions}

Use these definitions to classify each company into the most appropriate channel.
If none of the definitions fit well, use "Other" as the channel.
"""
        else:
            channel_section = """
## Channel Classification:
Since no channel definitions were provided, classify based on the company's primary business activity
inferred from the company name and SIC codes. Use descriptive channel names like:
- "Tyre Specialist"
- "Auto Parts Retailer"
- "Garage/Workshop"
- "Fast Fit Centre"
- "Vehicle Dealer"
- "General Retail"
- "Other"
"""

        prompt = f"""You are a business analyst classifying UK companies. Analyze each company and classify it.

## Shop Type Classification:
Classify each company into ONE of these three categories:
1. **Chain** - Part of a larger retail/franchise network (e.g., Kwik Fit, Halfords, National Tyres)
2. **Independent** - Single location or small family-owned business
3. **Buying Group** - Member of a buying consortium (e.g., Point-S, Tyre-S, First Stop)

Indicators for classification:
- Chains: Well-known brand names, PLC companies, multiple locations implied
- Independents: Personal names in company name, LTD with simple names, local business indicators
- Buying Groups: May have consortium name in company name, or are known members

{channel_section}

## Companies to Classify:
{companies_text}

## Response Format:
Return a JSON array with exactly {num_companies} objects, one for each company in order.
Each object must have:
- "shop_type": "Chain" or "Independent" or "Buying Group"
- "channel": The channel classification
- "confidence": A number between 0.0 and 1.0 indicating your confidence

Example response:
```json
[
  {{"shop_type": "Independent", "channel": "Tyre Specialist", "confidence": 0.85}},
  {{"shop_type": "Chain", "channel": "Fast Fit Centre", "confidence": 0.95}}
]
```

Return ONLY the JSON array, no other text."""

        return prompt

    def _parse_classification_response(
        self,
        response_text: str,
        expected_count: int
    ) -> List[Dict[str, Any]]:
        """Parse Claude's response into classification dictionaries"""

        try:
            # Try to extract JSON from the response
            # Handle case where response might have markdown code blocks
            text = response_text.strip()
            if text.startswith("```"):
                # Remove markdown code blocks
                lines = text.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.startswith("```json"):
                        in_json = True
                        continue
                    elif line.startswith("```"):
                        in_json = False
                        continue
                    if in_json:
                        json_lines.append(line)
                text = "\n".join(json_lines)

            classifications = json.loads(text)

            if isinstance(classifications, list):
                return classifications
            else:
                logger.error(f"Unexpected response format: {type(classifications)}")
                return [{"shop_type": "Unknown", "channel": "Unknown", "confidence": 0}] * expected_count

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.error(f"Response was: {response_text[:500]}...")
            return [{"shop_type": "Unknown", "channel": "Unknown", "confidence": 0}] * expected_count


# Singleton instance
classifier = ClaudeClassifier()
