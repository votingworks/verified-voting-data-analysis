#!/usr/bin/env python3
"""
Find jurisdictions with multiple instances of specific equipment types.

Analyzes all machines files (2006-2026) and identifies jurisdictions that have:
- Multiple "Ballot Marking Device"s
- Multiple "Hand-Fed Optical Scanner"s
- Multiple DRE machines (DRE-Push Button, DRE-Touchscreen, DRE-Dial, Hybrid Optical Scan/DRE)

Usage: python3 find_duplicate_equipment.py
Output: Writes results to duplicate_equipment_report.txt
"""

import csv
from collections import defaultdict
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'reports'

# Years to analyze
YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]

# Equipment types of interest
EQUIPMENT_TYPES_OF_INTEREST = {
    'Ballot Marking Device',
    'Hand-Fed Optical Scanner',
    'Hybrid Optical Scan/BMD',
    'Hybrid Optical Scan/DRE',
    'DRE-Push Button',
    'DRE-Touchscreen',
    'DRE-Dial'
}

# Group Hand-Fed and Hybrid Optical Scan types together
HANDFED_SCANNER_TYPES = {
    'Hand-Fed Optical Scanner',
    'Hybrid Optical Scan/BMD',
    'Hybrid Optical Scan/DRE'
}

# Group DRE types for reporting (excluding Hybrid Optical Scan types)
DRE_TYPES = {
    'DRE-Push Button',
    'DRE-Touchscreen',
    'DRE-Dial'
}


def load_machines_data(year):
    """
    Load machines data for a given year.

    Returns:
        dict: {fips_code: [(equipment_type, manufacturer, model), ...]}
    """
    filepath = SCRIPT_DIR / f'../../data/extracted/{year}_verifier-machines.csv'

    if not filepath.exists():
        print(f"Warning: {filepath} not found, skipping...")
        return {}

    equipment_by_jurisdiction = defaultdict(list)

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        # Skip title row
        lines = f.readlines()
        reader = csv.DictReader(lines[1:])

        for row in reader:
            fips = row.get('FIPS code', '').strip()
            equipment_type = row.get('Equipment Type', '').strip()
            manufacturer = row.get('Manufacturer', '').strip()
            model = row.get('Model', '').strip()

            # Only track equipment types we care about
            if equipment_type in EQUIPMENT_TYPES_OF_INTEREST:
                equipment_by_jurisdiction[fips].append({
                    'type': equipment_type,
                    'manufacturer': manufacturer,
                    'model': model,
                    'state': row.get('State', '').strip(),
                    'jurisdiction': row.get('Jurisdiction', '').strip()
                })

    return equipment_by_jurisdiction


def find_duplicates_by_year(year):
    """
    Find jurisdictions with multiple instances of specific equipment types for a given year.

    Returns:
        dict: {equipment_type: [(fips, state, jurisdiction, count, details), ...]}
    """
    equipment_data = load_machines_data(year)

    # Track duplicates by equipment type
    duplicates = {
        'Ballot Marking Device': [],
        'Hand-Fed Optical Scanner': [],
        'DRE (all types)': []
    }

    for fips, equipment_list in equipment_data.items():
        # Count each equipment type
        bmd_count = sum(1 for e in equipment_list if e['type'] == 'Ballot Marking Device')
        handfed_count = sum(1 for e in equipment_list if e['type'] in HANDFED_SCANNER_TYPES)
        dre_count = sum(1 for e in equipment_list if e['type'] in DRE_TYPES)

        # Get jurisdiction info (same for all equipment in this jurisdiction)
        state = equipment_list[0]['state'] if equipment_list else ''
        jurisdiction = equipment_list[0]['jurisdiction'] if equipment_list else ''

        # Track if multiple BMDs
        if bmd_count > 1:
            bmd_equipment = [e for e in equipment_list if e['type'] == 'Ballot Marking Device']
            bmd_details = [f"{e['manufacturer']} {e['model']}" for e in bmd_equipment]
            duplicates['Ballot Marking Device'].append({
                'fips': fips,
                'state': state,
                'jurisdiction': jurisdiction,
                'count': bmd_count,
                'details': bmd_details
            })

        # Track if multiple Hand-Fed/Hybrid scanners
        if handfed_count > 1:
            handfed_equipment = [e for e in equipment_list if e['type'] in HANDFED_SCANNER_TYPES]
            handfed_details = [f"{e['type']}: {e['manufacturer']} {e['model']}" for e in handfed_equipment]
            duplicates['Hand-Fed Optical Scanner'].append({
                'fips': fips,
                'state': state,
                'jurisdiction': jurisdiction,
                'count': handfed_count,
                'details': handfed_details
            })

        # Track if multiple DREs
        if dre_count > 1:
            dre_equipment = [e for e in equipment_list if e['type'] in DRE_TYPES]
            dre_details = [f"{e['type']}: {e['manufacturer']} {e['model']}" for e in dre_equipment]
            duplicates['DRE (all types)'].append({
                'fips': fips,
                'state': state,
                'jurisdiction': jurisdiction,
                'count': dre_count,
                'details': dre_details
            })

    return duplicates


