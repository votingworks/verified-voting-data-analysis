#!/usr/bin/env python3
"""
Condense jurisdiction-level voting data to state-level uniformity data.

Takes a year as input and outputs a CSV showing which states have uniform
voting equipment and/or poll book deployments.

Usage:
    python3 etl/condense_to_state_level.py 2026
    python3 etl/condense_to_state_level.py 2024

Output:
    data/processed/states/{year}_state-uniformity.csv
"""

import sys
import csv
from pathlib import Path
from collections import defaultdict

# Directories
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / 'data'
CONDENSED_DIR = DATA_DIR / 'processed' / 'jurisdictions'
STATE_LEVEL_DIR = DATA_DIR / 'processed' / 'states'

# US territories to exclude from analysis
EXCLUDED_TERRITORIES = {
    'American Samoa',
    'Guam',
    'Northern Mariana Islands',
    'Puerto Rico',
    'US Virgin Islands',
}


def load_jurisdiction_data(year):
    """
    Load condensed jurisdiction data for a given year.

    Args:
        year: Year to load (e.g., 2026)

    Returns:
        list of dicts: Jurisdiction data with keys:
            - State (column 2)
            - Poll_Book_Status (column 10)
            - Primary_Voting_Equipment (column 12)
    """
    filepath = CONDENSED_DIR / f'{year}_verifier-jurisdictions-condensed.csv'

    if not filepath.exists():
        raise FileNotFoundError(f"Condensed data file not found: {filepath}")

    jurisdictions = []

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

        # Skip title row (line 0) and header row (line 1)
        reader = csv.reader(lines[2:])

        for row in reader:
            if len(row) < 13:
                continue  # Skip incomplete rows

            jurisdictions.append({
                'State': row[1].strip(),
                'Poll_Book_Status': row[9].strip(),  # Column 10 (0-indexed: 9)
                'Primary_Voting_Equipment': row[11].strip(),  # Column 12 (0-indexed: 11)
            })

    return jurisdictions


def analyze_state_equipment_uniformity(state_jurisdictions):
    """
    Determine if a state has uniform voting equipment deployment.

    Ignores "Hand Count" jurisdictions when determining uniformity.

    Args:
        state_jurisdictions: List of jurisdiction dicts for one state

    Returns:
        tuple: (uniformity_status, equipment_type, total_juris, non_hand_count_juris)
            uniformity_status: "Uniform", "Mixed", or "All Hand Count"
            equipment_type: The uniform equipment or "Multiple systems"
            total_juris: Total number of jurisdictions
            non_hand_count_juris: Number of non-Hand-Count jurisdictions
    """
    total_juris = len(state_jurisdictions)

    # Filter out Hand Count jurisdictions
    non_hand_count = [j for j in state_jurisdictions
                      if j['Primary_Voting_Equipment'] != 'Hand Count']

    non_hand_count_juris = len(non_hand_count)

    if non_hand_count_juris == 0:
        return "All Hand Count", "Hand Count", total_juris, 0

    # Get unique equipment types (excluding Hand Count)
    equipment_types = set(j['Primary_Voting_Equipment'] for j in non_hand_count)

    if len(equipment_types) == 1:
        return "Uniform", list(equipment_types)[0], total_juris, non_hand_count_juris
    else:
        return "Mixed", "Multiple systems", total_juris, non_hand_count_juris


def analyze_state_pollbook_uniformity(state_jurisdictions):
    """
    Determine if a state has uniform poll book deployment.

    Ignores "Paper" poll book status when determining uniformity.

    Args:
        state_jurisdictions: List of jurisdiction dicts for one state

    Returns:
        tuple: (uniformity_status, pollbook_type, non_paper_juris)
            uniformity_status: "Uniform", "Mixed", or "All Paper"
            pollbook_type: The uniform poll book or "Multiple vendors"
            non_paper_juris: Number of non-Paper poll book jurisdictions
    """
    # Filter out Paper poll books
    non_paper = [j for j in state_jurisdictions
                 if j['Poll_Book_Status'] != 'Paper']

    non_paper_juris = len(non_paper)

    if non_paper_juris == 0:
        return "All Paper", "Paper", 0

    # Get unique poll book types (excluding Paper)
    pollbook_types = set(j['Poll_Book_Status'] for j in non_paper)

    if len(pollbook_types) == 1:
        return "Uniform", list(pollbook_types)[0], non_paper_juris
    else:
        return "Mixed", "Multiple vendors", non_paper_juris


