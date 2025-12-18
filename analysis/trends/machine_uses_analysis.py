#!/usr/bin/env python3
"""
Analyze machine_uses.csv to understand its content and data quality.

Generates a report with:
1. All unique (Equipment_Type, Manufacturer, Model) combinations by frequency
2. Anomalies where First_Year != Reported_First_Year_In_Use
3. Split spans - same equipment appearing in multiple spans for a jurisdiction

Output: outputs/reports/machine_uses_analysis.txt
"""

import csv
from pathlib import Path
from collections import Counter, defaultdict

# Directories
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'reports'


def load_machine_uses():
    """Load machine_uses.csv data."""
    filepath = DATA_DIR / 'machine_uses.csv'

    if not filepath.exists():
        raise FileNotFoundError(f"Machine uses file not found: {filepath}")

    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    return records


def analyze_equipment_combinations(records):
    """
    Count unique (Equipment_Type, Manufacturer, Model) combinations.

    Returns:
        list of tuples: [(count, equipment_type, manufacturer, model), ...]
        sorted by count descending
    """
    counter = Counter()

    for r in records:
        key = (r['Equipment_Type'], r['Manufacturer'], r['Model'])
        counter[key] += 1

    # Sort by count descending
    sorted_combinations = [
        (count, eq_type, mfr, model)
        for (eq_type, mfr, model), count in counter.most_common()
    ]

    return sorted_combinations


def find_year_anomalies(records):
    """
    Find records where First_Year != Reported_First_Year_In_Use.

    Only considers cases where both fields are non-blank.

    Returns:
        tuple: (anomaly_count, total_with_both, examples_list)
    """
    anomalies = []
    total_with_both = 0

    for r in records:
        first_year = r['First_Year'].strip()
        reported = r['Reported_First_Year_In_Use'].strip()

        if first_year and reported:
            total_with_both += 1
            if first_year != reported:
                anomalies.append({
                    'fips': r['FIPS'],
                    'state': r['State'],
                    'jurisdiction': r['Jurisdiction'],
                    'equipment': f"{r['Manufacturer']} {r['Model']}",
                    'equipment_type': r['Equipment_Type'],
                    'first_year': first_year,
                    'reported': reported,
                    'last_year': r['Last_Year']
                })

    return len(anomalies), total_with_both, anomalies


def find_split_spans(records):
    """
    Find equipment that appears in multiple spans for the same jurisdiction.

    Returns:
        dict: {(fips, type, mfr, model): [list of span records]}
        Only includes entries with 2+ spans
    """
    # Group by equipment key
    by_equipment = defaultdict(list)

    for r in records:
        key = (r['FIPS'], r['Equipment_Type'], r['Manufacturer'], r['Model'])
        by_equipment[key].append(r)

    # Filter to only those with multiple spans
    split_spans = {
        key: spans
        for key, spans in by_equipment.items()
        if len(spans) > 1
    }

    return split_spans


