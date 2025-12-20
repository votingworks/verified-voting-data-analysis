#!/usr/bin/env python3
"""
Analyze machine_uses.csv to understand equipment usage patterns.

Generates a report showing all unique (Manufacturer, Model) combinations
grouped by Equipment Type, with usage counts.

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


def analyze_equipment_by_type(records):
    """
    Count unique (Manufacturer, Model) combinations grouped by Equipment Type.

    Returns:
        dict: {equipment_type: [(count, manufacturer, model), ...]}
        Each list sorted by count descending
    """
    # Count by (equipment_type, manufacturer, model)
    counter = Counter()
    for r in records:
        key = (r['Equipment_Type'], r['Manufacturer'], r['Model'])
        counter[key] += 1

    # Group by equipment type
    by_type = defaultdict(list)
    for (eq_type, mfr, model), count in counter.items():
        by_type[eq_type].append((count, mfr, model))

    # Sort each group by count descending
    for eq_type in by_type:
        by_type[eq_type].sort(key=lambda x: -x[0])

    return dict(by_type)


def generate_report(records, output_path):
    """Generate the analysis report."""

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    equipment_by_type = analyze_equipment_by_type(records)

    # Sort equipment types alphabetically
    sorted_types = sorted(equipment_by_type.keys())

    # Count totals
    total_combinations = sum(len(models) for models in equipment_by_type.values())

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("MACHINE USES DATA ANALYSIS\n")
        f.write("=" * 100 + "\n\n")

        f.write(f"Total records: {len(records):,}\n")
        f.write(f"Total unique (Equipment_Type, Manufacturer, Model) combinations: {total_combinations:,}\n")
        f.write(f"Equipment types: {len(sorted_types):,}\n\n")

        # Write each equipment type section
        for eq_type in sorted_types:
            models = equipment_by_type[eq_type]
            type_total = sum(count for count, _, _ in models)

            f.write("=" * 100 + "\n")
            f.write(f"{eq_type.upper()}\n")
            f.write(f"({len(models)} models, {type_total:,} total records)\n")
            f.write("=" * 100 + "\n\n")

            f.write(f"{'Count':>8}  {'Manufacturer':<25} {'Model'}\n")
            f.write("-" * 80 + "\n")

            for count, mfr, model in models:
                f.write(f"{count:>8}  {mfr:<25} {model}\n")

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
    print("Generating report...")
    generate_report(records, output_path)
    print(f"✓ Report written to {output_path}")

    # Print summary stats
    equipment_by_type = analyze_equipment_by_type(records)
    total_combinations = sum(len(models) for models in equipment_by_type.values())

    print()
    print("Summary:")
    print(f"  - Equipment types: {len(equipment_by_type):,}")
    print(f"  - Unique equipment combinations: {total_combinations:,}")

    print()
    print("=" * 80)
    print("✓ ANALYSIS COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