def condense_year_to_states(year):
    """
    Process all jurisdictions for a year and condense to state-level data.

    Args:
        year: Year to process

    Returns:
        list of dicts: State-level data with uniformity information
    """
    print(f"\nProcessing {year} data...")

    # Load jurisdiction data
    jurisdictions = load_jurisdiction_data(year)
    print(f"✓ Loaded {len(jurisdictions):,} jurisdictions")

    # Group by state
    states_data = defaultdict(list)
    for jurisdiction in jurisdictions:
        states_data[jurisdiction['State']].append(jurisdiction)

    print(f"✓ Found {len(states_data):,} states/territories")

    # Analyze each state
    state_results = []
    excluded_count = 0

    for state_name in sorted(states_data.keys()):
        # Skip US territories
        if state_name in EXCLUDED_TERRITORIES:
            excluded_count += 1
            continue

        state_jurisdictions = states_data[state_name]

        # Analyze equipment uniformity
        equip_uniformity, equip_type, total_juris, non_hand_count = \
            analyze_state_equipment_uniformity(state_jurisdictions)

        # Analyze poll book uniformity
        pollbook_uniformity, pollbook_type, non_paper = \
            analyze_state_pollbook_uniformity(state_jurisdictions)

        # Special case: Alaska
        if state_name == "Alaska":
            equip_uniformity = "Mixed"
            equip_type = "Paper"
            pollbook_uniformity = "Uniform"
            pollbook_type = "Paper"

        # Determine if both are uniform
        both_uniform = "Yes" if (equip_uniformity == "Uniform" and
                                  pollbook_uniformity == "Uniform") else "No"

        state_results.append({
            'State': state_name,
            'Equipment_Uniformity': equip_uniformity,
            'Primary_Voting_Equipment': equip_type,
            'Total_Jurisdictions': total_juris,
            'Non_Hand_Count_Jurisdictions': non_hand_count,
            'Poll_Book_Uniformity': pollbook_uniformity,
            'Poll_Book_Status': pollbook_type,
            'Non_Paper_Poll_Book_Jurisdictions': non_paper,
            'Both_Uniform': both_uniform,
        })

    if excluded_count > 0:
        print(f"✓ Excluded {excluded_count} US territories from analysis")

    return state_results


def write_state_csv(year, state_data):
    """
    Write state-level data to CSV file.

    Args:
        year: Year of the data
        state_data: List of state data dicts
    """
    output_path = STATE_LEVEL_DIR / f'{year}_state-uniformity.csv'

    fieldnames = [
        'State',
        'Equipment_Uniformity',
        'Primary_Voting_Equipment',
        'Total_Jurisdictions',
        'Non_Hand_Count_Jurisdictions',
        'Poll_Book_Uniformity',
        'Poll_Book_Status',
        'Non_Paper_Poll_Book_Jurisdictions',
        'Both_Uniform',
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(state_data)

    print(f"✓ State-level data written to {output_path}")
    print(f"  ({len(state_data)} states/territories)")


def main():
    """Main execution function."""
    if len(sys.argv) != 2:
        print("Usage: python3 condense_to_state_level.py <year>")
        print("Example: python3 condense_to_state_level.py 2026")
        sys.exit(1)

    try:
        year = int(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid year")
        sys.exit(1)

    print("=" * 80)
    print(f"CONDENSING {year} JURISDICTION DATA TO STATE-LEVEL")
    print("=" * 80)

    # Process the year
    state_data = condense_year_to_states(year)

    # Write output
    write_state_csv(year, state_data)

    # Summary statistics
    print("\nSummary:")
    uniform_both = sum(1 for s in state_data if s['Both_Uniform'] == 'Yes')
    uniform_equip = sum(1 for s in state_data if s['Equipment_Uniformity'] == 'Uniform')
    uniform_pollbook = sum(1 for s in state_data if s['Poll_Book_Uniformity'] == 'Uniform')

    print(f"  - States uniform for both: {uniform_both}")
    print(f"  - States uniform for equipment: {uniform_equip}")
    print(f"  - States uniform for poll books: {uniform_pollbook}")

    print("\n" + "=" * 80)
    print("CONDENSING COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
