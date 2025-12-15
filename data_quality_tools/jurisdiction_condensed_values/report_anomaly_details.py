#!/usr/bin/env python3
"""
Report anomaly jurisdictions and their machine entries across all years.

Identifies jurisdictions where Primary Voting Equipment = "Anomaly" and exports
detailed information including all machine entries for those jurisdictions.

Usage: python3 report_anomaly_details.py
Output: anomaly_details_report.txt
"""

import csv
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent

# Years to analyze
YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]


def export_anomalies_for_year(year):
    """
    Export anomaly jurisdictions and their machine details for a specific year.

    Returns:
        tuple: (anomaly_count, anomaly_details_list)
    """
    # Load condensed data to find anomaly jurisdictions
    condensed_file = SCRIPT_DIR / f'../../data/verifier-condensed/{year}_verifier-jurisdictions-condensed.csv'
    machines_file = SCRIPT_DIR / f'../../data/verifier-original/{year}_verifier-machines.csv'

    if not condensed_file.exists():
        print(f"Warning: {condensed_file} not found, skipping {year}...")
        return 0, []

    if not machines_file.exists():
        print(f"Warning: {machines_file} not found, skipping {year}...")
        return 0, []

    anomaly_fips = []
    anomaly_jurisdictions = {}

    # Find anomaly jurisdictions
    with open(condensed_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        reader = csv.DictReader(lines[1:])  # Skip title row

        for row in reader:
            equipment_summary = row.get('Primary Voting Equipment', '').strip()
            if equipment_summary == 'Anomaly':
                fips = row['FIPS code']
                anomaly_fips.append(fips)
                anomaly_jurisdictions[fips] = row

    if not anomaly_fips:
        return 0, []

    # Load machine entries for anomaly jurisdictions
    machines_by_fips = {fips: [] for fips in anomaly_fips}

    with open(machines_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        reader = csv.DictReader(lines[1:])  # Skip title row

        for row in reader:
            fips = row['FIPS code']
            if fips in anomaly_fips:
                machines_by_fips[fips].append(row)

    # Format details for this year
    details = []
    for fips in anomaly_fips:
        details.append({
            'jurisdiction': anomaly_jurisdictions[fips],
            'machines': machines_by_fips[fips]
        })

    return len(anomaly_fips), details


def generate_report():
    """Generate comprehensive report of anomalies across all years."""

    output_file = SCRIPT_DIR / 'anomaly_details_report.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('=' * 100 + '\n')
        f.write('ANOMALY JURISDICTIONS REPORT (ALL YEARS)\n')
        f.write('=' * 100 + '\n\n')
        f.write('This report lists all jurisdictions where Primary Voting Equipment = "Anomaly"\n')
        f.write('along with their machine entries to help diagnose classification issues.\n\n')
        f.write('=' * 100 + '\n\n')

        total_anomalies = 0

        # Process each year
        for year in YEARS:
            print(f"Processing {year}...")
            count, details = export_anomalies_for_year(year)

            if count == 0:
                continue

            total_anomalies += count

            f.write('\n' + '=' * 100 + '\n')
            f.write(f'YEAR: {year}\n')
            f.write(f'Total Anomalies: {count}\n')
            f.write('=' * 100 + '\n\n')

            for i, item in enumerate(details, 1):
                jurisdiction = item['jurisdiction']
                machines = item['machines']

                f.write('-' * 100 + '\n')
                f.write(f'JURISDICTION {i} of {count}\n')
                f.write('-' * 100 + '\n\n')

                # Jurisdiction details
                f.write(f"FIPS: {jurisdiction['FIPS code']}\n")
                f.write(f"State: {jurisdiction['State']}\n")
                f.write(f"Jurisdiction: {jurisdiction['Jurisdiction']}\n")
                f.write(f"Registered Voters: {jurisdiction.get('Registered Voters', '')}\n")
                f.write(f"Precincts: {jurisdiction.get('Precincts', '')}\n")
                f.write(f"All Mail Ballot?: {jurisdiction.get('All Mail Ballot?', '')}\n")
                f.write(f"Election Day Marking Method: {jurisdiction.get('Election Day Marking Method', '')}\n")
                f.write(f"Election Day Tabulation: {jurisdiction.get('Election Day Tabulation', '')}\n")
                f.write(f"Primary Marking Method: {jurisdiction.get('Primary Marking Method', '')}\n")
                f.write(f"Primary Voting Equipment: {jurisdiction.get('Primary Voting Equipment', '')}\n")
                f.write(f"Primary Voting System: {jurisdiction.get('Primary Voting System', '')}\n")
                f.write(f"Primary Voting Vendor: {jurisdiction.get('Primary Voting Vendor', '')}\n")
                f.write(f"Poll Book Status: {jurisdiction.get('Poll Book Status', '')}\n")
                f.write(f"DRE?: {jurisdiction.get('DRE?', '')}\n")
                f.write('\n')

                # Machine entries
                f.write(f'MACHINE ENTRIES ({len(machines)} total):\n')
                f.write('~' * 100 + '\n\n')

                if not machines:
                    f.write("  (No machine entries found)\n\n")
                else:
                    for j, machine in enumerate(machines, 1):
                        f.write(f'Machine {j}:\n')
                        f.write(f"  Equipment Type: {machine.get('Equipment Type', '')}\n")
                        f.write(f"  Manufacturer: {machine.get('Manufacturer', '')}\n")
                        f.write(f"  Model: {machine.get('Model', '')}\n")
                        f.write(f"  First Year in Use: {machine.get('First Year in Use', '')}\n")
                        f.write(f"  Election Day Standard: {machine.get('Election Day Standard', '')}\n")
                        f.write(f"  Election Day Accessible: {machine.get('Election Day Accessible', '')}\n")
                        f.write(f"  Early Voting Standard: {machine.get('Early Voting Standard', '')}\n")
                        f.write(f"  Early Voting Accessible: {machine.get('Early Voting Accessible', '')}\n")
                        f.write(f"  Mail Ballot/Absentee Equipment: {machine.get('Mail Ballot/Absentee Equipment', '')}\n")
                        f.write(f"  VVPAT: {machine.get('VVPAT', '')}\n")
                        notes = machine.get('Notes on usage', '').strip()
                        if notes:
                            f.write(f"  Notes: {notes}\n")
                        f.write('\n')

                f.write('\n')

        # Summary statistics
        f.write('\n' + '=' * 100 + '\n')
        f.write('SUMMARY STATISTICS\n')
        f.write('=' * 100 + '\n\n')

        f.write('Anomalies by Year:\n')
        for year in YEARS:
            count, _ = export_anomalies_for_year(year)
            if count > 0:
                f.write(f"  {year}: {count} jurisdictions\n")

        f.write(f'\nTOTAL: {total_anomalies} anomaly jurisdiction-years across all years\n')

    print(f"\n✓ Report written to {output_file}")
    print(f"  Total anomalies: {total_anomalies}")
    return output_file


if __name__ == '__main__':
    generate_report()
