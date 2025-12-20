#!/usr/bin/env python3
"""
Run the complete data processing pipeline.

This script executes all data processing and analysis scripts in order:
0. Extract verifier data from zip files and process HAVA funding HTML
1. Generate machine lifetimes from extracted data
2. Generate jurisdictions time series
3. Generate jurisdiction transitions
4. Run all analysis scripts

Excludes: pollbook scripts (data fetching scripts only run on saved data)

This helps catch breaking changes when modifying upstream components.
"""

import argparse
import subprocess
import sys
from pathlib import Path

YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]

# Notable models for model-specific analysis
NOTABLE_MODELS = [
    'ExpressVote',
    'AutoMark',
    'Poll Pad',
    'ExpressPoll',
    'AccuVote TS',
    'AVC Edge',
    'DS200',
    'AccuVote OS',
    'Model 100',
    'ImageCast Precinct',
]


def run_command(command, description, show_output=False):
    """Run a command and handle errors."""
    print(f"  {description}...", end=" ", flush=True)
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=not show_output,
            text=True,
            check=True
        )
        print("✓")
        if show_output and result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ FAILED")
        if not show_output:
            print(f"    Error: {e.stderr}")
        return False


def run_all(analysis_only=False):
    """Run the complete data processing pipeline."""
    print("=" * 80)
    if analysis_only:
        print("RUNNING ANALYSIS SCRIPTS ONLY")
    else:
        print("RUNNING COMPLETE DATA PROCESSING PIPELINE")
    print("=" * 80)
    print()

    failed_steps = []

    if not analysis_only:
        # Phase 0: Extract and process source data
        print("Phase 0: Extracting and processing source data...")
        print("-" * 80)

        success = run_command(
            "python3 etl/extract_zips.py",
            "Extracting verifier zip files"
        )
        if not success:
            failed_steps.append(("Zip extraction", "etl/extract_zips.py"))

        success = run_command(
            "python3 etl/scrape_eac_hava_funding.py",
            "Processing HAVA funding HTML"
        )
        if not success:
            failed_steps.append(("HAVA funding scrape", "etl/scrape_eac_hava_funding.py"))
        print()

        # Phase 1: Generate core data files
        print("Phase 1: Generating core data files...")
        print("-" * 80)

        success = run_command(
            "python3 etl/generate_machine_lifetimes.py",
            "Generating machine lifetimes"
        )
        if not success:
            failed_steps.append(("Machine lifetimes", "etl/generate_machine_lifetimes.py"))

        success = run_command(
            "python3 etl/generate_jurisdictions_time_series.py",
            "Generating jurisdictions time series"
        )
        if not success:
            failed_steps.append(("Jurisdictions time series", "etl/generate_jurisdictions_time_series.py"))

        success = run_command(
            "python3 etl/generate_jurisdiction_transitions.py",
            "Generating jurisdiction transitions"
        )
        if not success:
            failed_steps.append(("Jurisdiction transitions", "etl/generate_jurisdiction_transitions.py"))

        success = run_command(
            "python3 etl/generate_pollbook_transitions.py",
            "Generating pollbook transitions"
        )
        if not success:
            failed_steps.append(("Pollbook transitions", "etl/generate_pollbook_transitions.py"))
        print()

    # Phase 2: Run analysis scripts
    print("Phase 2: Running analysis scripts...")
    print("-" * 80)

    analysis_scripts = [
        # Trends analysis
        ("analysis/trends/duplicate_equipment.py", "Finding duplicate equipment"),
        ("analysis/trends/jurisdiction_trends.py", "Analyzing jurisdiction trends"),
        ("analysis/trends/machine_lifetimes_analysis.py", "Analyzing machine lifetimes"),
        ("analysis/trends/jurisdiction_transition_analysis.py", "Generating transition analysis report"),
        ("analysis/trends/marking_method_sankey.py 2010 2026", "Generating marking method sankey diagram"),

        # Equipment analysis
        ("analysis/equipment/adoption_time_series.py", "Analyzing voting equipment adoption timeseries"),
        ("analysis/equipment/vendor_turnover.py", "Analyzing vendor turnover patterns"),
        ("analysis/equipment/vendor_market_share.py", "Analyzing vendor market share over time"),
        ("analysis/equipment/vendor_retention.py", "Analyzing voting system vendor retention"),

        # Poll book analysis
        ("analysis/pollbook/adoption_time_series.py", "Analyzing poll book adoption timeseries"),
        ("analysis/pollbook/by_jurisdiction_size.py", "Analyzing poll book adoption by jurisdiction size"),
        ("analysis/pollbook/vendor_market_share.py", "Analyzing poll book vendor market share"),
        ("analysis/pollbook/vendor_retention.py", "Analyzing poll book vendor retention"),
        ("analysis/pollbook/vendor_turnover.py", "Analyzing poll book vendor turnover"),
    ]

    # Add model-specific analysis for notable models
    for model in NOTABLE_MODELS:
        analysis_scripts.append(
            (f'analysis/equipment/model_introduction.py "{model}"', f"Model introduction: {model}")
        )

    # Add model survival analysis - grouped comparisons
    model_survival_groups = [
        (['AutoMark', 'ExpressVote'], 'BMDs: AutoMark vs ExpressVote'),
        (['Poll Pad', 'ExpressPoll'], 'E-Pollbooks: Poll Pad vs ExpressPoll'),
        (['AccuVote TS', 'AVC Edge'], 'DREs: AccuVote TS vs AVC Edge'),
        (['DS200', 'AccuVote OS', 'Model 100', 'ImageCast Precinct'], 'Hand-Fed Scanners'),
    ]
    for models, description in model_survival_groups:
        model_args = ' '.join(f'"{m}"' for m in models)
        analysis_scripts.append(
            (f'analysis/equipment/model_survival_analysis.py {model_args}', f"Model survival: {description}")
        )

    # Add equipment type survival analysis (DRE vs Hand-Fed Optical Scanner)
    analysis_scripts.append(
        ('analysis/equipment/equipment_type_survival_analysis.py "DRE" "Hand-Fed Optical Scanner"',
         "Equipment type survival: DRE vs Hand-Fed Optical Scanner")
    )

    # Add state equipment recency analysis
    analysis_scripts.append(
        ("analysis/equipment/state_recency.py", "Analyzing state equipment recency")
    )

    # Note: The following scripts require command-line arguments and are not included:
    # - analysis/trends/state_uniformity.py <year>
    # - analysis/trends/pollbook_uniformity_trends.py (requires state-level data)

    for script_cmd, description in analysis_scripts:
        # Check if script exists (handle commands with arguments)
        script_path = script_cmd.split()[0]
        if not Path(script_path).exists():
            print(f"  {description}... ⊘ SKIPPED (not found)")
            continue

        success = run_command(
            f"python3 {script_cmd}",
            description
        )
        if not success:
            failed_steps.append((description, script_path))
        print()

    # Summary
    print()
    print("=" * 80)
    print("PIPELINE SUMMARY")
    print("=" * 80)

    if not failed_steps:
        print(f"✓ Successfully completed all pipeline steps!")
        print()
        print("Generated outputs:")
        print(f"  - Extracted verifier data for {len(YEARS)} years")
        print(f"  - Machine lifetimes: data/processed/machine_lifetimes.csv")
        print(f"  - Jurisdictions time series: data/processed/jurisdictions_time_series.csv")
        print(f"  - Jurisdiction transitions: data/processed/jurisdiction_transitions.csv")
        print(f"  - Pollbook transitions: data/processed/pollbook_transitions.csv")
        print(f"  - Analysis reports in outputs/reports/")
        print(f"  - Charts in outputs/figures/")
        return 0
    else:
        print(f"⚠ Pipeline completed with {len(failed_steps)} failures:")
        for description, script in failed_steps:
            print(f"  - {description} ({script})")
        print()
        print("Fix the errors above and re-run the pipeline.")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the data processing pipeline")
    parser.add_argument(
        '--analysis-only', '-a',
        action='store_true',
        help='Skip ETL scripts and run analysis only (assumes data already exists)'
    )
    args = parser.parse_args()

    exit_code = run_all(analysis_only=args.analysis_only)
    sys.exit(exit_code)
