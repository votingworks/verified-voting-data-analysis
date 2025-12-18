#!/usr/bin/env python3
"""
Analyze voting system vendor retention using survival analysis.

Compares retention rates for ES&S, Dominion, and Hart at 2, 4, 6, 8, 10, 12,
14, 16, and 18+ year intervals after adoption.

Tracks all adoptions separately (jurisdictions that switch back count twice).
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Vendors to analyze
VENDORS = ['ES&S', 'Dominion', 'Hart']

# Color palette
COLORS = {
    'ES&S': '#3498db',
    'Dominion': '#e74c3c',
    'Hart': '#27ae60'
}

# Time intervals to analyze (years since adoption)
INTERVALS = [2, 4, 6, 8, 10, 12, 14, 16, "18+"]

# Current year (for censoring)
CURRENT_YEAR = 2026


def load_baseline_data():
    """Load 2006 baseline vendor data."""
    filepath = 'data/verifier-condensed/2006_verifier-jurisdictions-condensed.csv'

    # Read CSV, skipping the title row
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        df = pd.read_csv(filepath, skiprows=1)

    return df


def load_vendor_changes():
    """Load vendor change events from time series CSV."""
    filepath = 'data/voting_system_time_series.csv'
    df = pd.read_csv(filepath)

    # Filter to between_system records only
    df = df[df['Record_Type'] == 'between_system']

    # Filter to only vendor changes
    vendor_changes = df[df['Vendor_Retained'] == False].copy()

    return vendor_changes


def parse_first_year(year_str):
    """Parse First Year In Use field, return int or None."""
    if pd.isna(year_str) or year_str == '':
        return None

    try:
        year = int(year_str)
        # Validate reasonable range
        if 1950 <= year <= 2026:
            return year
        return None
    except (ValueError, TypeError):
        return None


def reconstruct_timelines(baseline_df, vendor_changes_df):
    """
    Reconstruct jurisdiction vendor timelines from baseline + changes.

    Returns:
        dict: {FIPS: [(year, vendor), (year, vendor), ...]}
    """
    timelines = defaultdict(list)

    # Step 1: Initialize with baseline vendor data
    for _, row in baseline_df.iterrows():
        fips = row['FIPS code']
        vendor = row['Primary Voting Vendor']
        first_year = parse_first_year(row['Primary Voting Equipment - First Year In Use'])

        # Skip if missing vendor
        if pd.isna(vendor) or vendor == '':
            continue

        # Use First Year In Use if valid, otherwise default to 2006
        baseline_year = first_year if first_year else 2006

        timelines[fips].append((baseline_year, vendor))

    # Step 2: Add vendor change events (chronologically)
    for _, row in vendor_changes_df.iterrows():
        fips = row['FIPS']
        to_year = row['To_Year']
        to_vendor = row['To_Vendor']

        # Skip if missing data
        if pd.isna(to_vendor) or to_vendor == '':
            continue

        # Add to timeline
        timelines[fips].append((to_year, to_vendor))

    # Step 3: Sort each timeline by year
    for fips in timelines:
        timelines[fips].sort()

    return timelines


def identify_adoptions(timelines, vendor):
    """
    Identify all adoptions of a vendor.

    Each transition TO the vendor counts as an adoption.
    Multiple adoptions by same jurisdiction count separately.

    Returns:
        list: [(FIPS, adoption_year, timeline_after_adoption), ...]
    """
    adoptions = []

    for fips, timeline in timelines.items():
        for i in range(len(timeline)):
            year, current_vendor = timeline[i]
            if current_vendor == vendor:
                # This is an adoption (switched TO vendor)
                # Get remaining timeline after this point
                future_timeline = timeline[i:]
                adoptions.append((fips, year, future_timeline))

    return adoptions


def calculate_retention(adoptions, interval):
    """
    Calculate retention rate at a specific time interval.

    Args:
        adoptions: List of (FIPS, adoption_year, timeline)
        interval: Years since adoption (e.g., 2, 4, 6) or "18+" for long-term

    Returns:
        tuple: (retention_rate, n_at_risk, n_retained, n_churned)
    """
    at_risk = []  # Adoptions with enough follow-up time
    retained = []  # Still using vendor at interval
    churned = []   # Switched away before interval

    # Handle "18+" interval specially - check current retention for all long-term users
    if interval == "18+":
        cutoff_year = CURRENT_YEAR - 18  # 2008 for 2026

        for fips, adoption_year, timeline in adoptions:
            # Include all adoptions from 2008 or earlier (18+ years ago)
            if adoption_year <= cutoff_year:
                at_risk.append(fips)

                # Find current status in 2026
                current_status = timeline[0][1]  # Start with adoption status

                for year, status in timeline:
                    if year <= CURRENT_YEAR:
                        current_status = status
                    else:
                        break

                # Check if still using the original vendor
                original_vendor = timeline[0][1]
                if current_status == original_vendor:
                    retained.append(fips)
                else:
                    churned.append(fips)
    else:
        # Standard interval calculation
        for fips, adoption_year, timeline in adoptions:
            target_year = adoption_year + interval

            # Skip if not enough follow-up time
            if target_year > CURRENT_YEAR:
                continue

            at_risk.append(fips)

            # Find status at target year
            current_status = timeline[0][1]  # Start with adoption status

            for year, status in timeline:
                if year <= target_year:
                    current_status = status
                else:
                    break

            # Check if still using the original vendor
            original_vendor = timeline[0][1]
            if current_status == original_vendor:
                retained.append(fips)
            else:
                churned.append(fips)

    # Calculate retention rate
    n_at_risk = len(at_risk)
    n_retained = len(retained)
    n_churned = len(churned)

    if n_at_risk == 0:
        return 0.0, 0, 0, 0

    retention_rate = (n_retained / n_at_risk) * 100

    return retention_rate, n_at_risk, n_retained, n_churned


def analyze_vendor_retention(timelines, vendor):
    """
    Analyze retention for a specific vendor.

    Returns:
        dict: {interval: (retention_rate, n_at_risk)}
    """
    # Identify all adoptions
    adoptions = identify_adoptions(timelines, vendor)

    print(f"\n{vendor}:")
    print(f"  Total adoptions: {len(adoptions)}")

    # Calculate retention at each interval
    retention_data = {}

    for interval in INTERVALS:
        rate, n_at_risk, n_retained, n_churned = calculate_retention(adoptions, interval)
        retention_data[interval] = (rate, n_at_risk)

        interval_label = f"{interval}-year" if interval != "18+" else "18+ year"
        if n_at_risk > 0:
            print(f"  {interval_label}: {rate:5.1f}% retention (n={n_at_risk}, retained={n_retained}, churned={n_churned})")
        else:
            print(f"  {interval_label}: N/A (insufficient data)")

    return retention_data


def analyze_churn_destinations(timelines, vendor):
    """
    Analyze where jurisdictions go when they leave a vendor.

    Returns:
        Counter: {destination_vendor: count}
    """
    adoptions = identify_adoptions(timelines, vendor)
    destinations = defaultdict(int)

    for fips, adoption_year, timeline in adoptions:
        # Find if/when they churned
        for i in range(len(timeline)):
            year, status = timeline[i]
            if status == vendor and i + 1 < len(timeline):
                # Next status is the churn destination
                next_status = timeline[i + 1][1]
                if next_status != vendor:
                    destinations[next_status] += 1
                    break

    return destinations


def create_comparison_chart(vendor_retention_data, output_path):
    """
    Create grouped bar chart comparing vendor retention rates.

    Args:
        vendor_retention_data: {vendor: {interval: (rate, n_at_risk)}}
        output_path: Path to save chart
    """
    fig, ax = plt.subplots(figsize=(16, 8))

    # Prepare data for plotting
    x = np.arange(len(INTERVALS))
    width = 0.25

    for i, vendor in enumerate(VENDORS):
        retention_data = vendor_retention_data[vendor]

        rates = []
        n_values = []

        for interval in INTERVALS:
            if interval in retention_data:
                rate, n_at_risk = retention_data[interval]
                rates.append(rate)
                n_values.append(n_at_risk)
            else:
                rates.append(0)
                n_values.append(0)

        # Plot bars
        offset = (i - 1) * width
        bars = ax.bar(x + offset, rates, width, label=vendor, color=COLORS[vendor], alpha=0.8)

        # Add value labels on bars
        for j, (bar, rate, n) in enumerate(zip(bars, rates, n_values)):
            if n > 0:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{rate:.0f}%\n(n={n})',
                       ha='center', va='bottom', fontsize=9)

    # Customize chart
    ax.set_xlabel('Years Since Adoption', fontsize=14)
    ax.set_ylabel('Retention Rate (%)', fontsize=14)
    ax.set_title('Voting System Vendor Retention Comparison\nWhat are the odds a jurisdiction is with the same vendor after X years?',
                fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels([str(interval) for interval in INTERVALS])
    ax.set_ylim(0, 105)
    ax.legend(fontsize=12, loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Chart saved to {output_path}")


def print_summary(vendor_retention_data, churn_data):
    """Print summary statistics."""
    print("\n" + "="*80)
    print("RETENTION SUMMARY")
    print("="*80)

    # Compare vendors at each interval
    for interval in INTERVALS:
        interval_label = f"{interval}-Year" if interval != "18+" else "18+ Year"
        print(f"\n{interval_label} Retention:")

        # Sort vendors by retention rate
        vendor_rates = []
        for vendor in VENDORS:
            if interval in vendor_retention_data[vendor]:
                rate, n = vendor_retention_data[vendor][interval]
                if n > 0:
                    vendor_rates.append((vendor, rate, n))

        vendor_rates.sort(key=lambda x: x[1], reverse=True)

        for rank, (vendor, rate, n) in enumerate(vendor_rates, 1):
            marker = "★" if rank == 1 else " "
            print(f"  {marker} {rank}. {vendor:10s}: {rate:5.1f}% (n={n})")

    # Churn destinations
    print("\n" + "="*80)
    print("CHURN DESTINATIONS")
    print("="*80)

    for vendor in VENDORS:
        destinations = churn_data[vendor]
        if destinations:
            print(f"\n{vendor} churned to:")
            for dest, count in sorted(destinations.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  - {dest:20s}: {count:3d} jurisdictions")


def main():
    """Main execution function."""
    print("="*80)
    print("VOTING SYSTEM VENDOR RETENTION ANALYSIS")
    print("="*80)

    # Load baseline data
    print("\nLoading 2006 baseline data...")
    baseline_df = load_baseline_data()
    print(f"✓ Loaded {len(baseline_df)} jurisdictions")

    # Load vendor changes
    print("\nLoading vendor change events...")
    vendor_changes_df = load_vendor_changes()
    print(f"✓ Loaded {len(vendor_changes_df)} vendor-changing transitions")

    # Reconstruct timelines
    print("\nReconstructing vendor timelines...")
    timelines = reconstruct_timelines(baseline_df, vendor_changes_df)
    print(f"✓ Reconstructed timelines for {len(timelines)} jurisdictions")

    # Analyze each vendor
    print("\n" + "-"*80)
    print("ANALYZING RETENTION RATES")
    print("-"*80)

    vendor_retention_data = {}
    churn_data = {}

    for vendor in VENDORS:
        vendor_retention_data[vendor] = analyze_vendor_retention(timelines, vendor)
        churn_data[vendor] = analyze_churn_destinations(timelines, vendor)

    # Create comparison chart
    print("\n" + "-"*80)
    print("CREATING COMPARISON CHART")
    print("-"*80)

    output_path = 'equipment_analysis/voting_vendor_retention_comparison.png'
    create_comparison_chart(vendor_retention_data, output_path)

    # Print summary
    print_summary(vendor_retention_data, churn_data)

    print("\n" + "="*80)
    print("✓ ANALYSIS COMPLETE")
    print("="*80)
    print()


if __name__ == "__main__":
    main()
