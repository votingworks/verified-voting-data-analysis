#!/usr/bin/env python3
"""
Run the complete data processing pipeline.

This script executes all data processing and analysis scripts in order:
0. Extract verifier data from zip files and process HAVA funding HTML
1. Condense jurisdictions for all years (2006-2026)
2. Generate summary reports for all years
3. Generate turnover analysis
4. Generate state-level uniformity data for all years
5. Run all data quality tools and equipment analysis

Excludes: pollbook scripts (data fetching scripts only run on saved data)

This helps catch breaking changes when modifying upstream components.
"""

import subprocess
import sys
from pathlib import Path

YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]


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


def run_all():
    """Run the complete data processing pipeline."""
    print("=" * 80)
    print("RUNNING COMPLETE DATA PROCESSING PIPELINE")
    print("=" * 80)
    print()

    total_years = len(YEARS)
    failed_steps = []

    # Phase 0: Extract and process source data
    print("Phase 0: Extracting and processing source data...")
    print("-" * 80)

    success = run_command(
        "python3 extract_zips.py",
        "Extracting verifier zip files"
    )
    if not success:
        failed_steps.append(("Zip extraction", "extract_zips.py"))

    success = run_command(
        "python3 scrape_eac_hava_funding.py",
        "Processing HAVA funding HTML"
    )
    if not success:
        failed_steps.append(("HAVA funding scrape", "scrape_eac_hava_funding.py"))
    print()

    # Phase 1: Condense all years
    print(f"Phase 1: Condensing jurisdiction data for {total_years} years...")
    print("-" * 80)

    for i, year in enumerate(YEARS, 1):
        print(f"[{i}/{total_years}] {year}")
        success = run_command(
            f"python3 condense_jurisdictions.py {year}",
            "  Condensing"
        )
        if not success:
            failed_steps.append((f"{year} condensing", "condense_jurisdictions.py"))
        print()

    # Phase 2: Generate summary reports for all years
    print()
    print(f"Phase 2: Generating summary reports for {total_years} years...")
    print("-" * 80)

    for i, year in enumerate(YEARS, 1):
        print(f"[{i}/{total_years}] {year}")
        success = run_command(
            f"python3 generate_summary_report.py {year}",
            "  Generating report"
        )
        if not success:
            failed_steps.append((f"{year} summary report", "generate_summary_report.py"))
        print()

    # Phase 3: Generate turnover analysis
    print()
    print("Phase 3: Generating turnover analysis...")
    print("-" * 80)
    success = run_command(
        "python3 identify_voting_equipment_turnover.py",
        "Analyzing equipment turnovers"
    )
    if not success:
        failed_steps.append(("Turnover analysis", "identify_voting_equipment_turnover.py"))
    print()

    # Phase 4: Generate state-level uniformity data
    print()
    print(f"Phase 4: Generating state-level uniformity data for {total_years} years...")
    print("-" * 80)

    for i, year in enumerate(YEARS, 1):
        print(f"[{i}/{total_years}] {year}")
        success = run_command(
            f"python3 condense_to_state_level.py {year}",
            "  Condensing to state-level"
        )
        if not success:
            failed_steps.append((f"{year} state-level condensing", "condense_to_state_level.py"))
        print()

    # Phase 5: Run data quality tools
    print()
    print("Phase 5: Running data quality tools...")
    print("-" * 80)

    data_quality_scripts = [
        ("data_quality_tools/machines/find_duplicate_equipment.py", "Finding duplicate equipment"),
        ("data_quality_tools/jurisdiction_condensed_values/report_unique_condensed_values.py", "Reporting unique condensed values"),
        ("data_quality_tools/jurisdiction_condensed_values/report_anomaly_details.py", "Reporting anomaly details"),
        ("data_quality_tools/jurisdiction_trends/analyze_jurisdiction_trends.py", "Analyzing jurisdiction trends"),
        ("data_quality_tools/turnover/analyze_within_system_patterns.py", "Analyzing within-system turnover patterns"),
        ("data_quality_tools/pollbook_vendor_analysis/analyze_and_report.py", "Analyzing pollbook vendor patterns"),
        ("data_quality_tools/dres/analyze_dre_equipment.py", "Analyzing DRE equipment distribution"),
        ("equipment_analysis/analyze_lifecycle_distribution.py", "Analyzing equipment lifecycle distribution"),
        ("equipment_analysis/analyze_vendor_turnover.py", "Analyzing vendor turnover patterns"),
        ("equipment_analysis/analyze_vendor_market_share.py", "Analyzing vendor market share over time"),
        ("equipment_analysis/analyze_voting_vendor_retention.py", "Analyzing voting system vendor retention"),
        ("pollbook/analyze_pollbook_adoption_timeseries.py", "Analyzing poll book adoption timeseries"),
        ("pollbook/analyze_pollbook_by_size.py", "Analyzing poll book adoption by jurisdiction size"),
        ("pollbook/analyze_pollbook_vendor_share_timeseries.py", "Analyzing poll book vendor market share"),
        ("pollbook/analyze_vendor_retention.py", "Analyzing poll book vendor retention"),
    ]

    for script_path, description in data_quality_scripts:
        # Check if script exists
        if not Path(script_path).exists():
            print(f"  {description}... ⊘ SKIPPED (not found)")
            continue

        success = run_command(
            f"python3 {script_path}",
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
        print(f"  - Extracted verifier data for {total_years} years")
        print(f"  - {total_years} condensed CSV files")
        print(f"  - {total_years} summary reports")
        print(f"  - {total_years} state-level uniformity CSV files")
        print(f"  - Turnover analysis files:")
        print(f"    • data/between_system_turnovers.csv")
        print(f"    • data/within_system_turnovers.csv")
        print(f"  - Data quality reports in data_quality_tools/")
        print(f"  - Equipment analysis charts in equipment_analysis/")
        print(f"  - Poll book analysis charts in pollbook/")
        return 0
    else:
        print(f"⚠ Pipeline completed with {len(failed_steps)} failures:")
        for description, script in failed_steps:
            print(f"  - {description} ({script})")
        print()
        print("Fix the errors above and re-run the pipeline.")
        return 1


if __name__ == "__main__":
    exit_code = run_all()
    sys.exit(exit_code)
