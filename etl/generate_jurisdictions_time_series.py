#!/usr/bin/env python3
"""
Generate jurisdictions_time_series.csv - longitudinal voting equipment data.

Creates one row per jurisdiction per election cycle (2006-2026), tracking:
- Jurisdiction metadata (copied from verifier-jurisdictions.csv)
- Voting class (Precinct Scan, Central Scan, Hand Count, BMD, DRE, etc.)
- Primary equipment, vendor, and system family

Uses machine_lifetimes.csv for equipment timeline data instead of per-year
machine files. Equipment is considered "active" for a year if:
    First_Year <= year <= Last_Year

Usage: python3 generate_jurisdictions_time_series.py
Output: data/processed/jurisdictions_time_series.csv
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from equipment_constants import EQUIPMENT_FAMILIES

# Project root directory (parent of etl/)
PROJECT_ROOT = Path(__file__).parent.parent

# ============================================================================
# CONSTANTS
# ============================================================================

YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]

# Election Day Marking Method → Voting_Class direct mappings
MARKING_METHOD_MAP = {
    "Ballot Marking Devices for all voters": "BMD",
    "DREs with VVPAT for all voters": "DRE with VVPAT",
    "DREs without VVPAT for all voters": "DRE without VVPAT",
    "Mechanical Lever Machine": "Mechanical Lever Machine",
}

# Equipment_Type values for each Voting_Class
EQUIPMENT_TYPES_BY_CLASS = {
    "BMD": ["Ballot Marking Device", "Hybrid BMD/Tabulator", "Hybrid Optical Scan/BMD"],
    "DRE with VVPAT": ["DRE-Touchscreen", "DRE-Push Button", "DRE-Dial"],
    "DRE without VVPAT": ["DRE-Touchscreen", "DRE-Push Button", "DRE-Dial"],
    "Mechanical Lever Machine": ["Mechanical Lever Machine"],
    "Punch Cards": ["Punch Card Voting System"],
    "Central Scan": ["Batch-Fed Optical Scanner", "Hand-Fed Optical Scanner"],
    "Precinct Scan": ["Hand-Fed Optical Scanner", "Hybrid Optical Scan/BMD", "Hybrid Optical Scan/DRE"],
    "Hand Count": ["Hand Counted Paper Ballots"],
}

# ============================================================================
# DATA LOADING
# ============================================================================

def load_machine_lifetimes():
    """
    Load machine_lifetimes.csv into a dict keyed by FIPS.

    Returns:
        dict: {fips: [list of equipment records]}
        Each equipment record is a dict with keys:
        - FIPS, State, Jurisdiction, Equipment_Type, Manufacturer, Vendor, Model
        - First_Year, Last_Year, Length_Of_Use, Reported_First_Year_In_Use, Source_Data_Record_Count
    """
    filepath = PROJECT_ROOT / 'data/processed/machine_lifetimes.csv'
    lifetimes_by_fips = defaultdict(list)

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fips = row['FIPS']
            # Convert year fields to int for comparison
            row['First_Year'] = int(row['First_Year'])
            row['Last_Year'] = int(row['Last_Year'])
            lifetimes_by_fips[fips].append(row)

    return lifetimes_by_fips


def load_jurisdiction_metadata(year):
    """
    Load verifier-jurisdictions.csv for a specific year.

    Args:
        year: Election year (e.g., 2024)

    Returns:
        dict: {fips: jurisdiction_metadata_dict}
    """
    filepath = PROJECT_ROOT / f'data/extracted/{year}_verifier-jurisdictions.csv'
    jurisdictions = {}

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        # Skip title row
        next(f)
        reader = csv.DictReader(f)
        for row in reader:
            fips = row['FIPS code']
            jurisdictions[fips] = row

    return jurisdictions


# ============================================================================
# EQUIPMENT FILTERING
# ============================================================================

def get_active_equipment(fips, year, lifetimes_by_fips):
    """
    Get equipment active for a jurisdiction in a specific year.

    Equipment is active if: First_Year <= year <= Last_Year

    Args:
        fips: Jurisdiction FIPS code
        year: Election year
        lifetimes_by_fips: Dict from load_machine_lifetimes()

    Returns:
        list: Equipment records active in the given year
    """
    all_equipment = lifetimes_by_fips.get(fips, [])
    active = [
        eq for eq in all_equipment
        if eq['First_Year'] <= year <= eq['Last_Year']
    ]
    return active


def filter_equipment_by_types(equipment_list, equipment_types):
    """
    Filter equipment list to only those matching specified types.

    Args:
        equipment_list: List of equipment records
        equipment_types: List of Equipment_Type values to match

    Returns:
        list: Filtered equipment records
    """
    return [
        eq for eq in equipment_list
        if eq['Equipment_Type'] in equipment_types
    ]


def select_primary_equipment(equipment_list):
    """
    Select the primary equipment from a list, breaking ties by earliest First_Year.

    Args:
        equipment_list: List of equipment records (already filtered by type)

    Returns:
        dict or None: Selected equipment record, or None if list is empty
    """
    if not equipment_list:
        return None

    # Sort by First_Year (earliest first)
    sorted_equipment = sorted(equipment_list, key=lambda x: x['First_Year'])
    return sorted_equipment[0]


# ============================================================================
# CLASSIFICATION LOGIC
# ============================================================================

def has_equipment_type(equipment_list, equipment_types):
    """Check if any equipment in the list matches the given types."""
    return any(eq['Equipment_Type'] in equipment_types for eq in equipment_list)


def classify_voting_class(jurisdiction_meta, active_equipment):
    """
    Determine Voting_Class from jurisdiction metadata and active equipment.

    Classification priority:
    1. Check Election Day Marking Method for direct mappings (BMD, DRE, Lever)
    2. Check for punch card in marking method
    3. For paper ballots:
       - All Mail → Central Scan
       - Hand-fed scanner found → Precinct Scan
       - Batch scanner found → Central Scan
       - Hand count equipment or < 500 voters → Hand Count
       - Fallback → Precinct Scan

    Args:
        jurisdiction_meta: Dict of jurisdiction data from verifier-jurisdictions.csv
        active_equipment: List of active equipment records

    Returns:
        str: Voting_Class value
    """
    marking_method = jurisdiction_meta.get('Election Day Marking Method', '').strip()

    # Step 1: Check direct mappings from marking method
    if marking_method in MARKING_METHOD_MAP:
        return MARKING_METHOD_MAP[marking_method]

    # Step 2: Check for punch card
    if 'punch card' in marking_method.lower():
        return "Punch Cards"

    # Step 3: Paper ballot classification based on equipment and All Mail status
    is_all_mail = jurisdiction_meta.get('All Mail Ballot?', '') == 'Yes'
    scanner_types = ["Hand-Fed Optical Scanner", "Batch-Fed Optical Scanner",
                     "Hybrid Optical Scan/BMD", "Hybrid Optical Scan/DRE"]
    has_scanner = has_equipment_type(active_equipment, scanner_types)

    # All-mail jurisdictions with scanners are Central Scan
    # (All-mail without scanner falls through to Hand Count below)
    if is_all_mail and has_scanner:
        return "Central Scan"

    # Check for hand-fed scanners (Precinct Scan)
    handfed_types = ["Hand-Fed Optical Scanner", "Hybrid Optical Scan/BMD", "Hybrid Optical Scan/DRE"]
    if has_equipment_type(active_equipment, handfed_types):
        return "Precinct Scan"

    # Check for batch-fed scanners (Central Scan)
    batchfed_types = ["Batch-Fed Optical Scanner"]
    if has_equipment_type(active_equipment, batchfed_types):
        return "Central Scan"

    # Check for hand count equipment
    handcount_types = ["Hand Counted Paper Ballots"]
    if has_equipment_type(active_equipment, handcount_types):
        return "Hand Count"

    # HMPB with no scanners → Hand Count
    # If marking method is hand-marked paper ballots but we found no optical scanners,
    # they must be hand counting (scanners would be in machine_lifetimes if they had them)
    if marking_method.startswith('Hand marked paper ballots'):
        scanner_types = ["Hand-Fed Optical Scanner", "Batch-Fed Optical Scanner",
                         "Hybrid Optical Scan/BMD", "Hybrid Optical Scan/DRE"]
        if not has_equipment_type(active_equipment, scanner_types):
            return "Hand Count"

    # Fallback: Precinct Scan (most common for paper ballots)
    return "Precinct Scan"


def get_primary_equipment_for_class(voting_class, active_equipment):
    """
    Get the primary equipment for a given voting class.

    For Central Scan (all-mail): prefer batch-fed, fall back to hand-fed
    For other classes: filter by class equipment types, select earliest

    Args:
        voting_class: Voting_Class value
        active_equipment: List of active equipment records

    Returns:
        dict or None: Selected equipment record
    """
    if voting_class == "Hand Count":
        # No equipment for hand count
        return None

    if voting_class == "Central Scan":
        # Prefer batch-fed scanners, fall back to hand-fed
        batch_scanners = filter_equipment_by_types(
            active_equipment, ["Batch-Fed Optical Scanner"]
        )
        if batch_scanners:
            return select_primary_equipment(batch_scanners)

        # Fall back to hand-fed (can be used centrally for mail ballots)
        handfed_scanners = filter_equipment_by_types(
            active_equipment, ["Hand-Fed Optical Scanner"]
        )
        return select_primary_equipment(handfed_scanners)

    # For other classes, use the standard equipment types
    equipment_types = EQUIPMENT_TYPES_BY_CLASS.get(voting_class, [])
    filtered = filter_equipment_by_types(active_equipment, equipment_types)
    return select_primary_equipment(filtered)


# ============================================================================
# POLL BOOK CLASSIFICATION
# ============================================================================

def get_poll_book_status(active_equipment):
    """
    Determine Poll_Book_Status from active equipment.

    Classification priority:
    1. If any "In-House Electronic Poll Book" → "In-House"
    2. Else if any "Commercial Electronic Poll Book" → vendor name
    3. Else → "Paper"

    Args:
        active_equipment: List of active equipment records for this FIPS/year

    Returns:
        str: Poll book status (vendor name, "In-House", or "Paper")
    """
    # Filter to poll book equipment
    poll_books = [
        eq for eq in active_equipment
        if 'Poll Book' in eq.get('Equipment_Type', '')
    ]

    if not poll_books:
        return "Paper"

    # Check for in-house first
    for eq in poll_books:
        if 'In-House' in eq.get('Equipment_Type', ''):
            return "In-House"

    # Check for commercial poll books - return vendor name
    for eq in poll_books:
        if 'Commercial' in eq.get('Equipment_Type', ''):
            vendor = eq.get('Manufacturer', '').strip()
            if vendor:
                return vendor

    # Fallback (shouldn't happen if data is clean)
    return "Paper"


# ============================================================================
# DERIVED FIELDS
# ============================================================================

def derive_primary_marking_method(marking_method):
    """
    Derive simplified Primary_Marking_Method from Election Day Marking Method.

    Collapses the detailed marking method into one of:
    - Hand Marked Paper Ballots (all HMPB variants)
    - Punch Cards
    - BMD
    - DRE with VVPAT
    - DRE without VVPAT
    - Mechanical Lever Machine

    Args:
        marking_method: Raw Election Day Marking Method value

    Returns:
        str: Simplified marking method
    """
    if not marking_method:
        return ""

    if marking_method.startswith('Hand marked paper ballots'):
        return 'Hand Marked Paper Ballots'
    if marking_method.startswith('Hand marked punch card ballots'):
        return 'Punch Cards'
    if marking_method == 'Ballot Marking Devices for all voters':
        return 'BMD'
    if marking_method == 'DREs with VVPAT for all voters':
        return 'DRE with VVPAT'
    if marking_method == 'DREs without VVPAT for all voters':
        return 'DRE without VVPAT'
    if marking_method == 'Mechanical Lever Machine':
        return 'Mechanical Lever Machine'

    # Fallback for any unrecognized values
    return marking_method


def derive_accessible_marking_method(marking_method):
    """
    Derive Accessible_Marking_Method for HMPB systems.

    For hand-marked paper ballot systems, extracts the accessible voting
    equipment type (BMD, DRE with/without VVPAT, or None).

    Returns empty string for non-HMPB systems (BMD-only, DRE-only, etc.).

    Args:
        marking_method: Raw Election Day Marking Method value

    Returns:
        str: Accessible method (BMD, DRE with VVPAT, DRE without VVPAT, None) or empty
    """
    if not marking_method:
        return ""

    # Non-HMPB systems get empty value
    if marking_method in ('Ballot Marking Devices for all voters',
                          'DREs with VVPAT for all voters',
                          'DREs without VVPAT for all voters',
                          'Mechanical Lever Machine'):
        return ""
    if marking_method.startswith('Hand marked punch card ballots'):
        return ""

    # HMPB systems - extract accessible method
    if marking_method == 'Hand marked paper ballots and BMDs':
        return 'BMD'
    if marking_method == 'Hand marked paper ballots and DREs with VVPAT':
        return 'DRE with VVPAT'
    if marking_method == 'Hand marked paper ballots and DREs without VVPAT':
        return 'DRE without VVPAT'
    if 'Direct recording assistive interface without VVPAT' in marking_method:
        return 'DRE without VVPAT'
    if 'No accessible equipment' in marking_method:
        return 'None'

    # Other HMPB variants (rare cases)
    if marking_method.startswith('Hand marked paper ballots'):
        return 'Mixed'

    return ""


def get_equipment_family(equipment):
    """
    Get the equipment family for grouping related models.

    Uses EQUIPMENT_FAMILIES dict from equipment_constants.py with substring matching.

    Args:
        equipment: Equipment record dict (or None)

    Returns:
        str: Equipment family name, or empty string if no match
    """
    if not equipment:
        return ""

    # Build the equipment name string for matching
    manufacturer = equipment.get('Manufacturer', '')
    model = equipment.get('Model', '')
    equipment_name = f"{manufacturer} {model}".strip()

    # Check for family matches (substring matching, order matters)
    for key, family in EQUIPMENT_FAMILIES.items():
        if key in equipment_name:
            return family

    # Default to the equipment name itself if no family match
    return equipment_name


def format_equipment_name(equipment):
    """
    Format equipment name as "Manufacturer Model" without prefix.

    Args:
        equipment: Equipment record dict (or None)

    Returns:
        str: Formatted equipment name
    """
    if not equipment:
        return ""

    manufacturer = equipment.get('Manufacturer', '').strip()
    model = equipment.get('Model', '').strip()

    if manufacturer and model:
        # Avoid duplicate manufacturer in model
        if model.startswith(manufacturer):
            return model
        return f"{manufacturer} {model}"
    elif manufacturer:
        return manufacturer
    elif model:
        return model
    return ""


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def main():
    print("Generating jurisdictions_time_series.csv...")

    # Step 1: Load machine lifetimes data (once)
    print("\nLoading machine lifetimes data...")
    lifetimes_by_fips = load_machine_lifetimes()
    print(f"  Loaded equipment for {len(lifetimes_by_fips):,} jurisdictions")

    # Track 2016 all-mail jurisdictions for 2018 fix
    all_mail_2016 = {}

    # Collect all output rows
    rows = []

    # Step 2: Process each year
    for year in YEARS:
        print(f"\nProcessing {year}...")

        # Load jurisdiction metadata for this year
        jurisdictions = load_jurisdiction_metadata(year)
        print(f"  Loaded {len(jurisdictions):,} jurisdictions")

        # 2018 fix: apply 2016 all-mail status to fill data gaps
        if year == 2018:
            fixed_count = 0
            for fips, was_all_mail in all_mail_2016.items():
                if was_all_mail and fips in jurisdictions:
                    if jurisdictions[fips].get('All Mail Ballot?') != 'Yes':
                        jurisdictions[fips]['All Mail Ballot?'] = 'Yes'
                        fixed_count += 1
            if fixed_count > 0:
                print(f"  Applied 2018 all-mail fix to {fixed_count} jurisdictions")

        # Process each jurisdiction
        for fips, meta in jurisdictions.items():
            # Track 2016 all-mail status for 2018 fix
            if year == 2016:
                all_mail_2016[fips] = (meta.get('All Mail Ballot?') == 'Yes')

            # Get active equipment for this jurisdiction/year
            active_equipment = get_active_equipment(fips, year, lifetimes_by_fips)

            # Classify voting method
            voting_class = classify_voting_class(meta, active_equipment)

            # Get primary equipment for this voting class
            primary_equipment = get_primary_equipment_for_class(voting_class, active_equipment)

            # Derive fields from equipment
            equipment_name = format_equipment_name(primary_equipment)
            vendor = primary_equipment['Vendor'] if primary_equipment else ''
            system_family = get_equipment_family(primary_equipment)
            first_year = str(primary_equipment['First_Year']) if primary_equipment else ''

            # Derive marking method fields
            marking_method = meta.get('Election Day Marking Method', '')
            primary_marking_method = derive_primary_marking_method(marking_method)
            accessible_marking_method = derive_accessible_marking_method(marking_method)

            # Derive poll book status
            poll_book_status = get_poll_book_status(active_equipment)

            # Build output row
            row = {
                'FIPS': fips,
                'State': meta.get('State', ''),
                'Jurisdiction': meta.get('Jurisdiction', ''),
                'Year': year,
                # Jurisdiction metadata (copied from source)
                'Registered_Voters': meta.get('Registered Voters', ''),
                'Precincts': meta.get('Precincts', ''),
                'Voting_Location': meta.get('Voting Location', ''),
                'All_Mail_Ballot': meta.get('All Mail Ballot?', ''),
                'Election_Day_Marking_Method': marking_method,
                'Election_Day_Tabulation': meta.get('Election Day Tabulation', ''),
                # Derived fields
                'Voting_Class': voting_class,
                'Primary_Marking_Method': primary_marking_method,
                'Accessible_Marking_Method': accessible_marking_method,
                'Primary_Voting_Equipment': equipment_name,
                'Primary_Voting_System': system_family,
                'Primary_Voting_Vendor': vendor,
                'First_Year_In_Use': first_year,
                'Poll_Book_Status': poll_book_status,
            }
            rows.append(row)

    # Step 3: Sort rows by FIPS then Year for easy longitudinal review
    print(f"\nSorting rows by jurisdiction and year...")
    rows.sort(key=lambda r: (r['FIPS'], r['Year']))

    # Step 4: Write output
    print(f"Writing output ({len(rows):,} rows)...")
    output_path = PROJECT_ROOT / 'data/processed/jurisdictions_time_series.csv'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        'FIPS', 'State', 'Jurisdiction', 'Year',
        'Registered_Voters', 'Precincts', 'Voting_Location',
        'All_Mail_Ballot', 'Election_Day_Marking_Method', 'Election_Day_Tabulation',
        'Voting_Class', 'Primary_Marking_Method', 'Accessible_Marking_Method',
        'Primary_Voting_Equipment', 'Primary_Voting_System',
        'Primary_Voting_Vendor', 'First_Year_In_Use',
        'Poll_Book_Status',
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Output written to {output_path}")

    # Step 4: Print summary statistics
    print("\nSummary by Voting_Class:")
    class_counts = defaultdict(int)
    for row in rows:
        class_counts[row['Voting_Class']] += 1

    for voting_class in sorted(class_counts.keys()):
        count = class_counts[voting_class]
        print(f"  {voting_class}: {count:,}")

    print("\nDone!")


if __name__ == '__main__':
    main()
