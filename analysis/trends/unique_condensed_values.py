#!/usr/bin/env python3
"""
Generate report of unique condensed values across all years.
Extracts Primary Voting Equipment, Primary Voting System, and Primary Voting Vendor.
"""

import csv
from pathlib import Path
from collections import Counter

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'reports'

def extract_all_equipment():
    """Extract all unique equipment summaries, families, and vendors across all years."""

    years = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]
    all_equipment = Counter()
    all_families = Counter()
    all_vendors = Counter()
    equipment_to_family = {}
    equipment_to_vendor = {}

    for year in years:
        filepath = SCRIPT_DIR / f'../../data/processed/jurisdictions/{year}_verifier-jurisdictions-condensed.csv'

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                reader = csv.DictReader(lines[1:])  # Skip title row

                for row in reader:
                    equipment = row.get('Primary Voting Equipment', '').strip()
                    family = row.get('Primary Voting System', '').strip()
                    vendor = row.get('Primary Voting Vendor', '').strip()

                    if equipment:
                        all_equipment[equipment] += 1
                        all_families[family] += 1
                        all_vendors[vendor] += 1
                        equipment_to_family[equipment] = family
                        equipment_to_vendor[equipment] = vendor
        except FileNotFoundError:
            print(f"Warning: {filepath} not found, skipping...")

    # Write to file
    output_file = OUTPUT_DIR / 'unique_condensed_values.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('UNIQUE CONDENSED VALUES ACROSS 2006-2026\n')
        f.write('=' * 120 + '\n\n')
        f.write(f'Total unique equipment values: {len(all_equipment)}\n')
        f.write(f'Total occurrences: {sum(all_equipment.values()):,}\n\n')
        f.write('=' * 120 + '\n\n')

        # Sort alphabetically for easy review
        f.write('PRIMARY VOTING EQUIPMENT (with Vendor and System):\n')
        f.write('-' * 120 + '\n\n')
        f.write(f'{"Primary Voting Equipment":<60} {"Count":<15} {"Vendor":<20} {"System"}\n')
        f.write('-' * 120 + '\n\n')

        for equipment in sorted(all_equipment.keys()):
            count = all_equipment[equipment]
            vendor = equipment_to_vendor.get(equipment, '')
            family = equipment_to_family.get(equipment, '')
            f.write(f'{equipment:<60} ({count:>6,} occurrences) {vendor:<20} {family}\n')

        f.write('\n\n')
        f.write('=' * 120 + '\n\n')

        # Sort by frequency
        f.write('EQUIPMENT SORTED BY FREQUENCY (most common first):\n')
        f.write('-' * 120 + '\n\n')

        for equipment, count in sorted(all_equipment.items(), key=lambda x: -x[1]):
            f.write(f'{count:>6,} | {equipment}\n')

        f.write('\n\n')
        f.write('=' * 120 + '\n\n')

        # Equipment systems section
        f.write('PRIMARY VOTING SYSTEMS:\n')
        f.write('-' * 120 + '\n\n')
        f.write(f'Total unique systems: {len(all_families)}\n')
        f.write(f'Total system occurrences: {sum(all_families.values()):,}\n\n')

        # Sort families alphabetically
        f.write('ALPHABETICALLY SORTED:\n')
        f.write('-' * 60 + '\n\n')

        for family in sorted(all_families.keys()):
            count = all_families[family]
            f.write(f'{family:<50} ({count:,} occurrences)\n')

        f.write('\n\n')

        # Sort families by frequency
        f.write('SORTED BY FREQUENCY (most common first):\n')
        f.write('-' * 60 + '\n\n')

        for family, count in sorted(all_families.items(), key=lambda x: -x[1]):
            f.write(f'{count:>6,} | {family}\n')

        f.write('\n\n')
        f.write('=' * 120 + '\n\n')

        # Vendors section
        f.write('PRIMARY VOTING VENDORS:\n')
        f.write('-' * 120 + '\n\n')
        f.write(f'Total unique vendors: {len(all_vendors)}\n')
        f.write(f'Total vendor occurrences: {sum(all_vendors.values()):,}\n\n')

        # Sort vendors alphabetically
        f.write('ALPHABETICALLY SORTED:\n')
        f.write('-' * 60 + '\n\n')

        for vendor in sorted(all_vendors.keys()):
            count = all_vendors[vendor]
            f.write(f'{vendor:<50} ({count:,} occurrences)\n')

        f.write('\n\n')

        # Sort vendors by frequency
        f.write('SORTED BY FREQUENCY (most common first):\n')
        f.write('-' * 60 + '\n\n')

        for vendor, count in sorted(all_vendors.items(), key=lambda x: -x[1]):
            f.write(f'{count:>6,} | {vendor}\n')

    return output_file, len(all_equipment), sum(all_equipment.values()), len(all_families), sum(all_families.values()), len(all_vendors), sum(all_vendors.values())

if __name__ == '__main__':
    output_file, unique_count, total_count, unique_families, total_family_count, unique_vendors, total_vendor_count = extract_all_equipment()
    print(f"✓ Extracted {unique_count:,} unique Primary Voting Equipment values")
    print(f"  Total occurrences: {total_count:,}")
    print(f"✓ Extracted {unique_families:,} unique Primary Voting Systems")
    print(f"  Total system occurrences: {total_family_count:,}")
    print(f"✓ Extracted {unique_vendors:,} unique Primary Voting Vendors")
    print(f"  Total vendor occurrences: {total_vendor_count:,}")
    print(f"  Written to: {output_file}")
