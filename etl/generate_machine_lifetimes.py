#!/usr/bin/env python3
"""
Generate longitudinal machine lifetime data from year-by-year Verifier machine files.

Consolidates equipment usage across all years (2006-2026) into lifetime records
showing when each (FIPS, Equipment Type, Model) combination was in use.

For each unique equipment:
- First_Year: from Reported_First_Year_In_Use if valid, else earliest survey year
- Last_Year: latest survey year the equipment appeared
- Length_Of_Use: years in service (Last_Year - First_Year + 2, accounting for 2-year cycles)

Model names are normalized to handle rebrands (e.g., Optech IV-C -> Optech 400C).

Output:
- data/processed/machine_lifetimes.csv - Equipment lifetime records
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict


YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]

# Manufacturer name normalization
MANUFACTURER_NORMALIZATION = {
    'Premier (Diebold)': 'Diebold',
    # State agencies
    'MI BoE': 'State of Michigan',
    'SC State Election Commission': 'State of South Carolina',
    'HI Office of Elections': 'State of Hawaii',
    'MO SoS': 'State of Missouri',
    'ND SoS': 'State of North Dakota',
    'AZ SoS': 'State of Arizona',
    'NV SoS': 'State of Nevada',
}

# Model name normalization (for rebrands and data quality fixes)
MODEL_NORMALIZATION = {
    'Optech IV-C': 'Optech 400C',
    'Optech 2': 'Optech Insight',
    'ImageCast': 'ImageCast Precinct BMD',
    'AccuVote OSX': 'AccuVote OS',
    'AccuVote TSX': 'AccuVote TS',
    # ES&S central scanners - group into one family
    'DS450': 'DS Central',
    'DS850': 'DS Central',
    'DS950': 'DS Central',
    # Poll book consolidations
    'Vote Center Pollbook': 'LEDS Poll Book',
    'e-Poll Book': 'LEDS Poll Book',
    'EA Pollbook': 'EA Poll Book',
    'EA Tablet': 'EA Poll Book',
}

# Equipment types to exclude (not actual machines)
EXCLUDED_EQUIPMENT_TYPES = {
    'Hand Counted Paper Ballots',
    'Paper Poll Book',
}

# Combined (manufacturer, model) normalization for context-dependent cases
# Used for In-House Poll Books where model names are generic
COMBINED_NORMALIZATION = {
    # Colorado
    ('CO SoS', 'Electronic PollBook'): ('State of Colorado', 'CO In-House Poll Book'),
    ('CO SoS', 'CO Electronic Pollbook'): ('State of Colorado', 'CO In-House Poll Book'),
    ('CO SoS', 'SCORE'): ('State of Colorado', 'CO In-House Poll Book'),
    # North Carolina
    ('NCSBE', 'SOSA'): ('State of North Carolina', 'NC In-House Poll Book'),
    ('NCSBE', 'OVRD'): ('State of North Carolina', 'NC In-House Poll Book'),
    # Wisconsin
    ('WI Election Commission', 'Badger Book'): ('State of Wisconsin', 'Badger Book'),
    ('State of Wisconsin', 'Badger Book'): ('State of Wisconsin', 'Badger Book'),
    # Rutherford County TN
    ('Rutherford County TN', 'Rutherford Voter Registration Database'): ('Rutherford County TN', 'Rutherford County EPB'),
    ('Rutherford County TN', 'Voter Registration Database'): ('Rutherford County TN', 'Rutherford County EPB'),
    # Orange County FL
    ('Orange County FL', 'OCVotes Laptop Solution'): ('Orange County FL', 'OCVotes ePoll Book'),
    # State SoS entries
    ('WA SoS', 'VoteWA'): ('State of Washington', 'VoteWA'),
    ('OR SoS', 'My Vote'): ('State of Oregon', 'My Vote'),
    ('IA SoS', 'Express Voter'): ('State of Iowa', 'Express Voter'),
}

# Vendor normalization (manufacturer → current parent company after acquisitions)
VENDOR_NORMALIZATION = {
    'Sequoia': 'Dominion',
    'Diebold': 'Dominion',
    'BPro': 'KNOWiNK',
}


def normalize_manufacturer(name):
    """Normalize manufacturer name to canonical form."""
    return MANUFACTURER_NORMALIZATION.get(name, name)


def normalize_model(name):
    """Normalize model name to canonical form."""
    return MODEL_NORMALIZATION.get(name, name)


def normalize_manufacturer_model(manufacturer, model):
    """
    Normalize manufacturer and model together for context-dependent cases.

    Returns (manufacturer, model) tuple.
    """
    key = (manufacturer, model)
    if key in COMBINED_NORMALIZATION:
        return COMBINED_NORMALIZATION[key]
    return (manufacturer, model)


def normalize_vendor(manufacturer):
    """Map manufacturer to current parent company after acquisitions."""
    return VENDOR_NORMALIZATION.get(manufacturer, manufacturer)


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
            equipment_type = row['Equipment Type']
            if equipment_type in EXCLUDED_EQUIPMENT_TYPES:
                continue

            # Apply individual normalizations first
            manufacturer = normalize_manufacturer(row['Manufacturer'])
            model = normalize_model(row['Model'])

            # Apply combined normalization for context-dependent cases
            manufacturer, model = normalize_manufacturer_model(manufacturer, model)

            machines.append({
                'fips': row['FIPS code'],
                'state': row['State'],
                'jurisdiction': row['Jurisdiction'],
                'equipment_type': equipment_type,
                'manufacturer': manufacturer,
                'model': model,
                'first_year_in_use': row.get('First Year in Use', '').strip()
            })

    return machines


def build_equipment_timelines():
    """
    Build timeline of equipment presence across all years.

    Key excludes manufacturer to avoid splitting spans due to rebrands.
    Manufacturer is stored in entries to use the earliest one in output.
    Deduplicates by year to handle cases where normalization creates duplicates
    (e.g., jurisdiction has both AccuVote TS and TSX, which normalize to same model).

    Returns:
        dict: {(fips, type, model): [{year, first_year_in_use, state, jurisdiction, manufacturer}, ...]}
    """
    # Use nested dict to deduplicate by year: {key: {year: entry}}
    timelines = defaultdict(dict)

    for year in YEARS:
        print(f"  Loading {year}...")
        machines = load_machines_for_year(year)

        for m in machines:
            # Key excludes manufacturer - rebrands shouldn't split spans
            key = (m['fips'], m['equipment_type'], m['model'])
            # Only keep first entry for each year (dedup normalized models)
            if year not in timelines[key]:
                timelines[key][year] = {
                    'year': year,
                    'first_year_in_use': m['first_year_in_use'],
                    'state': m['state'],
                    'jurisdiction': m['jurisdiction'],
                    'manufacturer': m['manufacturer']
                }

    # Convert year dicts to lists for span processing
    return {k: list(v.values()) for k, v in timelines.items()}


def parse_first_year_in_use(value):
    """
    Parse First Year in Use field, return int or None.

    Handles negative values (data entry errors) via absolute value.
    Only returns valid years (1950-2026 range).
    """
    if not value or value == '':
        return None

    try:
        year = abs(int(value))  # Handle negative years
        if 1950 <= year <= 2026:
            return year
        return None
    except (ValueError, TypeError):
        return None


def generate_usage_records(timelines):
    """
    Generate one usage record per unique equipment (lifetime tracking).

    For each (fips, equipment_type, model):
    - First_Year: from Reported_First_Year_In_Use if valid, else earliest survey year
    - Last_Year: latest survey year the equipment appeared
    - Years_In_Span: count of survey years with data

    Returns:
        list of dicts ready for CSV output
    """
    records = []

    for key, entries in timelines.items():
        fips, equipment_type, model = key

        # Sort entries by year
        sorted_entries = sorted(entries, key=lambda x: x['year'])
        first_entry = sorted_entries[0]
        last_entry = sorted_entries[-1]

        # Get metadata from earliest entry
        state = first_entry['state']
        jurisdiction = first_entry['jurisdiction']
        manufacturer = first_entry['manufacturer']
        reported_first_year = first_entry['first_year_in_use']

        # Calculate First_Year: use reported if valid, else earliest survey year
        parsed_reported = parse_first_year_in_use(reported_first_year)
        if parsed_reported is not None:
            first_year = parsed_reported
        else:
            first_year = first_entry['year']

        records.append({
            'FIPS': fips,
            'State': state,
            'Jurisdiction': jurisdiction,
            'Equipment_Type': equipment_type,
            'Manufacturer': manufacturer,
            'Vendor': normalize_vendor(manufacturer),
            'Model': model,
            'First_Year': first_year,
            'Last_Year': last_entry['year'],
            'Length_Of_Use': last_entry['year'] - first_year + 2,
            'Reported_First_Year_In_Use': reported_first_year,
            'Source_Data_Record_Count': len(sorted_entries)
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
        'Vendor',
        'Model',
        'First_Year',
        'Last_Year',
        'Length_Of_Use',
        'Reported_First_Year_In_Use',
        'Source_Data_Record_Count'
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

    # Generate records (one per unique equipment)
    print("Generating usage records...")
    records = generate_usage_records(timelines)
    print(f"✓ Generated {len(records):,} equipment lifetime records")
    print()

    # Calculate some stats
    single_year_records = sum(1 for r in records if r['Source_Data_Record_Count'] == 1)
    multi_year_records = len(records) - single_year_records
    records_starting_2006 = sum(1 for r in records if r['First_Year'] <= 2006)

    print("Statistics:")
    print(f"  - Single-year records: {single_year_records:,}")
    print(f"  - Multi-year records: {multi_year_records:,}")
    print(f"  - Records starting 2006 or earlier: {records_starting_2006:,}")
    print()

    # Write output
    output_path = Path('data/processed/machine_lifetimes.csv')
    print(f"Writing to {output_path}...")
    count = write_output(records, output_path)
    print(f"✓ Wrote {count:,} records")

    print()
    print("=" * 80)
    print("✓ MACHINE USAGE DATA GENERATION COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
