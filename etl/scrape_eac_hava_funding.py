#!/usr/bin/env python3
"""
Scrape HAVA funding data from EAC website.

Reads downloaded HTML from data/raw/eac_funding_levels.html
and extracts funding information by state, year, and grant type.

Generates: data/processed/hava_funding.csv
"""

from pathlib import Path
from bs4 import BeautifulSoup
import csv
import re

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / 'data'
RAW_DIR = DATA_DIR / 'raw'
HTML_FILE = RAW_DIR / 'eac_funding_levels.html'
OUTPUT_FILE = DATA_DIR / 'processed' / 'hava_funding.csv'


def clean_currency(value):
    """
    Convert currency string to clean numeric string.

    Examples:
        "$4,989,605 " -> "4989605"
        "&nbsp;" -> "0"
        "-" -> "0"
        "" -> "0"
    """
    if not value or value.strip() in ['&nbsp;', '', '-']:
        return '0'

    # Remove $, commas, spaces, and any HTML entities
    cleaned = re.sub(r'[$,\s&nbsp;]', '', value)

    # If after cleaning we get an empty string or dash, return 0
    if cleaned in ['', '-']:
        return '0'

    return cleaned


def split_year_grant(year_grant):
    """
    Split "Year/Grant" column into separate Year and Grant components.

    Examples:
        "2003 101" -> ("2003", "101")
        "2018 Election Security" -> ("2018", "Election Security")
        "2020 CARES" -> ("2020", "CARES")
    """
    parts = year_grant.strip().split(maxsplit=1)

    if len(parts) == 2:
        return parts[0], parts[1]
    elif len(parts) == 1:
        # Edge case: only year provided
        return parts[0], ''
    else:
        return '', ''


def parse_html():
    """
    Parse the downloaded HTML file and extract funding data.

    Returns:
        list of dicts: Each dict has keys: State, Year, Grant, Federal_Funding, Required_State_Match
    """
    print(f"Reading HTML from {HTML_FILE}...")

    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all state sections (views-row divs containing h2 tags)
    state_sections = soup.find_all('div', class_='views-row')

    data = []

    for section in state_sections:
        # Find the state name (h2 tag)
        h2 = section.find('h2')

        if not h2:
            continue

        state = h2.get_text(strip=True)

        # Skip total summary rows
        if 'Total' in state:
            continue

        # Find the table in this section
        table = section.find('table', class_='table')

        if not table:
            print(f"  Warning: No table found for {state}")
            continue

        # Find all table rows (skip header row)
        rows = table.find_all('tr')[1:]  # Skip the first row (header)

        for row in rows:
            cells = row.find_all('td')

            if len(cells) != 3:
                continue

            year_grant = cells[0].get_text(strip=True)
            federal_funding = cells[1].get_text(strip=True)
            state_match = cells[2].get_text(strip=True)

            # Skip if this looks like a total row (not needed)
            if 'Total' in year_grant or not year_grant:
                continue

            # Split Year/Grant into separate fields
            year, grant = split_year_grant(year_grant)

            # Clean currency values
            federal_funding_clean = clean_currency(federal_funding)
            state_match_clean = clean_currency(state_match)

            data.append({
                'State': state,
                'Year': year,
                'Grant': grant,
                'Federal_Funding': federal_funding_clean,
                'Required_State_Match': state_match_clean
            })

        print(f"  ✓ {state}: {len([d for d in data if d['State'] == state])} grants")

    return data


def write_csv(data):
    """
    Write funding data to CSV file.

    Args:
        data: list of dicts with keys: State, Year, Grant, Federal_Funding, Required_State_Match
    """
    print(f"\nWriting data to {OUTPUT_FILE}...")

    # Ensure output directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ['State', 'Year', 'Grant', 'Federal_Funding', 'Required_State_Match']

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"✓ Wrote {len(data):,} rows to {OUTPUT_FILE}")


def main():
    """Main processing pipeline."""
    print("=" * 80)
    print("SCRAPING EAC HAVA FUNDING DATA")
    print("=" * 80)
    print()

    # Check if HTML file exists
    if not HTML_FILE.exists():
        print(f"Error: HTML file not found at {HTML_FILE}")
        print("Please download the page first using:")
        print(f'  curl -s "https://www.eac.gov/funding-levels-by-state" -o {HTML_FILE}')
        return 1

    # Parse HTML
    data = parse_html()

    if not data:
        print("\nError: No data extracted from HTML")
        return 1

    # Write CSV
    write_csv(data)

    # Print summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    states = set(d['State'] for d in data)
    years = set(d['Year'] for d in data)
    grants = set(d['Grant'] for d in data)

    print(f"States: {len(states)}")
    print(f"Years: {sorted(years)}")
    print(f"Grant types: {sorted(grants)}")

    # Calculate total federal funding
    total_federal = sum(float(d['Federal_Funding']) for d in data if d['Federal_Funding'])
    total_state_match = sum(float(d['Required_State_Match']) for d in data if d['Required_State_Match'])

    print(f"\nTotal Federal Funding: ${total_federal:,}")
    print(f"Total Required State Match: ${total_state_match:,}")
    print(f"Grand Total: ${total_federal + total_state_match:,}")
    print()

    return 0


if __name__ == '__main__':
    exit(main())
