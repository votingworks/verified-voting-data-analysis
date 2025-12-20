#!/usr/bin/env python3
"""
Generate bar chart showing year of introduction distribution for equipment models.

Shows when jurisdictions adopted a particular model.

Usage:
    python3 model_introduction.py "DS200"
    python3 model_introduction.py "AccuVote OS"

Args:
    model: Model name (case-insensitive substring match)

Output: outputs/figures/equipment/model_lifetime/introduction_{model_slug}.png
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


def filter_by_model(records, model_pattern):
    """
    Filter records by model name.

    Args:
        records: List of machine use records
        model_pattern: Case-insensitive substring to match

    Returns:
        Filtered list of records
    """
    pattern = model_pattern.lower()
    return [r for r in records if pattern in r['Model'].lower()]


def create_introduction_chart(records, model_name, output_path):
    """
    Create bar chart of introduction year distribution.

    Args:
        records: Filtered list of machine use records
        model_name: Model name for title
        output_path: Path to save chart
    """
    # Count introductions by year
    year_counts = Counter(r['First_Year'] for r in records)

    # Get full range of years
    min_year = min(year_counts.keys())
    max_year = max(year_counts.keys())

    # Create continuous range (every 2 years to match election cycles)
    if min_year % 2 == 1:
        min_year -= 1
    years = list(range(min_year, max_year + 1, 2))
    counts = [year_counts.get(y, 0) for y in years]

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    # Create bar chart
    bars = ax.bar(range(len(years)), counts, color='steelblue',
                  edgecolor='black', linewidth=0.5)

    # Highlight peak year
    if counts:
        peak_idx = counts.index(max(counts))
        bars[peak_idx].set_color('darkorange')

    # Labels and title
    ax.set_xlabel('Year of Introduction', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of Jurisdictions', fontsize=13, fontweight='bold')

    n_total = len(records)
    peak_year = years[peak_idx] if counts else 'N/A'
    peak_count = max(counts) if counts else 0

    title = f'Equipment Introduction Timeline: {model_name}'
    subtitle = f'n={n_total:,} jurisdictions | Peak: {peak_year} ({peak_count:,} adoptions)'
    ax.set_title(f'{title}\n{subtitle}', fontsize=15, fontweight='bold', pad=20)

    # X-axis labels
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha='right')

    # Grid
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # Add value labels on significant bars
    if counts:
        max_height = max(counts)
        for i, count in enumerate(counts):
            if count > max_height * 0.1:  # Label bars > 10% of max
                ax.text(i, count + max_height * 0.02, f'{count:,}',
                        ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Layout
    plt.tight_layout()

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


def slugify(text):
    """Convert text to filename-safe slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text.strip('_')


def main():
    """Main execution function."""
    print("=" * 80)
    print("EQUIPMENT INTRODUCTION TIMELINE")
    print("=" * 80)
    print()

    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python3 model_introduction.py <model>")
        print("Example: python3 model_introduction.py 'DS200'")
        return 1

    model_pattern = sys.argv[1]
    print(f"Model pattern: {model_pattern}")
    print()

    # Load data
    print("Loading machine_lifetimes.csv...")
    records = load_machine_lifetimes()
    print(f"✓ Loaded {len(records):,} total records")

    # Filter
    print(f"Filtering for model matching '{model_pattern}'...")
    filtered = filter_by_model(records, model_pattern)
    print(f"✓ Found {len(filtered):,} matching records")

    if not filtered:
        print("No matching records found. Try a different model name.")
        return 1

    # Show which models matched
    matched_models = sorted(set(r['Model'] for r in filtered))
    print(f"  Matched models: {', '.join(matched_models)}")

    # Year range
    years = [r['First_Year'] for r in filtered]
    print(f"  Introduction years: {min(years)} - {max(years)}")
    print()

    # Generate chart
    model_slug = slugify(model_pattern)
    output_path = OUTPUT_DIR / f'introduction_{model_slug}.png'

    print("Generating introduction chart...")
    create_introduction_chart(filtered, model_pattern, output_path)
    print(f"✓ Chart saved to {output_path}")

    # Print summary
    year_counts = Counter(years)
    peak_year = max(year_counts, key=year_counts.get)

    print()
    print("Introduction Summary:")
    print(f"  - Total adoptions: {len(filtered):,}")
    print(f"  - First introduction: {min(years)}")
    print(f"  - Last introduction: {max(years)}")
    print(f"  - Peak year: {peak_year} ({year_counts[peak_year]:,} adoptions)")

    print()
    print("=" * 80)
    print("✓ INTRODUCTION CHART COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
