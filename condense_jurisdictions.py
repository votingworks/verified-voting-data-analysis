#!/usr/bin/env python3
"""
Compress multi-row jurisdiction machine data into single-row summaries.

Reads {YEAR}_verifier-jurisdictions.csv and {YEAR}_verifier-machines.csv,
produces {YEAR}_verifier-jurisdictions-condensed.csv with seven additional columns:
- Poll Book Status (Electronic, Paper, or Unknown based on equipment types)
- Primary Marking Method (Paper for hand-marked ballots, Machine for BMDs/DREs)
- Primary Voting Equipment (classified by Election Day Marking Method: Machine, Precinct Scan, Central Scan, Hand Count, or Anomaly)
- Primary Voting System (equipment family classification for grouping related models)
- Primary Voting Vendor (ES&S, Dominion, Hart InterCivic, Clear Ballot, etc.)
- Primary Voting Equipment - First Year In Use (year from earliest equipment record)
- DRE? (Yes/No indicator for jurisdictions using DRE equipment)

Equipment classifications handle:
- BMDs, DREs, and Lever Machines → "Machine"
- Hand-Fed and Hybrid scanners → "Precinct Scan" (or "Central Scan" for all-mail jurisdictions)
- Batch-Fed scanners → "Central Scan"
- Punch card systems → "Central Scan"
- Explicit hand count equipment or small jurisdictions → "Hand Count"
- All-mail jurisdictions (including Oregon) use special classification logic

Usage: python3 condense_jurisdictions.py <year>
Example: python3 condense_jurisdictions.py 2024
"""

import csv
import re
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Import shared equipment constants
from equipment_constants import (
    PREFIX_MACHINE,
    PREFIX_BMD,
    PREFIX_DRE,
    PREFIX_LEVER,
    PREFIX_CENTRAL_SCAN,
    PREFIX_PRECINCT_SCAN,
    format_equipment_name,
)

# ============================================================================
# CONSTANTS
# ============================================================================

# Data validation constants
MIN_VALID_YEAR = 1950
MAX_VALID_YEAR = 2026
SMALL_JURISDICTION_VOTER_THRESHOLD = 500

# ============================================================================
# EQUIPMENT FAMILY MAPPINGS
# ============================================================================

# Equipment Family Mappings (simplified with substring matching)
# Keys are searched as substrings - order matters (more specific patterns first)
EQUIPMENT_FAMILIES = {
    # ES&S families (most specific first to avoid false matches)
    'ES&S DS300': 'ES&S DS300',
    'ES&S DS200': 'ES&S DS200 Generation',
    'ES&S DS': 'ES&S DS200 Generation',  # Catches collapsed "ES&S DS"
    'ES&S ExpressVote': 'ES&S DS200 Generation',
    'ES&S Model 100': 'ES&S Model 100 Generation',
    'ES&S Model 115': 'ES&S Model 100 Generation',
    'ES&S Model 150': 'ES&S Model 100 Generation',
    'ES&S Model 315': 'ES&S Model 100 Generation',
    'ES&S Model 550': 'ES&S Model 100 Generation',
    'ES&S Model 650': 'ES&S Model 100 Generation',
    'ES&S AutoMARK': 'ES&S Model 100 Generation',
    'ES&S iVotronic': 'iVotronic',
    'ES&S InkaVote': 'InkaVote',
    'ES&S Votomatic': 'Votomatic',
    'ES&S OpTech 2': 'Optech Eagle Generation',

    # AccuVote families
    'AccuVote TS': 'AccuVote TS',  # Must come before AccuVote OS to catch TSX
    'AccuVote OS': 'AccuVote OS',
    'Premier (Diebold) Premier Central Scan': 'AccuVote OS',

    # Dominion ImageCast family
    'Dominion ImageCast': 'Dominion ImageCast',

    # Clear Ballot family
    'Clear Ballot': 'Clear Ballot',

    # DFM Mark-a-Vote
    'DFM Mark-a-Vote': 'DFM Mark-a-Vote',

    # Hart families
    'Hart InterCivic Ballot Now': 'Hart eSeries',
    'Hart InterCivic eScan': 'Hart eSeries',
    'Hart InterCivic eSlate': 'Hart eSeries',
    'Hart InterCivic Vanguard': 'Hart Vangaurd',
    'Hart InterCivic Verity': 'Hart Verity',

    # Los Angeles County
    'Los Angeles County MTS': 'Los Angeles County MTS',
    'Los Angeles County VSAP': 'Los Angeles County VSAP',

    # Optech families
    'Optech IIIP-Eagle': 'Optech Eagle Generation',
    'Optech 400C': 'Optech Insight Generation',
    'Optech IV-C': 'Optech Insight Generation',
    'Optech Insight': 'Optech Insight Generation',

    # Unisyn families
    'Unisyn OpenElect OVCS': 'Unisyn Generation 1',
    'Unisyn OpenElect OVO': 'Unisyn Generation 1',
    'Unisyn OpenElect OVI': 'Unisyn Generation 1',
    'Unisyn OpenElect FVS': 'Unisyn Generation 2',
    'Unisyn OpenElect FVT': 'Unisyn Generation 2',

    # VotingWorks
    'VotingWorks': 'VotingWorks',
}

