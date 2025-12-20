#!/usr/bin/env python3
"""
Generate bar chart showing lifetime distribution for a specific equipment model.

Usage:
    python3 model_lifetime_distribution.py "ExpressVote" 2016
    python3 model_lifetime_distribution.py "AccuVote OS" 2010

Args:
    model: Model name (case-insensitive substring match)
    max_first_year: Only include equipment first used on or before this year (default: 2020)

Output: outputs/figures/equipment/model_lifetime_{model_slug}.png
"""

import csv
import sys
import re
import matplotlib.pyplot as plt
from pathlib import Path
from collections import Counter

# Directories
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'equipment' / 'model_lifetime'


def load_machine_uses():
    """Load machine_uses.csv data."""
    filepath = DATA_DIR / 'machine_uses.csv'

    if not filepath.exists():
        raise FileNotFoundError(f"Machine uses file not found: {filepath}")

    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['First_Year'] = int(row['First_Year'])
            row['Last_Year'] = int(row['Last_Year'])
            row['Length_Of_Use'] = int(row['Length_Of_Use'])
            records.append(row)

    return records


def filter_by_model(records, model_pattern, max_first_year):
    """
    Filter records by model name and max first year.

    Args:
        records: List of machine use records
        model_pattern: Case-insensitive substring to match
        max_first_year: Only include equipment first used on or before this year

    Returns:
        Filtered list of records
    """
    pattern = model_pattern.lower()
    return [
        r for r in records
        if pattern in r['Model'].lower() and r['First_Year'] <= max_first_year
    ]


