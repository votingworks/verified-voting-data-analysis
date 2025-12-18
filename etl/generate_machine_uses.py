#!/usr/bin/env python3
"""
Generate longitudinal machine usage data from year-by-year Verifier machine files.

Consolidates equipment usage across all years (2006-2026) into spans showing
when each (FIPS, Equipment Type, Manufacturer, Model) combination was in use.

Output:
- data/processed/machine_uses.csv - Equipment usage spans with first/last year
"""

import csv
from pathlib import Path
from collections import defaultdict


YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]


def load_machines_for_year(year):
    """
    Load machine data for a given year.

    Returns:
        list of dicts with keys: fips, state, jurisdiction, equipment_type,
                                  manufacturer, model, first_year_in_use
    """
    filepath = Path(f'data/extracted/{year}_verifier-machines.csv')

    if not filepath.exists():
        print(f"  Warning: {filepath} not found, skipping...")
        return []

    machines = []

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        # Skip title row
        lines = f.readlines()
        reader = csv.DictReader(lines[1:])

        for row in reader:
            machines.append({
                'fips': row['FIPS code'],
                'state': row['State'],
                'jurisdiction': row['Jurisdiction'],
                'equipment_type': row['Equipment Type'],
                'manufacturer': row['Manufacturer'],
                'model': row['Model'],
                'first_year_in_use': row.get('First Year in Use', '').strip()
            })

    return machines


def build_equipment_timelines():
    """
    Build timeline of equipment presence across all years.

    Returns:
        dict: {(fips, type, mfr, model): [(year, first_year_in_use, state, jurisdiction), ...]}
    """
    timelines = defaultdict(list)

    for year in YEARS:
        print(f"  Loading {year}...")
        machines = load_machines_for_year(year)

        for m in machines:
            key = (m['fips'], m['equipment_type'], m['manufacturer'], m['model'])
            timelines[key].append({
                'year': year,
                'first_year_in_use': m['first_year_in_use'],
                'state': m['state'],
                'jurisdiction': m['jurisdiction']
            })

    return timelines


def parse_first_year_in_use(value):
    """
    Parse First Year in Use field, return int or None.

    Only returns valid positive years (1950-2026 range).
    """
    if not value or value == '':
        return None

    try:
        year = int(value)
        # Only valid positive years
        if 1950 <= year <= 2026:
            return year
        return None
    except (ValueError, TypeError):
        return None


def find_consecutive_spans(entries):
    """
    Find consecutive spans of years in timeline entries.

    A gap occurs when expected next survey year is missing.
    Survey years are every 2 years: 2006, 2008, 2010, etc.

    Args:
        entries: List of dicts with 'year' key, sorted by year

    Returns:
        list of lists: [[entry1, entry2, ...], [entry5, entry6, ...], ...]
    """
    if not entries:
        return []

    # Sort by year
    sorted_entries = sorted(entries, key=lambda x: x['year'])

    spans = []
    current_span = [sorted_entries[0]]

    for i in range(1, len(sorted_entries)):
        prev_year = sorted_entries[i-1]['year']
        curr_year = sorted_entries[i]['year']

        # Expected next survey year is +2
        if curr_year == prev_year + 2:
            # Consecutive
            current_span.append(sorted_entries[i])
        else:
            # Gap detected - start new span
            spans.append(current_span)
            current_span = [sorted_entries[i]]

    # Don't forget the last span
    spans.append(current_span)

    return spans


def generate_usage_records(timelines):
    """
    Generate usage records from equipment timelines.

    Returns:
        list of dicts ready for CSV output
    """
    records = []

    for key, entries in timelines.items():
        fips, equipment_type, manufacturer, model = key

        # Find consecutive spans
        spans = find_consecutive_spans(entries)

        for span in spans:
            first_entry = span[0]
            last_entry = span[-1]

            # Get metadata from first entry
            state = first_entry['state']
            jurisdiction = first_entry['jurisdiction']
            reported_first_year = first_entry['first_year_in_use']

            # Calculate First_Year
            span_start_year = first_entry['year']
            parsed_reported = parse_first_year_in_use(reported_first_year)

            if span_start_year == 2006 and parsed_reported is not None:
                # Use reported first year if span starts in 2006 and value is valid
                first_year = parsed_reported
            else:
                # Use actual first survey year
                first_year = span_start_year

            records.append({
                'FIPS': fips,
                'State': state,
                'Jurisdiction': jurisdiction,
                'Equipment_Type': equipment_type,
                'Manufacturer': manufacturer,
                'Model': model,
                'First_Year': first_year,
                'Last_Year': last_entry['year'],
                'Reported_First_Year_In_Use': reported_first_year,
                'Years_In_Span': len(span)
            })

    return records


def write_output(records, output_path):
    """Write usage records to CSV."""
    # Sort by State, Jurisdiction, Equipment_Type, First_Year
    sorted_records = sorted(
        records,
        key=lambda x: (x['State'], x['Jurisdiction'], x['Equipment_Type'], x['First_Year'])
    )

    fieldnames = [
        'FIPS',
        'State',
        'Jurisdiction',
        'Equipment_Type',
        'Manufacturer',
        'Model',
        'First_Year',
        'Last_Year',
        'Reported_First_Year_In_Use',
        'Years_In_Span'
    ]

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted_records)

    return len(sorted_records)


def main():
    """Main execution function."""
    print("=" * 80)
    print("GENERATING MACHINE USAGE LONGITUDINAL DATA")
    print("=" * 80)
    print()

    # Build timelines
    print("Loading machine data from all years...")
    timelines = build_equipment_timelines()
    print(f"✓ Found {len(timelines):,} unique equipment combinations")
    print()

    # Generate records
    print("Generating usage records...")
    records = generate_usage_records(timelines)
    print(f"✓ Generated {len(records):,} usage span records")
    print()

    # Calculate some stats
    single_year_spans = sum(1 for r in records if r['Years_In_Span'] == 1)
    multi_year_spans = len(records) - single_year_spans
    spans_starting_2006 = sum(1 for r in records if r['First_Year'] <= 2006)

    print("Statistics:")
    print(f"  - Single-year spans: {single_year_spans:,}")
    print(f"  - Multi-year spans: {multi_year_spans:,}")
    print(f"  - Spans starting 2006 or earlier: {spans_starting_2006:,}")
    print()

    # Write output
    output_path = Path('data/processed/machine_uses.csv')
    print(f"Writing to {output_path}...")
    count = write_output(records, output_path)
    print(f"✓ Wrote {count:,} records")

    print()
    print("=" * 80)
    print("✓ MACHINE USAGE DATA GENERATION COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