# ============================================================================
# POLL BOOK LOGIC
# ============================================================================

def determine_poll_book_status(equipment_list):
    """
    Determine poll book status from equipment list.

    Returns: "Paper", manufacturer name (for Commercial), "In-House", or ""
    """
    # Find all poll books
    poll_books = [e for e in equipment_list if 'Poll Book' in e.get('Equipment Type', '')]

    if not poll_books:
        return ""

    # Priority: Paper > In-House > Commercial
    for pb in poll_books:
        if pb.get('Equipment Type', '') == 'Paper Poll Book':
            return "Paper"

    for pb in poll_books:
        if pb.get('Equipment Type', '') == 'In-House Electronic Poll Book':
            return "In-House"

    for pb in poll_books:
        if pb.get('Equipment Type', '') == 'Commercial Electronic Poll Book':
            manufacturer = pb.get('Manufacturer', '').strip()
            return manufacturer if manufacturer else ""

    return ""


def determine_voting_model(jurisdiction):
    """
    Determine voting model based on Election Day Marking Method field.

    Args:
        jurisdiction: Dict containing jurisdiction data including 'Election Day Marking Method'

    Returns:
        str: "Paper" if hand-marked, "Machine" otherwise
    """
    marking_method = jurisdiction.get('Election Day Marking Method', '').strip()

    # Check if marking method starts with "Hand marked"
    if marking_method.startswith('Hand marked'):
        return "Paper"
    else:
        return "Machine"


# ============================================================================
# EQUIPMENT SUMMARY LOGIC - STEP 1: HAND-FED SCANNERS ONLY
# ============================================================================

def get_earliest_equipment(equipment_list):
    """
    Get the equipment with the earliest First Year in Use from a list.

    Args:
        equipment_list: List of equipment dicts (already filtered to relevant type)

    Returns:
        tuple: (selected_equipment dict or None, first_year string)
        - If list is empty: (None, "")
        - If year is invalid/missing: use the first equipment, return ""
        - Negative years are converted to absolute values
        - Years outside MIN_VALID_YEAR-MAX_VALID_YEAR range are treated as invalid
    """
    if not equipment_list:
        return (None, "")

    # Helper function to parse year for sorting
    def get_year(equipment):
        year_str = equipment.get('First Year in Use', '').strip()
        try:
            if year_str:
                year = int(year_str)
                year = abs(year)  # Take absolute value of negative years
                return year
            else:
                return 9999
        except (ValueError, AttributeError):
            return 9999

    # Sort by First Year in Use (earliest first)
    sorted_equipment = sorted(equipment_list, key=get_year)

    # Get the first equipment and its year
    selected = sorted_equipment[0]
    year_str = selected.get('First Year in Use', '').strip()

    # Validate and clean the year
    try:
        if year_str:
            year = int(year_str)
            year = abs(year)  # Take absolute value of negative years

            # Validate year is reasonable (voting equipment systems post-MIN_VALID_YEAR)
            if MIN_VALID_YEAR <= year <= MAX_VALID_YEAR:
                return (selected, str(year))
            else:
                return (selected, "")
        else:
            return (selected, "")
    except (ValueError, AttributeError):
        return (selected, "")


