#!/usr/bin/env python3
"""
Analyze poll book changes over time (2006-2026).

Tracks poll book status changes across jurisdictions, recording:
- Year of change
- Poll book status before and after
- Years between changes
- Whether this is the first change from 2006 baseline

Outputs:
- data/pollbook_turnover.csv - All poll book status changes
"""

import csv
from pathlib import Path
from collections import Counter, defaultdict


YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]


def load_all_years():
    """
    Load poll book data for all years (2006-2026).

    Returns:
        dict: {year: {fips: {state, jurisdiction, status}}}
    """
    data_by_year = {}

    for year in YEARS:
        filepath = f'data/processed/jurisdictions/{year}_verifier-jurisdictions-condensed.csv'

        if not Path(filepath).exists():
            print(f"Warning: {filepath} not found, skipping...")
            continue

        data_by_year[year] = {}

        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            reader = csv.DictReader(lines[1:])  # Skip title row

            for row in reader:
                fips = row['FIPS code']
                status = row.get('Poll Book Status', '').strip()

                data_by_year[year][fips] = {
                    'state': row['State'],
                    'jurisdiction': row['Jurisdiction'],
                    'status': status
                }

    return data_by_year


def initialize_baselines(data_2006):
    """
    Initialize jurisdiction timelines with 2006 baseline.

    For poll books, we always use 2006 as the baseline since there's no
    "First Year in Use" field for poll book data.

    Returns:
        dict: {fips: {state, jurisdiction, timeline: [baseline_entry]}}
    """
    timelines = {}

    for fips, data in data_2006.items():
        # Skip if missing poll book status
        if not data['status']:
            continue

        timelines[fips] = {
            'state': data['state'],
            'jurisdiction': data['jurisdiction'],
            'timeline': [{
                'year': 2006,
                'status': data['status'],
                'is_baseline': True
            }]
        }

    return timelines


def detect_changes(timelines, data_by_year, years):
    """
    Walk through years sequentially, detecting poll book status changes.

    For each year pair (year_from → year_to):
        For each jurisdiction:
            If poll book status changed:
                Add change entry to timeline

    Modifies timelines in place.
    """
    for i in range(len(years) - 1):
        year_from = years[i]
        year_to = years[i + 1]

        # Skip if either year's data is missing
        if year_from not in data_by_year or year_to not in data_by_year:
            continue

        for fips in timelines:
            # Get current poll book status (last entry in timeline)
            current = timelines[fips]['timeline'][-1]

            # Get status in year_to (if jurisdiction still exists)
            if fips in data_by_year[year_to]:
                new_data = data_by_year[year_to][fips]

                # Skip if missing status
                if not new_data['status']:
                    continue

                # Detect status change
                if new_data['status'] != current['status']:
                    timelines[fips]['timeline'].append({
                        'year': year_to,
                        'status': new_data['status'],
                        'is_baseline': False
                    })


def generate_turnover_csv(timelines, output_file):
    """
    Convert timelines to CSV file of poll book status changes.

    For each jurisdiction with multiple timeline entries:
        For each change (entry[i] → entry[i+1]):
            Write row with before/after data

    Returns:
        int: Number of turnover events
    """
    turnovers = []

    for fips, data in timelines.items():
        timeline = data['timeline']

        # Skip jurisdictions with no changes
        if len(timeline) <= 1:
            continue

        # For each pair of consecutive entries
        for i in range(len(timeline) - 1):
            from_entry = timeline[i]
            to_entry = timeline[i + 1]

            turnover_dict = {
                'FIPS': fips,
                'State': data['state'],
                'Jurisdiction': data['jurisdiction'],
                'From_Year': from_entry['year'] if not from_entry['is_baseline'] else '',
                'From_Status': from_entry['status'],
                'To_Year': to_entry['year'],
                'To_Status': to_entry['status'],
                'Years_Between': to_entry['year'] - from_entry['year'],
                'From_Baseline': from_entry['is_baseline']
            }

            turnovers.append(turnover_dict)

    # Write CSV file
    fieldnames = [
        'FIPS', 'State', 'Jurisdiction',
        'From_Year', 'From_Status',
        'To_Year', 'To_Status',
        'Years_Between', 'From_Baseline'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(turnovers)

    return len(turnovers)


def print_summary_statistics(timelines, turnovers_count):
    """Print summary statistics about poll book turnovers."""
    print("\n" + "="*80)
    print("POLL BOOK TURNOVER ANALYSIS SUMMARY")
    print("="*80)

    # Count jurisdictions by number of turnovers
    turnover_counts = defaultdict(int)
    for fips, data in timelines.items():
        num_changes = len(data['timeline']) - 1
        turnover_counts[num_changes] += 1

    print(f"\nTotal jurisdictions tracked: {len(timelines)}")
    print(f"Total turnover events: {turnovers_count}")
    print(f"\nJurisdictions by number of turnovers:")
    for num_changes in sorted(turnover_counts.keys()):
        count = turnover_counts[num_changes]
        print(f"  {num_changes} changes: {count:4d} jurisdictions")

    # Count transitions by type
    transitions = Counter()
    for fips, data in timelines.items():
        timeline = data['timeline']
        for i in range(len(timeline) - 1):
            from_status = timeline[i]['status']
            to_status = timeline[i + 1]['status']
            transitions[f"{from_status} → {to_status}"] += 1

    print(f"\nMost common transitions (top 10):")
    for transition, count in transitions.most_common(10):
        print(f"  {transition:40s}: {count:4d}")

    # Calculate average years between turnovers
    years_between = []
    for fips, data in timelines.items():
        timeline = data['timeline']
        for i in range(len(timeline) - 1):
            years_between.append(timeline[i + 1]['year'] - timeline[i]['year'])

    if years_between:
        avg_years = sum(years_between) / len(years_between)
        print(f"\nAverage years between turnovers: {avg_years:.1f}")

    # Count turnovers by year
    turnovers_by_year = Counter()
    for fips, data in timelines.items():
        for entry in data['timeline']:
            if not entry['is_baseline']:
                turnovers_by_year[entry['year']] += 1

    print(f"\nTurnovers by year:")
    for year in sorted(turnovers_by_year.keys()):
        count = turnovers_by_year[year]
        print(f"  {year}: {count:4d} turnovers")


def main():
    """Main execution function."""
    print("="*80)
    print("POLL BOOK TURNOVER DETECTION")
    print("="*80)
    print()

    # Load data
    print("Loading poll book data for all years...")
    data_by_year = load_all_years()
    print(f"✓ Loaded {len(data_by_year)} years of data")
    print()

    # Initialize baselines (2006)
    print("Initializing jurisdiction timelines with 2006 baseline...")
    if 2006 not in data_by_year:
        print("Error: 2006 data not found!")
        return

    timelines = initialize_baselines(data_by_year[2006])
    print(f"✓ Initialized {len(timelines)} jurisdictions")
    print()

    # Detect changes
    print("Detecting poll book status changes across years...")
    detect_changes(timelines, data_by_year, YEARS)
    print("✓ Change detection complete")
    print()

    # Generate output
    output_file = 'data/processed/pollbook_turnover.csv'
    print(f"Writing turnover data to {output_file}...")
    turnovers_count = generate_turnover_csv(timelines, output_file)
    print(f"✓ Wrote {turnovers_count} turnover events")

    # Print summary
    print_summary_statistics(timelines, turnovers_count)

    print("\n" + "="*80)
    print("✓ ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nOutput file: {output_file}")
    print()


if __name__ == "__main__":
    main()
