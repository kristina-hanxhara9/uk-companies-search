/**
 * UK Companies House Search - Main Application
 */

// API Base URL - automatically detects local vs production
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : window.location.origin;  // Uses same domain in production

// Store search results for export
let currentResults = [];

// DataTable instance
let dataTable = null;

// All available columns with their display names
const ALL_COLUMNS = {
    'company_number': 'Company Number',
    'company_name': 'Company Name',
    'company_status': 'Status',
    'company_type': 'Type',
    'date_of_creation': 'Date Created',
    'date_of_cessation': 'Date Ceased',
    'jurisdiction': 'Jurisdiction',
    'sic_codes': 'SIC Codes',
    'sic_descriptions': 'SIC Descriptions',
    'full_address': 'Full Address',
    'address_line_1': 'Address Line 1',
    'address_line_2': 'Address Line 2',
    'locality': 'City/Town',
    'region': 'Region',
    'postal_code': 'Postcode',
    'country': 'Country',
    'accounts_overdue': 'Accounts Overdue',
    'last_accounts_date': 'Last Accounts Date',
    'last_accounts_type': 'Accounts Type',
    'next_accounts_due': 'Next Accounts Due',
    'next_accounts_overdue': 'Next Accounts Overdue',
    'confirmation_statement_last': 'Last Confirmation',
    'confirmation_statement_next_due': 'Next Confirmation Due',
    'confirmation_statement_overdue': 'Confirmation Overdue',
    'has_charges': 'Has Charges',
    'has_insolvency_history': 'Insolvency History',
    'has_been_liquidated': 'Been Liquidated',
    'is_community_interest_company': 'CIC',
    'registered_office_in_dispute': 'Address Disputed',
    'undeliverable_address': 'Undeliverable Address',
    'previous_names': 'Previous Names',
    'companies_house_url': 'Companies House URL',
    // Directors & Owners columns
    'directors_count': 'Directors Count',
    'directors_names': 'Directors Names',
    'psc_count': 'Owners Count',
    'psc_names': 'Owners Names',
    'psc_control': 'Control Type',
    // Classification columns
    'size_category': 'Business Size',
    'ownership_type': 'Ownership Type',
};

/**
 * Initialize the application
 */
$(document).ready(function() {
    initializeSicCodeSelect();
    initializeEventHandlers();
    initializeTooltips();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (el) {
        return new bootstrap.Tooltip(el);
    });
}

/**
 * Initialize Select2 for SIC codes dropdown
 */
function initializeSicCodeSelect() {
    const sicOptions = SIC_CODES.map(sic => ({
        id: sic.code,
        text: `${sic.code} - ${sic.description}`
    }));

    $('#sicCodes').select2({
        theme: 'bootstrap-5',
        placeholder: 'Search and select SIC codes...',
        allowClear: true,
        data: sicOptions,
        tags: true,  // Allow custom codes
        createTag: function(params) {
            const term = $.trim(params.term);
            if (term === '' || !/^\d{5}$/.test(term)) {
                return null;
            }
            return {
                id: term,
                text: term + ' (Custom)',
                newTag: true
            };
        }
    });
}

/**
 * Initialize event handlers
 */
function initializeEventHandlers() {
    // Search form submission
    $('#searchForm').on('submit', function(e) {
        e.preventDefault();
        performSearch();
    });

    // Export buttons
    $('#exportCsvBtn').on('click', function() {
        exportResults('csv');
    });

    $('#exportExcelBtn').on('click', function() {
        exportResults('excel');
    });

    // Column selector buttons
    $('#selectAllCols').on('click', function() {
        $('.column-checkbox').prop('checked', true);
        // Only check people columns if includePeople is checked
        if (!$('#includePeople').is(':checked')) {
            $('.people-column').prop('checked', false);
        }
    });

    $('#deselectAllCols').on('click', function() {
        $('.column-checkbox').prop('checked', false);
        // Keep essential columns checked
        $('#col_company_number, #col_company_name').prop('checked', true);
    });

    // Toggle people columns based on includePeople checkbox
    $('#includePeople').on('change', function() {
        const isChecked = $(this).is(':checked');
        $('.people-column').prop('disabled', !isChecked);
        if (isChecked) {
            // Auto-select the people columns when enabled
            $('.people-column').prop('checked', true);
        } else {
            // Uncheck and disable when turned off
            $('.people-column').prop('checked', false);
        }
    });

    // Initialize people columns state
    $('.people-column').prop('disabled', !$('#includePeople').is(':checked'));

}

/**
 * Get selected columns
 */
function getSelectedColumns() {
    const selected = [];
    $('.column-checkbox:checked').each(function() {
        selected.push($(this).data('column'));
    });
    return selected.length > 0 ? selected : ['company_number', 'company_name']; // Minimum columns
}

/**
 * Parse comma-separated keywords input
 */
function parseKeywords(input) {
    if (!input || input.trim() === '') {
        return [];
    }
    return input.split(',')
        .map(k => k.trim())
        .filter(k => k.length > 0);
}

/**
 * Perform the search
 */
