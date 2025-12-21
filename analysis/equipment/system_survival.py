#!/usr/bin/env python3
"""
Analyze voting system survival using Kaplan-Meier survival analysis.

Uses jurisdiction_transitions.csv to calculate how long jurisdictions keep
their voting systems before switching vendors or upgrading to a new system.

A system "survives" until:
- Vendor change (Transition_Type == 'vendor') - switch to different vendor
- System change (Transition_Type == 'system') - major system upgrade

Right-censored: jurisdictions still using their system in 2026

Outputs:
- Overall system survival curve
- Survival curves by vendor (ES&S, Dominion, Hart systems compared)
- Median survival time and retention rates
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

# Vendors to compare
VENDORS = ['ES&S', 'Dominion', 'Hart InterCivic']

# Color palette
COLORS = {
    'All Systems': '#2F4F4F',  # Dark slate gray
    'ES&S': '#228B22',         # Forest green
    'Dominion': '#4169E1',     # Royal blue
    'Hart InterCivic': '#9370DB'  # Medium purple
}

# Current year for censoring
CURRENT_YEAR = 2026

# Transition types that end a system's life
SYSTEM_END_TRANSITIONS = ['vendor', 'system']


def load_transitions():
    """Load jurisdiction transitions data."""
    filepath = DATA_DIR / 'jurisdiction_transitions.csv'

    if not filepath.exists():
        raise FileNotFoundError(f"Transitions file not found: {filepath}")

    df = pd.read_csv(filepath)
    print(f"Loaded {len(df):,} transition records")

    return df


def calculate_system_survival_data(transitions_df, vendor=None):
    """
    Calculate survival data for voting systems.

    For each system adoption (baseline or vendor/system transition):
    - Find if/when they changed systems (vendor or system transition)
    - Calculate duration and censoring status

    Args:
        transitions_df: Full transitions DataFrame
        vendor: Optional vendor to filter to (None = all vendors)

    Returns:
        tuple: (durations, events, adoption_count, event_count)
    """
    # Get all transitions sorted by FIPS and To_Year
    df = transitions_df.sort_values(['FIPS', 'To_Year'])

    # Find all system adoptions
    # - baseline: initial system
    # - vendor: new vendor means new system
    # - system: system upgrade within vendor
    adoption_types = ['baseline', 'vendor', 'system']

    if vendor:
        adoptions = df[
            (df['To_Primary_Voting_Vendor'] == vendor) &
            (df['Transition_Type'].isin(adoption_types))
        ].copy()
    else:
        adoptions = df[
            df['Transition_Type'].isin(adoption_types)
        ].copy()

    durations = []
    events = []  # True = system replaced (event), False = still in use (censored)

    for _, adoption in adoptions.iterrows():
        fips = adoption['FIPS']
        adoption_year = adoption['To_Year']
        adopted_system = adoption['To_Primary_Voting_System']

        # Skip if no system recorded
        if pd.isna(adopted_system) or adopted_system == '':
            continue

        # Find subsequent transitions for this FIPS after adoption
        subsequent = df[
            (df['FIPS'] == fips) &
            (df['To_Year'] > adoption_year)
        ]

        if len(subsequent) > 0:
            # Check if any are system-ending transitions
            system_changes = subsequent[
                subsequent['Transition_Type'].isin(SYSTEM_END_TRANSITIONS)
            ]

            if len(system_changes) > 0:
                # System was replaced - first change wins
                first_change = system_changes.iloc[0]
                change_year = first_change['To_Year']
                duration = change_year - adoption_year
                durations.append(duration)
                events.append(True)  # Event observed (system replaced)
            else:
                # Only had other transitions (mail, equipment, etc.) - still same system
                duration = CURRENT_YEAR - adoption_year
                durations.append(duration)
                events.append(False)  # Censored
        else:
            # No subsequent transitions - still using same system (right-censored)
            duration = CURRENT_YEAR - adoption_year
            durations.append(duration)
            events.append(False)

    return (
        np.array(durations),
        np.array(events),
        len(durations),
        sum(events)
    )


def fit_overall_survival(transitions_df):
    """
    Fit overall Kaplan-Meier survival curve for all systems.

    Args:
        transitions_df: Full transitions DataFrame

    Returns:
        KaplanMeierFitter object
    """
    durations, events, n_adoptions, n_events = calculate_system_survival_data(
        transitions_df, vendor=None
    )

    n_censored = n_adoptions - n_events
    pct_censored = (n_censored / n_adoptions * 100) if n_adoptions > 0 else 0

    print(f"\nOverall System Survival:")
    print(f"  System adoptions: {n_adoptions:,}")
    print(f"  Systems replaced: {n_events:,}")
    print(f"  Still in use (censored): {n_censored:,} ({pct_censored:.1f}%)")

    kmf = KaplanMeierFitter()
    kmf.fit(durations, event_observed=events, label='All Systems')

    median = kmf.median_survival_time_
    if not np.isnan(median) and not np.isinf(median):
        print(f"  Median survival: {median:.0f} years")
    else:
        print(f"  Median survival: Not reached (>50% still in use)")

    # Print survival at key time points
    for t in [5, 10, 15, 20]:
        if t <= durations.max():
            surv = kmf.predict(t)
            print(f"  {t}-year survival: {surv:.1%}")

    return kmf


def fit_vendor_survival_curves(transitions_df):
    """
    Fit Kaplan-Meier survival curves for each vendor's systems.

    Args:
        transitions_df: Full transitions DataFrame

    Returns:
        dict: {vendor: KaplanMeierFitter object}
    """
    kmf_by_vendor = {}

    print("\nSurvival by Vendor:")
    print("-" * 60)

    for vendor in VENDORS:
        durations, events, n_adoptions, n_events = calculate_system_survival_data(
            transitions_df, vendor=vendor
        )

        if n_adoptions == 0:
            print(f"\n{vendor}: No system adoptions found")
            continue

        n_censored = n_adoptions - n_events
        pct_censored = (n_censored / n_adoptions * 100)

        print(f"\n{vendor}:")
        print(f"  System adoptions: {n_adoptions:,}")
        print(f"  Systems replaced: {n_events:,}")
        print(f"  Still in use: {n_censored:,} ({pct_censored:.1f}%)")

        if len(durations) > 0:
            kmf = KaplanMeierFitter()
            kmf.fit(durations, event_observed=events, label=vendor)
            kmf_by_vendor[vendor] = kmf

            median = kmf.median_survival_time_
            if not np.isnan(median) and not np.isinf(median):
                print(f"  Median survival: {median:.0f} years")
            else:
                print(f"  Median survival: Not reached (>50% still in use)")

    return kmf_by_vendor


def create_overall_survival_chart(kmf, output_path):
    """
    Create chart showing overall system survival.

    Args:
        kmf: KaplanMeierFitter object for all systems
        output_path: Path to save chart
    """
    fig, ax = plt.subplots(figsize=(12, 7))

    # Plot survival curve
    kmf.plot_survival_function(
        ax=ax,
        ci_show=True,
        color=COLORS['All Systems'],
        linewidth=2.5
    )

    # Get median
    median = kmf.median_survival_time_

    # Add median line if available
    if not np.isnan(median) and not np.isinf(median):
        ax.axvline(x=median, color='darkorange', linestyle='--', linewidth=1.5)
        ax.axhline(y=0.5, color='gray', linestyle=':', linewidth=1, alpha=0.5)
        ax.annotate(f'Median: {median:.0f} years',
                    xy=(median, 0.5),
                    xytext=(median + 1.5, 0.6),
                    fontsize=11, fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color='darkorange'),
                    color='darkorange')
    else:
        ax.axhline(y=0.5, color='gray', linestyle=':', linewidth=1, alpha=0.5)

    # Labels and title
    ax.set_xlabel('Years Since System Adoption', fontsize=13, fontweight='bold')
    ax.set_ylabel('Survival Probability', fontsize=13, fontweight='bold')
    ax.set_title('Voting System Survival Curve (2006-2026)\n'
                 'Probability of System Remaining in Use Over Time',
                 fontsize=15, fontweight='bold', pad=20)

    # Set axis limits
    ax.set_ylim(0, 1.05)
    ax.set_xlim(0, 25)

    # Grid
    ax.grid(axis='both', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # Legend
    ax.legend(loc='lower left', fontsize=11)

    plt.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"\nChart saved to {output_path}")


def create_vendor_comparison_chart(kmf_by_vendor, output_path):
    """
    Create chart comparing system survival by vendor.

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
               label='50% survival')

    # Labels and title
    ax.set_xlabel('Years Since System Adoption', fontsize=13, fontweight='bold')
    ax.set_ylabel('Survival Probability', fontsize=13, fontweight='bold')
    ax.set_title('Voting System Survival by Vendor (2006-2026)\n'
                 'Probability of System Remaining in Use Over Time',
                 fontsize=15, fontweight='bold', pad=20)

    # Set axis limits
    ax.set_ylim(0, 1.05)
    ax.set_xlim(0, 25)

    # Grid
    ax.grid(axis='both', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # Legend
    ax.legend(loc='lower left', fontsize=11, framealpha=0.9)

    # Add annotations for medians
    annotations = []
    for vendor in VENDORS:
        if vendor in kmf_by_vendor:
            kmf = kmf_by_vendor[vendor]
            median = kmf.median_survival_time_
            if not np.isnan(median) and not np.isinf(median):
                annotations.append(f"{vendor}: {median:.0f}yr median")
            else:
                annotations.append(f"{vendor}: >50% still in use")

    if annotations:
        annotation_text = "Median Survival:\n" + "\n".join(annotations)
        ax.text(0.98, 0.98, annotation_text,
                transform=ax.transAxes, fontsize=10,
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))

    plt.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"Chart saved to {output_path}")


def main():
    """Main execution function."""
    print("=" * 80)
    print("VOTING SYSTEM SURVIVAL ANALYSIS")
    print("=" * 80)

    # Load transitions data
    print("\nLoading jurisdiction transitions data...")
    transitions_df = load_transitions()

    # Fit overall survival curve
    print("\n" + "-" * 60)
    print("FITTING SURVIVAL CURVES")
    print("-" * 60)

    kmf_overall = fit_overall_survival(transitions_df)
    kmf_by_vendor = fit_vendor_survival_curves(transitions_df)

    # Create charts
    print("\n" + "-" * 60)
    print("GENERATING CHARTS")
    print("-" * 60)

    create_overall_survival_chart(
        kmf_overall,
        OUTPUT_DIR / 'system_survival.png'
    )

    create_vendor_comparison_chart(
        kmf_by_vendor,
        OUTPUT_DIR / 'system_survival_by_vendor.png'
    )

    # Summary
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nGenerated files:")
    print(f"  - {OUTPUT_DIR / 'system_survival.png'}")
    print(f"  - {OUTPUT_DIR / 'system_survival_by_vendor.png'}")
    print()


if __name__ == "__main__":
    main()
