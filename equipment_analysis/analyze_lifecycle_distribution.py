#!/usr/bin/env python3
"""
Analyze equipment lifecycle distributions from family change data.

Generates four bar charts combining both system changes and no-turnover jurisdictions:
1. Full distribution of all lifecycle lengths
2. Distribution for changes from Paper marking method
3. Distribution for changes from BMD (Machine marking + non-DRE)
4. Distribution for changes from DRE
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from collections import Counter
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from equipment_constants import PREFIX_LEVER

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
# Navigate to project root and data/output directories
DATA_DIR = SCRIPT_DIR.parent / 'data'
OUTPUT_DIR = SCRIPT_DIR


def load_family_changes_data():
    """Load equipment family changes data, including no-turnover jurisdictions."""

    # Load between-system turnovers
    between_filepath = DATA_DIR / 'between_system_turnovers.csv'
    if not between_filepath.exists():
        raise FileNotFoundError(f"Between-system file not found: {between_filepath}")

    df_between = pd.read_csv(between_filepath)
    print(f"✓ Loaded {len(df_between):,} between-system changes")

    # Load no-turnover jurisdictions
    no_turnover_filepath = DATA_DIR / 'no_system_turnovers.csv'
    if not no_turnover_filepath.exists():
        print(f"⚠ Warning: No-turnover file not found: {no_turnover_filepath}")
        print(f"  Proceeding with only between-system changes")
        return df_between

    df_no_turnover = pd.read_csv(no_turnover_filepath)
    print(f"✓ Loaded {len(df_no_turnover):,} no-turnover jurisdictions")

    # Merge datasets
    df_combined = pd.concat([df_between, df_no_turnover], ignore_index=True)
    print(f"✓ Combined: {len(df_combined):,} total lifecycle observations")
    print(f"  - Between-system changes: {len(df_between):,}")
    print(f"  - No-turnover (excl Hand Count): {len(df_no_turnover):,}")

    return df_combined


def print_summary_statistics(lifecycles, dataset_name):
    """Print summary statistics for a lifecycle distribution."""
    print(f"\n{dataset_name}:")
    print(f"  Total changes: {len(lifecycles):,}")
    print(f"  Mean lifecycle: {np.mean(lifecycles):.2f} years")
    print(f"  Median lifecycle: {np.median(lifecycles):.1f} years")
    print(f"  Mode (most common): {Counter(lifecycles).most_common(1)[0][0]} years ({Counter(lifecycles).most_common(1)[0][1]:,} occurrences)")
    print(f"  Min: {np.min(lifecycles)} years")
    print(f"  Max: {np.max(lifecycles)} years")
    print(f"  Std Dev: {np.std(lifecycles):.2f} years")


def create_lifecycle_distribution_chart(lifecycles, title, output_file, subtitle="", highlight_median=True):
    """Create and save bar chart of lifecycle distribution."""

    # Count frequency of each lifecycle length
    lifecycle_counts = Counter(lifecycles)

    # Sort by lifecycle length for proper x-axis ordering
    sorted_lifecycles = sorted(lifecycle_counts.items())
    x_values = [item[0] for item in sorted_lifecycles]
    y_values = [item[1] for item in sorted_lifecycles]

    # Create figure
    plt.figure(figsize=(14, 7))

    # Create bar chart
    bars = plt.bar(x_values, y_values, color='steelblue', edgecolor='black', linewidth=0.5)

    # Highlight the median value (if enabled)
    if highlight_median:
        median_value = int(np.median(lifecycles))
        if median_value in x_values:
            median_index = x_values.index(median_value)
            bars[median_index].set_color('darkorange')

    # Add labels and title
    plt.xlabel('Years Between Changes (Lifecycle Length)', fontsize=13, fontweight='bold')
    plt.ylabel('Number of Changes', fontsize=13, fontweight='bold')

    # Title with subtitle
    full_title = f'{title}\n(n={len(lifecycles):,} changes)'
    if subtitle:
        full_title += f'\n{subtitle}'
    plt.title(full_title, fontsize=15, fontweight='bold', pad=20)

    # Add grid for readability
    plt.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    # Set x-axis to show all years
    plt.xticks(x_values, rotation=0)

    # Add value labels on top of bars for significant peaks
    max_height = max(y_values)
    for i, (x, y) in enumerate(zip(x_values, y_values)):
        if y > max_height * 0.15:  # Label bars that are > 15% of max height
            plt.text(x, y + max_height * 0.01, f'{y:,}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Tight layout to prevent label cutoff
    plt.tight_layout()

    # Save figure
    output_path = OUTPUT_DIR / output_file
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Chart saved to {output_path}")

    # Close figure to free memory
    plt.close()


def main():
    """Main processing pipeline."""

    print("=" * 80)
    print("EQUIPMENT LIFECYCLE DISTRIBUTION ANALYSIS")
    print("=" * 80)

    # Step 1: Load family changes data
    print("\nLoading family changes data...")
    df = load_family_changes_data()

    # Step 2: Extract all lifecycle lengths
    print("\nProcessing lifecycle data...")
    all_lifecycles = df['Years_Between'].values

    # Print summary statistics for all changes
    print_summary_statistics(all_lifecycles, "Dataset 1: All Equipment Family Changes")

    # Step 3: Create Chart 1 - Full distribution
    print("\nGenerating Chart 1: All Changes...")
    create_lifecycle_distribution_chart(
        all_lifecycles,
        "Voting System Lifecycle Distribution - All Turnover",
        "lifecycle_distribution_all.png"
    )

    # Step 4: Filter for Paper marking method
    print("\nFiltering for Paper marking method...")
    paper_df = df[df['From_Marking_Method'] == 'Paper']
    paper_lifecycles_raw = paper_df['Years_Between'].values

    # Filter out top 10 outliers (longest turnovers)
    paper_lifecycles_sorted = np.sort(paper_lifecycles_raw)
    if len(paper_lifecycles_sorted) > 10:
        paper_lifecycles = paper_lifecycles_sorted[:-10]  # Exclude top 10
        print(f"✓ Found {len(paper_df):,} changes from Paper marking method")
        print(f"  (Excluding top 10 longest turnovers: {paper_lifecycles_sorted[-10:].tolist()})")
    else:
        paper_lifecycles = paper_lifecycles_raw
        print(f"✓ Found {len(paper_df):,} changes from Paper marking method")

    # Print summary statistics for Paper
    print_summary_statistics(paper_lifecycles, "Dataset 2: From Paper Marking Method (excluding top 10 outliers)")

    # Step 5: Create Chart 2 - Paper marking method
    print("\nGenerating Chart 2: From Paper Marking Method...")
    create_lifecycle_distribution_chart(
        paper_lifecycles,
        "Voting System Lifecycle Distribution - HMPB System Turnover",
        "lifecycle_distribution_from_paper.png"
    )

    # Step 6: Filter for BMD (Machine + non-DRE)
    print("\nFiltering for BMD (Machine marking + non-DRE)...")

    # Exclude mechanical lever machines (not BMDs)
    lever_machines = [
        f'{PREFIX_LEVER}AVM AVM Manual',
        f'{PREFIX_LEVER}AVM AVM Printomatic',
        f'{PREFIX_LEVER}IES Shoup Manual'
    ]

    bmd_df = df[
        (df['From_Marking_Method'] == 'Machine') &
        (df['From_DRE'] == 'No') &
        (~df['From_Equipment'].isin(lever_machines))
    ]
    bmd_lifecycles = bmd_df['Years_Between'].values

    print(f"✓ Found {len(bmd_df):,} changes from BMD (excluding mechanical lever machines)")

    # Print summary statistics for BMD
    print_summary_statistics(bmd_lifecycles, "Dataset 3: BMD Turnover")

    # Step 7: Create Chart 3 - BMD
    print("\nGenerating Chart 3: From BMD...")
    create_lifecycle_distribution_chart(
        bmd_lifecycles,
        "Voting System Lifecycle Distribution - BMD Turnover",
        "lifecycle_distribution_from_bmd.png",
        highlight_median=False
    )

    # Step 8: Filter for DRE
    print("\nFiltering for DRE...")
    dre_df = df[df['From_DRE'] == 'Yes']
    dre_lifecycles = dre_df['Years_Between'].values

    print(f"✓ Found {len(dre_df):,} changes from DRE")

    # Print summary statistics for DRE
    print_summary_statistics(dre_lifecycles, "Dataset 4: From DRE")

    # Step 9: Create Chart 4 - DRE
    print("\nGenerating Chart 4: From DRE...")
    create_lifecycle_distribution_chart(
        dre_lifecycles,
        "Voting System Lifecycle Distribution - DRE Turnover",
        "lifecycle_distribution_from_dre.png"
    )

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nGenerated files:")
    print("  - equipment_analysis/lifecycle_distribution_all.png")
    print("  - equipment_analysis/lifecycle_distribution_from_paper.png")
    print("  - equipment_analysis/lifecycle_distribution_from_bmd.png")
    print("  - equipment_analysis/lifecycle_distribution_from_dre.png")
    print()


if __name__ == "__main__":
    main()
