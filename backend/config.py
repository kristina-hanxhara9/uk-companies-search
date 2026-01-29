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

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080").split(",")
