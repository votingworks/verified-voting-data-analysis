#!/usr/bin/env python3
"""
Generate jurisdiction_transitions.csv - detect all jurisdiction changes over time.

Uses jurisdictions_time_series.csv to detect transitions in:
- Voting_Class
- Primary_Marking_Method
- Primary_Voting_Equipment
- Primary_Voting_System
- Primary_Voting_Vendor

Each jurisdiction gets a baseline row (From_* empty, To_* = initial state),
plus a row for each detected transition.

Transition types (priority order):
1. vendor - Primary_Voting_Vendor changed
2. system - Primary_Voting_System changed (same vendor)
3. mail - All_Mail_Ballot changed (No→Yes or Yes→No)
4. equipment - Primary_Voting_Equipment changed (same system)
5. vvpat_upgrade - DRE without VVPAT → DRE with VVPAT
6. vvpat_downgrade - DRE with VVPAT → DRE without VVPAT
7. to_hand_count - Any class → Hand Count
8. from_hand_count - Hand Count → Any other class
9. other - Any other change (Voting_Class, marking method, etc.)
"""

import csv
from pathlib import Path
from collections import defaultdict

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
INPUT_PATH = PROJECT_ROOT / 'data' / 'processed' / 'jurisdictions_time_series.csv'
OUTPUT_PATH = PROJECT_ROOT / 'data' / 'processed' / 'jurisdiction_transitions.csv'

YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]

# Fields to track for detecting changes
TRANSITION_FIELDS = [
    'Voting_Class',
    'Primary_Marking_Method',
    'Primary_Voting_Equipment',
    'Primary_Voting_System',
    'Primary_Voting_Vendor',
]


def load_time_series():
    """
    Load jurisdictions_time_series.csv and group by FIPS.

    Returns:
        dict: {fips: [row1, row2, ...]} sorted by year
    """
    print("Loading jurisdictions_time_series.csv...")
    by_fips = defaultdict(list)

    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            by_fips[row['FIPS']].append(row)

    # Sort each jurisdiction's rows by year
    for fips in by_fips:
        by_fips[fips].sort(key=lambda r: int(r['Year']))

    print(f"  Loaded {sum(len(v) for v in by_fips.values()):,} rows for {len(by_fips):,} jurisdictions")
    return dict(by_fips)


def has_transition(from_row, to_row):
    """
    Check if any transition field changed between two rows.

    Args:
        from_row: Previous state dict
        to_row: Current state dict

    Returns:
        bool: True if any tracked field changed
    """
    for field in TRANSITION_FIELDS:
        if from_row.get(field, '') != to_row.get(field, ''):
            return True
    # Also check All_Mail_Ballot (for mail transitions)
    if from_row.get('All_Mail_Ballot', '') != to_row.get('All_Mail_Ballot', ''):
        return True
    return False


def classify_transition(from_row, to_row):
    """
    Determine Transition_Type based on priority rules.

    Priority order:
    1. to_hand_count - Any class → Hand Count (highest priority - voting method change)
    2. from_hand_count - Hand Count → Any other class
    3. vendor - Vendor changed (only for non-blank transitions)
    4. system - System changed (same vendor)
    5. mail - All_Mail_Ballot changed
    6. equipment - Equipment changed (same system)
    7. vvpat_upgrade - DRE without VVPAT → DRE with VVPAT
    8. vvpat_downgrade - DRE with VVPAT → DRE without VVPAT
    9. other - Any other change

    Args:
        from_row: Previous state dict
        to_row: Current state dict

    Returns:
        str: Transition type
    """
    # 1. Transition to hand count (highest priority - fundamental voting method change)
    if (from_row.get('Voting_Class', '') != 'Hand Count' and
            to_row.get('Voting_Class', '') == 'Hand Count'):
        return 'to_hand_count'

    # 2. Transition from hand count
    if (from_row.get('Voting_Class', '') == 'Hand Count' and
            to_row.get('Voting_Class', '') != 'Hand Count'):
        return 'from_hand_count'

    # 3. Vendor change
    if from_row.get('Primary_Voting_Vendor', '') != to_row.get('Primary_Voting_Vendor', ''):
        return 'vendor'

    # 4. System change (same vendor)
    if from_row.get('Primary_Voting_System', '') != to_row.get('Primary_Voting_System', ''):
        return 'system'

    # 5. Mail transition (All_Mail_Ballot changed)
    if from_row.get('All_Mail_Ballot', '') != to_row.get('All_Mail_Ballot', ''):
        return 'mail'

    # 6. Equipment change (same system)
    if from_row.get('Primary_Voting_Equipment', '') != to_row.get('Primary_Voting_Equipment', ''):
        return 'equipment'

    # 7. VVPAT upgrade (DRE without VVPAT → DRE with VVPAT)
    if (from_row.get('Primary_Marking_Method', '') == 'DRE without VVPAT' and
            to_row.get('Primary_Marking_Method', '') == 'DRE with VVPAT'):
        return 'vvpat_upgrade'

    # 8. VVPAT downgrade (DRE with VVPAT → DRE without VVPAT)
    if (from_row.get('Primary_Marking_Method', '') == 'DRE with VVPAT' and
            to_row.get('Primary_Marking_Method', '') == 'DRE without VVPAT'):
        return 'vvpat_downgrade'

    # 9. Other (any remaining Voting_Class or marking method changes)
    return 'other'


