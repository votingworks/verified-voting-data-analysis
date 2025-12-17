#!/usr/bin/env python3
"""
Generate human-readable reports from state-level uniformity data.

Takes a year as input and generates a text report showing:
1. Summary statistics
2. States with uniform equipment (grouped by type)
3. States with uniform poll books (grouped by vendor)
4. Cross-tabulation of uniformity patterns

Usage:
    python3 data_quality_tools/state_uniformity/analyze_state_uniformity.py 2026

Input:
    data/state-level/{year}_state-uniformity.csv

Output:
    data_quality_tools/state_uniformity/state_uniformity_report_{year}.txt
"""

import sys
import csv
from pathlib import Path
from collections import defaultdict

# Directories
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
STATE_LEVEL_DIR = PROJECT_ROOT / 'data' / 'state-level'
OUTPUT_DIR = SCRIPT_DIR


def load_state_data(year):
    """
    Load state-level uniformity data for a given year.

    Args:
        year: Year to load

    Returns:
        list of dicts: State-level data
    """
    filepath = STATE_LEVEL_DIR / f'{year}_state-uniformity.csv'

    if not filepath.exists():
        raise FileNotFoundError(f"State-level data file not found: {filepath}\n"
                                f"Run: python3 condense_to_state_level.py {year}")

    states = []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        states = list(reader)

    return states


def generate_summary_stats(states):
    """
    Generate summary statistics about uniformity patterns.

    Args:
        states: List of state data dicts

    Returns:
        dict: Summary counts
    """
    total = len(states)

    both_uniform = sum(1 for s in states if s['Both_Uniform'] == 'Yes')

    equip_uniform = sum(1 for s in states if s['Equipment_Uniformity'] == 'Uniform')
    pollbook_uniform = sum(1 for s in states if s['Poll_Book_Uniformity'] == 'Uniform')

    equip_only = sum(1 for s in states
                     if s['Equipment_Uniformity'] == 'Uniform'
                     and s['Poll_Book_Uniformity'] != 'Uniform')

    pollbook_only = sum(1 for s in states
                        if s['Poll_Book_Uniformity'] == 'Uniform'
                        and s['Equipment_Uniformity'] != 'Uniform')

    mixed_both = sum(1 for s in states
                     if s['Equipment_Uniformity'] not in ['Uniform', 'All Hand Count']
                     and s['Poll_Book_Uniformity'] not in ['Uniform', 'All Paper'])

    return {
        'total': total,
        'both_uniform': both_uniform,
        'equip_uniform': equip_uniform,
        'pollbook_uniform': pollbook_uniform,
        'equip_only': equip_only,
        'pollbook_only': pollbook_only,
        'mixed_both': mixed_both,
    }


def group_by_equipment(states):
    """
    Group states with uniform equipment by equipment type.

    Args:
        states: List of state data dicts

    Returns:
        dict: {equipment_type: [list of state dicts]}
    """
    equipment_groups = defaultdict(list)

    for state in states:
        if state['Equipment_Uniformity'] == 'Uniform':
            equipment_type = state['Primary_Voting_Equipment']
            equipment_groups[equipment_type].append(state)

    return equipment_groups


def group_by_pollbook(states):
    """
    Group states with uniform poll books by vendor.

    Args:
        states: List of state data dicts

    Returns:
        dict: {pollbook_vendor: [list of state dicts]}
    """
    pollbook_groups = defaultdict(list)

    for state in states:
        if state['Poll_Book_Uniformity'] == 'Uniform':
            pollbook_type = state['Poll_Book_Status']
            pollbook_groups[pollbook_type].append(state)

    return pollbook_groups


def generate_crosstab(states):
    """
    Generate 2x2 cross-tabulation of uniformity patterns.

    Args:
        states: List of state data dicts

    Returns:
        dict: Counts for each cell in the matrix
    """
    # [Equipment Uniform, Poll Book Uniform]
    uniform_uniform = sum(1 for s in states
                          if s['Equipment_Uniformity'] == 'Uniform'
                          and s['Poll_Book_Uniformity'] == 'Uniform')

    # [Equipment Uniform, Poll Book Mixed/All Paper]
    uniform_mixed = sum(1 for s in states
                        if s['Equipment_Uniformity'] == 'Uniform'
                        and s['Poll_Book_Uniformity'] != 'Uniform')

    # [Equipment Mixed/All Hand Count, Poll Book Uniform]
    mixed_uniform = sum(1 for s in states
                        if s['Equipment_Uniformity'] != 'Uniform'
                        and s['Poll_Book_Uniformity'] == 'Uniform')

    # [Equipment Mixed/All Hand Count, Poll Book Mixed/All Paper]
    mixed_mixed = sum(1 for s in states
                      if s['Equipment_Uniformity'] != 'Uniform'
                      and s['Poll_Book_Uniformity'] != 'Uniform')

    return {
        'uniform_uniform': uniform_uniform,
        'uniform_mixed': uniform_mixed,
        'mixed_uniform': mixed_uniform,
        'mixed_mixed': mixed_mixed,
    }


