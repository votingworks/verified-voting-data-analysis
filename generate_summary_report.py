#!/usr/bin/env python3
"""
Generate a summary report of condensed jurisdiction data (v3).

Reads the condensed jurisdictions file and produces a summary report
showing the distribution of Poll Book Status, Primary Voting Equipment,
Primary Voting Vendor, and Primary Voting System.

Includes data quality alerts for fields with >2% empty or anomaly values.

Usage: python3 generate_summary_report.py <year>
Example: python3 generate_summary_report.py 2024
"""

import csv
import sys
from pathlib import Path
from collections import Counter


def check_anomaly_threshold(counter, total_count, field_name, threshold=0.02):
    """Check if empty or anomaly values exceed threshold and return alert message."""
    empty_count = counter.get('(empty)', 0)
    anomaly_count = counter.get('Anomaly', 0)
    problem_count = empty_count + anomaly_count
    problem_pct = (problem_count / total_count) if total_count > 0 else 0

    if problem_pct > threshold:
        alert = f"⚠️  WARNING: {field_name} has {problem_pct:.1%} problematic values "
        alert += f"({empty_count:,} empty, {anomaly_count:,} anomalies)\n"
        return alert
    return None


def load_compressed_data(year):
    """Load condensed jurisdictions data and count distributions."""
    filepath = f'data/verifier-condensed/{year}_verifier-jurisdictions-condensed.csv'

    if not Path(filepath).exists():
        raise FileNotFoundError(f"Condensed file not found: {filepath}")

    poll_book_counter = Counter()
    equipment_counter = Counter()
    vendor_counter = Counter()
    system_counter = Counter()
    total_jurisdictions = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        reader = csv.DictReader(lines[1:])  # Skip description header

        for row in reader:
            poll_book = row.get('Poll Book Status', '').strip()
            equipment = row.get('Primary Voting Equipment', '').strip()
            vendor = row.get('Primary Voting Vendor', '').strip()
            system = row.get('Primary Voting System', '').strip()

            poll_book_counter[poll_book if poll_book else '(empty)'] += 1
            equipment_counter[equipment if equipment else '(empty)'] += 1
            vendor_counter[vendor if vendor else '(empty)'] += 1
            system_counter[system if system else '(empty)'] += 1
            total_jurisdictions += 1

    return poll_book_counter, equipment_counter, vendor_counter, system_counter, total_jurisdictions


def generate_markdown_report(poll_book_counter, equipment_counter, vendor_counter, system_counter, total_jurisdictions, year):
    """Generate a simplified Markdown summary report."""
    output_file = f'data/verifier-condensed/{year}_summary_report.md'

    with open(output_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write(f'# Verifier Data Summary Report - {year}\n\n')
        f.write(f'Generated from `{year}_verifier-jurisdictions-condensed.csv`\n\n')
        f.write(f'**Total Jurisdictions:** {total_jurisdictions:,}\n\n')
        f.write('---\n\n')

        # Check for problematic data and add alerts
        alerts = []
        alerts.append(check_anomaly_threshold(poll_book_counter, total_jurisdictions, "Poll Book Status"))
        alerts.append(check_anomaly_threshold(equipment_counter, total_jurisdictions, "Primary Voting Equipment"))
        alerts.append(check_anomaly_threshold(vendor_counter, total_jurisdictions, "Primary Voting Vendor"))
        alerts.append(check_anomaly_threshold(system_counter, total_jurisdictions, "Primary Voting System"))

        # Filter out None values and add to report
        alerts = [a for a in alerts if a is not None]
        if alerts:
            f.write("\n## ⚠️ DATA QUALITY ALERTS\n\n")
            for alert in alerts:
                f.write(alert)
            f.write("\n---\n\n")

        # Poll Book Status section
        f.write('## Poll Book Status Distribution\n\n')
        f.write(f'**Total unique poll book statuses:** {len(poll_book_counter)}\n\n')
        f.write('| Poll Book Status | Count | Percentage |\n')
        f.write('|-----------------|-------|------------|\n')

        for status, count in sorted(poll_book_counter.items(), key=lambda x: -x[1]):
            pct = count / total_jurisdictions * 100
            f.write(f'| {status} | {count:,} | {pct:.2f}% |\n')

        f.write('\n')

        # Primary Voting Equipment section
        f.write('## Primary Voting Equipment Distribution\n\n')
        f.write(f'**Total unique equipment types:** {len(equipment_counter)}\n\n')
        f.write('| Primary Voting Equipment | Count | Percentage |\n')
        f.write('|-------------------------|-------|------------|\n')

        for equipment, count in sorted(equipment_counter.items(), key=lambda x: -x[1]):
            pct = count / total_jurisdictions * 100
            f.write(f'| {equipment} | {count:,} | {pct:.2f}% |\n')

        f.write('\n')

        # Primary Voting Vendor section
        f.write('## Primary Voting Vendor Distribution\n\n')
        f.write(f'**Total unique vendors:** {len(vendor_counter)}\n\n')
        f.write('| Primary Voting Vendor | Count | Percentage |\n')
        f.write('|----------------------|-------|------------|\n')

        for vendor, count in sorted(vendor_counter.items(), key=lambda x: -x[1]):
            pct = count / total_jurisdictions * 100
            f.write(f'| {vendor} | {count:,} | {pct:.2f}% |\n')

        f.write('\n')

        # Primary Voting System section
        f.write('## Primary Voting System Distribution\n\n')
        f.write(f'**Total unique systems:** {len(system_counter)}\n\n')
        f.write('| Primary Voting System | Count | Percentage |\n')
        f.write('|----------------------|-------|------------|\n')

        for system, count in sorted(system_counter.items(), key=lambda x: -x[1]):
            pct = count / total_jurisdictions * 100
            f.write(f'| {system} | {count:,} | {pct:.2f}% |\n')

        f.write('\n---\n\n')

        # Footer
        f.write(f'*Report generated for {year} verifier data*\n')

    return output_file


def main():
    """Main processing pipeline."""

    # Parse command-line arguments
    if len(sys.argv) != 2:
        print("Usage: python3 generate_summary_report.py <year>")
        print("Example: python3 generate_summary_report.py 2024")
        sys.exit(1)

    year = sys.argv[1]

    # Validate year
    try:
        year_int = int(year)
        if year_int < 2006 or year_int > 2026 or year_int % 2 != 0:
            print(f"Error: Year must be an even year between 2006 and 2026")
            sys.exit(1)
    except ValueError:
        print(f"Error: Invalid year: {year}")
        sys.exit(1)

    print(f"Generating summary report for {year}...\n")

    # Load condensed data
    try:
        poll_book_counter, equipment_counter, vendor_counter, system_counter, total_jurisdictions = load_compressed_data(year)
        print(f"Loaded data for {total_jurisdictions:,} jurisdictions")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"\nPlease run condense_jurisdictions.py first to generate the condensed file.")
        sys.exit(1)

    # Generate report
    print("\nGenerating Markdown report...")
    output_file = generate_markdown_report(poll_book_counter, equipment_counter, vendor_counter, system_counter, total_jurisdictions, year)

    print(f"\n✓ Summary report written to {output_file}")
    print(f"\nThe report includes:")
    print(f"  - Poll Book Status distribution ({len(poll_book_counter)} unique values)")
    print(f"  - Primary Voting Equipment distribution ({len(equipment_counter)} unique values)")
    print(f"  - Primary Voting Vendor distribution ({len(vendor_counter)} unique values)")
    print(f"  - Primary Voting System distribution ({len(system_counter)} unique values)")


if __name__ == "__main__":
    main()
