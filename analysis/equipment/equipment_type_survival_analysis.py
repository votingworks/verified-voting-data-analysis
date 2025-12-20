#!/usr/bin/env python3
"""
Generate Kaplan-Meier survival curves for equipment type categories.

Properly handles right-censored data (equipment still in use) to estimate
survival probabilities and median lifetime for equipment categories like
DRE, Hand-Fed Optical Scanner, etc.

Supports multiple equipment types on the same chart for comparison.

Usage:
    python3 equipment_type_survival_analysis.py "DRE"
    python3 equipment_type_survival_analysis.py "DRE" "Hand-Fed Optical Scanner"
    python3 equipment_type_survival_analysis.py "DRE" "Hand-Fed Optical Scanner" "Ballot Marking Device"

Args:
    equipment_types: One or more category names

Output: outputs/figures/equipment/model_lifetime/survival_{types}.png
"""

import csv
import sys
import re
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from lifelines import KaplanMeierFitter

# Directories
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'equipment' / 'model_lifetime'

# Map category names to Equipment_Type values in machine_lifetimes.csv
# Uses actual equipment type names for clarity
EQUIPMENT_TYPE_MAP = {
    'DRE': ['DRE-Touchscreen', 'DRE-Push Button', 'DRE-Dial'],
    'Hand-Fed Optical Scanner': ['Hand-Fed Optical Scanner'],
    'Batch-Fed Optical Scanner': ['Batch-Fed Optical Scanner'],
    'Ballot Marking Device': ['Ballot Marking Device'],
    'Hybrid': ['Hybrid Optical Scan/BMD', 'Hybrid Optical Scan/DRE', 'Hybrid BMD/Tabulator'],
}


def load_machine_lifetimes():
    """Load machine_lifetimes.csv data."""
    filepath = DATA_DIR / 'machine_lifetimes.csv'

    if not filepath.exists():
        raise FileNotFoundError(f"Machine lifetimes file not found: {filepath}")

    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['First_Year'] = int(row['First_Year'])
            row['Last_Year'] = int(row['Last_Year'])
            row['Length_Of_Use'] = int(row['Length_Of_Use'])
            records.append(row)

    return records


def filter_by_equipment_type(records, category):
    """
    Filter records by equipment type category.

    Args:
        records: List of machine use records
        category: Category name (e.g., 'DRE', 'Precinct Scan')

    Returns:
        Filtered list of records
    """
    if category not in EQUIPMENT_TYPE_MAP:
        # Try case-insensitive match
        for key in EQUIPMENT_TYPE_MAP:
            if key.lower() == category.lower():
                category = key
                break
        else:
            raise ValueError(
                f"Unknown equipment type: {category}\n"
                f"Valid options: {', '.join(EQUIPMENT_TYPE_MAP.keys())}"
            )

    equipment_types = EQUIPMENT_TYPE_MAP[category]
    return [r for r in records if r['Equipment_Type'] in equipment_types]