async function performSearch() {
    const sicCodes = $('#sicCodes').val() || [];
    const includeKeywords = parseKeywords($('#includeKeywords').val());
    const excludeKeywords = parseKeywords($('#excludeKeywords').val());

    // Validate: need either SIC codes or include keywords
    if (sicCodes.length === 0 && includeKeywords.length === 0) {
        alert('Please select at least one SIC code OR enter at least one include keyword');
        return;
    }

    const includePeople = $('#includePeople').is(':checked');

    const searchData = {
        sic_codes: sicCodes.length > 0 ? sicCodes : null,
        include_keywords: includeKeywords.length > 0 ? includeKeywords : null,
        exclude_keywords: excludeKeywords.length > 0 ? excludeKeywords : null,
        active_only: $('#activeOnly').is(':checked'),
        exclude_northern_ireland: $('#excludeNI').is(':checked'),
        include_people: includePeople
    };

    // Update loading text based on options
    if (includePeople) {
        $('#loadingText').text('Searching and fetching directors/owners data...');
    } else {
        $('#loadingText').text('Searching Companies House API...');
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE_URL}/api/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(searchData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Search failed');
        }

        const data = await response.json();

        currentResults = data.companies;
        displayResults(data);

    } catch (error) {
        console.error('Search error:', error);
        alert('Search failed: ' + error.message);
    } finally {
        hideLoading();
    }
}

/**
 * Display search results
 */
function displayResults(data) {
    $('#resultCount').text(data.count);
    $('#resultsSection').removeClass('d-none');

    // Destroy existing DataTable
    if (dataTable) {
        dataTable.destroy();
        $('#companiesTable').empty();
    }

    // Get selected columns
    const selectedColumns = getSelectedColumns();

    // Build table header
    let headerHtml = '<thead><tr>';
    selectedColumns.forEach(col => {
        headerHtml += `<th>${ALL_COLUMNS[col] || col}</th>`;
    });
    headerHtml += '</tr></thead><tbody></tbody>';
    $('#companiesTable').html(headerHtml);

    // Show search completeness info
    if (data.search_metadata) {
        const meta = data.search_metadata;
        let cls = meta.hit_api_limit ? 'alert-warning' : 'alert-info';
        let html = `<div class="alert ${cls} py-2 px-3 mb-2 small">`;
        html += `<strong>Search Completeness:</strong> `;
        html += `Retrieved ${meta.companies_retrieved.toLocaleString()} of ${meta.total_api_hits.toLocaleString()} API matches`;
        if (meta.hit_api_limit) {
            html += ` <span class="badge bg-warning text-dark ms-1">API limit reached (10,000)</span>`;
            html += `<br><small>Some results may be missing. Try narrowing your search with more specific keywords.</small>`;
        }
        html += `</div>`;
        $('#searchCompleteness').html(html);
    } else {
        $('#searchCompleteness').empty();
    }

    // Prepare table data based on selected columns
    const tableData = data.companies.map(company => {
        return selectedColumns.map(col => {
            let value = company[col] || '';
            // Special formatting for status
            if (col === 'company_status') {
                return formatStatus(value);
            }
            if (col === 'size_category') {
                return formatSizeCategory(value);
            }
            if (col === 'ownership_type') {
                return formatOwnershipType(value);
            }
            // Make URL clickable
            if (col === 'companies_house_url' && value) {
                return `<a href="${value}" target="_blank">View</a>`;
            }
            return value;
        });
    });

    // Find columns that need truncation (long text fields)
    const truncateCols = [];
    selectedColumns.forEach((col, idx) => {
        if (['full_address', 'sic_descriptions', 'previous_names', 'directors_names', 'psc_names', 'psc_control'].includes(col)) {
            truncateCols.push(idx);
        }
    });

    // Initialize DataTable
    dataTable = $('#companiesTable').DataTable({
        data: tableData,
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
        order: [[1, 'asc']],
        scrollX: true,
        columnDefs: [
            { targets: truncateCols, className: 'truncate-text' }
        ],
        language: {
            search: "Filter results:",
            lengthMenu: "Show _MENU_ companies",
            info: "Showing _START_ to _END_ of _TOTAL_ companies",
            infoEmpty: "No companies found",
            infoFiltered: "(filtered from _MAX_ total)"
        }
    });

    // Scroll to results
    $('html, body').animate({
        scrollTop: $('#resultsSection').offset().top - 20
    }, 500);
}

/**
 * Format company status with colors
 */
function formatStatus(status) {
    if (!status) return '';

    const statusLower = status.toLowerCase();
    let className = '';

    if (statusLower === 'active') {
        className = 'status-active';
    } else if (statusLower === 'dissolved') {
        className = 'status-dissolved';
    } else if (statusLower.includes('liquidation')) {
        className = 'status-liquidation';
    }

    return `<span class="${className}">${status}</span>`;
}

/**
 * Format business size category with colored badge
 */
function formatSizeCategory(value) {
    if (!value) return '';
    const classMap = {
        'micro': 'size-micro',
        'small': 'size-small',
        'medium': 'size-medium',
        'large': 'size-large',
        'large (group)': 'size-large',
        'subsidiary': 'size-subsidiary',
        'dormant': 'size-dormant',
        'new': 'size-dormant',
        'unknown': 'size-unknown',
    };
    const cls = classMap[value.toLowerCase()] || 'size-unknown';
    return `<span class="${cls}">${value}</span>`;
}

