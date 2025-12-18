#!/usr/bin/env python3
"""
Shared utility functions for time series analysis of voting equipment data.

This module provides helper functions for loading, processing, and analyzing
the condensed jurisdiction data from 2006-2026.
"""

import pandas as pd
from pathlib import Path


def load_all_years(data_dir='data/processed/jurisdictions'):
    """
    Load all 11 years (2006-2026, even years) into a dict of DataFrames.

    Args:
        data_dir: Directory containing the condensed CSV files

    Returns:
        Dictionary mapping year (int) to DataFrame
    """
    years = range(2006, 2027, 2)
    dfs = {}

    for year in years:
        df = pd.read_csv(
            f'{data_dir}/{year}_verifier-jurisdictions-condensed.csv',
            skiprows=1  # Skip description header
        )
        dfs[year] = df

    return dfs


def load_year(year, data_dir='data/processed/jurisdictions'):
    """
    Load a single year's data.

    Args:
        year: Year to load (2006-2026, even years only)
        data_dir: Directory containing the condensed CSV files

    Returns:
        DataFrame for the specified year
    """
    if year % 2 != 0 or year < 2006 or year > 2026:
        raise ValueError(f"Year must be an even year between 2006 and 2026, got {year}")

    return pd.read_csv(
        f'{data_dir}/{year}_verifier-jurisdictions-condensed.csv',
        skiprows=1
    )


def get_vendor_from_equipment(equipment_summary):
    """
    Extract vendor name from equipment summary string.

    Handles special cases like:
    - "ES&S DS200" -> "ES&S"
    - "Dominion ImageCast" -> "Dominion"
    - "Dominion / AccuVote" -> "Dominion"
    - "Hand Count" -> "Hand Count"
    - "Multiple Vendors" -> "Multiple Vendors"

    Args:
        equipment_summary: Equipment summary string from condensed data

    Returns:
        Vendor name (string) or None if empty/invalid
    """
    # Handle null/empty values
    if pd.isna(equipment_summary) or equipment_summary == '':
        return None

    # Handle special complete values
    if equipment_summary == 'Hand Count':
        return 'Hand Count'
    if equipment_summary == 'Multiple Vendors':
        return 'Multiple Vendors'

    # Handle vendor / product pattern (e.g., "Dominion / AccuVote")
    if '/' in equipment_summary:
        return equipment_summary.split('/')[0].strip()

    # Extract first word as vendor (e.g., "ES&S DS200" -> "ES&S")
    parts = equipment_summary.split()
    if len(parts) > 0:
        return parts[0]

    return None


def calculate_market_share(df, column='Equipment Summary', year=None):
    """
    Calculate market share percentages for vendors.

    Args:
        df: DataFrame with equipment data
        column: Column name to analyze (default: 'Equipment Summary')
        year: Optional year for labeling (included in result)

    Returns:
        Series with vendor counts and percentages, or DataFrame if year specified
    """
    # Extract vendor from column
    vendors = df[column].apply(get_vendor_from_equipment)

    # Count by vendor
    vendor_counts = vendors.value_counts()

    # Calculate percentages
    vendor_pct = (vendor_counts / len(df) * 100).round(2)

    if year is not None:
        # Return DataFrame with both counts and percentages
        result = pd.DataFrame({
            'Count': vendor_counts,
            'Percentage': vendor_pct,
            'Year': year
        })
        return result
    else:
        return vendor_pct


def create_time_series_df(dfs, column='Equipment Summary', extract_fn=None):
    """
    Create a wide-format DataFrame with years as columns.

    Args:
        dfs: Dictionary of DataFrames by year
        column: Column to extract from each year's data
        extract_fn: Optional function to apply to column values (e.g., get_vendor_from_equipment)

    Returns:
        DataFrame with index as unique values and columns as years
    """
    series_by_year = {}

    for year, df in dfs.items():
        if extract_fn:
            values = df[column].apply(extract_fn)
        else:
            values = df[column]

        # Count occurrences
        counts = values.value_counts()
        series_by_year[year] = counts

    # Combine into wide DataFrame
    result = pd.DataFrame(series_by_year)

    # Fill NaN with 0 (vendor not present in that year)
    result = result.fillna(0)

    return result


def merge_years_on_fips(dfs, columns=None):
    """
    Merge all years on FIPS code for jurisdiction tracking.

    Args:
        dfs: Dictionary of DataFrames by year
        columns: List of columns to include (default: all columns)
                 If None, includes all columns except metadata

    Returns:
        DataFrame with FIPS code as index and columns for each year
    """
    if columns is None:
        # Default columns to track
        columns = ['Equipment Summary', 'Poll Book Status']

    # Start with first year
    first_year = min(dfs.keys())
    merged = dfs[first_year][['FIPS code', 'State', 'Jurisdiction'] + columns].copy()

    # Rename columns with year suffix
    rename_dict = {col: f'{col}_{first_year}' for col in columns}
    merged = merged.rename(columns=rename_dict)

    # Merge subsequent years
    for year in sorted(dfs.keys())[1:]:
        year_data = dfs[year][['FIPS code'] + columns].copy()

        # Rename columns with year suffix
        rename_dict = {col: f'{col}_{year}' for col in columns}
        year_data = year_data.rename(columns=rename_dict)

        # Outer join to include all jurisdictions
        merged = merged.merge(year_data, on='FIPS code', how='outer')

    return merged


def get_summary_stats(dfs):
    """
    Get summary statistics across all years.

    Args:
        dfs: Dictionary of DataFrames by year

    Returns:
        DataFrame with summary statistics by year
    """
    stats = []

    for year, df in sorted(dfs.items()):
        vendors = df['Equipment Summary'].apply(get_vendor_from_equipment)

        stat = {
            'Year': year,
            'Total Jurisdictions': len(df),
            'Unique Vendors': vendors.nunique(),
            'Hand Count': (vendors == 'Hand Count').sum(),
            'Multiple Vendors': (vendors == 'Multiple Vendors').sum(),
            'Paper Poll Books': (df['Poll Book Status'] == 'Paper').sum(),
            'Electronic Poll Books': (
                (df['Poll Book Status'] == 'In-House') |
                (~df['Poll Book Status'].isin(['Paper', '', None]))
            ).sum()
        }
        stats.append(stat)

    return pd.DataFrame(stats)