def create_survival_curves(categories_data, output_path):
    """
    Create Kaplan-Meier survival curves for multiple equipment types on one chart.

    Args:
        categories_data: List of (category_name, records) tuples
        output_path: Path to save chart

    Returns:
        dict: {category_name: median_survival}
    """
    # Colors for different categories
    colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#a65628']

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7))

    median_results = {}
    max_duration = 0
    total_n = 0

    for i, (category_name, records) in enumerate(categories_data):
        color = colors[i % len(colors)]

        # Prepare data for survival analysis
        durations = np.array([r['Length_Of_Use'] for r in records])
        event_observed = np.array([r['Last_Year'] < 2026 for r in records])  # True = retired

        max_duration = max(max_duration, durations.max())

        # Calculate stats
        n_total = len(records)
        n_retired = event_observed.sum()
        total_n += n_total

        # Fit Kaplan-Meier model
        kmf = KaplanMeierFitter()
        kmf.fit(durations, event_observed=event_observed, label=f'{category_name} (n={n_total:,})')

        # Get median survival
        median_survival = kmf.median_survival_time_
        median_results[category_name] = median_survival

        # Plot survival curve with confidence interval
        kmf.plot_survival_function(ax=ax, ci_show=True, color=color, linewidth=2)

    # Add horizontal line at 50% survival
    ax.axhline(y=0.5, color='gray', linestyle=':', linewidth=1, alpha=0.5)

    # Labels and title
    ax.set_xlabel('Years in Service', fontsize=13, fontweight='bold')
    ax.set_ylabel('Survival Probability', fontsize=13, fontweight='bold')

    if len(categories_data) == 1:
        title = f'Equipment Survival Curve: {categories_data[0][0]}'
    else:
        title = 'Equipment Survival Curves by Type'
    ax.set_title(f'{title}\n(n={total_n:,} total)', fontsize=15, fontweight='bold', pad=20)

    # Set axis limits
    ax.set_ylim(0, 1.05)
    ax.set_xlim(0, max_duration + 2)

    # Grid
    ax.grid(axis='both', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # Legend
    ax.legend(loc='upper right', fontsize=10)

    # Layout
    plt.tight_layout()

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return median_results


def slugify(text):
    """Convert text to filename-safe slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text.strip('_')


def main():
    """Main execution function."""
    print("=" * 80)
    print("EQUIPMENT TYPE SURVIVAL ANALYSIS (Kaplan-Meier)")
    print("=" * 80)
    print()

    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python3 equipment_type_survival_analysis.py <type1> [type2] [type3] ...")
        print("Example: python3 equipment_type_survival_analysis.py 'DRE'")
        print("Example: python3 equipment_type_survival_analysis.py 'DRE' 'Hand-Fed Optical Scanner'")
        print(f"\nValid equipment types: {', '.join(EQUIPMENT_TYPE_MAP.keys())}")
        return 1

    categories = sys.argv[1:]
    print(f"Equipment types: {', '.join(categories)}")
    print()

    # Load data
    print("Loading machine_lifetimes.csv...")
    records = load_machine_lifetimes()
    print(f"✓ Loaded {len(records):,} total records")
    print()

    # Filter for each category
    categories_data = []
    for category in categories:
        print(f"Filtering for equipment type '{category}'...")
        try:
            filtered = filter_by_equipment_type(records, category)
        except ValueError as e:
            print(f"Error: {e}")
            return 1

        if not filtered:
            print(f"  No matching records found for '{category}'.")
            continue

        # Show which equipment types matched
        matched_types = sorted(set(r['Equipment_Type'] for r in filtered))
        print(f"  ✓ Found {len(filtered):,} records")
        print(f"    Matched: {', '.join(matched_types)}")

        # Calculate stats
        retired = [r for r in filtered if r['Last_Year'] < 2026]
        still_in_use = [r for r in filtered if r['Last_Year'] == 2026]
        print(f"    Retired: {len(retired):,}, Still in use: {len(still_in_use):,}")

        categories_data.append((category, filtered))

    if not categories_data:
        print("No valid categories found.")
        return 1

    print()

    # Generate output filename
    if len(categories) == 1:
        type_slug = slugify(categories[0])
    else:
        type_slug = '_vs_'.join(slugify(c) for c in categories)
    output_path = OUTPUT_DIR / f'survival_{type_slug}.png'

    print("Fitting Kaplan-Meier survival models...")
    median_results = create_survival_curves(categories_data, output_path)
    print(f"✓ Survival curve saved to {output_path}")

    # Print summary
    print()
    print("Survival Analysis Results:")
    for category, median in median_results.items():
        if not np.isnan(median) and not np.isinf(median):
            print(f"  - {category}: median survival = {median:.0f} years")
        else:
            print(f"  - {category}: median not yet reached (>50% still in use)")

    print()
    print("=" * 80)
    print("✓ SURVIVAL ANALYSIS COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
