#!/usr/bin/env python3
"""
Inspect jurisdictions with no equipment turnover (2006-2026).

Reads from: ../../data/voting_system_time_series.csv
Outputs: no_turnover_jurisdictions.txt

Finds jurisdictions that only have baseline records (no transition records).
"""

import csv
from pathlib import Path
from collections import Counter, defaultdict

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / 'data'


def load_no_turnover_from_csv():
    """Load no-turnover jurisdictions from time series CSV.

    Finds jurisdictions that ONLY have baseline rows (no transition rows).
    Excludes Hand Count jurisdictions.
    """
    csv_path = DATA_DIR / 'voting_system_time_series.csv'

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {csv_path}\n"
            "Run identify_voting_equipment_turnover.py first to generate it."
        )

    # First pass: identify which FIPS have transitions
    fips_with_transitions = set()
    baseline_rows = {}

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fips = row['FIPS']
            record_type = row['Record_Type']

            if record_type in ('between_system', 'within_system'):
                fips_with_transitions.add(fips)
            elif record_type == 'baseline':
                baseline_rows[fips] = row

    # Second pass: collect baseline-only jurisdictions (excluding Hand Count)
    no_turnover = {}
    for fips, row in baseline_rows.items():
        if fips not in fips_with_transitions:
            # Use To_* columns for baseline rows (From_* are empty)
            equipment = row['To_Equipment']
            if equipment != 'Hand Count':
                # Create a compatible row format for the report
                # Calculate lifecycle as 2026 - baseline year
                baseline_year = int(row['To_Year']) if row['To_Year'] else 2006
                years_between = 2026 - baseline_year

                no_turnover[fips] = {
                    'FIPS': fips,
                    'State': row['State'],
                    'Jurisdiction': row['Jurisdiction'],
                    'From_Year': baseline_year,  # For reporting compatibility
                    'From_Equipment': equipment,
                    'From_Vendor': row['To_Vendor'],
                    'From_System': row['To_System'],
                    'From_DRE': row['To_DRE'],
                    'From_Marking_Method': row['To_Marking_Method'],
                    'Years_Between': years_between
                }

    return no_turnover


def write_no_turnover_report(no_turnover, output_file):
    """Write detailed report of no-turnover jurisdictions."""

    # Sort by state, then jurisdiction
    sorted_jurisdictions = sorted(
        no_turnover.items(),
        key=lambda x: (x[1]['State'], x[1]['Jurisdiction'])
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('JURISDICTIONS WITH NO EQUIPMENT TURNOVER (2006-2026)\n')
        f.write('EXCLUDING: Hand Count\n')
        f.write('=' * 100 + '\n\n')
        f.write(f'Total: {len(no_turnover):,} jurisdictions\n\n')
        f.write('=' * 100 + '\n\n')

        # Write jurisdiction details by state
        current_state = None
        for fips, row in sorted_jurisdictions:
            state = row['State']

            if state != current_state:
                if current_state is not None:
                    f.write('\n')
                f.write(f'\n{state}\n')
                f.write('-' * 100 + '\n')
                current_state = state

            f.write(f"\n{row['Jurisdiction']} (FIPS: {fips})\n")
            f.write(f"  Equipment: {row['From_Equipment']}\n")
            f.write(f"  Vendor: {row['From_Vendor']}\n")
            f.write(f"  System: {row['From_System']}\n")
            f.write(f"  First Year: {row['From_Year']}\n")
            f.write(f"  Lifecycle: {row['Years_Between']} years\n")
            f.write(f"  DRE: {row['From_DRE']}\n")
            f.write(f"  Marking Method: {row['From_Marking_Method']}\n")

        # Summary statistics
        f.write('\n\n' + '=' * 100 + '\n')
        f.write('SUMMARY STATISTICS\n')
        f.write('=' * 100 + '\n\n')

        # Equipment distribution
        equipment_counts = Counter(row['From_Equipment'] for row in no_turnover.values())
        f.write('Equipment Distribution:\n')
        for equipment, count in sorted(equipment_counts.items(), key=lambda x: -x[1]):
            pct = count / len(no_turnover) * 100
            f.write(f"  {equipment}: {count:,} ({pct:.1f}%)\n")

        # Vendor distribution
        vendor_counts = Counter(row['From_Vendor'] for row in no_turnover.values())
        f.write('\nVendor Distribution:\n')
        for vendor, count in sorted(vendor_counts.items(), key=lambda x: -x[1]):
            if vendor:
                pct = count / len(no_turnover) * 100
                f.write(f"  {vendor}: {count:,} ({pct:.1f}%)\n")

        # State distribution
        state_counts = Counter(row['State'] for row in no_turnover.values())
        f.write('\nTop 10 States:\n')
        for state, count in sorted(state_counts.items(), key=lambda x: -x[1])[:10]:
            pct = count / len(no_turnover) * 100
            f.write(f"  {state}: {count:,} ({pct:.1f}%)\n")

        # Lifecycle distribution
        lifecycle_counts = Counter(int(row['Years_Between']) for row in no_turnover.values())
        f.write('\nLifecycle Length Distribution:\n')
        for years, count in sorted(lifecycle_counts.items()):
            pct = count / len(no_turnover) * 100
            f.write(f"  {years} years: {count:,} ({pct:.1f}%)\n")


def main():
    print("=" * 80)
    print("INSPECTING NO-TURNOVER JURISDICTIONS")
    print("=" * 80)
    print()

    print("Loading no-turnover jurisdictions from CSV...")
    no_turnover = load_no_turnover_from_csv()
    print(f"✓ Loaded {len(no_turnover):,} jurisdictions")

    output_file = SCRIPT_DIR / 'no_turnover_jurisdictions.txt'
    print(f"\nWriting report to {output_file}...")
    write_no_turnover_report(no_turnover, output_file)
    print(f"✓ Report written")

    print()
    print("=" * 80)
    print()


if __name__ == '__main__':
    main()
