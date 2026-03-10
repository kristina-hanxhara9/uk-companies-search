"""
UK Companies House Search API - FastAPI Application
"""
import os
import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import CORS_ORIGINS
from services.companies_house import CompaniesHouseAPI, get_all_sic_codes
from services.export_service import export_to_csv, export_to_excel
from utils.filters import (
    filter_by_include_keywords,
    filter_by_exclude_keywords,
    filter_exclude_northern_ireland,
    filter_active_only,
    deduplicate_companies
)
from utils.classification import enrich_with_classification
from utils.recall import compare_with_known_list

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="UK Companies House Search",
    description="Search and export UK company data from Companies House",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize API client
api_client = CompaniesHouseAPI()


# Request/Response models
class SearchRequest(BaseModel):
    sic_codes: Optional[List[str]] = None  # Now optional!
    include_keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    active_only: bool = True
    exclude_northern_ireland: bool = True
    include_people: bool = False  # Include directors & owners data (slower)


class ExportRequest(BaseModel):
    companies: List[dict]
    columns: Optional[List[str]] = None
    column_names: Optional[dict] = None


class RecallCompareRequest(BaseModel):
    known_companies: List[dict]
    search_results: List[dict]


# Store results in memory for export (in production, use Redis or similar)
search_results_cache = {}


@app.get("/api")
async def api_root():
    """API info endpoint"""
    return {"message": "UK Companies House Search API", "version": "1.0.0"}


@app.get("/api/sic-codes")
async def get_sic_codes():
    """Get all available SIC codes for the dropdown"""
    return get_all_sic_codes()


@app.post("/api/search")
async def search_companies(request: SearchRequest):
    """
    Search companies by SIC codes and/or keywords.
    - If SIC codes provided: search by SIC codes, then filter by keywords
    - If only keywords provided: search directly by company name
    """
    logger.info(f"Search request - SIC codes: {request.sic_codes}, Include keywords: {request.include_keywords}")

    # Validate: need either SIC codes or include keywords
    has_sic_codes = request.sic_codes and len(request.sic_codes) > 0
    has_include_keywords = request.include_keywords and len(request.include_keywords) > 0

    if not has_sic_codes and not has_include_keywords:
        raise HTTPException(
            status_code=400,
            detail="Please provide at least one SIC code OR one include keyword"
        )

    try:
        companies = []
        # Accumulate search metadata across multiple queries
        accumulated_hits = 0
        accumulated_retrieved = 0
        accumulated_limit_hit = False
        accumulated_queries = []

        if has_sic_codes:
            if has_include_keywords:
                # SIC codes + include keywords: search each keyword at the API level
                # This is MUCH faster than fetching all SIC results then filtering locally
                all_companies = []
                seen_company_numbers = set()

                for keyword in request.include_keywords:
                    keyword_results = api_client.search_by_sic_codes(
                        sic_codes=request.sic_codes,
                        active_only=request.active_only,
                        company_name_includes=keyword
                    )
                    meta = api_client.last_search_metadata
                    accumulated_hits += meta.get('total_api_hits', 0)
                    accumulated_retrieved += meta.get('companies_retrieved', 0)
                    accumulated_limit_hit = accumulated_limit_hit or meta.get('hit_api_limit', False)
                    accumulated_queries.extend(meta.get('queries_run', []))

                    for company in keyword_results:
                        company_num = company.get('company_number')
                        if company_num and company_num not in seen_company_numbers:
                            seen_company_numbers.add(company_num)
                            all_companies.append(company)

                companies = all_companies
                logger.info(f"Found {len(companies)} companies from SIC + keyword search")
            else:
                # SIC codes only (no keywords) - fetch all companies for these SIC codes
                companies = api_client.search_by_sic_codes(
                    sic_codes=request.sic_codes,
                    active_only=request.active_only
                )
                meta = api_client.last_search_metadata
                accumulated_hits = meta.get('total_api_hits', 0)
                accumulated_retrieved = meta.get('companies_retrieved', 0)
                accumulated_limit_hit = meta.get('hit_api_limit', False)
                accumulated_queries = meta.get('queries_run', [])
                logger.info(f"Found {len(companies)} companies from SIC code search")
        else:
            # No SIC codes - search by each keyword directly
            all_companies = []
            seen_company_numbers = set()

            for keyword in request.include_keywords:
                keyword_results = api_client.search_by_company_name(
                    search_term=keyword,
                    active_only=request.active_only
                )
                meta = api_client.last_search_metadata
                accumulated_hits += meta.get('total_api_hits', 0)
                accumulated_retrieved += meta.get('companies_retrieved', 0)
                accumulated_limit_hit = accumulated_limit_hit or meta.get('hit_api_limit', False)
                accumulated_queries.extend(meta.get('queries_run', []))

                # Deduplicate across keywords
                for company in keyword_results:
                    company_num = company.get('company_number')
                    if company_num and company_num not in seen_company_numbers:
                        seen_company_numbers.add(company_num)
                        all_companies.append(company)

            companies = all_companies
            logger.info(f"Found {len(companies)} companies from keyword search")
            # Note: company_name_includes API parameter already filters by name,
            # so no additional keyword filtering needed here

        # Apply filters
        if request.exclude_northern_ireland:
            companies = filter_exclude_northern_ireland(companies)
            logger.info(f"After NI filter: {len(companies)} companies")

        if request.exclude_keywords:
            companies = filter_by_exclude_keywords(companies, request.exclude_keywords)
            logger.info(f"After exclude filter: {len(companies)} companies")

        # Deduplicate
        companies = deduplicate_companies(companies)
        logger.info(f"Final count: {len(companies)} companies")

        # Enrich with people data if requested
        if request.include_people and companies:
            logger.info(f"Enriching {len(companies)} companies with officers/PSC data...")
            companies = api_client.enrich_with_people_data(companies)
            logger.info("Enrichment complete")
        elif companies:
            # Even without people data, fetch accounts type for classification
            logger.info(f"Fetching accounts type for {len(companies)} companies...")
            companies = api_client.enrich_with_accounts_type(companies)
            logger.info("Accounts type enrichment complete")

        # Add business size classification and chain detection
        companies = enrich_with_classification(companies)

        return {
            "count": len(companies),
            "companies": companies,
            "search_metadata": {
                "total_api_hits": accumulated_hits,
                "companies_retrieved": accumulated_retrieved,
                "hit_api_limit": accumulated_limit_hit,
                "queries_run": accumulated_queries,
            }
        }

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export/csv")
async def export_csv(request: ExportRequest):
    """Export companies to CSV"""
    if not request.companies:
        raise HTTPException(status_code=400, detail="No companies to export")

    csv_data = export_to_csv(
        request.companies,
        columns=request.columns,
        column_names=request.column_names
    )

    return StreamingResponse(
        csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=uk_companies.csv"
        }
    )


