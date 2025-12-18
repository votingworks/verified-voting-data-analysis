#!/usr/bin/env python3
"""
Analyze vendor turnover patterns in between-system equipment changes.

Generates:
1. Vendor switching matrix heatmap (Dominion, ES&S, Hart, Other)
2. Vendor retention timeline by 2-year period

Reads from: ../data/voting_system_time_series.csv (filtered to Record_Type='between_system')
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
CONDENSED_DIR = DATA_DIR / 'processed' / 'jurisdictions'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'equipment'

# Major vendors to track separately
MAJOR_VENDORS = ['Dominion', 'ES&S', 'Hart']


def categorize_vendor(vendor_name):
    """Map vendor to major category (Dominion, ES&S, Hart, Other)."""
    if pd.isna(vendor_name) or vendor_name == '':
        return 'Other'

    vendor = vendor_name.strip()

    if vendor in MAJOR_VENDORS:
        return vendor
    else:
        return 'Other'


def get_period_label(to_year):
    """Convert To_Year to 2-year period label."""
    # Round down to nearest even year
    start_year = (to_year // 2) * 2
    end_year = start_year + 2
    return f"{start_year}-{end_year}"


def load_turnovers_with_voters():
    """
    Load turnover data and join with condensed CSVs to add registered voters.

    Returns:
        DataFrame with additional 'Registered_Voters' column
    """
    # Load time series data and filter to between_system records
    filepath = DATA_DIR / 'processed' / 'voting_system_time_series.csv'
    df_turnovers = pd.read_csv(filepath)
    df_turnovers = df_turnovers[df_turnovers['Record_Type'] == 'between_system'].copy()

    # Initialize voters column
    df_turnovers['Registered_Voters'] = 0

    # Get unique years from turnovers
    years = df_turnovers['To_Year'].unique()

    # For each year, load condensed data and join
    for year in sorted(years):
        condensed_path = CONDENSED_DIR / f'{year}_verifier-jurisdictions-condensed.csv'

        if not condensed_path.exists():
            print(f"  Warning: Missing condensed data for {year}")
            continue

        # Read condensed data (skip header row)
        df_year = pd.read_csv(condensed_path, skiprows=1)

        # Create lookup: FIPS -> Registered Voters
        voters_lookup = df_year.set_index('FIPS code')['Registered Voters'].to_dict()

        # Update turnovers for this year
        year_mask = df_turnovers['To_Year'] == year
        df_turnovers.loc[year_mask, 'Registered_Voters'] = df_turnovers.loc[year_mask, 'FIPS'].map(voters_lookup).fillna(0)

    # Print join statistics
    total = len(df_turnovers)
    matched = (df_turnovers['Registered_Voters'] > 0).sum()
    print(f"✓ Matched {matched:,}/{total:,} turnovers with voter data ({matched/total*100:.1f}%)")

    return df_turnovers


def load_yearly_totals():
    """
    Load total jurisdictions and registered voters for each year.

    Returns:
        tuple: (jurisdictions_by_year, voters_by_year) dicts
    """
    jurisdictions_by_year = {}
    voters_by_year = {}

    # Years in the condensed data
    years = range(2006, 2028, 2)

    for year in years:
        filepath = CONDENSED_DIR / f'{year}_verifier-jurisdictions-condensed.csv'

        if not filepath.exists():
            continue

        # Read CSV (skip header row)
        df = pd.read_csv(filepath, skiprows=1)

        # Count jurisdictions
        jurisdictions_by_year[year] = len(df)

        # Sum registered voters (exclude NaN values)
        voters_by_year[year] = df['Registered Voters'].dropna().sum()

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


def get_turnover_voters_by_year(df):
    """
    Load condensed data and calculate registered voters in jurisdictions with turnovers.

    Args:
        df: DataFrame with To_Year and FIPS columns

    Returns:
        dict: Year -> total registered voters in turnover jurisdictions
    """
    # Get FIPS of jurisdictions with turnovers by year
    turnover_by_year = get_turnover_jurisdictions_by_year(df)

    voters_by_year = {}

    for year in turnover_by_year.keys():
        filepath = CONDENSED_DIR / f'{year}_verifier-jurisdictions-condensed.csv'

        if not filepath.exists():
            continue

        # Read condensed data for this year
        year_df = pd.read_csv(filepath, skiprows=1)

        # Filter to jurisdictions with turnovers
        turnover_fips = turnover_by_year[year]
        turnover_jurisdictions = year_df[year_df['FIPS code'].isin(turnover_fips)]

        # Sum registered voters
        voters_by_year[year] = turnover_jurisdictions['Registered Voters'].dropna().sum()

    return voters_by_year


def load_hava_funding_by_even_year():
    """
    Load HAVA funding data and aggregate by even years (rounded down).

    Groups odd years with the preceding even year:
    - 2003 → 2002
    - 2009 → 2008
    - 2011 → 2010

    Returns:
        dict: {even_year: total_funding_dollars}
    """
    hava_filepath = DATA_DIR / 'processed' / 'hava_funding.csv'

    if not hava_filepath.exists():
        print(f"  Warning: HAVA funding file not found at {hava_filepath}")
        return {}

    # Load HAVA data
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
    for year in sorted(funding_by_year.keys()):
        print(f"    {year}: ${funding_by_year[year]:,.0f}")

    return funding_by_year


def load_initial_deployments_from_2006(start_year=2000):
    """
    Load initial equipment deployment data from 2006 verifier file.

    Uses "Primary Voting Equipment - First Year In Use" field to infer
    when equipment was first deployed, extending turnover data backwards.

    Args:
        start_year: Earliest year to include (default: 2000)

    Returns:
        dict: {
            'deployments_by_year': {year: count_of_jurisdictions},
            'total_jurisdictions': total count in 2006,
            'percentages_by_year': {year: percentage}
        }
    """
    filepath = CONDENSED_DIR / '2006_verifier-jurisdictions-condensed.csv'

    if not filepath.exists():
        print(f"  Warning: 2006 condensed file not found")
        return {'deployments_by_year': {}, 'total_jurisdictions': 0, 'percentages_by_year': {}}

    # Read 2006 data (skip title row)
    df_2006 = pd.read_csv(filepath, skiprows=1)

    # Count total jurisdictions
    total_jurisdictions = len(df_2006)

    # Extract first year in use (convert to numeric, handle non-numeric)
    df_2006['First_Year'] = pd.to_numeric(
        df_2006['Primary Voting Equipment - First Year In Use'],
        errors='coerce'
    )

    # Filter to valid years >= start_year and <= 2006
    df_filtered = df_2006[
        (df_2006['First_Year'] >= start_year) &
        (df_2006['First_Year'] <= 2006) &
        (df_2006['First_Year'].notna())
    ].copy()

    # Round years down to nearest even year
    df_filtered['Even_Year'] = (df_filtered['First_Year'] // 2) * 2

    # Count deployments by even year
    deployments_by_year = df_filtered['Even_Year'].value_counts().to_dict()

    # Convert year keys from numpy types to int
    deployments_by_year = {int(year): count for year, count in deployments_by_year.items()}

    # Calculate percentages
    percentages_by_year = {
        year: (count / total_jurisdictions * 100) if total_jurisdictions > 0 else 0
        for year, count in deployments_by_year.items()
    }

    print(f"✓ Loaded initial deployments from 2006 file ({total_jurisdictions:,} jurisdictions)")
    for year in sorted(deployments_by_year.keys()):
        pct = percentages_by_year[year]
        count = deployments_by_year[year]
        print(f"    {year}: {count:,} jurisdictions ({pct:.1f}%)")

    return {
        'deployments_by_year': deployments_by_year,
        'total_jurisdictions': total_jurisdictions,
        'percentages_by_year': percentages_by_year
    }


def create_turnover_volume_chart(df):
    """
    Create bar chart showing total number of between-system turnovers per year.

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
    ax.set_ylabel('Number of System Upgrades', fontsize=13, fontweight='bold')
    ax.set_title('Volume of System Upgrades Over Time (2008-2026)\n'
                 'Total Jurisdictions Changing Voting Systems Each Year',
                 fontsize=15, fontweight='bold', pad=20)

    # Add grid for readability
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    # Add value labels on top of bars
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height,
                f'{int(count):,}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Set x-axis to show all years
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha='right')

    plt.tight_layout()
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
    # Get number of jurisdictions with turnovers per year
    turnover_by_year = get_turnover_jurisdictions_by_year(df)

    # Calculate percentages
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

    # Create bar chart
    fig, ax = plt.subplots(figsize=(14, 7))

    bars = ax.bar(years, percentages, color='darkorange', edgecolor='black', linewidth=0.5, width=0.8)

    # Styling
    ax.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax.set_ylabel('Percentage of Jurisdictions (%)', fontsize=13, fontweight='bold')
    ax.set_title('System Upgrades as Percentage of All Jurisdictions (2008-2026)\n'
                 'Jurisdictions Changing Voting Systems Each Year',
                 fontsize=15, fontweight='bold', pad=20)

    # Add grid for readability
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    # Add value labels on top of bars
    for bar, pct in zip(bars, percentages):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height,
                f'{pct:.1f}%',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Set x-axis to show all years
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha='right')

    # Set y-axis range
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
        df: DataFrame with To_Year and FIPS columns
        total_voters_by_year: dict of year -> total registered voters
    """
    # Get registered voters in jurisdictions with turnovers per year
    turnover_voters_by_year = get_turnover_voters_by_year(df)

    # Calculate percentages
    years = sorted(turnover_voters_by_year.keys())
    percentages = []

    for year in years:
        turnover_voters = turnover_voters_by_year.get(year, 0)
        total_voters = total_voters_by_year.get(year, 0)

        if total_voters > 0:
            pct = (turnover_voters / total_voters) * 100
        else:
            pct = 0

        percentages.append(pct)

    # Create bar chart
    fig, ax = plt.subplots(figsize=(14, 7))

    bars = ax.bar(years, percentages, color='mediumseagreen', edgecolor='black', linewidth=0.5, width=0.8)

    # Styling
    ax.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax.set_ylabel('Percentage of Registered Voters (%)', fontsize=13, fontweight='bold')
    ax.set_title('System Upgrades as Percentage of All Registered Voters (2008-2026)\n'
                 'Registered Voters in Jurisdictions Changing Voting Systems Each Year',
                 fontsize=15, fontweight='bold', pad=20)

    # Add grid for readability
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    # Add value labels on top of bars
    for bar, pct in zip(bars, percentages):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height,
                f'{pct:.1f}%',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Set x-axis to show all years
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha='right')

    # Set y-axis range
    ax.set_ylim(0, max(percentages) * 1.15)

    plt.tight_layout()
    output_path = OUTPUT_DIR / 'upgrade_percentage_voters.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Chart saved to {output_path}")


def create_turnover_and_hava_dual_axis_chart(df, total_jurisdictions_by_year):
    """
    Create dual-axis chart showing turnover percentage and HAVA funding over time.

    Left axis: Turnover percentage of jurisdictions (actual + inferred)
    Right axis: HAVA funding in millions of dollars

    Args:
        df: DataFrame with To_Year and FIPS columns
        total_jurisdictions_by_year: dict of year -> total jurisdiction count
    """
    # Load initial deployments from 2006 (for years 2000-2006)
    initial_deployments = load_initial_deployments_from_2006(start_year=2000)

    # Get turnover data (reuse existing logic)
    turnover_by_year = get_turnover_jurisdictions_by_year(df)

    # Calculate turnover percentages
    years_turnover = sorted(turnover_by_year.keys())
    percentages = []

    for year in years_turnover:
        turnover_count = len(turnover_by_year[year])
        total_count = total_jurisdictions_by_year.get(year, 0)

        if total_count > 0:
            pct = (turnover_count / total_count) * 100
        else:
            pct = 0

        percentages.append(pct)

    # Load HAVA funding data
    hava_funding = load_hava_funding_by_even_year()

    # Determine full year range (extend backwards to include all data sources)
    min_year_hava = min(hava_funding.keys()) if hava_funding else 2008
    min_year_turnover = min(years_turnover) if years_turnover else 2008
    min_year_deployments = min(initial_deployments['percentages_by_year'].keys()) if initial_deployments['percentages_by_year'] else 2008
    min_year = min(min_year_hava, min_year_turnover, min_year_deployments)

    max_year_turnover = max(years_turnover) if years_turnover else 2026
    max_year = max_year_turnover

    # Create complete year range (even years only)
    all_years = list(range(min_year, max_year + 1, 2))

    # Prepare data aligned to all years
    turnover_pcts_aligned = []
    hava_funding_aligned = []

    for year in all_years:
        # Turnover percentage - prioritize actual turnover data (2008+), fall back to inferred deployments (2000-2006)
        if year in years_turnover:
            idx = years_turnover.index(year)
            turnover_pcts_aligned.append(percentages[idx])
        elif year in initial_deployments['percentages_by_year']:
            turnover_pcts_aligned.append(initial_deployments['percentages_by_year'][year])
        else:
            turnover_pcts_aligned.append(0)

        # HAVA funding in millions (0 if year not in HAVA data)
        funding_dollars = hava_funding.get(year, 0)
        hava_funding_aligned.append(funding_dollars / 1_000_000)  # Convert to millions

    # Create figure with dual axes
    fig, ax1 = plt.subplots(figsize=(16, 8))

    # Left axis: Turnover percentage (bars)
    # Split into two series for different visual styling
    color_turnover = 'darkorange'

    # Split years into actual (2008+) and inferred (pre-2008)
    years_actual = [y for y in all_years if y >= 2008]
    years_inferred = [y for y in all_years if y < 2008]

    # Get corresponding percentages
    actual_pcts = [turnover_pcts_aligned[all_years.index(y)] for y in years_actual]
    inferred_pcts = [turnover_pcts_aligned[all_years.index(y)] for y in years_inferred]

    # Plot inferred initial deployments (2000-2006): Lighter bars with hatching
    if years_inferred and any(p > 0 for p in inferred_pcts):
        ax1.bar(years_inferred, inferred_pcts, color=color_turnover,
                edgecolor='black', linewidth=0.5, width=1.5, alpha=0.4,
                hatch='//', label='Initial Deployments (Inferred from 2006)')

    # Plot actual turnovers (2008+): Solid bars
    if years_actual:
        ax1.bar(years_actual, actual_pcts, color=color_turnover,
                edgecolor='black', linewidth=0.5, width=1.5, alpha=0.8,
                label='Upgrade % (Actual)')

    ax1.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Upgrade Percentage of Jurisdictions (%)',
                   fontsize=13, fontweight='bold', color=color_turnover)
    ax1.tick_params(axis='y', labelcolor=color_turnover)
    ax1.set_ylim(0, max(turnover_pcts_aligned) * 1.15 if turnover_pcts_aligned else 100)

    # Right axis: HAVA funding (line)
    ax2 = ax1.twinx()
    color_hava = 'green'
    ax2.plot(all_years, hava_funding_aligned, color=color_hava,
             marker='o', linewidth=2.5, markersize=8,
             label='HAVA Funding (Total)')

    ax2.set_ylabel('HAVA Funding (Millions $)', fontsize=13, fontweight='bold', color=color_hava)
    ax2.tick_params(axis='y', labelcolor=color_hava)

    # Title
    ax1.set_title('System Upgrade Percentage vs. HAVA Funding Investment (2000-2026)\n'
                  'Comparing System Upgrades with HAVA Funding',
                  fontsize=15, fontweight='bold', pad=20)

    # X-axis labels
    ax1.set_xticks(all_years)
    ax1.set_xticklabels([str(y) for y in all_years], rotation=45, ha='right')

    # Grid
    ax1.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               loc='upper left', fontsize=11, framealpha=0.9)

    # Save
    plt.tight_layout()
    output_path = OUTPUT_DIR / 'upgrade_and_hava_funding.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Chart saved to {output_path}")


def create_vendor_switching_matrix(df):
    """
    Create vendor switching matrix heatmap weighted by registered voters.

    Args:
        df: DataFrame with From_Vendor, To_Vendor, and Registered_Voters columns

    Returns:
        DataFrame: Transition probability matrix (weighted by voters)
    """
    # Exclude Hand Count transitions (not a vendor)
    df_filtered = df[
        (df['From_Vendor'] != 'Hand Count') &
        (df['To_Vendor'] != 'Hand Count')
    ].copy()

    # Filter out 2-year same-vendor transitions (likely coordinated upgrades)
    df_filtered = df_filtered[
        ~((df_filtered['Vendor_Retained'] == True) &
          (df_filtered['Years_Between'] == 2))
    ].copy()

    # Categorize vendors
    df_filtered['From_Cat'] = df_filtered['From_Vendor'].apply(categorize_vendor)
    df_filtered['To_Cat'] = df_filtered['To_Vendor'].apply(categorize_vendor)

    # Build transition matrix - SUM REGISTERED VOTERS instead of counting
    vendors = ['Dominion', 'ES&S', 'Hart', 'Other']
    voter_sums = pd.DataFrame(0.0, index=vendors, columns=vendors)

    for _, row in df_filtered.iterrows():
        from_vendor = row['From_Cat']
        to_vendor = row['To_Cat']
        voters = row['Registered_Voters']
        voter_sums.loc[from_vendor, to_vendor] += voters

    # Calculate transition probabilities (row-wise percentages based on voters)
    transition_probs = voter_sums.div(voter_sums.sum(axis=1), axis=0) * 100

    # Create heatmap
    fig, ax = plt.subplots(figsize=(10, 8))

    sns.heatmap(
        transition_probs,
        annot=True,              # Show percentages in cells
        fmt='.1f',               # 1 decimal place
        cmap='Greens',           # White (low) → Green (high)
        cbar_kws={'label': 'Transition Probability (%)'},
        linewidths=0.5,
        linecolor='gray',
        vmin=0,
        vmax=100,
        ax=ax
    )

    # Styling
    ax.set_xlabel('Vendor TO', fontsize=14, fontweight='bold')
    ax.set_ylabel('Vendor FROM', fontsize=14, fontweight='bold')
    ax.set_title('Voting System Vendor Switching Matrix (2006-2026)\n'
                 'Vendor Transition Probabilities in System Upgrades (Weighted by Registered Voters)',
                 fontsize=16, fontweight='bold', pad=20)

    plt.tight_layout()
    output_path = OUTPUT_DIR / 'vendor_switching_matrix.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Chart saved to {output_path}")

    return transition_probs


def create_vendor_retention_timeline(df):
    """
    Create vendor retention timeline chart weighted by registered voters.

    Args:
        df: DataFrame with From_Vendor, To_Year, Vendor_Retained, and Registered_Voters columns

    Returns:
        dict: Retention rates by period and vendor (weighted by voters)
    """
    # Add period labels
    df_periods = df.copy()
    df_periods['Period'] = df_periods['To_Year'].apply(get_period_label)

    # Get unique periods and sort them
    periods = sorted(df_periods['Period'].unique())

    # Calculate retention rates per vendor per period (weighted by voters)
    retention_data = defaultdict(list)

    for period in periods:
        period_df = df_periods[df_periods['Period'] == period].copy()

        # Filter out 2-year same-vendor transitions (likely coordinated upgrades)
        period_df = period_df[
            ~((period_df['Vendor_Retained'] == True) &
              (period_df['Years_Between'] == 2))
        ].copy()

        for vendor in MAJOR_VENDORS:
            vendor_transitions = period_df[period_df['From_Vendor'] == vendor]

            # Sum total voters for this vendor in this period
            total_voters = vendor_transitions['Registered_Voters'].sum()

            # Apply minimum sample size filter - require at least 5 jurisdictions
            if len(vendor_transitions) >= 5 and total_voters > 0:
                # Sum voters who retained same vendor
                retained_voters = vendor_transitions[
                    vendor_transitions['Vendor_Retained'] == True
                ]['Registered_Voters'].sum()

                retention_rate = (retained_voters / total_voters) * 100
            else:
                retention_rate = np.nan  # Insufficient data

            retention_data[vendor].append(retention_rate)

    # Create line chart
    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot each vendor as a line
    colors = {
        'Dominion': '#4169E1',  # Royal blue
        'ES&S': '#228B22',      # Forest green
        'Hart': '#9370DB'       # Medium purple
    }

    for vendor in MAJOR_VENDORS:
        ax.plot(periods, retention_data[vendor],
                marker='o', linewidth=2.5, markersize=8,
                color=colors[vendor], label=vendor)

    # Styling
    ax.set_xlabel('2-Year Period', fontsize=13, fontweight='bold')
    ax.set_ylabel('Retention Rate (%)', fontsize=13, fontweight='bold')
    ax.set_title('Vendor Retention Rates Upon System Upgrades (2006-2026)\n'
                 'Percentage of Registered Voters Retaining Same Vendor in System Upgrade',
                 fontsize=15, fontweight='bold', pad=20)

    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.legend(loc='best', fontsize=11, framealpha=0.9)
    ax.set_ylim(0, 100)

    # Add horizontal reference line at 50%
    ax.axhline(y=50, color='gray', linestyle=':', linewidth=1, alpha=0.5)

    # Rotate x-axis labels for readability
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()
    output_path = OUTPUT_DIR / 'vendor_retention_timeline.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Chart saved to {output_path}")

    return retention_data


def main():
    """Main processing pipeline."""
    print("=" * 80)
    print("VENDOR TURNOVER ANALYSIS (WEIGHTED BY REGISTERED VOTERS)")
    print("=" * 80)
    print()

    # Load data with voter information
    print("Loading between-system turnovers with registered voters...")
    df = load_turnovers_with_voters()
    print(f"✓ Loaded {len(df):,} transitions")
    print()

    # Print voter weighting statistics
    print("Voter Weighting Statistics:")
    total_voters = df['Registered_Voters'].sum()
    print(f"  Total registered voters in transitions: {total_voters:,}")
    print(f"  Average voters per transition: {df['Registered_Voters'].mean():,.0f}")
    print(f"  Median voters per transition: {df['Registered_Voters'].median():,.0f}")
    print()

    # Load yearly totals for percentage calculations
    print("Loading yearly totals from condensed data...")
    total_jurisdictions_by_year, total_voters_by_year = load_yearly_totals()
    print(f"✓ Loaded totals for {len(total_jurisdictions_by_year)} years")
    print()

    # Generate turnover volume chart
    print("Generating turnover volume by year chart...")
    year_counts = create_turnover_volume_chart(df)
    print()

    # Generate percentage charts
    print("Generating turnover percentage (jurisdictions) chart...")
    create_turnover_percentage_jurisdictions_chart(df, total_jurisdictions_by_year)
    print()

    print("Generating turnover percentage (voters) chart...")
    create_turnover_percentage_voters_chart(df, total_voters_by_year)
    print()

    # Generate dual-axis chart (turnover + HAVA)
    print("Generating turnover + HAVA funding dual-axis chart...")
    create_turnover_and_hava_dual_axis_chart(df, total_jurisdictions_by_year)
    print()

    # Print vendor summary statistics
    print("Vendor Distribution:")
    from_counts = df['From_Vendor'].value_counts()
    to_counts = df['To_Vendor'].value_counts()
    print(f"  From: {len(from_counts)} unique vendors")
    print(f"  To: {len(to_counts)} unique vendors")
    print()

    print("Major Vendor Statistics:")
    for vendor in MAJOR_VENDORS:
        from_count = (df['From_Vendor'] == vendor).sum()
        to_count = (df['To_Vendor'] == vendor).sum()
        retained = ((df['From_Vendor'] == vendor) & (df['Vendor_Retained'] == True)).sum()
        if from_count > 0:
            retention_pct = (retained / from_count) * 100
            print(f"  {vendor}:")
            print(f"    - From: {from_count:,} transitions ({from_count/len(df)*100:.1f}%)")
            print(f"    - To: {to_count:,} transitions ({to_count/len(df)*100:.1f}%)")
            print(f"    - Retention: {retained:,} ({retention_pct:.1f}%)")
    print()

    # Generate switching matrix
    print("Generating vendor switching matrix...")
    transition_matrix = create_vendor_switching_matrix(df)
    print()

    # Generate retention timeline
    print("Generating vendor retention timeline...")
    retention_data = create_vendor_retention_timeline(df)
    print()

    # Summary
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print("Generated files:")
    print("  - equipment_analysis/upgrade_volume_by_year.png")
    print("  - equipment_analysis/upgrade_percentage_jurisdictions.png")
    print("  - equipment_analysis/upgrade_percentage_voters.png")
    print("  - equipment_analysis/upgrade_and_hava_funding.png")
    print("  - equipment_analysis/vendor_switching_matrix.png")
    print("  - equipment_analysis/vendor_retention_timeline.png")
    print()


if __name__ == '__main__':
    main()
