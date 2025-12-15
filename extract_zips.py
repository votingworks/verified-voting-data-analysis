#!/usr/bin/env python3
"""Extract all zip files from data/downloads to data/verifier-original directory."""

import os
import zipfile
from pathlib import Path

def extract_all_zips():
    downloads_dir = Path("data/downloads")
    extract_to_dir = Path("data/verifier-original")

    # Ensure extraction directory exists
    extract_to_dir.mkdir(parents=True, exist_ok=True)

    # Find all zip files
    zip_files = list(downloads_dir.glob("*.zip"))

    if not zip_files:
        print("No zip files found in data/downloads/")
        return

    print(f"Found {len(zip_files)} zip file(s) to extract")

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

                    # Write the file with new name
                    output_path.write_bytes(file_content)
                    print(f"  ✓ Extracted as {new_filename}")

        except Exception as e:
            print(f"  ✗ Error extracting {zip_path.name}: {e}")

    print("\n✓ All zip files processed!")

if __name__ == "__main__":
    extract_all_zips()