def generate_report():
    """Generate comprehensive report of duplicate equipment across all years."""

    output_file = OUTPUT_DIR / 'duplicate_equipment_report.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('=' * 100 + '\n')
        f.write('DUPLICATE EQUIPMENT REPORT\n')
        f.write('Jurisdictions with Multiple Instances of Specific Equipment Types\n')
        f.write('=' * 100 + '\n\n')
        f.write('This report identifies jurisdictions that have multiple instances of:\n')
        f.write('  - Ballot Marking Devices (BMDs)\n')
        f.write('  - Hand-Fed Optical Scanners (including Hybrid Optical Scan types)\n')
        f.write('  - DRE machines (DRE-Push Button, DRE-Touchscreen, DRE-Dial)\n\n')
        f.write('=' * 100 + '\n\n')

        # Analyze each year
        for year in YEARS:
            print(f"Analyzing {year}...")
            duplicates = find_duplicates_by_year(year)

            # Check if this year has any duplicates
            has_duplicates = any(len(items) > 0 for items in duplicates.values())

            if not has_duplicates:
                continue

            f.write(f'\n{"=" * 100}\n')
            f.write(f'YEAR: {year}\n')
            f.write(f'{"=" * 100}\n\n')

            # Report each equipment type
            for equipment_type, items in duplicates.items():
                if not items:
                    continue

                f.write(f'\n{equipment_type} - {len(items)} jurisdictions with duplicates:\n')
                f.write('-' * 100 + '\n\n')

                # Sort by state, then jurisdiction
                items_sorted = sorted(items, key=lambda x: (x['state'], x['jurisdiction']))

                for item in items_sorted:
                    f.write(f"{item['state']}, {item['jurisdiction']} (FIPS: {item['fips']})\n")
                    f.write(f"  Count: {item['count']}\n")
                    f.write(f"  Equipment:\n")
                    for detail in item['details']:
                        f.write(f"    - {detail}\n")
                    f.write('\n')

        # Summary statistics
        f.write('\n' + '=' * 100 + '\n')
        f.write('SUMMARY STATISTICS\n')
        f.write('=' * 100 + '\n\n')

        summary = defaultdict(lambda: defaultdict(int))

        for year in YEARS:
            duplicates = find_duplicates_by_year(year)
            for equipment_type, items in duplicates.items():
                summary[equipment_type][year] = len(items)

        for equipment_type in ['Ballot Marking Device', 'Hand-Fed Optical Scanner', 'DRE (all types)']:
            f.write(f'\n{equipment_type}:\n')
            total = 0
            for year in YEARS:
                count = summary[equipment_type][year]
                if count > 0:
                    f.write(f"  {year}: {count} jurisdictions\n")
                    total += count
            f.write(f"  TOTAL: {total} jurisdiction-years with duplicates\n")

    print(f"\n✓ Report written to {output_file}")
    return output_file


if __name__ == '__main__':
    generate_report()