def get_baseline_year(first_row):
    """
    Determine baseline year from First_Year_In_Use.

    Uses First_Year_In_Use if valid (1950-2026), otherwise uses
    the first appearance year in the data.

    Args:
        first_row: First time series row for this jurisdiction

    Returns:
        int: Baseline year
    """
    first_year_str = first_row.get('First_Year_In_Use', '')
    first_appearance = int(first_row['Year'])

    if first_year_str:
        try:
            year = int(first_year_str)
            # Take absolute value (negative years are data entry errors)
            year = abs(year)
            # Validate year is reasonable
            if 1950 <= year <= 2026:
                return year
        except ValueError:
            pass

    # Fall back to first appearance year
    return first_appearance


def build_row(fips, state, jurisdiction, from_row, to_row, transition_type):
    """
    Build a transition row.

    Args:
        fips: FIPS code
        state: State name
        jurisdiction: Jurisdiction name
        from_row: Previous state dict (or None for baseline)
        to_row: Current state dict
        transition_type: Type of transition

    Returns:
        dict: Row for output CSV
    """
    row = {
        'FIPS': fips,
        'State': state,
        'Jurisdiction': jurisdiction,
    }

    # From fields (empty for baseline)
    if from_row:
        row['From_Year'] = from_row['Year']
        row['From_Voting_Class'] = from_row.get('Voting_Class', '')
        row['From_Primary_Marking_Method'] = from_row.get('Primary_Marking_Method', '')
        row['From_Primary_Voting_Equipment'] = from_row.get('Primary_Voting_Equipment', '')
        row['From_Primary_Voting_System'] = from_row.get('Primary_Voting_System', '')
        row['From_Primary_Voting_Vendor'] = from_row.get('Primary_Voting_Vendor', '')
        row['From_All_Mail_Ballot'] = from_row.get('All_Mail_Ballot', '')
    else:
        row['From_Year'] = ''
        row['From_Voting_Class'] = ''
        row['From_Primary_Marking_Method'] = ''
        row['From_Primary_Voting_Equipment'] = ''
        row['From_Primary_Voting_System'] = ''
        row['From_Primary_Voting_Vendor'] = ''
        row['From_All_Mail_Ballot'] = ''

    # To fields
    if transition_type == 'baseline':
        # Use First_Year_In_Use for baseline year
        row['To_Year'] = get_baseline_year(to_row)
    else:
        row['To_Year'] = int(to_row['Year'])

    row['To_Voting_Class'] = to_row.get('Voting_Class', '')
    row['To_Primary_Marking_Method'] = to_row.get('Primary_Marking_Method', '')
    row['To_Primary_Voting_Equipment'] = to_row.get('Primary_Voting_Equipment', '')
    row['To_Primary_Voting_System'] = to_row.get('Primary_Voting_System', '')
    row['To_Primary_Voting_Vendor'] = to_row.get('Primary_Voting_Vendor', '')
    row['To_All_Mail_Ballot'] = to_row.get('All_Mail_Ballot', '')

    # Metadata
    row['Transition_Type'] = transition_type

    if from_row:
        row['Years_Between'] = int(to_row['Year']) - int(from_row['Year'])
        row['Vendor_Retained'] = (from_row.get('Primary_Voting_Vendor', '') ==
                                   to_row.get('Primary_Voting_Vendor', ''))
    else:
        row['Years_Between'] = ''
        row['Vendor_Retained'] = ''

    return row