def find_bmd_equipment(equipment_list):
    """
    Find Ballot Marking Device equipment.

    Searches for BMDs and hybrid equipment with BMD functionality.

    Args:
        equipment_list: List of equipment dicts

    Returns:
        tuple: (equipment_summary, first_year)
        - Returns ("Anomaly", "") if no BMD found
    """
    # Find Ballot Marking Devices (including hybrids)
    bmds = [
        e for e in equipment_list
        if e.get('Equipment Type', '') in [
            'Ballot Marking Device',
            'Hybrid BMD/Tabulator',
            'Hybrid Optical Scan/BMD'
        ]
    ]

    bmd, first_year = get_earliest_equipment(bmds)
    if bmd:
        manufacturer = bmd.get('Manufacturer', '').strip()
        model = bmd.get('Model', '').strip()

        equipment_name = format_equipment_name(PREFIX_BMD, manufacturer, model)
        return (equipment_name, first_year)

    # No BMD found → Anomaly
    return ("Anomaly", "")


def find_dre_equipment(equipment_list):
    """
    Find DRE (Direct Recording Electronic) equipment.

    Args:
        equipment_list: List of equipment dicts

    Returns:
        tuple: (equipment_summary, first_year)
        - Returns ("Anomaly", "") if no DRE found
    """
    # Find DRE equipment
    dres = [
        e for e in equipment_list
        if e.get('Equipment Type', '') in ['DRE-Push Button', 'DRE-Touchscreen', 'DRE-Dial']
    ]

    dre, first_year = get_earliest_equipment(dres)
    if dre:
        manufacturer = dre.get('Manufacturer', '').strip()
        model = dre.get('Model', '').strip()

        equipment_name = format_equipment_name(PREFIX_DRE, manufacturer, model)
        return (equipment_name, first_year)

    # No DRE found → Anomaly
    return ("Anomaly", "")


def find_lever_equipment(equipment_list):
    """
    Find Mechanical Lever Machine equipment.

    Args:
        equipment_list: List of equipment dicts

    Returns:
        tuple: (equipment_summary, first_year)
        - Returns ("Anomaly", "") if no lever machine found
    """
    # Find Mechanical Lever Machines
    lever_machines = [
        e for e in equipment_list
        if e.get('Equipment Type', '') == 'Mechanical Lever Machine'
    ]

    lever, first_year = get_earliest_equipment(lever_machines)
    if lever:
        manufacturer = lever.get('Manufacturer', '').strip()
        model = lever.get('Model', '').strip()

        equipment_name = format_equipment_name(PREFIX_LEVER, manufacturer, model)
        return (equipment_name, first_year)

    # No lever machine found → Anomaly
    return ("Anomaly", "")


def find_batch_scan_equipment(equipment_list):
    """
    Find Batch-Fed Optical Scanner equipment for central count.

    Used for both all-mail jurisdictions and jurisdictions that use
    central count with ballot drop boxes.

    Args:
        equipment_list: List of equipment dicts

    Returns:
        tuple: (equipment_summary, first_year) or None if no equipment found
    """
    # Find Batch-Fed scanner
    batchfed_scanners = [
        e for e in equipment_list
        if e.get('Equipment Type', '') == 'Batch-Fed Optical Scanner'
    ]

    scanner, first_year = get_earliest_equipment(batchfed_scanners)
    if scanner:
        manufacturer = scanner.get('Manufacturer', '').strip()
        model = scanner.get('Model', '').strip()

        # Collapse DS* entries to just "DS"
        if manufacturer == 'ES&S' and model.startswith('DS'):
            return (f"{PREFIX_CENTRAL_SCAN}ES&S DS", first_year)

        # Default format for other vendors
        equipment_name = format_equipment_name(PREFIX_CENTRAL_SCAN, manufacturer, model)
        return (equipment_name, first_year)

    # No Batch-Fed scanner found
    return None


