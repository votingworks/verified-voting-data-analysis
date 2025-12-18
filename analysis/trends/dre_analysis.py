#!/usr/bin/env python3
"""
Analyze DRE equipment distribution across jurisdictions.

Examines all condensed jurisdiction files to understand:
1. Distribution of Primary Voting Equipment for DREs with VVPAT
2. Distribution of Primary Voting Equipment for DREs without VVPAT
3. Equipment models that appear in both categories

Outputs results to: data_quality_tools/dres/dre_equipment_analysis.txt
"""

import sys
from pathlib import Path
from collections import Counter, defaultdict
import csv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Years to analyze
YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]

# DRE categories to analyze
DRE_WITH_VVPAT = "DREs with VVPAT for all voters"
DRE_WITHOUT_VVPAT = "DREs without VVPAT for all voters"


def load_all_jurisdictions():
    """
    Load all condensed jurisdiction files and extract DRE jurisdictions.

    Returns:
        dict: {
            'with_vvpat': [(year, state, jurisdiction, equipment), ...],
            'without_vvpat': [(year, state, jurisdiction, equipment), ...]
        }
    """
    dre_data = {
        'with_vvpat': [],
        'without_vvpat': []
    }

    for year in YEARS:
        filepath = f'data/processed/jurisdictions/{year}_verifier-jurisdictions-condensed.csv'

        if not Path(filepath).exists():
            print(f"⚠ Warning: {filepath} not found, skipping...")
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            reader = csv.DictReader(lines[1:])  # Skip title row

            for row in reader:
                marking_method = row.get('Election Day Marking Method', '').strip()
                primary_equipment = row.get('Primary Voting Equipment', '').strip()
                state = row.get('State', '').strip()
                jurisdiction = row.get('Jurisdiction', '').strip()

                # Skip if missing key fields
                if not marking_method or not primary_equipment:
                    continue

                # Categorize by VVPAT status
                if marking_method == DRE_WITH_VVPAT:
                    dre_data['with_vvpat'].append((year, state, jurisdiction, primary_equipment))
                elif marking_method == DRE_WITHOUT_VVPAT:
                    dre_data['without_vvpat'].append((year, state, jurisdiction, primary_equipment))

    return dre_data


def analyze_equipment_distribution(dre_data):
    """
    Analyze equipment distribution for each DRE category.

    Args:
        dre_data: Dictionary with 'with_vvpat' and 'without_vvpat' lists

    Returns:
        dict: {
            'with_vvpat': Counter({equipment: count, ...}),
            'without_vvpat': Counter({equipment: count, ...}),
            'overlap': set of equipment in both categories
        }
    """
    # Count equipment occurrences in each category
    with_vvpat_counter = Counter(equipment for _, _, _, equipment in dre_data['with_vvpat'])
    without_vvpat_counter = Counter(equipment for _, _, _, equipment in dre_data['without_vvpat'])

    # Find equipment that appears in both categories
    with_vvpat_set = set(with_vvpat_counter.keys())
    without_vvpat_set = set(without_vvpat_counter.keys())
    overlap = with_vvpat_set & without_vvpat_set

    return {
        'with_vvpat': with_vvpat_counter,
        'without_vvpat': without_vvpat_counter,
        'overlap': overlap
    }


