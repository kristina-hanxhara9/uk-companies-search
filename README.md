# UK Companies House Search Tool

A web application to search UK companies from the Companies House API with advanced filtering and export capabilities.

## Features

- **Search by SIC Codes** - Filter by industry (700+ codes available)
- **Keyword Search** - Find companies with specific words in their name
- **Exclude Keywords** - Filter out unwanted results
- **Active Only Filter** - Show only active companies
- **Geographic Filter** - Exclude Northern Ireland
- **Export to CSV/Excel** - Download all results with full company data

## Quick Start

### Prerequisites

- **Python 3.8+** installed
- **Companies House API Key** (free from https://developer.company-information.service.gov.uk/)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/uk-companies-search.git
   cd uk-companies-search
   ```

2. **Install Python dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   Create a `.env` file in the root folder:
   ```
   COMPANIES_HOUSE_API_KEY=your_api_key_here
   CORS_ORIGINS=http://localhost:3000,http://localhost:9000,http://127.0.0.1:9000
   ```

4. **Start the backend server**
   ```bash
   cd backend
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

5. **Start the frontend server** (in a new terminal)
   ```bash
   cd frontend
   python3 -m http.server 9000
   ```

6. **Open in browser**
   ```
   http://localhost:9000
   ```

## Project Structure

```
uk-companies-search/
├── backend/
│   ├── app.py                    # FastAPI application
│   ├── config.py                 # Configuration settings
│   ├── requirements.txt          # Python dependencies
│   ├── services/
│   │   ├── companies_house.py    # Companies House API client
│   │   └── export_service.py     # CSV/Excel export
│   └── utils/
│       └── filters.py            # Keyword filtering utilities
├── frontend/
│   ├── index.html                # Main page
│   ├── css/
│   │   └── styles.css
│   └── js/
│       ├── app.js                # Main JavaScript logic
│       └── sic_codes.js          # SIC codes data
├── .env                          # Environment variables (create this)
├── .gitignore
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/search` | Search companies with filters |
| POST | `/api/export/csv` | Export results as CSV |
| POST | `/api/export/excel` | Export results as Excel |
| GET | `/api/sic-codes` | Get all SIC codes |
| GET | `/health` | Health check |

## Getting a Companies House API Key

1. Go to https://developer.company-information.service.gov.uk/
2. Create an account (free)
3. Register an application
4. Copy your API key
5. Add it to your `.env` file

## Usage

1. **Select SIC Codes** (optional) - Choose industry codes to filter by
2. **Enter Keywords** - Type keywords to search in company names (comma-separated)
3. **Enter Exclude Keywords** (optional) - Words to exclude from results
4. **Check Filters** - Active only, Exclude Northern Ireland
5. **Click Search** - Results appear in table below
6. **Export** - Click "Export CSV" or "Export Excel" to download

## Example Searches

- **Tyre manufacturers**: SIC code `22110` or keyword `tyre`
- **Vehicle repair**: SIC code `45200`
- **Truck companies**: Keyword `truck`, exclude `car`

## Tech Stack

- **Backend**: Python, FastAPI
- **Frontend**: HTML, CSS (Bootstrap 5), JavaScript
- **Table**: DataTables.js
- **API**: Companies House Public Data API

## Limitations

- Maximum 10,000 results per search (API limit)
- Rate limited to 600 requests per 5 minutes
- No phone numbers (Companies House doesn't store them)

## License

Data sourced from Companies House under Open Government Licence v3.0.
Commercial use is permitted with attribution.

## Support

For issues or questions, please open a GitHub issue.