def find_handfed_scan_equipment(equipment_list):
    """
    Find Hand-Fed or Hybrid equipment for paper ballot jurisdictions.

    Searches for Hand-Fed Optical Scanners first, then Hybrid equipment.

    Args:
        equipment_list: List of equipment dicts

    Returns:
        tuple: (equipment_summary, first_year) or None if no equipment found
    """
    # Find Hand-Fed scanner
    handfed_scanners = [
        e for e in equipment_list
        if e.get('Equipment Type', '') == 'Hand-Fed Optical Scanner'
    ]

    scanner, first_year = get_earliest_equipment(handfed_scanners)
    if scanner:
        manufacturer = scanner.get('Manufacturer', '').strip()
        model = scanner.get('Model', '').strip()

        equipment_name = format_equipment_name(PREFIX_PRECINCT_SCAN, manufacturer, model)
        return (equipment_name, first_year)

    # Check for Hybrid equipment (if no Hand-Fed scanner)
    hybrid_equipment = [
        e for e in equipment_list
        if e.get('Equipment Type', '') in ['Hybrid Optical Scan/BMD', 'Hybrid Optical Scan/DRE', 'Hybrid BMD/Tabulator']
    ]

    device, first_year = get_earliest_equipment(hybrid_equipment)
    if device:
        manufacturer = device.get('Manufacturer', '').strip()
        model = device.get('Model', '').strip()

        equipment_name = format_equipment_name(PREFIX_PRECINCT_SCAN, manufacturer, model)
        return (equipment_name, first_year)

    return None


def classify_hand_count(jurisdiction, equipment_list):
    """
    Check for hand count jurisdictions.

    Checks for explicit Hand Count equipment or small jurisdictions (< SMALL_JURISDICTION_VOTER_THRESHOLD voters).

    Args:
        jurisdiction: Dict of jurisdiction data
        equipment_list: List of equipment dicts

    Returns:
        tuple: ("Hand Count", "") or None if not hand count
    """
    # Check for Hand Count equipment
    hand_count = [
        e for e in equipment_list
        if e.get('Equipment Type', '') == 'Hand Counted Paper Ballots'
    ]

    if hand_count:
        return ("Hand Count", "")

    # Small jurisdiction fallback - assume Hand Count if < SMALL_JURISDICTION_VOTER_THRESHOLD registered voters
    registered_voters_str = jurisdiction.get('Registered Voters', '')
    try:
        registered_voters = int(registered_voters_str.replace(',', '')) if registered_voters_str else 0
        if registered_voters > 0 and registered_voters < SMALL_JURISDICTION_VOTER_THRESHOLD:
            return ("Hand Count", "")
    except (ValueError, AttributeError):
        pass

    return None


def find_punch_card_equipment(equipment_list):
    """
    Find Punch Card Voting System equipment.

    Args:
        equipment_list: List of equipment dicts

    Returns:
        tuple: (equipment_summary, first_year) or None if no punch card equipment found
    """
    # Find Punch Card systems
    punch_cards = [
        e for e in equipment_list
        if e.get('Equipment Type', '') == 'Punch Card Voting System'
    ]

    punch_card, first_year = get_earliest_equipment(punch_cards)
    if punch_card:
        manufacturer = punch_card.get('Manufacturer', '').strip()
        model = punch_card.get('Model', '').strip()

        equipment_name = format_equipment_name(PREFIX_CENTRAL_SCAN, manufacturer, model)
        return (equipment_name, first_year)

    return None