/**
 * Format ownership type with colored badge
 */
function formatOwnershipType(value) {
    if (!value) return '';
    const classMap = {
        'chain': 'ownership-chain',
        'independent': 'ownership-independent',
        'buying group': 'ownership-buying-group',
        'unknown': 'ownership-unknown',
    };
    const cls = classMap[value.toLowerCase()] || 'ownership-unknown';
    return `<span class="${cls}">${value}</span>`;
}

/**
 * Export results to CSV or Excel
 */
async function exportResults(format) {
    if (!currentResults || currentResults.length === 0) {
        alert('No results to export');
        return;
    }

    const endpoint = format === 'csv' ? '/api/export/csv' : '/api/export/excel';
    const filename = format === 'csv' ? 'uk_companies.csv' : 'uk_companies.xlsx';
    const selectedColumns = getSelectedColumns();

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                companies: currentResults,
                columns: selectedColumns,
                column_names: selectedColumns.reduce((acc, col) => {
                    acc[col] = ALL_COLUMNS[col] || col;
                    return acc;
                }, {})
            })
        });

        if (!response.ok) {
            throw new Error('Export failed');
        }

        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

    } catch (error) {
        console.error('Export error:', error);
        alert('Export failed: ' + error.message);
    }
}

/**
 * Show loading overlay
 */
function showLoading() {
    $('#loadingOverlay').removeClass('d-none');
    $('#searchBtn').prop('disabled', true);
    $('#searchSpinner').removeClass('d-none');
    $('#searchBtnText').text('Searching...');
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    $('#loadingOverlay').addClass('d-none');
    $('#searchBtn').prop('disabled', false);
    $('#searchSpinner').addClass('d-none');
    $('#searchBtnText').text('Search Companies');
}

/**
 * Parse a CSV file containing known company numbers
 */
function parseKnownListCSV(text) {
    const lines = text.trim().split('\n');
    const companies = [];
    const header = lines[0].toLowerCase();
    const startIdx = header.includes('company') ? 1 : 0;
    for (let i = startIdx; i < lines.length; i++) {
        const parts = lines[i].split(',');
        const companyNumber = parts[0].trim().replace(/"/g, '');
        if (companyNumber) {
            companies.push({
                company_number: companyNumber,
                company_name: parts.length > 1 ? parts[1].trim().replace(/"/g, '') : ''
            });
        }
    }
    return companies;
}

/**
 * Display recall comparison results
 */
function displayRecallResults(data) {
    let html = `
        <div class="row text-center g-2 mt-2">
            <div class="col-6 col-md-3">
                <div class="card h-100"><div class="card-body py-2">
                    <h4 class="mb-0">${(data.recall * 100).toFixed(1)}%</h4>
                    <small class="text-muted">Recall</small>
                </div></div>
            </div>
            <div class="col-6 col-md-3">
                <div class="card h-100"><div class="card-body py-2">
                    <h4 class="mb-0">${data.true_positives}</h4>
                    <small class="text-muted">Found from known list</small>
                </div></div>
            </div>
            <div class="col-6 col-md-3">
                <div class="card h-100"><div class="card-body py-2">
                    <h4 class="mb-0 text-danger">${data.false_negatives}</h4>
                    <small class="text-muted">Missed</small>
                </div></div>
            </div>
            <div class="col-6 col-md-3">
                <div class="card h-100"><div class="card-body py-2">
                    <h4 class="mb-0 text-success">${data.additional_found}</h4>
                    <small class="text-muted">Additional found</small>
                </div></div>
            </div>
        </div>`;

    if (data.missed_companies && data.missed_companies.length > 0) {
        html += `<details class="mt-2"><summary class="small fw-bold">Missed Companies (${data.missed_companies.length})</summary><ul class="small mt-1">`;
        data.missed_companies.forEach(c => {
            html += `<li>${c.company_number}${c.company_name ? ' - ' + c.company_name : ''}</li>`;
        });
        html += `</ul></details>`;
    }

    $('#recallResults').html(html);
}

// Initialize recall comparison handler
$(document).ready(function() {
    $(document).on('click', '#compareRecallBtn', async function() {
        const fileInput = document.getElementById('knownListFile');
        if (!fileInput || !fileInput.files[0]) {
            alert('Please select a CSV file with known company numbers');
            return;
        }
        if (!currentResults || currentResults.length === 0) {
            alert('Please run a search first');
            return;
        }

        const text = await fileInput.files[0].text();
        const knownCompanies = parseKnownListCSV(text);

        if (knownCompanies.length === 0) {
            alert('No company numbers found in the file');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/recall/compare`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    known_companies: knownCompanies,
                    search_results: currentResults
                })
            });

            if (!response.ok) {
                throw new Error('Recall comparison failed');
            }

            const result = await response.json();
            displayRecallResults(result);
        } catch (error) {
            console.error('Recall comparison error:', error);
            alert('Recall comparison failed: ' + error.message);
        }
    });
});