def write_text_report(year, states, summary, equipment_groups, pollbook_groups, crosstab):
    """
    Write formatted text report.

    Args:
        year: Year of the data
        states: List of state data dicts
        summary: Summary statistics dict
        equipment_groups: Equipment groupings dict
        pollbook_groups: Poll book groupings dict
        crosstab: Cross-tabulation dict
    """
    output_path = OUTPUT_DIR / f'state_uniformity_report_{year}.txt'

    with open(output_path, 'w', encoding='utf-8') as f:
        # Header
        f.write("=" * 80 + "\n")
        f.write(f"STATE UNIFORMITY ANALYSIS - {year}\n")
        f.write("=" * 80 + "\n\n")

        # Section 1: Summary Statistics
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total states/territories analyzed: {summary['total']}\n\n")

        f.write("Uniformity Patterns:\n")
        f.write(f"  - Both equipment and poll books uniform: {summary['both_uniform']} states\n")
        f.write(f"  - Equipment uniform, poll books mixed: {summary['equip_only']} states\n")
        f.write(f"  - Poll books uniform, equipment mixed: {summary['pollbook_only']} states\n")
        f.write(f"  - Both mixed: {summary['mixed_both']} states\n")
        f.write("\n")

        f.write(f"Total states with uniform equipment: {summary['equip_uniform']}\n")
        f.write(f"Total states with uniform poll books: {summary['pollbook_uniform']}\n")
        f.write("\n\n")

        # Section 2: States with Uniform Equipment
        f.write("=" * 80 + "\n")
        f.write("STATES WITH UNIFORM VOTING EQUIPMENT\n")
        f.write("=" * 80 + "\n\n")

        if equipment_groups:
            f.write(f"Total: {summary['equip_uniform']} states with uniform equipment\n\n")

            for equipment_type in sorted(equipment_groups.keys()):
                state_list = equipment_groups[equipment_type]
                f.write(f"{equipment_type}\n")
                f.write(f"  {len(state_list)} state(s):\n")

                for state in sorted(state_list, key=lambda x: x['State']):
                    f.write(f"    - {state['State']} "
                            f"({state['Non_Hand_Count_Jurisdictions']} jurisdictions)\n")

                f.write("\n")
        else:
            f.write("No states have uniform voting equipment.\n\n")

        # Section 3: States with Uniform Poll Books
        f.write("=" * 80 + "\n")
        f.write("STATES WITH UNIFORM POLL BOOKS\n")
        f.write("=" * 80 + "\n\n")

        if pollbook_groups:
            f.write(f"Total: {summary['pollbook_uniform']} states with uniform poll books\n\n")

            for pollbook_type in sorted(pollbook_groups.keys()):
                state_list = pollbook_groups[pollbook_type]
                f.write(f"{pollbook_type}\n")
                f.write(f"  {len(state_list)} state(s):\n")

                for state in sorted(state_list, key=lambda x: x['State']):
                    non_paper = state['Non_Paper_Poll_Book_Jurisdictions']
                    if non_paper == '0':
                        detail = "(all paper)"
                    else:
                        detail = f"({non_paper} non-paper jurisdictions)"

                    f.write(f"    - {state['State']} {detail}\n")

                f.write("\n")
        else:
            f.write("No states have uniform poll books.\n\n")

        # Section 4: Cross-Tabulation
        f.write("=" * 80 + "\n")
        f.write("CROSS-TABULATION OF UNIFORMITY PATTERNS\n")
        f.write("=" * 80 + "\n\n")

        f.write("                           Poll Book Uniform    Poll Book Mixed\n")
        f.write("-" * 80 + "\n")
        f.write(f"Equipment Uniform          {crosstab['uniform_uniform']:^19} "
                f"{crosstab['uniform_mixed']:^19}\n")
        f.write(f"Equipment Mixed            {crosstab['mixed_uniform']:^19} "
                f"{crosstab['mixed_mixed']:^19}\n")
        f.write("\n")

        # Verify totals
        total_from_crosstab = sum(crosstab.values())
        f.write(f"Total states in cross-tabulation: {total_from_crosstab}\n")

        if total_from_crosstab != summary['total']:
            f.write(f"⚠ Warning: Cross-tab total ({total_from_crosstab}) "
                    f"!= total states ({summary['total']})\n")

        f.write("\n")

        # Footer
        f.write("=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")

    print(f"✓ Report written to {output_path}")


def main():
    """Main execution function."""
    if len(sys.argv) != 2:
        print("Usage: python3 data_quality_tools/state_uniformity/analyze_state_uniformity.py <year>")
        print("Example: python3 data_quality_tools/state_uniformity/analyze_state_uniformity.py 2026")
        sys.exit(1)

    try:
        year = int(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid year")
        sys.exit(1)

    print("=" * 80)
    print(f"GENERATING STATE UNIFORMITY REPORT FOR {year}")
    print("=" * 80)
    print()

    # Load state-level data
    print(f"Loading state-level data for {year}...")
    states = load_state_data(year)
    print(f"✓ Loaded {len(states)} states/territories\n")

    # Generate analyses
    print("Analyzing uniformity patterns...")
    summary = generate_summary_stats(states)
    equipment_groups = group_by_equipment(states)
    pollbook_groups = group_by_pollbook(states)
    crosstab = generate_crosstab(states)
    print("✓ Analysis complete\n")

    # Write report
    print("Writing text report...")
    write_text_report(year, states, summary, equipment_groups, pollbook_groups, crosstab)

    print("\n" + "=" * 80)
    print("REPORT GENERATION COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