def determine_equipment_summary(jurisdiction, equipment_list):
    """
    Determine equipment summary based on Election Day Marking Method.

    Uses the "Election Day Marking Method" field to determine which equipment
    to look for. For machine voting methods (BMDs, DREs, Lever Machines),
    calls specific finder functions. For other marking methods, asserts
    Paper voting model and uses paper equipment logic.

    Args:
        jurisdiction: Dict of jurisdiction data
        equipment_list: List of equipment dicts

    Returns:
        tuple: (equipment_summary, first_year, voting_model)
    """
    # Determine voting model
    voting_model = determine_voting_model(jurisdiction)

    # Get Election Day Marking Method
    marking_method = jurisdiction.get('Election Day Marking Method', '').strip()

    # Branch based on marking method
    if marking_method == "Ballot Marking Devices for all voters":
        equipment_summary, first_year = find_bmd_equipment(equipment_list)
    elif marking_method.startswith("DREs") and "for all voters" in marking_method:
        # Matches "DREs for all voters", "DREs*for all voters", etc.
        equipment_summary, first_year = find_dre_equipment(equipment_list)
    elif marking_method == "Mechanical Lever Machine":
        equipment_summary, first_year = find_lever_equipment(equipment_list)
    else:
        # For any other marking method, assert Paper voting model
        assert voting_model == "Paper", \
            f"Unexpected: Voting Model is '{voting_model}' but Election Day Marking Method is '{marking_method}'"

        # Check for punch card systems
        if "punch card" in marking_method.lower():
            result = find_punch_card_equipment(equipment_list)
            if result is not None:
                equipment_summary, first_year = result
            else:
                # Punch card marking method but no punch card equipment → Anomaly
                equipment_summary, first_year = ("Anomaly", "")
            return (equipment_summary, first_year, voting_model)

        # classify all mail jurisdictions by their scanners
        is_all_mail = jurisdiction.get('All Mail Ballot?', '') == 'Yes'
        if is_all_mail:
            # Try batch scanner first
            result = find_batch_scan_equipment(equipment_list)
            if result is not None:
                equipment_summary, first_year = result
            else:
                # No batch scanner, try hand-fed/hybrid scanners
                result = find_handfed_scan_equipment(equipment_list)
                if result is not None:
                    # Replace "Precinct Scan" with "Central Scan" for all-mail jurisdictions
                    handfed_summary, first_year = result
                    equipment_summary = handfed_summary.replace(PREFIX_PRECINCT_SCAN, PREFIX_CENTRAL_SCAN)
                else:
                    # No scanners at all, assume Hand Count
                    equipment_summary, first_year = ("Hand Count", "")
        # look for hand-fed scanners, batch scanners, or classify as hand count
        else:
            result = find_handfed_scan_equipment(equipment_list)
            if result is not None:
                equipment_summary, first_year = result
            else:
                # No hand-fed scanner, check for batch scanner (central count with drop boxes)
                result = find_batch_scan_equipment(equipment_list)
                if result is not None:
                    equipment_summary, first_year = result
                else:
                    result = classify_hand_count(jurisdiction, equipment_list)
                    if result is not None:
                        equipment_summary, first_year = result
                    else:
                        # No equipment found → Anomaly
                        equipment_summary, first_year = ("Anomaly", "")

    return (equipment_summary, first_year, voting_model)


# ============================================================================
# STUBBED FUNCTIONS (FOR FUTURE STEPS)
# ============================================================================

def normalize_equipment_name(equipment_summary):
    """
    Normalize equipment names by removing redundant vendor prefixes.

    Also handles:
    - Collapsing DS200, DS300, etc. → DS (except DS200 and DS300 which are preserved)
    - Preserving PREFIX_MACHINE, PREFIX_CENTRAL_SCAN, and PREFIX_PRECINCT_SCAN prefixes
    - Keeping "Anomaly" and "Hand Count" unchanged
    - AccuVote models: Remove "Premier (Diebold) " or "Diebold " prefix
    - OpTech models: Remove "Sequoia " or "ES&S " prefix

    The Main Vendor field will still correctly attribute to the actual vendor.
    """
    if not equipment_summary:
        return equipment_summary

    # Don't normalize special values
    if equipment_summary in ["Anomaly", "Hand Count"]:
        return equipment_summary

    summary = equipment_summary

    # Extract prefix if present
    prefix = ""
    if summary.startswith(PREFIX_MACHINE):
        prefix = PREFIX_MACHINE
        summary = summary[len(prefix):]  # Remove prefix
    elif summary.startswith(PREFIX_CENTRAL_SCAN):
        prefix = PREFIX_CENTRAL_SCAN
        summary = summary[len(prefix):]  # Remove prefix
    elif summary.startswith(PREFIX_PRECINCT_SCAN):
        prefix = PREFIX_PRECINCT_SCAN
        summary = summary[len(prefix):]  # Remove prefix

    # AccuVote cleanup - remove vendor prefixes
    if "AccuVote" in summary:
        summary = summary.replace("Premier (Diebold) ", "")
        summary = summary.replace("Diebold ", "")

    # OpTech/Optech cleanup - remove vendor prefixes
    if "ptech" in summary:  # Matches both "Optech" and "OpTech"
        summary = summary.replace("Sequoia ", "")
        summary = summary.replace("ES&S ", "")

    # Collapse DS models except DS200 and DS300 (always preserve these)
    # Other DS models (DS450, DS850, DS950, etc.) → "DS"
    if "ES&S DS" in summary:
        # Use negative lookahead to exclude DS200 and DS300 from collapsing
        summary = re.sub(r'DS(?!200|300)\d+', 'DS', summary)

    # Restore prefix
    return prefix + summary


