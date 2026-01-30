"""
Export service for CSV and Excel files
"""
import io
import csv
from typing import List, Dict, Any, Optional
import pandas as pd
from openpyxl.utils import get_column_letter


def export_to_csv(
    companies: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    column_names: Optional[Dict[str, str]] = None
) -> io.BytesIO:
    """
    Export companies to CSV format.
    Returns a BytesIO object containing the CSV data.

    Args:
        companies: List of company dictionaries
        columns: Optional list of columns to include (in order)
        column_names: Optional dict mapping column keys to display names
    """
    if not companies:
        output = io.BytesIO()
        output.write(b"No data to export")
        output.seek(0)
        return output

    # Use specified columns or all columns from first company
    if columns:
        headers = columns
    else:
        headers = list(companies[0].keys())

    # Get display names for headers
    display_headers = [column_names.get(h, h) if column_names else h for h in headers]

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header with display names
    writer.writerow(display_headers)

    # Write data rows
    for company in companies:
        row = [company.get(col, '') for col in headers]
        writer.writerow(row)

    # Convert to bytes
    bytes_output = io.BytesIO()
    bytes_output.write(output.getvalue().encode('utf-8-sig'))  # UTF-8 with BOM for Excel compatibility
    bytes_output.seek(0)

    return bytes_output


def export_to_excel(
    companies: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    column_names: Optional[Dict[str, str]] = None,
    sheet_name: str = "Companies"
) -> io.BytesIO:
    """
    Export companies to Excel format.
    Returns a BytesIO object containing the Excel data.

    Args:
        companies: List of company dictionaries
        columns: Optional list of columns to include (in order)
        column_names: Optional dict mapping column keys to display names
        sheet_name: Name of the Excel sheet
    """
    if not companies:
        output = io.BytesIO()
        df = pd.DataFrame({"Message": ["No data to export"]})
        df.to_excel(output, index=False, sheet_name=sheet_name)
        output.seek(0)
        return output

    # Use specified columns or all columns
    if columns:
        # Create DataFrame with only specified columns
        data = [{col: company.get(col, '') for col in columns} for company in companies]
        df = pd.DataFrame(data, columns=columns)
    else:
        df = pd.DataFrame(companies)

    # Rename columns to display names if provided
    if column_names:
        df = df.rename(columns=column_names)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)

        # Auto-adjust column widths
        worksheet = writer.sheets[sheet_name]
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).map(len).max(),
                len(str(col))
            ) + 2
            # Cap at 50 characters
            max_length = min(max_length, 50)
            worksheet.column_dimensions[get_column_letter(idx + 1)].width = max_length

    output.seek(0)
    return output
