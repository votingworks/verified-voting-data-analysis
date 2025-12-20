#!/usr/bin/env python3
"""
Generate pollbook_transitions.csv - poll book status changes over time.

Reads jurisdictions_time_series.csv and detects changes in Poll_Book_Status
between consecutive election cycles.

Transition types:
- baseline: First observation for a jurisdiction (2006 or first appearance)
- to_electronic: Paper → any electronic vendor/In-House
- vendor_change: Electronic → different electronic vendor
- to_paper: Electronic → Paper

Output: data/processed/pollbook_transitions.csv
"""

import csv
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'

YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]


def load_time_series():
    """
    Load jurisdictions_time_series.csv.

    Returns:
        dict: {fips: {year: {state, jurisdiction, poll_book_status, registered_voters}}}
    """
    filepath = DATA_DIR / 'jurisdictions_time_series.csv'
    data = defaultdict(dict)

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fips = row['FIPS']
            year = int(row['Year'])
            data[fips][year] = {
                'state': row['State'],
                'jurisdiction': row['Jurisdiction'],
                'poll_book_status': row['Poll_Book_Status'],
                'registered_voters': row['Registered_Voters'],
            }

    return data


def classify_transition(from_status, to_status):
    """
    Classify the type of poll book transition.

    Args:
        from_status: Previous poll book status (or None for baseline)
        to_status: New poll book status

    Returns:
        str: Transition type
    """
    if from_status is None:
        return 'baseline'

    from_is_paper = (from_status == 'Paper')
    to_is_paper = (to_status == 'Paper')

    if from_is_paper and not to_is_paper:
        return 'to_electronic'
    elif not from_is_paper and to_is_paper:
        return 'to_paper'
    elif not from_is_paper and not to_is_paper:
        return 'vendor_change'
    else:
        # Paper → Paper (shouldn't happen, but handle it)
        return 'no_change'


def detect_transitions(data):
    """
    Detect poll book status transitions for all jurisdictions.

    Args:
        data: Dict from load_time_series()

    Returns:
        list: Transition records
    """
    transitions = []

    for fips, year_data in data.items():
        # Get years for this jurisdiction, sorted
        years = sorted(year_data.keys())

        if not years:
            continue

        # Get jurisdiction metadata from most recent year
        latest = year_data[years[-1]]
        state = latest['state']
        jurisdiction = latest['jurisdiction']

        # First year is always a baseline
        first_year = years[0]
        first_status = year_data[first_year]['poll_book_status']

        transitions.append({
            'FIPS': fips,
            'State': state,
            'Jurisdiction': jurisdiction,
            'From_Year': '',
            'From_Poll_Book_Status': '',
            'To_Year': first_year,
            'To_Poll_Book_Status': first_status,
            'Transition_Type': 'baseline',
            'Years_Between': '',
        })

        # Walk through consecutive years looking for changes
        for i in range(len(years) - 1):
            from_year = years[i]
            to_year = years[i + 1]

            from_status = year_data[from_year]['poll_book_status']
            to_status = year_data[to_year]['poll_book_status']

            # Skip if no change
            if from_status == to_status:
                continue

            transition_type = classify_transition(from_status, to_status)

            transitions.append({
                'FIPS': fips,
                'State': state,
                'Jurisdiction': jurisdiction,
                'From_Year': from_year,
                'From_Poll_Book_Status': from_status,
                'To_Year': to_year,
                'To_Poll_Book_Status': to_status,
                'Transition_Type': transition_type,
                'Years_Between': to_year - from_year,
            })

    return transitions


def write_transitions(transitions, output_path):
    """
    Write transitions to CSV file.

    Args:
        transitions: List of transition records
        output_path: Path to output file
    """
    fieldnames = [
        'FIPS', 'State', 'Jurisdiction',
        'From_Year', 'From_Poll_Book_Status',
        'To_Year', 'To_Poll_Book_Status',
        'Transition_Type', 'Years_Between',
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transitions)


def print_summary(transitions):
    """Print summary statistics."""
    from collections import Counter

    print("\n" + "=" * 60)
    print("POLLBOOK TRANSITIONS SUMMARY")
    print("=" * 60)

    # Count by transition type
    type_counts = Counter(t['Transition_Type'] for t in transitions)
    print("\nTransitions by type:")
    for t_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t_type:20s}: {count:,}")

    # Count non-baseline transitions by year
    print("\nTransitions by year (excluding baseline):")
    year_counts = Counter(
        t['To_Year'] for t in transitions
        if t['Transition_Type'] != 'baseline'
    )
    for year in sorted(year_counts.keys()):
        print(f"  {year}: {year_counts[year]:,}")

    # Most common vendor changes
    print("\nMost common transitions (excluding baseline):")
    transition_pairs = Counter(
        f"{t['From_Poll_Book_Status']} -> {t['To_Poll_Book_Status']}"
        for t in transitions
        if t['Transition_Type'] != 'baseline'
    )
    for pair, count in transition_pairs.most_common(10):
        print(f"  {pair:40s}: {count:,}")


def main():
    print("=" * 60)
    print("GENERATING POLLBOOK TRANSITIONS")
    print("=" * 60)

    # Load time series data
    print("\nLoading jurisdictions time series...")
    data = load_time_series()
    print(f"  Loaded data for {len(data):,} jurisdictions")

    # Detect transitions
    print("\nDetecting poll book transitions...")
    transitions = detect_transitions(data)
    print(f"  Found {len(transitions):,} transitions")

    # Write output
    output_path = DATA_DIR / 'pollbook_transitions.csv'
    print(f"\nWriting to {output_path}...")
    write_transitions(transitions, output_path)
    print(f"  Done!")

    # Print summary
    print_summary(transitions)

    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