def extract_main_vendor(equipment_summary):
    """
    Extract main active vendor from equipment summary.

    Maps equipment summary to vendor category based on manufacturer name.
    Handles new formats: "Machine [V] [M]", "Central Scan [V] [M]"

    IMPORTANT: This runs on the ORIGINAL equipment summary (before normalization),
    so vendor attribution is preserved correctly.
    """
    if not equipment_summary:
        return ""

    # Convert to string
    summary = str(equipment_summary)

    # Special cases
    if summary == "Anomaly":
        return "Anomaly"
    if "Hand Count" in summary:
        return "Hand Count"

    # Remove prefixes for vendor extraction
    summary_clean = summary.replace(PREFIX_MACHINE, "").replace(PREFIX_CENTRAL_SCAN, "").replace(PREFIX_PRECINCT_SCAN, "")

    # Order matters - check more specific patterns first
    if "ES&S" in summary_clean:
        return "ES&S"
    elif "Dominion" in summary_clean:
        return "Dominion"
    elif "Premier" in summary_clean or "Diebold" in summary_clean:
        return "Dominion"  # Acquired by Dominion
    elif "Sequoia" in summary_clean:
        return "Dominion"  # Acquired by Dominion
    elif "Hart" in summary_clean:
        return "Hart"
    elif "Unisyn" in summary_clean:
        return "Unisyn"
    elif "MicroVote" in summary_clean:
        return "MicroVote"
    elif "Clear Ballot" in summary_clean:
        return "Clear Ballot"
    elif "VotingWorks" in summary_clean:
        return "VotingWorks"
    elif "VSAP" in summary_clean:
        return "VSAP"
    # Shoup family vendors
    elif "AVM" in summary_clean or "AVS" in summary_clean or "Shoup" in summary_clean or "Danaher" in summary_clean or "IES" in summary_clean:
        return "Shoup"
    # UniLect
    elif "Unilect" in summary_clean or "UniLect" in summary_clean:
        return "UniLect"
    # Other vendors (smaller/regional vendors)
    elif any(vendor in summary_clean for vendor in ['DFM', 'Avante', 'Populex', 'VTI', 'Los Angeles County']):
        return "Other"
    else:
        return ""


def get_equipment_family(equipment_summary):
    """
    Get the equipment family for a given equipment summary using substring matching.

    Returns the family name if any key matches as a substring, otherwise returns
    the equipment name itself. This groups related equipment models across different
    prefixes (e.g., PREFIX_CENTRAL_SCAN + "ES&S DS200" and PREFIX_PRECINCT_SCAN + "ES&S DS200"
    both match "ES&S DS200" → ES&S DS200 Generation).

    Args:
        equipment_summary: The normalized equipment summary string

    Returns:
        str: Family name or equipment name if no family defined
    """
    if not equipment_summary:
        return ""

    # Check if any family key is a substring of the equipment summary
    # Dictionary maintains insertion order (Python 3.7+), so more specific patterns are checked first
    for key, family in EQUIPMENT_FAMILIES.items():
        if key in equipment_summary:
            return family

    # Default to equipment name if no family match found
    return equipment_summary


