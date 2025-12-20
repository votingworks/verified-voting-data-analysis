#!/usr/bin/env python3
"""
Generate Kaplan-Meier survival curves for equipment models.

Properly handles right-censored data (equipment still in use) to estimate
survival probabilities and median lifetime.

Usage:
    python3 model_survival_analysis.py "DS200"
    python3 model_survival_analysis.py "AccuVote OS"

Args:
    model: Model name (case-insensitive substring match)

Output: outputs/figures/equipment/model_lifetime/survival_{model_slug}.png
"""

import csv
import sys
import re
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from lifelines import KaplanMeierFitter

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


def create_survival_curve(records, model_name, output_path):
    """
    Create Kaplan-Meier survival curve.

    Args:
        records: Filtered list of machine use records
        model_name: Model name for title
        output_path: Path to save chart
    """
    # Prepare data for survival analysis
    durations = np.array([r['Length_Of_Use'] for r in records])
    event_observed = np.array([r['Last_Year'] < 2026 for r in records])  # True = retired

    # Calculate censoring stats
    n_total = len(records)
    n_retired = event_observed.sum()
    n_censored = n_total - n_retired
    pct_censored = (n_censored / n_total) * 100

    # Fit Kaplan-Meier model
    kmf = KaplanMeierFitter()
    kmf.fit(durations, event_observed=event_observed, label=model_name)

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7))

    # Plot survival curve with confidence interval
    kmf.plot_survival_function(ax=ax, ci_show=True, color='steelblue', linewidth=2)

    # Get median survival (may be NaN if not enough events)
    median_survival = kmf.median_survival_time_

    # Add vertical line at median if it exists
    if not np.isnan(median_survival) and not np.isinf(median_survival):
        ax.axvline(x=median_survival, color='darkorange', linestyle='--', linewidth=1.5,
                   label=f'Median: {median_survival:.0f} years')
        ax.axhline(y=0.5, color='gray', linestyle=':', linewidth=1, alpha=0.5)

    # Labels and title
    ax.set_xlabel('Years in Service', fontsize=13, fontweight='bold')
    ax.set_ylabel('Survival Probability', fontsize=13, fontweight='bold')

    title = f'Equipment Survival Curve: {model_name}'
    subtitle = f'n={n_total:,} ({n_retired:,} retired, {n_censored:,} censored [{pct_censored:.0f}%])'
    ax.set_title(f'{title}\n{subtitle}', fontsize=15, fontweight='bold', pad=20)

    # Set axis limits
    ax.set_ylim(0, 1.05)
    ax.set_xlim(0, max(durations) + 2)

    # Grid
    ax.grid(axis='both', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # Add median annotation
    if not np.isnan(median_survival) and not np.isinf(median_survival):
        ax.annotate(f'Median survival: {median_survival:.0f} years',
                    xy=(median_survival, 0.5),
                    xytext=(median_survival + 2, 0.6),
                    fontsize=11, fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color='darkorange'),
                    color='darkorange')
    else:
        # Median not reached
        ax.annotate('Median not yet reached\n(>50% still in use)',
                    xy=(0.95, 0.95), xycoords='axes fraction',
                    fontsize=11, fontweight='bold',
                    ha='right', va='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Add survival probabilities at key time points
    time_points = [10, 15, 20]
    survival_text = []
    for t in time_points:
        if t <= max(durations):
            # Get survival probability at time t
            surv_prob = kmf.predict(t)
            survival_text.append(f'{t}yr: {surv_prob:.0%}')

    if survival_text:
        ax.text(0.02, 0.02, 'Survival at: ' + ', '.join(survival_text),
                transform=ax.transAxes, fontsize=10,
                verticalalignment='bottom',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

    # Legend
    ax.legend(loc='upper right', fontsize=10)

    # Layout
    plt.tight_layout()

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return median_survival


def slugify(text):
    """Convert text to filename-safe slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text.strip('_')


def main():
    """Main execution function."""
    print("=" * 80)
    print("EQUIPMENT SURVIVAL ANALYSIS (Kaplan-Meier)")
    print("=" * 80)
    print()

    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python3 model_survival_analysis.py <model>")
        print("Example: python3 model_survival_analysis.py 'DS200'")
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
        print("No matching records found. Try a different model name or year.")
        return 1

    # Show which models matched
    matched_models = sorted(set(r['Model'] for r in filtered))
    print(f"  Matched models: {', '.join(matched_models)}")

    # Calculate stats
    retired = [r for r in filtered if r['Last_Year'] < 2026]
    still_in_use = [r for r in filtered if r['Last_Year'] == 2026]
    print(f"  Retired: {len(retired):,}")
    print(f"  Still in use (censored): {len(still_in_use):,}")
    print()

    # Generate survival curve
    model_slug = slugify(model_pattern)
    output_path = OUTPUT_DIR / f'survival_{model_slug}.png'

    print("Fitting Kaplan-Meier survival model...")
    median_survival = create_survival_curve(filtered, model_pattern, output_path)
    print(f"✓ Survival curve saved to {output_path}")

    # Print summary
    print()
    print("Survival Analysis Results:")
    print(f"  - Sample size: {len(filtered):,}")
    print(f"  - Events (retirements): {len(retired):,}")
    print(f"  - Censored (still in use): {len(still_in_use):,} ({len(still_in_use)/len(filtered)*100:.0f}%)")

    if not np.isnan(median_survival) and not np.isinf(median_survival):
        print(f"  - Median survival time: {median_survival:.0f} years")
    else:
        print(f"  - Median survival time: Not yet reached (>50% still in use)")

    print()
    print("=" * 80)
    print("✓ SURVIVAL ANALYSIS COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
