#!/usr/bin/env python3
"""
Analyze voting system vendor retention using Kaplan-Meier survival analysis.

Uses jurisdiction_transitions.csv to calculate how long jurisdictions stay
with each vendor before switching to another vendor.

For each vendor:
- An "adoption" is a baseline or vendor transition TO that vendor
- A "departure" is a subsequent vendor transition AWAY from that vendor
- Right-censored: jurisdictions still with that vendor in 2026

Outputs:
- Kaplan-Meier survival curves comparing ES&S, Dominion, Hart
- Median survival time (years until 50% have switched)
- Survival probabilities at key time points
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'equipment'

# Vendors to analyze (actual names in data)
VENDORS = ['ES&S', 'Dominion', 'Hart InterCivic']

# Color palette
COLORS = {
    'ES&S': '#228B22',        # Forest green
    'Dominion': '#4169E1',    # Royal blue
    'Hart InterCivic': '#9370DB'  # Medium purple
}

# Current year for censoring
CURRENT_YEAR = 2026


def load_transitions():
    """Load jurisdiction transitions data."""
    filepath = DATA_DIR / 'jurisdiction_transitions.csv'

    if not filepath.exists():
        raise FileNotFoundError(f"Transitions file not found: {filepath}")

    df = pd.read_csv(filepath)
    print(f"✓ Loaded {len(df):,} transition records")

    return df


def calculate_vendor_survival_data(transitions_df, vendor):
    """
    Calculate survival data for a specific vendor.

    For each adoption of this vendor (baseline or transition TO vendor):
    - Find if/when they departed (vendor transition away)
    - Calculate duration and censoring status

    Args:
        transitions_df: Full transitions DataFrame
        vendor: Vendor name to analyze

    Returns:
        tuple: (durations, events, adoption_count, departure_count)
    """
    # Get all transitions sorted by FIPS and To_Year
    df = transitions_df.sort_values(['FIPS', 'To_Year'])

    # Find all adoptions of this vendor (baseline or vendor transition TO this vendor)
    adoptions = df[
        (df['To_Primary_Voting_Vendor'] == vendor) &
        (df['Transition_Type'].isin(['vendor', 'baseline']))
    ].copy()

    durations = []
    events = []  # True = departed (event), False = still with vendor (censored)

    for _, adoption in adoptions.iterrows():
        fips = adoption['FIPS']
        adoption_year = adoption['To_Year']

        # Find subsequent transitions for this FIPS after adoption
        subsequent = df[
            (df['FIPS'] == fips) &
            (df['To_Year'] > adoption_year) &
            (df['From_Primary_Voting_Vendor'] == vendor)
        ]

        if len(subsequent) > 0:
            # Check if any are vendor transitions (meaning they left this vendor)
            vendor_departures = subsequent[subsequent['Transition_Type'] == 'vendor']

            if len(vendor_departures) > 0:
                # They left this vendor - first departure wins
                first_departure = vendor_departures.iloc[0]
                departure_year = first_departure['To_Year']
                duration = departure_year - adoption_year
                durations.append(duration)
                events.append(True)  # Event observed (departed)
            else:
                # They had system transitions but stayed with vendor
                # Check if still active by finding last transition
                last_transition = subsequent.iloc[-1]
                if last_transition['To_Year'] >= CURRENT_YEAR:
                    # Still with vendor in current year
                    duration = CURRENT_YEAR - adoption_year
                    durations.append(duration)
                    events.append(False)  # Censored
                else:
                    # Edge case: last observed but before current year
                    duration = CURRENT_YEAR - adoption_year
                    durations.append(duration)
                    events.append(False)
        else:
            # No subsequent transitions - still with vendor (right-censored)
            duration = CURRENT_YEAR - adoption_year
            durations.append(duration)
            events.append(False)

    return (
        np.array(durations),
        np.array(events),
        len(adoptions),
        sum(events)
    )


def fit_survival_curves(transitions_df):
    """
    Fit Kaplan-Meier survival curves for each vendor.

    Args:
        transitions_df: Full transitions DataFrame

    Returns:
        dict: {vendor: KaplanMeierFitter object}
    """
    kmf_by_vendor = {}

    print("\nFitting Kaplan-Meier survival curves...")
    print("-" * 60)

    for vendor in VENDORS:
        durations, events, n_adoptions, n_departures = calculate_vendor_survival_data(
            transitions_df, vendor
        )

        n_censored = n_adoptions - n_departures
        pct_censored = (n_censored / n_adoptions * 100) if n_adoptions > 0 else 0

        print(f"\n{vendor}:")
        print(f"  Adoptions: {n_adoptions:,}")
        print(f"  Departures: {n_departures:,}")
        print(f"  Censored (still with vendor): {n_censored:,} ({pct_censored:.1f}%)")

        if len(durations) > 0:
            kmf = KaplanMeierFitter()
            kmf.fit(durations, event_observed=events, label=vendor)
            kmf_by_vendor[vendor] = kmf

            # Print median survival
            median = kmf.median_survival_time_
            if not np.isnan(median) and not np.isinf(median):
                print(f"  Median retention: {median:.0f} years")
            else:
                print(f"  Median retention: Not reached (>50% still retained)")

            # Print survival at key time points
            for t in [5, 10, 15, 20]:
                if t <= durations.max():
                    surv = kmf.predict(t)
                    print(f"  {t}-year retention: {surv:.1%}")
        else:
            print(f"  No adoptions found for {vendor}")

    return kmf_by_vendor


def create_survival_comparison_chart(kmf_by_vendor, output_path):
    """
    Create comparison chart of vendor survival curves.

    Args:
        kmf_by_vendor: dict of {vendor: KaplanMeierFitter}
        output_path: Path to save chart
    """
    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot each vendor's survival curve
    for vendor in VENDORS:
        if vendor in kmf_by_vendor:
            kmf = kmf_by_vendor[vendor]
            kmf.plot_survival_function(
                ax=ax,
                ci_show=True,
                color=COLORS[vendor],
                linewidth=2.5,
                alpha=0.9
            )

    # Add 50% reference line
    ax.axhline(y=0.5, color='gray', linestyle=':', linewidth=1, alpha=0.5,
               label='50% retention')

    # Labels and title
    ax.set_xlabel('Years Since Vendor Adoption', fontsize=13, fontweight='bold')
    ax.set_ylabel('Retention Probability', fontsize=13, fontweight='bold')
    ax.set_title('Vendor Retention Survival Curves (2006-2026)\n'
                 'Probability of Remaining with Vendor Over Time',
                 fontsize=15, fontweight='bold', pad=20)

    # Set axis limits
    ax.set_ylim(0, 1.05)
    ax.set_xlim(0, 25)

    # Grid
    ax.grid(axis='both', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # Legend
    ax.legend(loc='lower left', fontsize=11, framealpha=0.9)

    # Add annotations for key findings
    annotations = []
    for vendor in VENDORS:
        if vendor in kmf_by_vendor:
            kmf = kmf_by_vendor[vendor]
            median = kmf.median_survival_time_
            if not np.isnan(median) and not np.isinf(median):
                annotations.append(f"{vendor}: {median:.0f}yr median")
            else:
                annotations.append(f"{vendor}: >50% retained")

    if annotations:
        annotation_text = "Median Retention:\n" + "\n".join(annotations)
        ax.text(0.98, 0.98, annotation_text,
                transform=ax.transAxes, fontsize=10,
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))

    plt.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"\n✓ Chart saved to {output_path}")


def create_individual_survival_charts(kmf_by_vendor, transitions_df):
    """
    Create individual survival charts for each vendor with more detail.

    Args:
        kmf_by_vendor: dict of {vendor: KaplanMeierFitter}
        transitions_df: Full transitions DataFrame
    """
    for vendor in VENDORS:
        if vendor not in kmf_by_vendor:
            continue

        kmf = kmf_by_vendor[vendor]
        durations, events, n_adoptions, n_departures = calculate_vendor_survival_data(
            transitions_df, vendor
        )

        n_censored = n_adoptions - n_departures
        pct_censored = (n_censored / n_adoptions * 100) if n_adoptions > 0 else 0

        fig, ax = plt.subplots(figsize=(12, 7))

        # Plot survival curve with confidence interval
        kmf.plot_survival_function(ax=ax, ci_show=True, color=COLORS[vendor], linewidth=2.5)

        # Get median survival
        median = kmf.median_survival_time_

        # Add vertical line at median if it exists
        if not np.isnan(median) and not np.isinf(median):
            ax.axvline(x=median, color='darkorange', linestyle='--', linewidth=1.5)
            ax.axhline(y=0.5, color='gray', linestyle=':', linewidth=1, alpha=0.5)

            ax.annotate(f'Median: {median:.0f} years',
                        xy=(median, 0.5),
                        xytext=(median + 2, 0.6),
                        fontsize=11, fontweight='bold',
                        arrowprops=dict(arrowstyle='->', color='darkorange'),
                        color='darkorange')
        else:
            ax.annotate('Median not reached\n(>50% still retained)',
                        xy=(0.95, 0.95), xycoords='axes fraction',
                        fontsize=11, fontweight='bold',
                        ha='right', va='top',
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # Labels and title
        ax.set_xlabel('Years Since Adoption', fontsize=13, fontweight='bold')
        ax.set_ylabel('Retention Probability', fontsize=13, fontweight='bold')

        title = f'{vendor} Vendor Retention Survival Curve'
        subtitle = f'n={n_adoptions:,} ({n_departures:,} departed, {n_censored:,} retained [{pct_censored:.0f}%])'
        ax.set_title(f'{title}\n{subtitle}', fontsize=15, fontweight='bold', pad=20)

        # Set axis limits
        ax.set_ylim(0, 1.05)
        ax.set_xlim(0, max(durations) + 2 if len(durations) > 0 else 25)

        # Grid
        ax.grid(axis='both', alpha=0.3, linestyle='--', linewidth=0.5)
        ax.set_axisbelow(True)

        # Add survival probabilities at key time points
        time_points = [5, 10, 15, 20]
        survival_text = []
        for t in time_points:
            if len(durations) > 0 and t <= max(durations):
                surv_prob = kmf.predict(t)
                survival_text.append(f'{t}yr: {surv_prob:.0%}')

        if survival_text:
            ax.text(0.02, 0.02, 'Retention at: ' + ', '.join(survival_text),
                    transform=ax.transAxes, fontsize=10,
                    verticalalignment='bottom',
                    bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

        # Legend
        ax.legend(loc='upper right', fontsize=10)

        plt.tight_layout()

        vendor_slug = vendor.lower().replace('&', '').replace(' ', '_')
        output_path = OUTPUT_DIR / f'vendor_retention_{vendor_slug}.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Individual chart saved to {output_path}")


def analyze_churn_destinations(transitions_df):
    """
    Analyze where jurisdictions go when they leave each vendor.

    Args:
        transitions_df: Full transitions DataFrame

    Returns:
        dict: {vendor: {destination: count}}
    """
    print("\n" + "=" * 60)
    print("CHURN DESTINATION ANALYSIS")
    print("=" * 60)

    # Filter to vendor transitions only
    vendor_changes = transitions_df[transitions_df['Transition_Type'] == 'vendor']

    for vendor in VENDORS:
        departures = vendor_changes[vendor_changes['From_Primary_Voting_Vendor'] == vendor]

        if len(departures) == 0:
            print(f"\n{vendor}: No departures recorded")
            continue

        print(f"\n{vendor} → (where did they go?):")
        destinations = departures['To_Primary_Voting_Vendor'].value_counts()

        for dest, count in destinations.head(5).items():
            pct = count / len(departures) * 100
            print(f"  → {dest}: {count:,} ({pct:.1f}%)")


def print_summary(kmf_by_vendor):
    """Print summary statistics."""
    print("\n" + "=" * 60)
    print("RETENTION SUMMARY")
    print("=" * 60)

    # Compare median retention
    print("\nMedian Retention Times (50% still with vendor):")
    medians = []
    for vendor in VENDORS:
        if vendor in kmf_by_vendor:
            median = kmf_by_vendor[vendor].median_survival_time_
            if not np.isnan(median) and not np.isinf(median):
                medians.append((vendor, median))
                print(f"  {vendor}: {median:.0f} years")
            else:
                print(f"  {vendor}: Not reached (>50% retained)")

    # Compare 10-year retention
    print("\n10-Year Retention Rates:")
    rates_10yr = []
    for vendor in VENDORS:
        if vendor in kmf_by_vendor:
            kmf = kmf_by_vendor[vendor]
            try:
                rate = kmf.predict(10)
                rates_10yr.append((vendor, rate))
            except Exception:
                continue

    rates_10yr.sort(key=lambda x: x[1], reverse=True)
    for rank, (vendor, rate) in enumerate(rates_10yr, 1):
        marker = "★" if rank == 1 else " "
        print(f"  {marker} {rank}. {vendor}: {rate:.1%}")


def main():
    """Main execution function."""
    print("=" * 80)
    print("VENDOR RETENTION SURVIVAL ANALYSIS")
    print("=" * 80)

    # Load transitions data
    print("\nLoading jurisdiction transitions data...")
    transitions_df = load_transitions()

    # Fit survival curves
    kmf_by_vendor = fit_survival_curves(transitions_df)

    # Create comparison chart
    print("\n" + "-" * 60)
    print("GENERATING CHARTS")
    print("-" * 60)

    output_path = OUTPUT_DIR / 'vendor_survival_curves.png'
    create_survival_comparison_chart(kmf_by_vendor, output_path)

    # Create individual vendor charts
    create_individual_survival_charts(kmf_by_vendor, transitions_df)

    # Analyze churn destinations
    analyze_churn_destinations(transitions_df)

    # Print summary
    print_summary(kmf_by_vendor)

    print("\n" + "=" * 80)
    print("✓ ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print("Generated files:")
    print(f"  - {OUTPUT_DIR / 'vendor_survival_curves.png'}")
    for vendor in VENDORS:
        vendor_slug = vendor.lower().replace('&', '').replace(' ', '_')
        print(f"  - {OUTPUT_DIR / f'vendor_retention_{vendor_slug}.png'}")
    print()


if __name__ == "__main__":
    main()