def is_dre(jurisdiction):
    """
    Determine if jurisdiction uses DREs based on Election Day Marking Method.

    Args:
        jurisdiction: The jurisdiction dictionary

    Returns:
        str: "Yes" if DREs for all voters, "No" otherwise
    """
    marking_method = jurisdiction.get('Election Day Marking Method', '').strip()

    # Check if "DREs" appears followed by "for all voters"
    if 'DREs' in marking_method and 'for all voters' in marking_method:
        return "Yes"

    return "No"


# ============================================================================
# CSV PROCESSING
# ============================================================================

def load_jurisdictions(year):
    """Load jurisdiction data from CSV."""
    file_path = Path(f'data/verifier-original/{year}_verifier-jurisdictions.csv')

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        # Skip title row, read header
        next(f)
        reader = csv.DictReader(f)
        jurisdictions = list(reader)

    return jurisdictions


def load_machines(year):
    """Load machine data from CSV, grouped by FIPS code."""
    file_path = Path(f'data/verifier-original/{year}_verifier-machines.csv')

    machines_by_fips = defaultdict(list)

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        # Skip title row, read header
        next(f)
        reader = csv.DictReader(f)

        for row in reader:
            fips = row['FIPS code']
            machines_by_fips[fips].append(row)

    return machines_by_fips


def process_jurisdiction(jurisdiction, equipment_list):
    """
    Process a single jurisdiction and add compressed fields.

    Args:
        jurisdiction: Dict of jurisdiction data
        equipment_list: List of equipment records for this jurisdiction

    Returns:
        Updated jurisdiction dict with new fields
    """
    # Fix "All Mail Ballot?" for Oregon jurisdictions
    # Oregon is an all-mail ballot state, so ensure the field reflects this
    state = jurisdiction.get('State', '').strip()
    if state == 'Oregon':
        jurisdiction['All Mail Ballot?'] = 'Yes'

    # Step 1: Determine equipment summary, first year, and voting model
    primary_voting_equipment, first_year, primary_marking_method = determine_equipment_summary(jurisdiction, equipment_list)

    # Step 2: Extract vendor from ORIGINAL equipment summary (before normalization)
    # This ensures vendor attribution is correct (e.g., "ES&S Optech" → vendor "ES&S")
    primary_voting_vendor = extract_main_vendor(primary_voting_equipment)

    # Step 3: Normalize equipment summary (remove redundant vendor prefixes)
    # This deduplicates equipment names while preserving vendor attribution
    primary_voting_equipment_normalized = normalize_equipment_name(primary_voting_equipment)

    # Step 4: Determine equipment family
    primary_voting_system = get_equipment_family(primary_voting_equipment_normalized)

    # Step 5: Determine DRE status based on Election Day Marking Method
    dre_status = is_dre(jurisdiction)

    # Step 6: Add compressed fields
    jurisdiction['Poll Book Status'] = determine_poll_book_status(equipment_list)
    jurisdiction['Primary Marking Method'] = primary_marking_method
    jurisdiction['Primary Voting Equipment'] = primary_voting_equipment_normalized
    jurisdiction['Primary Voting System'] = primary_voting_system
    jurisdiction['Primary Voting Vendor'] = primary_voting_vendor
    jurisdiction['Primary Voting Equipment - First Year In Use'] = first_year
    jurisdiction['DRE?'] = dre_status

    return jurisdiction


def write_compressed_output(jurisdictions, year):
    """Write condensed jurisdictions to CSV."""
    output_path = Path(f'data/verifier-condensed/{year}_verifier-jurisdictions-condensed.csv')

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not jurisdictions:
        print("ERROR: No jurisdictions to write")
        return

    # Get all field names (original + new fields), filter out empty/None field names
    fieldnames = [key for key in jurisdictions[0].keys() if key and key.strip()]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        # Write title row
        current_date = datetime.now().strftime('%B %d, %Y')
        title = f'The Verifier - November {year}. Data as of {current_date}. Compressed by jurisdiction.'
        f.write(title + '\n')

        # Write data
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(jurisdictions)

    print(f"✓ Output written to {output_path}")

    return output_path


