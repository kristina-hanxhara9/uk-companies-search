"""
Export service for CSV and Excel files
"""
import io
import csv
from typing import List, Dict, Any
import pandas as pd


def export_to_csv(companies: List[Dict[str, Any]]) -> io.BytesIO:
    """
    Export companies to CSV format.
    Returns a BytesIO object containing the CSV data.
    """
    if not companies:
        output = io.BytesIO()
        output.write(b"No data to export")
        output.seek(0)
        return output

    # Get headers from first company
    headers = list(companies[0].keys())

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(companies)

    # Convert to bytes
    bytes_output = io.BytesIO()
    bytes_output.write(output.getvalue().encode('utf-8-sig'))  # UTF-8 with BOM for Excel compatibility
    bytes_output.seek(0)

    return bytes_output


def export_to_excel(companies: List[Dict[str, Any]], sheet_name: str = "Companies") -> io.BytesIO:
    """
    Export companies to Excel format.
    Returns a BytesIO object containing the Excel data.
    """
    if not companies:
        output = io.BytesIO()
        df = pd.DataFrame({"Message": ["No data to export"]})
        df.to_excel(output, index=False, sheet_name=sheet_name)
        output.seek(0)
        return output

    df = pd.DataFrame(companies)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)

        # Auto-adjust column widths
        worksheet = writer.sheets[sheet_name]
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).map(len).max(),
                len(col)
            ) + 2
            # Cap at 50 characters
            max_length = min(max_length, 50)
            worksheet.column_dimensions[chr(65 + idx) if idx < 26 else 'A' + chr(65 + idx - 26)].width = max_length

    output.seek(0)
    return output
