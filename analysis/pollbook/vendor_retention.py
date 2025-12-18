#!/usr/bin/env python3
"""
Analyze poll book vendor retention using survival analysis.

Compares retention rates for KNOWiNK, ES&S, and Tenex at 2, 4, 6, 8, 10, 12,
and 14+ year intervals after adoption.

Tracks all adoptions separately (jurisdictions that switch back count twice).
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Vendors to analyze
VENDORS = ['KNOWiNK', 'ES&S', 'Tenex', 'In-House']

# Color palette
COLORS = {
    'KNOWiNK': '#e74c3c',
    'ES&S': '#3498db',
    'Tenex': '#27ae60',
    'In-House': '#F4D03F'
}

# Time intervals to analyze (years since adoption)
INTERVALS = [2, 4, 6, 8, 10, 12, "14+"]

# Current year (for censoring)
CURRENT_YEAR = 2026


def load_turnover_data():
    """Load poll book turnover data."""
    filepath = 'data/processed/pollbook_turnover.csv'
    df = pd.read_csv(filepath)
    return df


def load_baseline_data():
    """Load 2006 baseline poll book data."""
    filepath = 'data/processed/jurisdictions/2006_verifier-jurisdictions-condensed.csv'

    # Read CSV, skipping title row
    df = pd.read_csv(filepath, skiprows=1)

    # Extract relevant columns
    baseline = df[['FIPS code', 'State', 'Jurisdiction', 'Poll Book Status']].copy()
    baseline.rename(columns={'FIPS code': 'FIPS'}, inplace=True)

    return baseline


def reconstruct_timelines(baseline_df, turnover_df):
    """
    Reconstruct jurisdiction timelines from 2006 baseline + turnover events.

    Returns:
        dict: {FIPS: [(year, status), (year, status), ...]}
    """
    timelines = defaultdict(list)

    # Step 1: Initialize with 2006 baseline poll book status
    for _, row in baseline_df.iterrows():
        fips = row['FIPS']
        status = row['Poll Book Status']

        # Skip if missing poll book status
        if pd.isna(status) or status == '':
            continue

        # Initialize timeline with 2006 baseline (assume all started in 2006)
        timelines[fips].append((2006, status))

    # Step 2: Add turnover events (chronologically)
    for _, row in turnover_df.iterrows():
        fips = row['FIPS']
        to_year = row['To_Year']
        to_status = row['To_Status']

        # Skip if missing data
        if pd.isna(to_status) or to_status == '':
            continue

        # Add to timeline
        timelines[fips].append((to_year, to_status))

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
            year, status = timeline[i]
            if status == vendor:
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
        interval: Years since adoption (e.g., 2, 4, 6) or "14+" for long-term

    Returns:
        tuple: (retention_rate, n_at_risk, n_retained, n_churned)
    """
    at_risk = []  # Adoptions with enough follow-up time
    retained = []  # Still using vendor at interval
    churned = []   # Switched away before interval

    # Handle "14+" interval specially - check current retention for all long-term users
    if interval == "14+":
        cutoff_year = CURRENT_YEAR - 14  # 2012 for 2026

        for fips, adoption_year, timeline in adoptions:
            # Include all adoptions from 2012 or earlier (14+ years ago)
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

    Args:
        timelines: Pre-constructed timelines dict
        vendor: Vendor name to analyze

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

        interval_label = f"{interval}-year" if interval != "14+" else "14+ year"
        if n_at_risk > 0:
            print(f"  {interval_label}: {rate:5.1f}% retention (n={n_at_risk}, retained={n_retained}, churned={n_churned})")
        else:
            print(f"  {interval_label}: N/A (insufficient data)")

    return retention_data


def analyze_churn_destinations(timelines, vendor):
    """
    Analyze where jurisdictions go when they leave a vendor.

    Args:
        timelines: Pre-constructed timelines dict
        vendor: Vendor name to analyze

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
    width = 0.20  # Narrower bars for 4 vendors

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

        # Plot bars (adjust offset for 4 vendors)
        offset = (i - 1.5) * width
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
    ax.set_title('Poll Book Vendor Retention Comparison\nPercentage of jurisdictions still using vendor X years after adoption',
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
        interval_label = f"{interval}-Year" if interval != "14+" else "14+ Year"
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
    print("POLL BOOK VENDOR RETENTION ANALYSIS")
    print("="*80)

    # Load baseline data
    print("\nLoading 2006 baseline data...")
    baseline_df = load_baseline_data()
    print(f"✓ Loaded {len(baseline_df)} jurisdictions")

    # Load turnover data
    print("\nLoading turnover data...")
    turnover_df = load_turnover_data()
    print(f"✓ Loaded {len(turnover_df)} turnover events")

    # Reconstruct timelines
    print("\nReconstructing poll book timelines...")
    timelines = reconstruct_timelines(baseline_df, turnover_df)
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

    output_path = 'outputs/figures/pollbook/vendor_retention_comparison.png'
    create_comparison_chart(vendor_retention_data, output_path)

    # Print summary
    print_summary(vendor_retention_data, churn_data)

    print("\n" + "="*80)
    print("✓ ANALYSIS COMPLETE")
    print("="*80)
    print()


if __name__ == "__main__":
    main()