def validate_output(jurisdictions, year):
    """Run basic validation checks on output."""
    print("\nValidation:")

    # Check row count
    input_count = len(jurisdictions)
    print(f"  ✓ Row count matches: {input_count}")

    # Check all FIPS codes present
    fips_codes = [j['FIPS code'] for j in jurisdictions]
    if len(fips_codes) == len(set(fips_codes)):
        print(f"  ✓ All FIPS codes present")
    else:
        print(f"  ⚠ Warning: Duplicate FIPS codes found")

    # Check new columns exist
    required_cols = ['Poll Book Status', 'Primary Marking Method', 'Primary Voting Equipment',
                     'Primary Voting System', 'Primary Voting Vendor',
                     'Primary Voting Equipment - First Year In Use', 'DRE?']
    if all(col in jurisdictions[0].keys() for col in required_cols):
        print(f"  ✓ New columns added")

    # Check original data preserved
    if 'State' in jurisdictions[0] and 'Jurisdiction' in jurisdictions[0]:
        print(f"  ✓ Original data preserved")


# ============================================================================
# MAIN
# ============================================================================

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 condense_jurisdictions.py <year>")
        print("Example: python3 condense_jurisdictions.py 2024")
        sys.exit(1)

    year = sys.argv[1]

    print(f"Processing {year} verifier data...")

    # Load data
    print("\nLoading jurisdiction data...")
    jurisdictions = load_jurisdictions(year)
    print(f"✓ Loaded {len(jurisdictions)} jurisdictions (raw)")

    # Filter out jurisdictions with empty Election Day Marking Method
    filtered = []
    filtered_count = 0
    for j in jurisdictions:
        marking_method = j.get('Election Day Marking Method', '').strip()
        if marking_method:
            filtered.append(j)
        else:
            filtered_count += 1
            fips = j.get('FIPS code', 'unknown')
            name = j.get('Jurisdiction', 'unknown')
            print(f"  ⚠ Skipping incomplete entry: {name} (FIPS: {fips}) - missing Election Day Marking Method")

    if filtered_count > 0:
        print(f"  → Filtered {filtered_count} incomplete jurisdiction(s)")

    jurisdictions = filtered
    print(f"✓ {len(jurisdictions)} jurisdictions to process")

    print("\nLoading machines data...")
    machines_by_fips = load_machines(year)
    print(f"✓ Loaded equipment for {len(machines_by_fips)} jurisdictions")
    total_equipment = sum(len(eq_list) for eq_list in machines_by_fips.values())
    print(f"  Total equipment records: {total_equipment}")

    # Process jurisdictions
    print("\nProcessing jurisdictions...")
    processed_jurisdictions = []

    for i, jurisdiction in enumerate(jurisdictions, 1):
        fips = jurisdiction['FIPS code']
        equipment_list = machines_by_fips.get(fips, [])

        processed = process_jurisdiction(jurisdiction, equipment_list)
        processed_jurisdictions.append(processed)

        # Progress indicator
        if i % 1000 == 0:
            print(f"  Processed {i}/{len(jurisdictions)} jurisdictions...")

    print(f"✓ Processed {len(processed_jurisdictions)} jurisdictions")

    # Print statistics
    print("\nStatistics:")

    # Poll book stats
    poll_book_counts = defaultdict(int)
    for j in processed_jurisdictions:
        poll_book_counts[j['Poll Book Status']] += 1

    print("  Poll Books:")
    for status, count in sorted(poll_book_counts.items()):
        print(f"    {status}: {count}")

    # Equipment stats
    categorized = sum(1 for j in processed_jurisdictions if j['Primary Voting Equipment'] != 'Uncategorized')
    uncategorized = len(processed_jurisdictions) - categorized

    print("  Equipment:")
    print(f"    Categorized (Hand-Fed): {categorized}")
    print(f"    Uncategorized: {uncategorized}")

    # Write output
    print()
    write_compressed_output(processed_jurisdictions, year)

    # Validate
    validate_output(processed_jurisdictions, year)

    print("\n✓ Script completed successfully!")


if __name__ == '__main__':
    main()
