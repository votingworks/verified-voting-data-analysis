#!/usr/bin/env python3
"""Extract all zip files from data/raw/verifier-zips to data/extracted directory."""

import csv
import io
import zipfile
from pathlib import Path


def clean_jurisdictions_csv(content):
    """
    Clean jurisdiction CSV by filtering out invalid rows.

    Removes rows that have empty Registered Voters AND empty Election Day Marking Method,
    which are typically duplicate entries with typo FIPS codes.

    Args:
        content: Raw CSV file content (bytes)

    Returns:
        tuple: (cleaned content as bytes, number of rows removed)
    """
    # Decode content
    text = content.decode('utf-8-sig')
    lines = text.split('\n')

    if len(lines) < 3:
        return content, 0

    # First line is title, second is header
    title_line = lines[0]
    header_line = lines[1]

    # Parse header to find column indices
    reader = csv.reader([header_line])
    headers = next(reader)

    try:
        reg_voters_idx = headers.index('Registered Voters')
        marking_method_idx = headers.index('Election Day Marking Method')
    except ValueError:
        # Headers not found, return original content
        return content, 0

    # Filter data rows
    cleaned_lines = [title_line, header_line]
    removed = 0

    for line in lines[2:]:
        if not line.strip():
            continue

        # Parse the row
        row_reader = csv.reader([line])
        try:
            row = next(row_reader)
        except StopIteration:
            continue

        # Check if row has empty registered voters AND empty marking method
        if len(row) > max(reg_voters_idx, marking_method_idx):
            reg_voters = row[reg_voters_idx].strip()
            marking_method = row[marking_method_idx].strip()

            if not reg_voters and not marking_method:
                removed += 1
                continue

        cleaned_lines.append(line)

    # Reconstruct content
    cleaned_text = '\n'.join(cleaned_lines)
    return cleaned_text.encode('utf-8'), removed


def extract_all_zips():
    downloads_dir = Path("data/raw/verifier-zips")
    extract_to_dir = Path("data/extracted")

    # Ensure extraction directory exists
    extract_to_dir.mkdir(parents=True, exist_ok=True)

    # Find all zip files
    zip_files = list(downloads_dir.glob("*.zip"))

    if not zip_files:
        print("No zip files found in data/raw/verifier-zips/")
        return

    print(f"Found {len(zip_files)} zip file(s) to extract")

    total_removed = 0

    # Extract each zip file with year prefix
    for zip_path in zip_files:
        # Extract year from filename (e.g., "2006" from "2006_Verifier_Data_2025-12-07.zip")
        year = zip_path.stem.split('_')[0]
        print(f"\nExtracting {zip_path.name} (year: {year})...")

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_info in zip_ref.namelist():
                    # Read the file content
                    file_content = zip_ref.read(file_info)

                    # Create new filename with year prefix
                    original_name = Path(file_info).name
                    new_filename = f"{year}_{original_name}"
                    output_path = extract_to_dir / new_filename

                    # Clean jurisdiction files
                    if 'jurisdictions' in original_name.lower():
                        file_content, removed = clean_jurisdictions_csv(file_content)
                        if removed > 0:
                            print(f"    Removed {removed} invalid row(s)")
                            total_removed += removed

                    # Write the file with new name
                    output_path.write_bytes(file_content)
                    print(f"  ✓ Extracted as {new_filename}")

        except Exception as e:
            print(f"  ✗ Error extracting {zip_path.name}: {e}")

    if total_removed > 0:
        print(f"\n  Total invalid rows removed: {total_removed}")

    print("\n✓ All zip files processed!")

if __name__ == "__main__":
    extract_all_zips()