def generate_report(dre_data, analysis):
    """
    Generate text report of DRE equipment analysis.

    Args:
        dre_data: Raw DRE data
        analysis: Analysis results
    """
    output_path = 'outputs/reports/dre_equipment_analysis.txt'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("DRE EQUIPMENT DISTRIBUTION ANALYSIS\n")
        f.write("=" * 80 + "\n\n")

        # Summary statistics
        total_with_vvpat = len(dre_data['with_vvpat'])
        total_without_vvpat = len(dre_data['without_vvpat'])
        unique_with_vvpat = len(analysis['with_vvpat'])
        unique_without_vvpat = len(analysis['without_vvpat'])

        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total jurisdiction-years with DREs (with VVPAT):    {total_with_vvpat:,}\n")
        f.write(f"Total jurisdiction-years with DREs (without VVPAT): {total_without_vvpat:,}\n")
        f.write(f"Unique equipment models (with VVPAT):               {unique_with_vvpat:,}\n")
        f.write(f"Unique equipment models (without VVPAT):            {unique_without_vvpat:,}\n")
        f.write(f"Equipment models appearing in both categories:      {len(analysis['overlap']):,}\n")
        f.write("\n\n")

        # DREs WITH VVPAT
        f.write("=" * 80 + "\n")
        f.write("DREs WITH VVPAT FOR ALL VOTERS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total occurrences: {total_with_vvpat:,}\n")
        f.write(f"Unique equipment models: {unique_with_vvpat:,}\n\n")

        f.write("Equipment Distribution (sorted by frequency):\n")
        f.write("-" * 80 + "\n")
        for equipment, count in analysis['with_vvpat'].most_common():
            percentage = (count / total_with_vvpat * 100) if total_with_vvpat > 0 else 0
            overlap_marker = " [*]" if equipment in analysis['overlap'] else ""
            f.write(f"  {count:5,} ({percentage:5.1f}%)  {equipment}{overlap_marker}\n")

        f.write("\n[*] = Also appears in 'without VVPAT' category\n\n\n")

        # DREs WITHOUT VVPAT
        f.write("=" * 80 + "\n")
        f.write("DREs WITHOUT VVPAT FOR ALL VOTERS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total occurrences: {total_without_vvpat:,}\n")
        f.write(f"Unique equipment models: {unique_without_vvpat:,}\n\n")

        f.write("Equipment Distribution (sorted by frequency):\n")
        f.write("-" * 80 + "\n")
        for equipment, count in analysis['without_vvpat'].most_common():
            percentage = (count / total_without_vvpat * 100) if total_without_vvpat > 0 else 0
            overlap_marker = " [*]" if equipment in analysis['overlap'] else ""
            f.write(f"  {count:5,} ({percentage:5.1f}%)  {equipment}{overlap_marker}\n")

        f.write("\n[*] = Also appears in 'with VVPAT' category\n\n\n")

        # OVERLAP ANALYSIS
        if analysis['overlap']:
            f.write("=" * 80 + "\n")
            f.write("EQUIPMENT APPEARING IN BOTH CATEGORIES\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Found {len(analysis['overlap'])} equipment model(s) used both with and without VVPAT:\n\n")

            for equipment in sorted(analysis['overlap']):
                with_count = analysis['with_vvpat'][equipment]
                without_count = analysis['without_vvpat'][equipment]
                total_count = with_count + without_count

                f.write(f"\nEquipment: {equipment}\n")
                f.write(f"  - With VVPAT:    {with_count:5,} occurrences ({with_count/total_count*100:5.1f}%)\n")
                f.write(f"  - Without VVPAT: {without_count:5,} occurrences ({without_count/total_count*100:5.1f}%)\n")
                f.write(f"  - Total:         {total_count:5,} occurrences\n")

            f.write("\n\nNote: Some DRE models were deployed both with and without VVPAT capabilities,\n")
            f.write("either due to different configurations or jurisdictions upgrading to add VVPAT.\n")
        else:
            f.write("=" * 80 + "\n")
            f.write("EQUIPMENT APPEARING IN BOTH CATEGORIES\n")
            f.write("=" * 80 + "\n\n")
            f.write("No equipment models appear in both categories.\n")
            f.write("All DRE equipment is exclusively used either with or without VVPAT.\n")

        f.write("\n\n")
        f.write("=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")

    print(f"✓ Report saved to {output_path}")
    return output_path


def main():
    """Main execution function."""
    print("=" * 80)
    print("DRE EQUIPMENT DISTRIBUTION ANALYSIS")
    print("=" * 80)
    print()

    # Load data
    print("Loading condensed jurisdiction files...")
    dre_data = load_all_jurisdictions()
    print(f"✓ Loaded {len(dre_data['with_vvpat']):,} jurisdiction-years with VVPAT")
    print(f"✓ Loaded {len(dre_data['without_vvpat']):,} jurisdiction-years without VVPAT")
    print()

    # Analyze distributions
    print("Analyzing equipment distributions...")
    analysis = analyze_equipment_distribution(dre_data)
    print(f"✓ Found {len(analysis['with_vvpat'])} unique equipment models (with VVPAT)")
    print(f"✓ Found {len(analysis['without_vvpat'])} unique equipment models (without VVPAT)")
    print(f"✓ Found {len(analysis['overlap'])} equipment models in both categories")
    print()

    # Generate report
    print("Generating report...")
    output_path = generate_report(dre_data, analysis)
    print()

    # Print summary to console
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print(f"Output file: {output_path}")
    print()


if __name__ == "__main__":
    main()
