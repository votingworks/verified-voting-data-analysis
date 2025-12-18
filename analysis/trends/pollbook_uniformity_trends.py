#!/usr/bin/env python3
"""
Analyze trends in statewide poll book uniformity over time.

Creates a stacked bar chart showing the number of states with uniform
poll book deployments for each year, broken down by vendor:
- KNOWiNK
- ES&S
- In-House
- Other (Tenex, VR Systems, DemTech, etc.)

Only includes states where at least 80% of jurisdictions use electronic
poll books (EPBs) rather than paper.

Usage:
    python3 data_quality_tools/state_uniformity/analyze_pollbook_uniformity_trends.py

Input:
    data/state-level/{year}_state-uniformity.csv for all years

Output:
    data_quality_tools/state_uniformity/pollbook_uniformity_trends.png
"""

import csv
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

# Directories
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
STATE_LEVEL_DIR = PROJECT_ROOT / 'data' / 'processed' / 'states'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'trends'

# Years to analyze
YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]

# Poll book vendor categories
MAJOR_POLLBOOK_VENDORS = ['KNOWiNK', 'ES&S', 'In-House']


def categorize_pollbook_vendor(vendor):
    """
    Categorize poll book vendor into major categories.

    Args:
        vendor: Poll book vendor name

    Returns:
        str: Category name (KNOWiNK, ES&S, In-House, or Other)
    """
    if vendor in MAJOR_POLLBOOK_VENDORS:
        return vendor
    else:
        return 'Other'


def load_state_data(year):
    """
    Load state-level uniformity data for a given year.

    Args:
        year: Year to load

    Returns:
        list of dicts or None: State data, or None if file doesn't exist
    """
    filepath = STATE_LEVEL_DIR / f'{year}_state-uniformity.csv'

    if not filepath.exists():
        return None

    states = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        states = list(reader)

    return states


def analyze_pollbook_uniformity_by_year():
    """
    Analyze poll book uniformity across all years.

    Returns:
        dict: Year -> {vendor_category: count}
    """
    results = {}

    for year in YEARS:
        states = load_state_data(year)

        if states is None:
            print(f"⚠ Warning: No state-level data for {year}, skipping...")
            continue

        # Count states with uniform poll books by vendor category
        # Filter: only include states where >=80% of jurisdictions use EPBs
        vendor_counts = defaultdict(int)

        for state in states:
            if state['Poll_Book_Uniformity'] == 'Uniform':
                total_juris = int(state['Total_Jurisdictions'])
                non_paper_juris = int(state['Non_Paper_Poll_Book_Jurisdictions'])

                # Only count if at least 80% of jurisdictions use EPBs
                if total_juris > 0 and (non_paper_juris / total_juris) >= 0.80:
                    vendor = state['Poll_Book_Status']
                    category = categorize_pollbook_vendor(vendor)
                    vendor_counts[category] += 1

        results[year] = vendor_counts
        print(f"✓ {year}: {sum(vendor_counts.values())} states with uniform poll books (≥80% EPB adoption)")

    return results


def create_stacked_bar_chart(data):
    """
    Create stacked bar chart of poll book uniformity trends.

    Args:
        data: Dict of year -> {vendor_category: count}
    """
    years = sorted(data.keys())

    # Prepare data for stacking
    categories = ['KNOWiNK', 'ES&S', 'In-House', 'Other']
    category_data = {cat: [] for cat in categories}

    for year in years:
        year_counts = data[year]
        for cat in categories:
            category_data[cat].append(year_counts.get(cat, 0))

    # Create the stacked bar chart
    fig, ax = plt.subplots(figsize=(14, 8))

    # Define colors for each category
    colors = {
        'KNOWiNK': '#1f77b4',    # Blue
        'ES&S': '#ff7f0e',        # Orange
        'In-House': '#2ca02c',    # Green
        'Other': '#d62728',       # Red
    }

    # Create the stacked bars
    bottom = np.zeros(len(years))

    for category in categories:
        values = category_data[category]
        ax.bar(years, values, bottom=bottom, label=category,
               color=colors[category], edgecolor='black', linewidth=0.5, width=1.5)
        bottom += np.array(values)

    # Styling
    ax.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of States with Uniform Poll Book Deployment', fontsize=13, fontweight='bold')
    ax.set_title('Statewide Poll Book Uniformity Over Time (2006-2026)\n'
                 'States with Uniform Poll Book Deployments by Vendor (≥80% EPB Adoption)',
                 fontsize=15, fontweight='bold', pad=20)

    # Set x-axis ticks to show all years
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha='right')

    # Grid for readability
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # Legend
    ax.legend(loc='upper left', fontsize=11, framealpha=0.9)

    # Set y-axis to start at 0
    ax.set_ylim(0, max(bottom) * 1.1)

    # Tight layout
    plt.tight_layout()

    # Save figure
    output_path = OUTPUT_DIR / 'pollbook_uniformity_trends.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"\n✓ Chart saved to {output_path}")


def print_summary_table(data):
    """
    Print a summary table of the data.

    Args:
        data: Dict of year -> {vendor_category: count}
    """
    years = sorted(data.keys())
    categories = ['KNOWiNK', 'ES&S', 'In-House', 'Other', 'Total']

    print("\n" + "=" * 80)
    print("POLL BOOK UNIFORMITY SUMMARY TABLE")
    print("=" * 80)
    print()

    # Header
    header = f"{'Year':<8}"
    for cat in categories:
        header += f"{cat:>12}"
    print(header)
    print("-" * 80)

    # Data rows
    for year in years:
        year_counts = data[year]
        total = sum(year_counts.values())

        row = f"{year:<8}"
        for cat in categories[:-1]:  # All except 'Total'
            count = year_counts.get(cat, 0)
            row += f"{count:>12}"
        row += f"{total:>12}"
        print(row)

    print()


def main():
    """Main execution function."""
    print("=" * 80)
    print("ANALYZING POLL BOOK UNIFORMITY TRENDS")
    print("=" * 80)
    print()

    # Load and analyze data
    print("Loading state-level data for all years...")
    data = analyze_pollbook_uniformity_by_year()

    if not data:
        print("\n✗ No state-level data found. Run condense_to_state_level.py first.")
        return 1

    print(f"\n✓ Loaded data for {len(data)} years")

    # Print summary table
    print_summary_table(data)

    # Create chart
    print("Generating stacked bar chart...")
    create_stacked_bar_chart(data)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

    return 0


if __name__ == '__main__':
    exit(main())
