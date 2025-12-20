#!/usr/bin/env python3
"""
Generate Kaplan-Meier survival curves for equipment models.

Properly handles right-censored data (equipment still in use) to estimate
survival probabilities and median lifetime.

Supports multiple models on the same chart for comparison.

Usage:
    python3 model_survival_analysis.py "DS200"
    python3 model_survival_analysis.py "DS200" "AccuVote OS"
    python3 model_survival_analysis.py "ExpressVote" "AutoMark" "ImageCast"

Args:
    models: One or more model names (case-insensitive substring match)

Output: outputs/figures/equipment/model_lifetime/survival_{models}.png
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


def create_survival_curves(models_data, output_path):
    """
    Create Kaplan-Meier survival curves for multiple models on one chart.

    Args:
        models_data: List of (model_name, records) tuples
        output_path: Path to save chart

    Returns:
        dict: {model_name: median_survival}
    """
    # Colors for different models
    colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#a65628']

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7))

    median_results = {}
    max_duration = 0
    total_n = 0

    for i, (model_name, records) in enumerate(models_data):
        color = colors[i % len(colors)]

        # Prepare data for survival analysis
        durations = np.array([r['Length_Of_Use'] for r in records])
        event_observed = np.array([r['Last_Year'] < 2026 for r in records])  # True = retired

        max_duration = max(max_duration, durations.max())

        # Calculate stats
        n_total = len(records)
        n_retired = event_observed.sum()
        total_n += n_total

        # Fit Kaplan-Meier model
        kmf = KaplanMeierFitter()
        kmf.fit(durations, event_observed=event_observed, label=f'{model_name} (n={n_total:,})')

        # Get median survival
        median_survival = kmf.median_survival_time_
        median_results[model_name] = median_survival

        # Plot survival curve with confidence interval
        kmf.plot_survival_function(ax=ax, ci_show=True, color=color, linewidth=2)

    # Add horizontal line at 50% survival
    ax.axhline(y=0.5, color='gray', linestyle=':', linewidth=1, alpha=0.5)

    # Labels and title
    ax.set_xlabel('Years in Service', fontsize=13, fontweight='bold')
    ax.set_ylabel('Survival Probability', fontsize=13, fontweight='bold')

    if len(models_data) == 1:
        title = f'Equipment Survival Curve: {models_data[0][0]}'
    else:
        title = 'Equipment Survival Curves by Model'
    ax.set_title(f'{title}\n(n={total_n:,} total)', fontsize=15, fontweight='bold', pad=20)

    # Set axis limits
    ax.set_ylim(0, 1.05)
    ax.set_xlim(0, max_duration + 2)

    # Grid
    ax.grid(axis='both', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # Legend
    ax.legend(loc='upper right', fontsize=10)

    # Layout
    plt.tight_layout()

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return median_results


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
        print("Usage: python3 model_survival_analysis.py <model1> [model2] [model3] ...")
        print("Example: python3 model_survival_analysis.py 'DS200'")
        print("Example: python3 model_survival_analysis.py 'DS200' 'AccuVote OS'")
        return 1

    model_patterns = sys.argv[1:]
    print(f"Model patterns: {', '.join(model_patterns)}")
    print()

    # Load data
    print("Loading machine_lifetimes.csv...")
    records = load_machine_lifetimes()
    print(f"✓ Loaded {len(records):,} total records")
    print()

    # Filter for each model
    models_data = []
    for model_pattern in model_patterns:
        print(f"Filtering for model matching '{model_pattern}'...")
        filtered = filter_by_model(records, model_pattern)

        if not filtered:
            print(f"  No matching records found for '{model_pattern}'.")
            continue

        # Show which models matched
        matched_models = sorted(set(r['Model'] for r in filtered))
        print(f"  ✓ Found {len(filtered):,} records")
        print(f"    Matched: {', '.join(matched_models[:5])}" +
              (f" (+{len(matched_models)-5} more)" if len(matched_models) > 5 else ""))

        # Calculate stats
        retired = [r for r in filtered if r['Last_Year'] < 2026]
        still_in_use = [r for r in filtered if r['Last_Year'] == 2026]
        print(f"    Retired: {len(retired):,}, Still in use: {len(still_in_use):,}")

        models_data.append((model_pattern, filtered))

    if not models_data:
        print("No valid models found.")
        return 1

    print()

    # Generate output filename
    if len(model_patterns) == 1:
        model_slug = slugify(model_patterns[0])
    else:
        model_slug = '_vs_'.join(slugify(m) for m in model_patterns)
    output_path = OUTPUT_DIR / f'survival_{model_slug}.png'

    print("Fitting Kaplan-Meier survival models...")
    median_results = create_survival_curves(models_data, output_path)
    print(f"✓ Survival curve saved to {output_path}")

    # Print summary
    print()
    print("Survival Analysis Results:")
    for model, median in median_results.items():
        if not np.isnan(median) and not np.isinf(median):
            print(f"  - {model}: median survival = {median:.0f} years")
        else:
            print(f"  - {model}: median not yet reached (>50% still in use)")

    print()
    print("=" * 80)
    print("✓ SURVIVAL ANALYSIS COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
