#!/usr/bin/env python3
"""
Analyze equipment lifecycle distributions from family change data.

Generates six bar charts combining both system changes and no-turnover jurisdictions:
1. Full distribution of all lifecycle lengths
2. Distribution for changes from Paper marking method
3. Distribution for changes from Paper (excluding AccuVote OS)
4. Distribution for changes from BMD (Machine marking + non-DRE)
5. Distribution for changes from DREs without VVPAT option
6. Distribution for changes from DREs with VVPAT option
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
CONDENSED_DIR = DATA_DIR / 'verifier-condensed'
OUTPUT_DIR = SCRIPT_DIR

# DREs that NEVER have VVPAT option (only appear without VVPAT)
# These models cannot be configured with paper trail capabilities
DRES_WITHOUT_VVPAT_OPTION = [
    'DRE - Sequoia AVC Advantage',
    'DRE - AccuVote TS',
    'DRE - Danaher Shouptronic 1242',
    'DRE - AVS WinVote',
    'DRE - Unilect Patriot',
    'DRE - Hart InterCivic Verity Touch',
    'DRE - MicroVote MV-464',
    'DRE - VTI VoTWARE'
]


def load_family_changes_data():
    """Load equipment family changes data, including no-turnover jurisdictions.

    Reads from voting_system_time_series.csv and combines:
    1. between_system transition rows (have Years_Between already)
    2. baseline-only rows (need to calculate lifecycle as 2026 - To_Year)
    """
    filepath = DATA_DIR / 'voting_system_time_series.csv'
    if not filepath.exists():
        raise FileNotFoundError(f"Time series file not found: {filepath}")

    df = pd.read_csv(filepath)

    # Get between_system transition rows (these already have Years_Between)
    df_transitions = df[df['Record_Type'] == 'between_system'].copy()
    print(f"✓ Loaded {len(df_transitions):,} between-system changes")

    # Find baseline-only jurisdictions (no transitions)
    # First, get FIPS that have any transitions
    transition_fips = df[df['Record_Type'].isin(['between_system', 'within_system'])]['FIPS'].unique()

    # Get baseline rows for FIPS that have NO transitions
    df_baseline_only = df[
        (df['Record_Type'] == 'baseline') &
        (~df['FIPS'].isin(transition_fips)) &
        (df['To_Equipment'] != 'Hand Count')  # Exclude Hand Count
    ].copy()

    print(f"✓ Loaded {len(df_baseline_only):,} no-turnover jurisdictions")

    # For baseline-only rows, calculate Years_Between and set From_* fields for compatibility
    # Baseline rows have From_* empty and To_* populated with starting equipment
    df_baseline_only['Years_Between'] = 2026 - df_baseline_only['To_Year'].astype(int)

    # Copy To_* to From_* for compatibility with downstream analysis
    # (filters like From_Marking_Method, From_Equipment, etc.)
    for col in ['Year', 'Equipment', 'Vendor', 'System', 'DRE', 'Marking_Method']:
        df_baseline_only[f'From_{col}'] = df_baseline_only[f'To_{col}']

    # Set To_Year to 2026 (end of observation window)
    df_baseline_only['To_Year'] = 2026

    # Merge datasets
    df_combined = pd.concat([df_transitions, df_baseline_only], ignore_index=True)
    print(f"✓ Combined: {len(df_combined):,} total lifecycle observations")
    print(f"  - Between-system changes: {len(df_transitions):,}")
    print(f"  - No-turnover (excl Hand Count): {len(df_baseline_only):,}")

    return df_combined


def load_family_changes_data_with_voters():
    """
    Load family changes data and join with registered voter counts.

    Reuses pattern from analyze_vendor_turnover.py to join turnover data
    with condensed CSVs via FIPS code.

    Returns:
        DataFrame with additional 'Registered_Voters' column
    """
    # Load base data
    df = load_family_changes_data()

    # Initialize voters column
    df['Registered_Voters'] = 0

    # Get unique years from data
    years = df['To_Year'].unique()

    # For each year, load condensed data and join
    for year in sorted(years):
        condensed_path = CONDENSED_DIR / f'{year}_verifier-jurisdictions-condensed.csv'

        if not condensed_path.exists():
            print(f"  Warning: Missing condensed data for {year}")
            continue

        # Read condensed data (skip title row)
        df_year = pd.read_csv(condensed_path, skiprows=1)

        # Create lookup: FIPS -> Registered Voters
        voters_lookup = df_year.set_index('FIPS code')['Registered Voters'].to_dict()

        # Update for this year
        year_mask = df['To_Year'] == year
        df.loc[year_mask, 'Registered_Voters'] = df.loc[year_mask, 'FIPS'].map(voters_lookup).fillna(0)

    # Print join statistics
    total = len(df)
    matched = (df['Registered_Voters'] > 0).sum()
    print(f"✓ Matched {matched:,}/{total:,} transitions with voter data ({matched/total*100:.1f}%)")

    # Additional diagnostic output
    print(f"\nVoter Data Join Statistics:")
    print(f"  Total transitions: {len(df):,}")
    print(f"  Matched with voters: {matched:,} ({matched/total*100:.1f}%)")
    print(f"  Zero voters: {(df['Registered_Voters'] == 0).sum():,}")
    print(f"  Total registered voters: {df['Registered_Voters'].sum():,.0f}")
    print(f"  Mean voters per transition: {df['Registered_Voters'].mean():,.0f}")

    return df


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


def print_summary_statistics_voters(lifecycles, voters, dataset_name):
    """Print summary statistics for voter-weighted lifecycle distribution."""
    total_voters = sum(voters)

    # Calculate weighted mean
    if total_voters > 0:
        weighted_mean = sum(lc * v for lc, v in zip(lifecycles, voters)) / total_voters
    else:
        weighted_mean = 0

    # Calculate weighted median (need to expand lifecycles by voter counts)
    expanded_lifecycles = []
    for lifecycle, voter_count in zip(lifecycles, voters):
        # Add lifecycle value 'voter_count' times (approximate for large numbers)
        if voter_count > 1000:
            # For large voter counts, add proportionally fewer entries (sampling)
            expanded_lifecycles.extend([lifecycle] * int(voter_count / 100))
        else:
            expanded_lifecycles.extend([lifecycle] * int(voter_count))

    weighted_median = np.median(expanded_lifecycles) if expanded_lifecycles else 0

    print(f"\n{dataset_name}:")
    print(f"  Total voters: {total_voters:,}")
    print(f"  Weighted mean lifecycle: {weighted_mean:.2f} years")
    print(f"  Weighted median lifecycle: {weighted_median:.1f} years")
    print(f"  Unweighted mean (for comparison): {np.mean(lifecycles):.2f} years")
    print(f"  Unweighted median (for comparison): {np.median(lifecycles):.1f} years")


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


def create_bmd_lifecycle_chart(lifecycles, title, output_file):
    """Create BMD-specific lifecycle chart with >10 aggregation."""

    # Separate lifecycles into individual bars (2-9) and aggregated (10+)
    individual_counts = Counter()
    count_10_plus = 0

    for lifecycle in lifecycles:
        if lifecycle >= 10:
            count_10_plus += 1
        else:
            individual_counts[lifecycle] += 1

    # Build x_values and y_values
    x_values = []
    y_values = []
    x_labels = []

    # Add individual lifecycle counts (sorted)
    for lifecycle in sorted(individual_counts.keys()):
        x_values.append(lifecycle)
        y_values.append(individual_counts[lifecycle])
        x_labels.append(str(lifecycle))

    # Add >10 bar
    if count_10_plus > 0:
        # Use the next position for >10
        if x_values:
            x_values.append(max(x_values) + 1)
        else:
            x_values.append(10)
        y_values.append(count_10_plus)
        x_labels.append('>10')

    # Create figure
    plt.figure(figsize=(14, 7))

    # Create bar chart
    bars = plt.bar(range(len(x_values)), y_values, color='steelblue', edgecolor='black', linewidth=0.5)

    # Highlight the >10 bar in a different color
    if x_labels and x_labels[-1] == '>10':
        bars[-1].set_color('darkorange')

    # Add labels and title
    plt.xlabel('Years Between Changes (Lifecycle Length)', fontsize=13, fontweight='bold')
    plt.ylabel('Number of Changes', fontsize=13, fontweight='bold')

    # Title
    full_title = f'{title}\n(n={len(lifecycles):,} changes)'
    plt.title(full_title, fontsize=15, fontweight='bold', pad=20)

    # Add grid for readability
    plt.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    # Set x-axis labels
    plt.xticks(range(len(x_labels)), x_labels, rotation=0)

    # Add value labels on top of bars
    max_height = max(y_values) if y_values else 1
    for i, y in enumerate(y_values):
        plt.text(i, y + max_height * 0.01, f'{y:,}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Tight layout to prevent label cutoff
    plt.tight_layout()

    # Save figure
    output_path = OUTPUT_DIR / output_file
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Chart saved to {output_path}")

    # Close figure to free memory
    plt.close()


def create_lifecycle_distribution_chart_voters(lifecycles, voters, title, output_file,
                                               subtitle="", highlight_median=True):
    """
    Create bar chart of lifecycle distribution weighted by registered voters.

    Instead of counting jurisdictions, sums total registered voters for each lifecycle length.

    Args:
        lifecycles: Array of lifecycle lengths (years)
        voters: Array of registered voter counts (same length as lifecycles)
        title: Chart title
        output_file: Filename to save
        subtitle: Optional subtitle
        highlight_median: Whether to highlight median bar
    """
    # Sum voters by lifecycle length
    lifecycle_voter_sums = {}
    for lifecycle, voter_count in zip(lifecycles, voters):
        lifecycle_voter_sums[lifecycle] = lifecycle_voter_sums.get(lifecycle, 0) + voter_count

    # Sort by lifecycle length for proper x-axis ordering
    sorted_lifecycles = sorted(lifecycle_voter_sums.items())
    x_values = [item[0] for item in sorted_lifecycles]
    y_values = [item[1] for item in sorted_lifecycles]

    # Create figure
    plt.figure(figsize=(14, 7))

    # Create bar chart
    bars = plt.bar(x_values, y_values, color='steelblue', edgecolor='black', linewidth=0.5)

    # Highlight the median value (if enabled)
    if highlight_median and len(lifecycles) > 0:
        median_value = int(np.median(lifecycles))
        if median_value in x_values:
            median_index = x_values.index(median_value)
            bars[median_index].set_color('darkorange')

    # Add labels and title
    plt.xlabel('Years Between Changes (Lifecycle Length)', fontsize=13, fontweight='bold')
    plt.ylabel('Total Registered Voters', fontsize=13, fontweight='bold')

    # Title with subtitle
    total_voters = sum(y_values)
    full_title = f'{title}\n(Total: {total_voters:,} registered voters)'
    if subtitle:
        full_title += f'\n{subtitle}'
    plt.title(full_title, fontsize=15, fontweight='bold', pad=20)

    # Add grid for readability
    plt.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    # Set x-axis to show all years
    plt.xticks(x_values, rotation=0)

    # Add value labels on top of bars for significant peaks
    max_height = max(y_values) if y_values else 1
    for i, (x, y) in enumerate(zip(x_values, y_values)):
        if y > max_height * 0.15:  # Label bars that are > 15% of max height
            # Format large numbers with K/M suffix
            if y >= 1_000_000:
                label = f'{y/1_000_000:.1f}M'
            elif y >= 1_000:
                label = f'{y/1_000:.0f}K'
            else:
                label = f'{y:,.0f}'
            plt.text(x, y + max_height * 0.01, label,
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

    # Step 1b: Load family changes data with registered voters for voter-weighted charts
    print("\nLoading family changes data with registered voters...")
    df_voters = load_family_changes_data_with_voters()

    # Step 2: Extract all lifecycle lengths
    print("\nProcessing lifecycle data...")
    # Exclude 2-year same-vendor transitions (likely coordinated upgrades)
    df_filtered = df[
        ~((df['Vendor_Retained'] == True) & (df['Years_Between'] == 2))
    ]
    all_lifecycles = df_filtered['Years_Between'].values

    # Print summary statistics for all changes
    print_summary_statistics(all_lifecycles, "Dataset 1: All Equipment Family Changes")

    # Step 3: Create Chart 1 - Full distribution
    print("\nGenerating Chart 1: All Changes...")
    create_lifecycle_distribution_chart(
        all_lifecycles,
        "Voting System Lifecycle Distribution - All Turnover",
        "lifecycle_distribution_all.png"
    )

    # Step 3b: Create Chart 1 (Voter-Weighted) - Full distribution
    print("\nGenerating Chart 1 (Voter-Weighted): All Changes...")
    # Apply same filter to voter dataset
    df_voters_filtered = df_voters[
        ~((df_voters['Vendor_Retained'] == True) & (df_voters['Years_Between'] == 2))
    ]
    all_lifecycles_voters = df_voters_filtered['Years_Between'].values
    all_voters = df_voters_filtered['Registered_Voters'].values
    print_summary_statistics_voters(all_lifecycles_voters, all_voters,
                                    "Dataset 1 (Voters): All Equipment Family Changes")
    create_lifecycle_distribution_chart_voters(
        all_lifecycles_voters,
        all_voters,
        "Voting System Lifecycle Distribution - All Turnover (Weighted by Voters)",
        "lifecycle_distribution_all_voters.png"
    )

    # Step 4: Filter for Paper marking method
    print("\nFiltering for Paper marking method...")
    # Filter for Paper marking method, excluding 2-year same-vendor transitions
    paper_df = df[
        (df['From_Marking_Method'] == 'Paper') &
        ~((df['Vendor_Retained'] == True) & (df['Years_Between'] == 2))
    ]
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

    # Step 5b: Create Chart 2 (Voter-Weighted) - Paper marking method
    print("\nGenerating Chart 2 (Voter-Weighted): From Paper Marking Method...")
    # Apply same filter to voter dataset
    paper_df_voters = df_voters[
        (df_voters['From_Marking_Method'] == 'Paper') &
        ~((df_voters['Vendor_Retained'] == True) & (df_voters['Years_Between'] == 2))
    ]

    # Need to filter outliers similarly - exclude transitions corresponding to top 10 lifecycle values
    # First, identify indices of top 10 outliers in original paper_df
    if len(paper_lifecycles_sorted) > 10:
        # Get top 10 lifecycle values
        top_10_values = set(paper_lifecycles_sorted[-10:])
        # Filter out rows with these lifecycle values from voter dataset
        paper_df_voters_filtered = paper_df_voters[~paper_df_voters['Years_Between'].isin(top_10_values)]
    else:
        paper_df_voters_filtered = paper_df_voters

    paper_lifecycles_voters = paper_df_voters_filtered['Years_Between'].values
    paper_voters = paper_df_voters_filtered['Registered_Voters'].values
    print_summary_statistics_voters(paper_lifecycles_voters, paper_voters,
                                    "Dataset 2 (Voters): From Paper Marking Method (excluding top 10 outliers)")
    create_lifecycle_distribution_chart_voters(
        paper_lifecycles_voters,
        paper_voters,
        "Voting System Lifecycle Distribution - HMPB System Turnover (Weighted by Voters)",
        "lifecycle_distribution_from_paper_voters.png"
    )

    # Step 5.5: Filter for Paper marking method (excluding AccuVote OS)
    print("\nFiltering for Paper marking method (excluding AccuVote OS)...")
    # Filter for Paper, excluding AccuVote OS Family and 2-year same-vendor transitions
    paper_no_accuvote_df = df[
        (df['From_Marking_Method'] == 'Paper') &
        (~df['From_Equipment'].str.contains('AccuVote OS', case=False, na=False)) &
        ~((df['Vendor_Retained'] == True) & (df['Years_Between'] == 2))
    ]
    paper_no_accuvote_lifecycles_raw = paper_no_accuvote_df['Years_Between'].values

    # Filter out top 10 outliers (longest turnovers) - same approach as main paper chart
    paper_no_accuvote_lifecycles_sorted = np.sort(paper_no_accuvote_lifecycles_raw)
    if len(paper_no_accuvote_lifecycles_sorted) > 10:
        paper_no_accuvote_lifecycles = paper_no_accuvote_lifecycles_sorted[:-10]  # Exclude top 10
        print(f"✓ Found {len(paper_no_accuvote_df):,} changes from Paper (excluding AccuVote OS)")
        print(f"  (Excluding top 10 longest turnovers: {paper_no_accuvote_lifecycles_sorted[-10:].tolist()})")
    else:
        paper_no_accuvote_lifecycles = paper_no_accuvote_lifecycles_raw
        print(f"✓ Found {len(paper_no_accuvote_df):,} changes from Paper (excluding AccuVote OS)")

    # Print summary statistics
    print_summary_statistics(paper_no_accuvote_lifecycles, "Dataset 2b: From Paper Marking Method (excluding AccuVote OS and top 10 outliers)")

    # Step 5.6: Create Chart 2b - Paper marking method (excluding AccuVote OS)
    print("\nGenerating Chart 2b: From Paper Marking Method (excluding AccuVote OS)...")
    create_lifecycle_distribution_chart(
        paper_no_accuvote_lifecycles,
        "Voting System Lifecycle Distribution - HMPB System Turnover (Excluding AccuVote OS)",
        "lifecycle_distribution_from_paper_no_accuvote.png"
    )

    # Step 5.6b: Create Chart 2b (Voter-Weighted) - Paper marking method (excluding AccuVote OS)
    print("\nGenerating Chart 2b (Voter-Weighted): From Paper Marking Method (excluding AccuVote OS)...")
    # Apply same filter to voter dataset
    paper_no_accuvote_df_voters = df_voters[
        (df_voters['From_Marking_Method'] == 'Paper') &
        (~df_voters['From_Equipment'].str.contains('AccuVote OS', case=False, na=False)) &
        ~((df_voters['Vendor_Retained'] == True) & (df_voters['Years_Between'] == 2))
    ]

    # Filter out top 10 outliers similarly
    if len(paper_no_accuvote_lifecycles_sorted) > 10:
        top_10_values_no_accuvote = set(paper_no_accuvote_lifecycles_sorted[-10:])
        paper_no_accuvote_df_voters_filtered = paper_no_accuvote_df_voters[~paper_no_accuvote_df_voters['Years_Between'].isin(top_10_values_no_accuvote)]
    else:
        paper_no_accuvote_df_voters_filtered = paper_no_accuvote_df_voters

    paper_no_accuvote_lifecycles_voters = paper_no_accuvote_df_voters_filtered['Years_Between'].values
    paper_no_accuvote_voters = paper_no_accuvote_df_voters_filtered['Registered_Voters'].values
    print_summary_statistics_voters(paper_no_accuvote_lifecycles_voters, paper_no_accuvote_voters,
                                    "Dataset 2b (Voters): From Paper Marking Method (excluding AccuVote OS and top 10 outliers)")
    create_lifecycle_distribution_chart_voters(
        paper_no_accuvote_lifecycles_voters,
        paper_no_accuvote_voters,
        "Voting System Lifecycle Distribution - HMPB System Turnover (Excluding AccuVote OS, Weighted by Voters)",
        "lifecycle_distribution_from_paper_no_accuvote_voters.png"
    )

    # Step 6: Filter for BMD (Machine + non-DRE)
    print("\nFiltering for BMD (Machine marking + non-DRE)...")

    # Exclude mechanical lever machines (not BMDs) - filter by prefix
    bmd_df = df[
        (df['From_Marking_Method'] == 'Machine') &
        (df['From_DRE'] == 'No') &
        (~df['From_Equipment'].str.startswith(PREFIX_LEVER, na=False)) &
        ~((df['Vendor_Retained'] == True) & (df['Years_Between'] == 2))
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

    # Step 7b: Create Chart 3 (Voter-Weighted) - BMD
    print("\nGenerating Chart 3 (Voter-Weighted): From BMD...")
    # Apply same filter to voter dataset
    bmd_df_voters = df_voters[
        (df_voters['From_Marking_Method'] == 'Machine') &
        (df_voters['From_DRE'] == 'No') &
        (~df_voters['From_Equipment'].str.startswith(PREFIX_LEVER, na=False)) &
        ~((df_voters['Vendor_Retained'] == True) & (df_voters['Years_Between'] == 2))
    ]
    bmd_lifecycles_voters = bmd_df_voters['Years_Between'].values
    bmd_voters = bmd_df_voters['Registered_Voters'].values
    print_summary_statistics_voters(bmd_lifecycles_voters, bmd_voters,
                                    "Dataset 3 (Voters): BMD Turnover")
    create_lifecycle_distribution_chart_voters(
        bmd_lifecycles_voters,
        bmd_voters,
        "Voting System Lifecycle Distribution - BMD Turnover (Weighted by Voters)",
        "lifecycle_distribution_from_bmd_voters.png",
        highlight_median=False
    )

    # Step 8: Filter for DREs without VVPAT option
    print("\nFiltering for DREs without VVPAT option...")
    dre_no_vvpat_df = df[
        (df['From_DRE'] == 'Yes') &
        (df['From_Equipment'].isin(DRES_WITHOUT_VVPAT_OPTION)) &
        ~((df['Vendor_Retained'] == True) & (df['Years_Between'] == 2))
    ]
    dre_no_vvpat_lifecycles = dre_no_vvpat_df['Years_Between'].values

    print(f"✓ Found {len(dre_no_vvpat_df):,} changes from DREs without VVPAT option")

    # Print summary statistics for DREs without VVPAT option
    print_summary_statistics(dre_no_vvpat_lifecycles, "Dataset 4a: DREs without VVPAT Option")

    # Step 9: Create Chart 4a - DREs without VVPAT option
    print("\nGenerating Chart 4a: DREs without VVPAT option...")
    create_lifecycle_distribution_chart(
        dre_no_vvpat_lifecycles,
        "Voting System Lifecycle Distribution - DRE Turnover (Without VVPAT Option)",
        "lifecycle_distribution_from_dre_no_vvpat.png"
    )

    # Step 9b: Create Chart 4a (Voter-Weighted) - DREs without VVPAT option
    print("\nGenerating Chart 4a (Voter-Weighted): DREs without VVPAT option...")
    # Apply same filter to voter dataset
    dre_no_vvpat_df_voters = df_voters[
        (df_voters['From_DRE'] == 'Yes') &
        (df_voters['From_Equipment'].isin(DRES_WITHOUT_VVPAT_OPTION)) &
        ~((df_voters['Vendor_Retained'] == True) & (df_voters['Years_Between'] == 2))
    ]
    dre_no_vvpat_lifecycles_voters = dre_no_vvpat_df_voters['Years_Between'].values
    dre_no_vvpat_voters = dre_no_vvpat_df_voters['Registered_Voters'].values
    print_summary_statistics_voters(dre_no_vvpat_lifecycles_voters, dre_no_vvpat_voters,
                                    "Dataset 4a (Voters): DREs without VVPAT Option")
    create_lifecycle_distribution_chart_voters(
        dre_no_vvpat_lifecycles_voters,
        dre_no_vvpat_voters,
        "Voting System Lifecycle Distribution - DRE Turnover (Without VVPAT Option, Weighted by Voters)",
        "lifecycle_distribution_from_dre_no_vvpat_voters.png"
    )

    # Step 10: Filter for DREs with VVPAT option
    print("\nFiltering for DREs with VVPAT option...")
    dre_with_vvpat_df = df[
        (df['From_DRE'] == 'Yes') &
        (~df['From_Equipment'].isin(DRES_WITHOUT_VVPAT_OPTION)) &
        ~((df['Vendor_Retained'] == True) & (df['Years_Between'] == 2))
    ]
    dre_with_vvpat_lifecycles = dre_with_vvpat_df['Years_Between'].values

    print(f"✓ Found {len(dre_with_vvpat_df):,} changes from DREs with VVPAT option")

    # Print summary statistics for DREs with VVPAT option
    print_summary_statistics(dre_with_vvpat_lifecycles, "Dataset 4b: DREs with VVPAT Option")

    # Step 11: Create Chart 4b - DREs with VVPAT option
    print("\nGenerating Chart 4b: DREs with VVPAT option...")
    create_lifecycle_distribution_chart(
        dre_with_vvpat_lifecycles,
        "Voting System Lifecycle Distribution - DRE Turnover (With VVPAT Option)",
        "lifecycle_distribution_from_dre_with_vvpat.png"
    )

    # Step 11b: Create Chart 4b (Voter-Weighted) - DREs with VVPAT option
    print("\nGenerating Chart 4b (Voter-Weighted): DREs with VVPAT option...")
    # Apply same filter to voter dataset
    dre_with_vvpat_df_voters = df_voters[
        (df_voters['From_DRE'] == 'Yes') &
        (~df_voters['From_Equipment'].isin(DRES_WITHOUT_VVPAT_OPTION)) &
        ~((df_voters['Vendor_Retained'] == True) & (df_voters['Years_Between'] == 2))
    ]
    dre_with_vvpat_lifecycles_voters = dre_with_vvpat_df_voters['Years_Between'].values
    dre_with_vvpat_voters = dre_with_vvpat_df_voters['Registered_Voters'].values
    print_summary_statistics_voters(dre_with_vvpat_lifecycles_voters, dre_with_vvpat_voters,
                                    "Dataset 4b (Voters): DREs with VVPAT Option")
    create_lifecycle_distribution_chart_voters(
        dre_with_vvpat_lifecycles_voters,
        dre_with_vvpat_voters,
        "Voting System Lifecycle Distribution - DRE Turnover (With VVPAT Option, Weighted by Voters)",
        "lifecycle_distribution_from_dre_with_vvpat_voters.png"
    )

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nGenerated files:")
    print("  Jurisdiction-count charts:")
    print("    - equipment_analysis/lifecycle_distribution_all.png")
    print("    - equipment_analysis/lifecycle_distribution_from_paper.png")
    print("    - equipment_analysis/lifecycle_distribution_from_paper_no_accuvote.png")
    print("    - equipment_analysis/lifecycle_distribution_from_bmd.png")
    print("    - equipment_analysis/lifecycle_distribution_from_dre_no_vvpat.png")
    print("    - equipment_analysis/lifecycle_distribution_from_dre_with_vvpat.png")
    print("  Voter-weighted charts:")
    print("    - equipment_analysis/lifecycle_distribution_all_voters.png")
    print("    - equipment_analysis/lifecycle_distribution_from_paper_voters.png")
    print("    - equipment_analysis/lifecycle_distribution_from_paper_no_accuvote_voters.png")
    print("    - equipment_analysis/lifecycle_distribution_from_bmd_voters.png")
    print("    - equipment_analysis/lifecycle_distribution_from_dre_no_vvpat_voters.png")
    print("    - equipment_analysis/lifecycle_distribution_from_dre_with_vvpat_voters.png")
    print()


if __name__ == "__main__":
    main()
