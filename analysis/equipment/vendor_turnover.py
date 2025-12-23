#!/usr/bin/env python3
"""
Analyze vendor turnover patterns in voting system changes.

Uses jurisdiction_transitions.csv filtered to vendor and system transitions.
Generates:
1. Turnover volume by year
2. Turnover percentage (jurisdictions and voters)
3. Turnover + HAVA funding dual-axis chart
4. Vendor switching matrix heatmap

Reads from:
- data/processed/jurisdiction_transitions.csv
- data/processed/jurisdictions_time_series.csv (for registered voters)
- data/processed/hava_funding.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
from collections import defaultdict
from adjustText import adjust_text

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'equipment'

# Major vendors to track separately (maps data names to display names)
MAJOR_VENDORS = {
    'Dominion': 'Dominion',
    'ES&S': 'ES&S',
    'Hart InterCivic': 'Hart',
}


def categorize_vendor(vendor_name):
    """Map vendor to major category (Dominion, ES&S, Hart, Other)."""
    if pd.isna(vendor_name) or vendor_name == '':
        return 'Other'

    vendor = vendor_name.strip()

    if vendor in MAJOR_VENDORS:
        return MAJOR_VENDORS[vendor]
    else:
        return 'Other'


def load_transitions():
    """
    Load jurisdiction transitions filtered to vendor and system types.

    Returns:
        DataFrame with turnover transitions
    """
    filepath = DATA_DIR / 'jurisdiction_transitions.csv'

    if not filepath.exists():
        raise FileNotFoundError(f"Transitions file not found: {filepath}")

    df = pd.read_csv(filepath)

    # Filter to vendor and system transitions (the significant equipment changes)
    df = df[df['Transition_Type'].isin(['vendor', 'system'])].copy()

    print(f"✓ Loaded {len(df):,} vendor/system transitions")

    return df


def load_time_series():
    """Load jurisdictions time series for registered voter data."""
    filepath = DATA_DIR / 'jurisdictions_time_series.csv'

    if not filepath.exists():
        raise FileNotFoundError(f"Time series file not found: {filepath}")

    return pd.read_csv(filepath)


def join_with_voters(df, time_series_df):
    """
    Add Registered_Voters to transitions by joining with time series.

    Args:
        df: Transitions DataFrame
        time_series_df: Time series DataFrame with Registered_Voters

    Returns:
        DataFrame with Registered_Voters added
    """
    df = df.copy()

    # Create lookup from time series
    voters_lookup = time_series_df.set_index(['FIPS', 'Year'])['Registered_Voters'].to_dict()

    # Join on FIPS and To_Year
    df['Registered_Voters'] = df.apply(
        lambda row: voters_lookup.get((row['FIPS'], row['To_Year']), 0),
        axis=1
    )

    # Print join statistics
    total = len(df)
    matched = (df['Registered_Voters'] > 0).sum()
    print(f"✓ Matched {matched:,}/{total:,} transitions with voter data ({matched/total*100:.1f}%)")

    return df


def load_yearly_totals(time_series_df):
    """
    Calculate total jurisdictions and registered voters for each year.

    Args:
        time_series_df: Time series DataFrame

    Returns:
        tuple: (jurisdictions_by_year, voters_by_year) dicts
    """
    jurisdictions_by_year = time_series_df.groupby('Year')['FIPS'].count().to_dict()
    voters_by_year = time_series_df.groupby('Year')['Registered_Voters'].sum().to_dict()

    return jurisdictions_by_year, voters_by_year


def get_turnover_jurisdictions_by_year(df):
    """
    Get FIPS codes of jurisdictions that had turnovers each year.

    Args:
        df: DataFrame with To_Year and FIPS columns

    Returns:
        dict: Year -> set of FIPS codes
    """
    turnover_by_year = defaultdict(set)

    for _, row in df.iterrows():
        year = row['To_Year']
        fips = row['FIPS']
        turnover_by_year[year].add(fips)

    return turnover_by_year


def load_hava_funding_by_even_year():
    """
    Load HAVA funding data and aggregate by even years.

    Returns:
        dict: {even_year: total_funding_dollars}
    """
    hava_filepath = DATA_DIR / 'hava_funding.csv'

    if not hava_filepath.exists():
        print(f"  Warning: HAVA funding file not found at {hava_filepath}")
        return {}

    df_hava = pd.read_csv(hava_filepath)

    # Convert funding columns to numeric
    df_hava['Federal_Funding'] = pd.to_numeric(df_hava['Federal_Funding'], errors='coerce').fillna(0)
    df_hava['Required_State_Match'] = pd.to_numeric(df_hava['Required_State_Match'], errors='coerce').fillna(0)

    # Calculate total funding per row
    df_hava['Total_Funding'] = df_hava['Federal_Funding'] + df_hava['Required_State_Match']

    # Round year down to nearest even year
    df_hava['Even_Year'] = (df_hava['Year'].astype(int) // 2) * 2

    # Group by even year and sum total funding
    funding_by_year = df_hava.groupby('Even_Year')['Total_Funding'].sum().to_dict()

    print(f"✓ Loaded HAVA funding for {len(funding_by_year)} even-year periods")

    return funding_by_year


def load_initial_deployments_from_time_series(time_series_df, start_year=2000):
    """
    Infer initial equipment deployments from First_Year_In_Use in time series.

    Args:
        time_series_df: Time series DataFrame
        start_year: Earliest year to include

    Returns:
        dict with deployments_by_year and percentages_by_year
    """
    # Get 2006 data (first year in time series)
    df_2006 = time_series_df[time_series_df['Year'] == 2006].copy()

    total_jurisdictions = len(df_2006)

    # Extract first year in use
    df_2006['First_Year'] = pd.to_numeric(df_2006['First_Year_In_Use'], errors='coerce')

    # Filter to valid years
    df_filtered = df_2006[
        (df_2006['First_Year'] >= start_year) &
        (df_2006['First_Year'] <= 2006) &
        (df_2006['First_Year'].notna())
    ].copy()

    # Round years down to nearest even year
    df_filtered['Even_Year'] = (df_filtered['First_Year'] // 2) * 2

    # Count deployments by even year
    deployments_by_year = df_filtered['Even_Year'].value_counts().to_dict()
    deployments_by_year = {int(year): count for year, count in deployments_by_year.items()}

    # Calculate percentages
    percentages_by_year = {
        year: (count / total_jurisdictions * 100) if total_jurisdictions > 0 else 0
        for year, count in deployments_by_year.items()
    }

    print(f"✓ Loaded initial deployments from time series ({total_jurisdictions:,} jurisdictions)")

    return {
        'deployments_by_year': deployments_by_year,
        'total_jurisdictions': total_jurisdictions,
        'percentages_by_year': percentages_by_year
    }


def create_turnover_volume_chart(df):
    """
    Create bar chart showing total number of turnovers per year.

    Args:
        df: DataFrame with To_Year column

    Returns:
        dict: Year -> count of turnovers
    """
    # Count turnovers by year
    year_counts = df['To_Year'].value_counts().sort_index()

    # Create bar chart
    fig, ax = plt.subplots(figsize=(14, 7))

    years = year_counts.index.tolist()
    counts = year_counts.values.tolist()

    bars = ax.bar(years, counts, color='steelblue', edgecolor='black', linewidth=0.5, width=0.8)

    # Styling
    ax.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of System Changes', fontsize=13, fontweight='bold')
    ax.set_title('Volume of Voting System Changes Over Time\n'
                 'Vendor and System Transitions by Year',
                 fontsize=15, fontweight='bold', pad=20)

    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    # Add value labels on top of bars
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height,
                f'{int(count):,}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha='right')

    plt.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / 'upgrade_volume_by_year.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Chart saved to {output_path}")

    return year_counts.to_dict()


def create_turnover_percentage_jurisdictions_chart(df, total_jurisdictions_by_year):
    """
    Create bar chart showing turnover as percentage of all jurisdictions.

    Args:
        df: DataFrame with To_Year and FIPS columns
        total_jurisdictions_by_year: dict of year -> total jurisdiction count
    """
    turnover_by_year = get_turnover_jurisdictions_by_year(df)

    years = sorted(turnover_by_year.keys())
    percentages = []

    for year in years:
        turnover_count = len(turnover_by_year[year])
        total_count = total_jurisdictions_by_year.get(year, 0)

        if total_count > 0:
            pct = (turnover_count / total_count) * 100
        else:
            pct = 0

        percentages.append(pct)

    fig, ax = plt.subplots(figsize=(14, 7))

    bars = ax.bar(years, percentages, color='darkorange', edgecolor='black', linewidth=0.5, width=0.8)

    ax.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax.set_ylabel('Percentage of Jurisdictions (%)', fontsize=13, fontweight='bold')
    ax.set_title('System Changes as Percentage of All Jurisdictions\n'
                 'Jurisdictions with Vendor or System Transitions Each Year',
                 fontsize=15, fontweight='bold', pad=20)

    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    for bar, pct in zip(bars, percentages):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height,
                f'{pct:.1f}%',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha='right')
    ax.set_ylim(0, max(percentages) * 1.15)

    plt.tight_layout()
    output_path = OUTPUT_DIR / 'upgrade_percentage_jurisdictions.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Chart saved to {output_path}")


def create_turnover_percentage_voters_chart(df, total_voters_by_year):
    """
    Create bar chart showing turnover as percentage of all registered voters.

    Args:
        df: DataFrame with To_Year and Registered_Voters columns
        total_voters_by_year: dict of year -> total registered voters
    """
    # Sum registered voters by year for jurisdictions with transitions
    turnover_voters = df.groupby('To_Year')['Registered_Voters'].sum().to_dict()

    years = sorted(turnover_voters.keys())
    percentages = []

    for year in years:
        turnover_v = turnover_voters.get(year, 0)
        total_v = total_voters_by_year.get(year, 0)

        if total_v > 0:
            pct = (turnover_v / total_v) * 100
        else:
            pct = 0

        percentages.append(pct)

    fig, ax = plt.subplots(figsize=(14, 7))

    bars = ax.bar(years, percentages, color='mediumseagreen', edgecolor='black', linewidth=0.5, width=0.8)

    ax.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax.set_ylabel('Percentage of Registered Voters (%)', fontsize=13, fontweight='bold')
    ax.set_title('System Changes as Percentage of All Registered Voters\n'
                 'Registered Voters in Jurisdictions with Vendor or System Transitions',
                 fontsize=15, fontweight='bold', pad=20)

    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    for bar, pct in zip(bars, percentages):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height,
                f'{pct:.1f}%',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha='right')
    ax.set_ylim(0, max(percentages) * 1.15)

    plt.tight_layout()
    output_path = OUTPUT_DIR / 'upgrade_percentage_voters.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Chart saved to {output_path}")


def create_turnover_and_hava_dual_axis_chart(df, total_jurisdictions_by_year, time_series_df):
    """
    Create dual-axis chart showing turnover percentage and HAVA funding over time.

    Args:
        df: Transitions DataFrame
        total_jurisdictions_by_year: dict of year -> total jurisdiction count
        time_series_df: Time series DataFrame for initial deployments
    """
    # Load initial deployments from time series
    initial_deployments = load_initial_deployments_from_time_series(time_series_df, start_year=2000)

    # Get turnover data
    turnover_by_year = get_turnover_jurisdictions_by_year(df)

    # Get jurisdiction counts (not percentages)
    years_turnover = sorted(turnover_by_year.keys())
    counts = []

    for year in years_turnover:
        turnover_count = len(turnover_by_year[year])
        counts.append(turnover_count)

    # Load HAVA funding
    hava_funding = load_hava_funding_by_even_year()

    # Determine full year range
    min_year_hava = min(hava_funding.keys()) if hava_funding else 2008
    min_year_turnover = min(years_turnover) if years_turnover else 2008
    min_year_deployments = min(initial_deployments['deployments_by_year'].keys()) if initial_deployments['deployments_by_year'] else 2008
    min_year = min(min_year_hava, min_year_turnover, min_year_deployments)

    max_year_turnover = max(years_turnover) if years_turnover else 2026
    max_year = max_year_turnover

    # Create complete year range (even years only)
    all_years = list(range(min_year, max_year + 1, 2))

    # Prepare aligned data (counts, not percentages)
    turnover_counts_aligned = []
    hava_funding_aligned = []

    for year in all_years:
        if year in years_turnover:
            idx = years_turnover.index(year)
            turnover_counts_aligned.append(counts[idx])
        elif year in initial_deployments['deployments_by_year']:
            turnover_counts_aligned.append(initial_deployments['deployments_by_year'][year])
        else:
            turnover_counts_aligned.append(0)

        funding_dollars = hava_funding.get(year, 0)
        hava_funding_aligned.append(funding_dollars / 1_000_000)

    # Create figure with dual axes
    fig, ax1 = plt.subplots(figsize=(16, 8))

    color_turnover = 'darkorange'

    # Split years into actual (2008+) and inferred (pre-2008)
    years_actual = [y for y in all_years if y >= 2008]
    years_inferred = [y for y in all_years if y < 2008]

    actual_counts = [turnover_counts_aligned[all_years.index(y)] for y in years_actual]
    inferred_counts = [turnover_counts_aligned[all_years.index(y)] for y in years_inferred]

    # Plot inferred initial deployments (pre-2008)
    if years_inferred and any(c > 0 for c in inferred_counts):
        ax1.bar(years_inferred, inferred_counts, color=color_turnover,
                edgecolor='black', linewidth=0.5, width=1.5, alpha=0.4,
                hatch='//', label='Initial Deployments (Inferred from 2006)')

    # Plot actual turnovers (2008+)
    if years_actual:
        ax1.bar(years_actual, actual_counts, color=color_turnover,
                edgecolor='black', linewidth=0.5, width=1.5, alpha=0.8,
                label='System Changes (Actual)')

    ax1.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Number of Jurisdictions with System Changes',
                   fontsize=13, fontweight='bold', color=color_turnover)
    ax1.tick_params(axis='y', labelcolor=color_turnover)
    ax1.set_ylim(0, max(turnover_counts_aligned) * 1.15 if turnover_counts_aligned else 100)

    # Right axis: HAVA funding
    ax2 = ax1.twinx()
    color_hava = 'green'
    ax2.plot(all_years, hava_funding_aligned, color=color_hava,
             marker='o', linewidth=2.5, markersize=8,
             label='HAVA Funding (Total)')

    ax2.set_ylabel('HAVA Funding (Millions $)', fontsize=13, fontweight='bold', color=color_hava)
    ax2.tick_params(axis='y', labelcolor=color_hava)

    ax1.set_title('Major Upgrades vs. HAVA Funding Investment',
                  fontsize=15, fontweight='bold', pad=20)

    ax1.set_xticks(all_years)
    ax1.set_xticklabels([str(y) for y in all_years], rotation=45, ha='right')

    ax1.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               loc='upper right', fontsize=11, framealpha=0.9)

    plt.tight_layout()
    output_path = OUTPUT_DIR / 'upgrade_and_hava_funding.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Chart saved to {output_path}")


def create_vendor_switching_matrix(df):
    """
    Create vendor switching matrix heatmap weighted by registered voters.

    Includes both vendor changes AND system changes (same vendor, different system).
    This shows retention probability: when a jurisdiction changes systems,
    what percentage stay with the same vendor vs switch to a competitor.

    Args:
        df: DataFrame with From/To vendor and Registered_Voters columns

    Returns:
        DataFrame: Transition probability matrix
    """
    df_filtered = df.copy()

    # Include both vendor AND system transitions
    # System transitions = same vendor, different system (counts as retention)
    # Vendor transitions = different vendor (counts as switching)
    df_filtered = df_filtered[df_filtered['Transition_Type'].isin(['vendor', 'system'])]

    # Categorize vendors
    df_filtered['From_Cat'] = df_filtered['From_Primary_Voting_Vendor'].apply(categorize_vendor)
    df_filtered['To_Cat'] = df_filtered['To_Primary_Voting_Vendor'].apply(categorize_vendor)

    # Build transition matrix weighted by voters
    vendors = ['Dominion', 'ES&S', 'Hart', 'Other']
    voter_sums = pd.DataFrame(0.0, index=vendors, columns=vendors)

    for _, row in df_filtered.iterrows():
        from_vendor = row['From_Cat']
        to_vendor = row['To_Cat']
        voters = row['Registered_Voters']
        voter_sums.loc[from_vendor, to_vendor] += voters

    # Calculate transition probabilities (row-wise percentages)
    transition_probs = voter_sums.div(voter_sums.sum(axis=1), axis=0) * 100

    # Create heatmap
    fig, ax = plt.subplots(figsize=(10, 8))

    sns.heatmap(
        transition_probs,
        annot=True,
        fmt='.1f',
        cmap='Greens',
        cbar_kws={'label': 'Transition Probability (%)'},
        linewidths=0.5,
        linecolor='gray',
        vmin=0,
        vmax=100,
        ax=ax
    )

    ax.set_xlabel('Vendor TO', fontsize=14, fontweight='bold')
    ax.set_ylabel('Vendor FROM', fontsize=14, fontweight='bold')
    ax.set_title('Vendor Retention Matrix (2006-2026)\n'
                 'On Major Upgrade: % Staying vs Switching Vendors',
                 fontsize=16, fontweight='bold', pad=20)

    plt.tight_layout()
    output_path = OUTPUT_DIR / 'vendor_switching_matrix.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Chart saved to {output_path}")

    return transition_probs


def create_vendor_retention_timeline(df, output_path):
    """
    Create line chart showing vendor retention rates over time.

    For each 2-year cycle, calculates what percentage of system changes
    (weighted by registered voters) stayed with the same vendor.

    Args:
        df: DataFrame with transitions (should include both vendor and system types)
        output_path: Path to save chart
    """
    df_filtered = df.copy()

    # Include both vendor AND system transitions
    df_filtered = df_filtered[df_filtered['Transition_Type'].isin(['vendor', 'system'])]

    # Categorize vendors
    df_filtered['From_Cat'] = df_filtered['From_Primary_Voting_Vendor'].apply(categorize_vendor)
    df_filtered['To_Cat'] = df_filtered['To_Primary_Voting_Vendor'].apply(categorize_vendor)

    # Get unique years (should already be 2-year cycles)
    years = sorted(df_filtered['To_Year'].unique())

    # Colors matching vendor_market_share.py
    vendor_colors = {
        'Dominion': '#4169E1',    # Royal blue
        'ES&S': '#228B22',        # Forest green
        'Hart': '#9370DB',        # Medium purple
    }

    # Calculate retention rate for each vendor and year
    vendors = ['Dominion', 'ES&S', 'Hart']
    retention_data = {vendor: [] for vendor in vendors}
    sample_sizes = {vendor: [] for vendor in vendors}

    for year in years:
        year_df = df_filtered[df_filtered['To_Year'] == year]

        for vendor in vendors:
            # Get all transitions FROM this vendor in this year
            from_vendor = year_df[year_df['From_Cat'] == vendor]

            if len(from_vendor) == 0:
                retention_data[vendor].append(None)
                sample_sizes[vendor].append(0)
                continue

            # Track sample size (number of transitions)
            sample_sizes[vendor].append(len(from_vendor))

            # Calculate voter-weighted retention rate
            total_voters = from_vendor['Registered_Voters'].sum()
            retained_voters = from_vendor[from_vendor['To_Cat'] == vendor]['Registered_Voters'].sum()

            if total_voters > 0:
                retention_rate = (retained_voters / total_voters) * 100
                retention_data[vendor].append(retention_rate)
            else:
                retention_data[vendor].append(None)

    # Create the chart
    fig, ax = plt.subplots(figsize=(14, 8))

    # Collect all text annotations for adjust_text
    texts = []

    for vendor in vendors:
        rates = retention_data[vendor]
        sizes = sample_sizes[vendor]
        # Filter out None and 0 values for plotting
        valid_data = [(y, r, n) for y, r, n in zip(years, rates, sizes)
                      if r is not None and r > 0]

        if valid_data:
            valid_years = [d[0] for d in valid_data]
            valid_rates = [d[1] for d in valid_data]
            valid_sizes = [d[2] for d in valid_data]

            ax.plot(valid_years, valid_rates,
                    marker='o', markersize=8, linewidth=2.5,
                    color=vendor_colors[vendor], label=vendor)

            # Add sample size labels - collect for adjust_text
            for y, r, n in zip(valid_years, valid_rates, valid_sizes):
                txt = ax.text(y, r, f'n={n}', fontsize=7, color=vendor_colors[vendor],
                              alpha=0.8, ha='center')
                texts.append(txt)

    ax.set_xlabel('Year', fontsize=14, fontweight='bold')
    ax.set_ylabel('Retention Rate (%)', fontsize=14, fontweight='bold')
    ax.set_title('Vendor Retention Rate Over Time (2006-2026)\n'
                 'Weighted by Registered Voters (n = jurisdiction count)',
                 fontsize=16, fontweight='bold', pad=20)

    ax.set_ylim(0, 105)
    ax.set_xlim(min(years) - 0.5, max(years) + 0.5)
    ax.set_xticks(years)

    ax.legend(loc='upper left', fontsize=12, framealpha=0.9)
    ax.grid(axis='both', alpha=0.3, linestyle='--')

    # Use adjust_text to avoid label overlaps
    adjust_text(texts, ax=ax,
                arrowprops=dict(arrowstyle='-', color='gray', alpha=0.6, lw=0.5),
                expand=(1.2, 1.4),  # Allow more vertical expansion
                force_text=(0.5, 1.0),  # Stronger vertical force
                force_static=(0.3, 0.5))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Chart saved to {output_path}")

    return retention_data


def main():
    """Main processing pipeline."""
    print("=" * 80)
    print("VENDOR TURNOVER ANALYSIS")
    print("=" * 80)
    print()

    # Load transitions (vendor + system only)
    print("Loading jurisdiction transitions (vendor + system types)...")
    df = load_transitions()
    print()

    # Load time series for voter data
    print("Loading jurisdictions time series for voter data...")
    time_series_df = load_time_series()
    print(f"✓ Loaded {len(time_series_df):,} time series records")
    print()

    # Join transitions with voter data
    print("Joining transitions with registered voters...")
    df = join_with_voters(df, time_series_df)
    print()

    # Get yearly totals
    total_jurisdictions_by_year, total_voters_by_year = load_yearly_totals(time_series_df)
    print(f"✓ Calculated totals for {len(total_jurisdictions_by_year)} years")
    print()

    # Print voter weighting statistics
    print("Voter Weighting Statistics:")
    total_voters = df['Registered_Voters'].sum()
    print(f"  Total registered voters in transitions: {total_voters:,}")
    print(f"  Average voters per transition: {df['Registered_Voters'].mean():,.0f}")
    print(f"  Median voters per transition: {df['Registered_Voters'].median():,.0f}")
    print()

    # Generate charts
    print("-" * 60)
    print("GENERATING CHARTS")
    print("-" * 60)
    print()

    print("Generating turnover volume by year chart...")
    year_counts = create_turnover_volume_chart(df)
    print()

    print("Generating turnover percentage (jurisdictions) chart...")
    create_turnover_percentage_jurisdictions_chart(df, total_jurisdictions_by_year)
    print()

    print("Generating turnover percentage (voters) chart...")
    create_turnover_percentage_voters_chart(df, total_voters_by_year)
    print()

    print("Generating turnover + HAVA funding dual-axis chart...")
    create_turnover_and_hava_dual_axis_chart(df, total_jurisdictions_by_year, time_series_df)
    print()

    # Print vendor summary statistics
    print("-" * 60)
    print("VENDOR STATISTICS")
    print("-" * 60)
    print()

    # Filter to vendor transitions for stats
    vendor_transitions = df[df['Transition_Type'] == 'vendor']

    print(f"Vendor Transitions: {len(vendor_transitions):,}")
    print(f"System Transitions (same vendor): {len(df) - len(vendor_transitions):,}")
    print()

    print("Major Vendor Statistics (vendor transitions only):")
    for data_name, display_name in MAJOR_VENDORS.items():
        from_count = (vendor_transitions['From_Primary_Voting_Vendor'] == data_name).sum()
        to_count = (vendor_transitions['To_Primary_Voting_Vendor'] == data_name).sum()
        net = to_count - from_count

        if from_count > 0 or to_count > 0:
            direction = "↑" if net > 0 else "↓" if net < 0 else "→"
            print(f"  {display_name}:")
            print(f"    - Lost to other vendors: {from_count:,}")
            print(f"    - Gained from other vendors: {to_count:,}")
            print(f"    - Net: {direction} {abs(net):,}")
    print()

    # Generate switching matrix
    print("Generating vendor switching matrix...")
    transition_matrix = create_vendor_switching_matrix(df)
    print()

    # Generate retention timeline
    print("Generating vendor retention timeline...")
    retention_data = create_vendor_retention_timeline(
        df, OUTPUT_DIR / 'vendor_retention_timeline.png'
    )
    print()

    # Summary
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print("Generated files:")
    print(f"  - {OUTPUT_DIR / 'upgrade_volume_by_year.png'}")
    print(f"  - {OUTPUT_DIR / 'upgrade_percentage_jurisdictions.png'}")
    print(f"  - {OUTPUT_DIR / 'upgrade_percentage_voters.png'}")
    print(f"  - {OUTPUT_DIR / 'upgrade_and_hava_funding.png'}")
    print(f"  - {OUTPUT_DIR / 'vendor_switching_matrix.png'}")
    print(f"  - {OUTPUT_DIR / 'vendor_retention_timeline.png'}")
    print()


if __name__ == '__main__':
    main()