@app.post("/api/export/excel")
async def export_excel(request: ExportRequest):
    """Export companies to Excel"""
    if not request.companies:
        raise HTTPException(status_code=400, detail="No companies to export")

    excel_data = export_to_excel(
        request.companies,
        columns=request.columns,
        column_names=request.column_names
    )

    return StreamingResponse(
        excel_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=uk_companies.xlsx"
        }
    )


@app.post("/api/recall/compare")
async def recall_compare(request: RecallCompareRequest):
    """Compare search results against a known list of companies to measure recall."""
    if not request.known_companies:
        raise HTTPException(status_code=400, detail="No known companies provided")

    result = compare_with_known_list(request.search_results, request.known_companies)
    return result


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Serve static frontend files in production
# Get the absolute path to frontend folder (works both locally and on Railway)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_path = os.path.join(BASE_DIR, 'frontend')

logger.info(f"Looking for frontend at: {frontend_path}")
logger.info(f"Frontend exists: {os.path.exists(frontend_path)}")

if os.path.exists(frontend_path):
    # Serve static files (CSS, JS)
    css_path = os.path.join(frontend_path, "css")
    js_path = os.path.join(frontend_path, "js")

    if os.path.exists(css_path):
        app.mount("/css", StaticFiles(directory=css_path), name="css")
    if os.path.exists(js_path):
        app.mount("/js", StaticFiles(directory=js_path), name="js")


# Serve index.html for root path
@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the frontend HTML"""
    index_path = os.path.join(BASE_DIR, 'frontend', 'index.html')
    logger.info(f"Serving frontend from: {index_path}, exists: {os.path.exists(index_path)}")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    # Fallback: return API info
    return {"message": "UK Companies House Search API", "version": "1.0.0", "frontend_path": index_path}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