def generate_baselines(by_fips):
    """
    Generate baseline rows for all jurisdictions.

    Each jurisdiction gets one baseline row with:
    - From_* fields empty
    - To_* fields from their first time series entry
    - To_Year = First_Year_In_Use (if valid) or first appearance year

    Args:
        by_fips: dict mapping FIPS to sorted list of time series rows

    Returns:
        list: Baseline row dicts
    """
    rows = []

    for fips, fips_rows in by_fips.items():
        first_row = fips_rows[0]
        row = build_row(
            fips=fips,
            state=first_row['State'],
            jurisdiction=first_row['Jurisdiction'],
            from_row=None,
            to_row=first_row,
            transition_type='baseline'
        )
        rows.append(row)

    return rows


def detect_transitions(by_fips):
    """
    Detect all transitions across all jurisdictions.

    Walks through consecutive year pairs for each jurisdiction,
    detecting when any transition field changes.

    Args:
        by_fips: dict mapping FIPS to sorted list of time series rows

    Returns:
        tuple: (list of transition rows, dict of counts by type)
    """
    rows = []
    counts = defaultdict(int)

    for fips, fips_rows in by_fips.items():
        state = fips_rows[0]['State']
        jurisdiction = fips_rows[0]['Jurisdiction']

        # Compare consecutive years
        for i in range(1, len(fips_rows)):
            from_row = fips_rows[i - 1]
            to_row = fips_rows[i]

            if has_transition(from_row, to_row):
                transition_type = classify_transition(from_row, to_row)
                row = build_row(
                    fips=fips,
                    state=state,
                    jurisdiction=jurisdiction,
                    from_row=from_row,
                    to_row=to_row,
                    transition_type=transition_type
                )
                rows.append(row)
                counts[transition_type] += 1

    return rows, dict(counts)


def write_output(rows, output_path):
    """
    Write rows to CSV, sorted by State, Jurisdiction, To_Year.

    Args:
        rows: List of row dicts
        output_path: Path to output file
    """
    # Sort by State, Jurisdiction, To_Year
    def sort_key(row):
        to_year = row['To_Year']
        if to_year == '' or to_year is None:
            to_year = 0
        return (row['State'], row['Jurisdiction'], int(to_year))

    rows.sort(key=sort_key)

    fieldnames = [
        'FIPS', 'State', 'Jurisdiction',
        'From_Year', 'From_Voting_Class', 'From_Primary_Marking_Method',
        'From_Primary_Voting_Equipment', 'From_Primary_Voting_System',
        'From_Primary_Voting_Vendor', 'From_All_Mail_Ballot',
        'To_Year', 'To_Voting_Class', 'To_Primary_Marking_Method',
        'To_Primary_Voting_Equipment', 'To_Primary_Voting_System',
        'To_Primary_Voting_Vendor', 'To_All_Mail_Ballot',
        'Transition_Type', 'Years_Between', 'Vendor_Retained',
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(num_jurisdictions, num_baselines, transition_counts):
    """Print summary statistics."""
    print()
    print("=" * 70)
    print("JURISDICTION TRANSITIONS SUMMARY")
    print("=" * 70)
    print()
    print(f"Total jurisdictions: {num_jurisdictions:,}")
    print(f"Baseline rows: {num_baselines:,}")
    print()

    total_transitions = sum(transition_counts.values())
    print(f"Total transitions detected: {total_transitions:,}")
    print()

    if total_transitions > 0:
        print("Transitions by type:")
        # Order by priority
        priority_order = ['vendor', 'system', 'mail', 'equipment', 'vvpat', 'other']
        for t_type in priority_order:
            count = transition_counts.get(t_type, 0)
            if count > 0:
                pct = count / total_transitions * 100
                print(f"  {t_type}: {count:,} ({pct:.1f}%)")
        print()

    jurisdictions_with_transitions = total_transitions  # Approximate
    print("=" * 70)


def main():
    """Main processing pipeline."""
    print("=" * 70)
    print("GENERATING JURISDICTION TRANSITIONS")
    print("=" * 70)
    print()

    # Load time series data
    by_fips = load_time_series()

    # Generate baseline rows
    print("\nGenerating baseline rows...")
    baseline_rows = generate_baselines(by_fips)
    print(f"  Generated {len(baseline_rows):,} baseline rows")

    # Detect transitions
    print("\nDetecting transitions...")
    transition_rows, transition_counts = detect_transitions(by_fips)
    print(f"  Detected {len(transition_rows):,} transitions")

    # Combine and write output
    all_rows = baseline_rows + transition_rows
    print(f"\nWriting {len(all_rows):,} rows to {OUTPUT_PATH}...")
    write_output(all_rows, OUTPUT_PATH)
    print("  Done!")

    # Print summary
    print_summary(len(by_fips), len(baseline_rows), transition_counts)


if __name__ == '__main__':
    main()
