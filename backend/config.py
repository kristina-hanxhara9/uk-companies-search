import os
from dotenv import load_dotenv

load_dotenv()

# Companies House API
COMPANIES_HOUSE_API_KEY = os.getenv("COMPANIES_HOUSE_API_KEY", "48d17266-ff2e-425f-9b20-7dcc9b25bb79")
COMPANIES_HOUSE_BASE_URL = "https://api.company-information.service.gov.uk"

# API Settings
ITEMS_PER_PAGE = 500
RATE_LIMIT_DELAY = 0.2  # seconds between requests
RATE_LIMIT_BACKOFF = 60  # seconds to wait on 429

# CORS - allow all origins in production (frontend served from same domain)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"]