def create_lifetime_chart(records, model_name, max_first_year, output_path):
    """
    Create bar chart of lifetime distribution with "Still In Use" separated.

    Args:
        records: Filtered list of machine use records
        model_name: Model name for title
        max_first_year: Max first year filter for subtitle
        output_path: Path to save chart
    """
    # Split into retired vs still in use
    retired = [r for r in records if r['Last_Year'] < 2026]
    still_in_use = [r for r in records if r['Last_Year'] == 2026]

    # Count retired lifetimes
    retired_counts = Counter(r['Length_Of_Use'] for r in retired)

    # Build x values and y values for retired equipment
    if retired_counts:
        min_lifetime = min(retired_counts.keys())
        max_lifetime = max(retired_counts.keys())
        # Create continuous range (step by 2 since lifetimes are in 2-year increments)
        x_retired = list(range(min_lifetime, max_lifetime + 1, 2))
        y_retired = [retired_counts.get(x, 0) for x in x_retired]
    else:
        x_retired = []
        y_retired = []

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    # Calculate bar positions
    if x_retired:
        # Retired bars
        bar_positions = list(range(len(x_retired)))
        bars_retired = ax.bar(bar_positions, y_retired, color='steelblue',
                              edgecolor='black', linewidth=0.5, label='Retired')

        # Still In Use bar with gap
        if still_in_use:
            gap_position = len(x_retired) + 1  # +1 creates gap
            bar_still_in_use = ax.bar([gap_position], [len(still_in_use)],
                                      color='#D3D3D3', edgecolor='black',
                                      linewidth=0.5, label='Still In Use')

        # X-axis labels
        x_labels = [str(x) for x in x_retired]
        x_tick_positions = bar_positions.copy()
        if still_in_use:
            x_labels.append('Still\nIn Use')
            x_tick_positions.append(gap_position)

        ax.set_xticks(x_tick_positions)
        ax.set_xticklabels(x_labels)

    elif still_in_use:
        # Only "Still In Use" data
        ax.bar([0], [len(still_in_use)], color='#D3D3D3', edgecolor='black',
               linewidth=0.5, label='Still In Use')
        ax.set_xticks([0])
        ax.set_xticklabels(['Still\nIn Use'])
    else:
        # No data at all
        ax.text(0.5, 0.5, 'No matching records found',
                ha='center', va='center', transform=ax.transAxes, fontsize=14)

    # Labels and title
    ax.set_xlabel('Lifetime (Years)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of Jurisdictions', fontsize=13, fontweight='bold')

    total_count = len(records)
    retired_count = len(retired)
    still_in_use_count = len(still_in_use)

    title = f'Equipment Lifetime Distribution: {model_name}'
    subtitle = f'First Year ≤ {max_first_year} | n={total_count:,} ({retired_count:,} retired, {still_in_use_count:,} still in use)'
    ax.set_title(f'{title}\n{subtitle}', fontsize=15, fontweight='bold', pad=20)

    # Grid
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # Add value labels on bars
    all_y = y_retired + ([len(still_in_use)] if still_in_use else [])
    if all_y:
        max_height = max(all_y)
        # Label retired bars
        for i, y in enumerate(y_retired):
            if y > 0:
                ax.text(i, y + max_height * 0.01, f'{y:,}',
                        ha='center', va='bottom', fontsize=9, fontweight='bold')
        # Label still in use bar
        if still_in_use and x_retired:
            gap_position = len(x_retired) + 1
            ax.text(gap_position, len(still_in_use) + max_height * 0.01,
                    f'{len(still_in_use):,}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
        elif still_in_use:
            ax.text(0, len(still_in_use) + max_height * 0.01,
                    f'{len(still_in_use):,}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Legend if we have both categories
    if retired and still_in_use:
        ax.legend(loc='upper right', fontsize=10)

    # Layout
    plt.tight_layout()

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return output_path


def slugify(text):
    """Convert text to filename-safe slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text.strip('_')


def main():
    """Main execution function."""
    print("=" * 80)
    print("MODEL LIFETIME DISTRIBUTION CHART")
    print("=" * 80)
    print()

    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python3 model_lifetime_distribution.py <model> [max_first_year]")
        print("Example: python3 model_lifetime_distribution.py 'ExpressVote' 2016")
        return 1

    model_pattern = sys.argv[1]
    max_first_year = int(sys.argv[2]) if len(sys.argv) > 2 else 2020

    print(f"Model pattern: {model_pattern}")
    print(f"Max First Year: {max_first_year}")
    print()

    # Load data
    print("Loading machine_uses.csv...")
    records = load_machine_uses()
    print(f"✓ Loaded {len(records):,} total records")

    # Filter
    print(f"Filtering for model matching '{model_pattern}'...")
    filtered = filter_by_model(records, model_pattern, max_first_year)
    print(f"✓ Found {len(filtered):,} matching records")

    if not filtered:
        print("No matching records found. Try a different model name or year.")
        return 1

    # Show which models matched
    matched_models = sorted(set(r['Model'] for r in filtered))
    print(f"  Matched models: {', '.join(matched_models)}")
    print()

    # Generate chart
    model_slug = slugify(model_pattern)
    output_path = OUTPUT_DIR / f'model_lifetime_{model_slug}_{max_first_year}.png'

    print("Generating chart...")
    create_lifetime_chart(filtered, model_pattern, max_first_year, output_path)
    print(f"✓ Chart saved to {output_path}")

    # Print summary stats
    retired = [r for r in filtered if r['Last_Year'] < 2026]
    still_in_use = [r for r in filtered if r['Last_Year'] == 2026]

    print()
    print("Summary:")
    print(f"  - Total matches: {len(filtered):,}")
    print(f"  - Retired: {len(retired):,}")
    print(f"  - Still in use: {len(still_in_use):,}")

    if retired:
        lifetimes = [r['Length_Of_Use'] for r in retired]
        print(f"  - Mean lifetime (retired): {sum(lifetimes)/len(lifetimes):.1f} years")
        print(f"  - Median lifetime (retired): {sorted(lifetimes)[len(lifetimes)//2]} years")

    print()
    print("=" * 80)
    print("✓ CHART GENERATION COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
