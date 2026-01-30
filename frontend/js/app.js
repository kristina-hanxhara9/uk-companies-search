/**
 * UK Companies House Search - Main Application
 */

// API Base URL - change this for production
const API_BASE_URL = 'http://localhost:8000';

// Store search results for export
let currentResults = [];

// DataTable instance
let dataTable = null;

/**
 * Initialize the application
 */
$(document).ready(function() {
    initializeSicCodeSelect();
    initializeEventHandlers();
});

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

    const searchData = {
        sic_codes: sicCodes.length > 0 ? sicCodes : null,
        include_keywords: includeKeywords.length > 0 ? includeKeywords : null,
        exclude_keywords: excludeKeywords.length > 0 ? excludeKeywords : null,
        active_only: $('#activeOnly').is(':checked'),
        exclude_northern_ireland: $('#excludeNI').is(':checked')
    };

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
    }

    // Clear existing data
    $('#companiesTable tbody').empty();

    // Prepare table data
    const tableData = data.companies.map(company => [
        company.company_number,
        company.company_name,
        formatStatus(company.company_status),
        company.company_type || '',
        company.date_of_creation || '',
        company.sic_codes || '',
        company.sic_descriptions || '',
        company.full_address || '',
        company.postal_code || '',
        company.region || ''
    ]);

    // Initialize DataTable
    dataTable = $('#companiesTable').DataTable({
        data: tableData,
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
        order: [[1, 'asc']],
        scrollX: true,
        columnDefs: [
            { targets: [6, 7], className: 'truncate-text' }
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
 * Export results to CSV or Excel
 */
async function exportResults(format) {
    if (!currentResults || currentResults.length === 0) {
        alert('No results to export');
        return;
    }

    const endpoint = format === 'csv' ? '/api/export/csv' : '/api/export/excel';
    const filename = format === 'csv' ? 'uk_companies.csv' : 'uk_companies.xlsx';

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ companies: currentResults })
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
