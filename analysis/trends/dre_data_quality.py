#!/usr/bin/env python3
"""
DRE Data Quality Analysis.

Verify that jurisdiction-level DRE labels match machine records:
1. Jurisdictions labelled as DRE should have DRE machine records
2. VVPAT status in labels should match machine records

Reads from: data/extracted/{year}_verifier-jurisdictions.csv
            data/extracted/{year}_verifier-machines.csv
Outputs to: outputs/reports/dre_data_quality_report.txt
"""

import csv
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'extracted'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'reports'

YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]

# DRE label patterns in "Election Day Marking Method" field
# Only checking "DREs for all voters" - excludes mixed systems where primary is hand marked paper
DRE_LABELS_WITH_VVPAT = [
    'DREs with VVPAT for all voters',
]

DRE_LABELS_WITHOUT_VVPAT = [
    'DREs without VVPAT for all voters',
]

# DRE equipment types in machines file
DRE_EQUIPMENT_TYPES = ['DRE-Touchscreen', 'DRE-Push Button', 'DRE-Dial']


def load_jurisdictions(year):
    """Load jurisdiction data for a given year."""
    filepath = DATA_DIR / f'{year}_verifier-jurisdictions.csv'
    if not filepath.exists():
        return []

    jurisdictions = []
    with open(filepath, 'r', encoding='utf-8') as f:
        # Skip first line (metadata), then read CSV
        next(f)
        reader = csv.DictReader(f)
        for row in reader:
            jurisdictions.append(row)
    return jurisdictions


def load_machines(year):
    """Load machine data for a given year."""
    filepath = DATA_DIR / f'{year}_verifier-machines.csv'
    if not filepath.exists():
        return []

    machines = []
    with open(filepath, 'r', encoding='utf-8') as f:
        # Skip first line (metadata), then read CSV
        next(f)
        reader = csv.DictReader(f)
        for row in reader:
            machines.append(row)
    return machines


def get_dre_machines_by_fips(machines):
    """
    Get DRE machines grouped by FIPS code.

    Returns dict: FIPS -> list of (equipment_type, vvpat_status)
    """
    dre_by_fips = defaultdict(list)

    for machine in machines:
        equipment_type = machine.get('Equipment Type', '')
        if equipment_type in DRE_EQUIPMENT_TYPES:
            fips = machine.get('FIPS code', '')
            vvpat = machine.get('VVPAT', '')
            dre_by_fips[fips].append({
                'equipment_type': equipment_type,
                'vvpat': vvpat,
                'model': machine.get('Model', ''),
                'manufacturer': machine.get('Manufacturer', ''),
            })

    return dre_by_fips


def classify_jurisdiction_dre_label(marking_method):
    """
    Classify jurisdiction's DRE label.

    Returns: 'with_vvpat', 'without_vvpat', or None
    """
    if marking_method in DRE_LABELS_WITH_VVPAT:
        return 'with_vvpat'
    elif marking_method in DRE_LABELS_WITHOUT_VVPAT:
        return 'without_vvpat'
    return None


def analyze_year(year):
    """
    Analyze DRE data quality for a single year.

    Returns dict with:
        - dre_jurisdictions: count of jurisdictions with DRE labels
        - missing_machine: list of jurisdictions missing DRE machine records
        - vvpat_mismatch: list of jurisdictions with VVPAT mismatch
    """
    jurisdictions = load_jurisdictions(year)
    machines = load_machines(year)

    if not jurisdictions or not machines:
        return None

    dre_by_fips = get_dre_machines_by_fips(machines)

    results = {
        'dre_jurisdictions': 0,
        'missing_machine': [],
        'vvpat_mismatch': [],
    }

    for jur in jurisdictions:
        marking_method = jur.get('Election Day Marking Method', '')
        dre_label = classify_jurisdiction_dre_label(marking_method)

        if dre_label is None:
            continue

        results['dre_jurisdictions'] += 1

        fips = jur.get('FIPS code', '')
        state = jur.get('State', '')
        jurisdiction_name = jur.get('Jurisdiction', '')

        dre_machines = dre_by_fips.get(fips, [])

        # Check 1: Does this jurisdiction have any DRE machine records?
        if not dre_machines:
            results['missing_machine'].append({
                'state': state,
                'jurisdiction': jurisdiction_name,
                'fips': fips,
                'label': marking_method,
            })
            continue

        # Check 2: Does VVPAT status match?
        expected_vvpat = 'Yes' if dre_label == 'with_vvpat' else 'No'

        # Check all DRE machines for this jurisdiction
        mismatched_machines = []
        for machine in dre_machines:
            actual_vvpat = machine['vvpat']
            if actual_vvpat != expected_vvpat:
                mismatched_machines.append(machine)

        if mismatched_machines:
            results['vvpat_mismatch'].append({
                'state': state,
                'jurisdiction': jurisdiction_name,
                'fips': fips,
                'label': marking_method,
                'expected_vvpat': expected_vvpat,
                'machines': mismatched_machines,
            })

    return results