def generate_report(records, output_path):
    """Generate the analysis report."""

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("MACHINE USES DATA ANALYSIS\n")
        f.write("=" * 100 + "\n\n")

        f.write(f"Total records in machine_uses.csv: {len(records):,}\n\n")

        # Section 1: Equipment combinations
        f.write("-" * 100 + "\n")
        f.write("1. UNIQUE EQUIPMENT COMBINATIONS (by frequency)\n")
        f.write("-" * 100 + "\n\n")

        combinations = analyze_equipment_combinations(records)
        f.write(f"Total unique (Equipment_Type, Manufacturer, Model) combinations: {len(combinations):,}\n\n")

        f.write(f"{'Count':>8}  {'Equipment Type':<35} {'Manufacturer':<20} {'Model'}\n")
        f.write("-" * 100 + "\n")

        for count, eq_type, mfr, model in combinations:
            f.write(f"{count:>8}  {eq_type:<35} {mfr:<20} {model}\n")

        f.write("\n")

        # Section 2: Year anomalies
        f.write("-" * 100 + "\n")
        f.write("2. FIRST_YEAR vs REPORTED_FIRST_YEAR_IN_USE ANOMALIES\n")
        f.write("-" * 100 + "\n\n")

        anomaly_count, total_with_both, anomalies = find_year_anomalies(records)

        f.write(f"Records with both First_Year and Reported_First_Year_In_Use: {total_with_both:,}\n")
        f.write(f"Records where values don't match: {anomaly_count:,}\n")

        if total_with_both > 0:
            pct = (anomaly_count / total_with_both) * 100
            f.write(f"Anomaly rate: {pct:.2f}%\n")

        f.write("\n")

        if anomalies:
            f.write("Examples (showing up to 20):\n\n")
            f.write(f"{'State':<20} {'Jurisdiction':<25} {'Equipment Type':<30} {'First_Year':>10} {'Reported':>10} {'Last_Year':>10}\n")
            f.write("-" * 100 + "\n")

            for a in anomalies[:20]:
                f.write(f"{a['state']:<20} {a['jurisdiction']:<25} {a['equipment_type']:<30} {a['first_year']:>10} {a['reported']:>10} {a['last_year']:>10}\n")

            if len(anomalies) > 20:
                f.write(f"\n... and {len(anomalies) - 20:,} more\n")
        else:
            f.write("No anomalies found.\n")

        f.write("\n")

        # Section 3: Split spans
        f.write("-" * 100 + "\n")
        f.write("3. SPLIT SPANS (same equipment with multiple usage periods)\n")
        f.write("-" * 100 + "\n\n")

        split_spans = find_split_spans(records)

        total_split_equipment = len(split_spans)
        total_split_records = sum(len(spans) for spans in split_spans.values())

        f.write(f"Equipment with multiple spans: {total_split_equipment:,}\n")
        f.write(f"Total records in split spans: {total_split_records:,}\n")
        f.write("\n")

        if split_spans:
            f.write("Examples (showing up to 15 equipment items):\n\n")

            # Sort by number of spans descending
            sorted_splits = sorted(
                split_spans.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )

            for i, (key, spans) in enumerate(sorted_splits[:15]):
                fips, eq_type, mfr, model = key
                state = spans[0]['State']
                jurisdiction = spans[0]['Jurisdiction']

                f.write(f"  {state}, {jurisdiction}\n")
                f.write(f"  Equipment: {eq_type} - {mfr} {model}\n")
                f.write(f"  Spans ({len(spans)}):\n")

                for span in sorted(spans, key=lambda x: int(x['First_Year'])):
                    f.write(f"    {span['First_Year']} - {span['Last_Year']} ({span['Years_In_Span']} survey years)\n")

                f.write("\n")

            if len(sorted_splits) > 15:
                f.write(f"... and {len(sorted_splits) - 15:,} more equipment items with split spans\n")
        else:
            f.write("No split spans found.\n")

        f.write("\n")
        f.write("=" * 100 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 100 + "\n")

    return output_path


def main():
    """Main execution function."""
    print("=" * 80)
    print("ANALYZING MACHINE USES DATA")
    print("=" * 80)
    print()

    # Load data
    print("Loading machine_uses.csv...")
    records = load_machine_uses()
    print(f"✓ Loaded {len(records):,} records")
    print()

    # Generate report
    output_path = OUTPUT_DIR / 'machine_uses_analysis.txt'
    print(f"Generating report...")
    generate_report(records, output_path)
    print(f"✓ Report written to {output_path}")

    # Print summary stats
    combinations = analyze_equipment_combinations(records)
    anomaly_count, total_with_both, _ = find_year_anomalies(records)
    split_spans = find_split_spans(records)

    print()
    print("Summary:")
    print(f"  - Unique equipment combinations: {len(combinations):,}")
    print(f"  - Year anomalies: {anomaly_count:,} of {total_with_both:,} records with both years")
    print(f"  - Split spans: {len(split_spans):,} equipment items")

    print()
    print("=" * 80)
    print("✓ ANALYSIS COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