def generate_report():
    """Generate comprehensive DRE data quality report."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / 'dre_data_quality_report.txt'

    all_results = {}

    print("Analyzing DRE data quality...")
    for year in YEARS:
        print(f"  Processing {year}...")
        results = analyze_year(year)
        if results:
            all_results[year] = results

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('=' * 100 + '\n')
        f.write('DRE DATA QUALITY REPORT\n')
        f.write('Verifying jurisdiction DRE labels match machine records\n')
        f.write('=' * 100 + '\n\n')

        # Summary table
        f.write('SUMMARY BY YEAR\n')
        f.write('-' * 80 + '\n')
        f.write(f'{"Year":<6} | {"DRE Jurisdictions":>18} | {"Missing Machine":>16} | {"VVPAT Mismatch":>15}\n')
        f.write('-' * 80 + '\n')

        total_dre = 0
        total_missing = 0
        total_mismatch = 0

        for year in YEARS:
            if year in all_results:
                r = all_results[year]
                dre_count = r['dre_jurisdictions']
                missing_count = len(r['missing_machine'])
                mismatch_count = len(r['vvpat_mismatch'])

                total_dre += dre_count
                total_missing += missing_count
                total_mismatch += mismatch_count

                f.write(f'{year:<6} | {dre_count:>18} | {missing_count:>16} | {mismatch_count:>15}\n')
            else:
                f.write(f'{year:<6} | {"(no data)":>18} | {"-":>16} | {"-":>15}\n')

        f.write('-' * 80 + '\n')
        f.write(f'{"TOTAL":<6} | {total_dre:>18} | {total_missing:>16} | {total_mismatch:>15}\n')
        f.write('\n\n')

        # Detailed missing machine records
        f.write('=' * 100 + '\n')
        f.write('[1] MISSING DRE MACHINE RECORDS\n')
        f.write('    Jurisdictions labelled as DRE but no DRE equipment found in machines file\n')
        f.write('=' * 100 + '\n\n')

        any_missing = False
        for year in YEARS:
            if year in all_results and all_results[year]['missing_machine']:
                any_missing = True
                f.write(f'--- {year} ---\n')
                for item in all_results[year]['missing_machine']:
                    f.write(f"  {item['state']}, {item['jurisdiction']} (FIPS: {item['fips']})\n")
                    f.write(f"    Label: {item['label']}\n")
                f.write('\n')

        if not any_missing:
            f.write('  No missing machine records found.\n\n')

        # Detailed VVPAT mismatches
        f.write('=' * 100 + '\n')
        f.write('[2] VVPAT MISMATCHES\n')
        f.write('    Jurisdictions where VVPAT label does not match machine records\n')
        f.write('=' * 100 + '\n\n')

        any_mismatch = False
        for year in YEARS:
            if year in all_results and all_results[year]['vvpat_mismatch']:
                any_mismatch = True
                f.write(f'--- {year} ---\n')
                for item in all_results[year]['vvpat_mismatch']:
                    f.write(f"  {item['state']}, {item['jurisdiction']} (FIPS: {item['fips']})\n")
                    f.write(f"    Label: {item['label']}\n")
                    f.write(f"    Expected VVPAT: {item['expected_vvpat']}\n")
                    f.write(f"    Machines with wrong VVPAT:\n")
                    for m in item['machines']:
                        f.write(f"      - {m['manufacturer']} {m['model']} ({m['equipment_type']}): VVPAT={m['vvpat']}\n")
                f.write('\n')

        if not any_mismatch:
            f.write('  No VVPAT mismatches found.\n\n')

    print(f"\n✓ Report saved to {output_path}")

    # Print summary to console
    print(f"\nSummary:")
    print(f"  Total DRE-labelled jurisdictions: {total_dre}")
    print(f"  Missing machine records: {total_missing}")
    print(f"  VVPAT mismatches: {total_mismatch}")

    return all_results


def main():
    """Main entry point."""
    print("=" * 80)
    print("DRE DATA QUALITY ANALYSIS")
    print("=" * 80)
    print()

    generate_report()

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
