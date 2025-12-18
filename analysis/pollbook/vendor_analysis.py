#!/usr/bin/env python3
"""
Analyze poll book vendors and equipment models in the Verifier data.
Generates a concise text report with source data examples.
"""

import pandas as pd
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Years to analyze
YEARS = range(2006, 2028, 2)

def load_machines_data(year):
    """Load machines data for a given year."""
    filepath = f'data/extracted/{year}_verifier-machines.csv'
    try:
        df = pd.read_csv(filepath, skiprows=1, index_col=False)
        return df, filepath
    except FileNotFoundError:
        return None, None

def analyze_pollbook_variety():
    """Analyze poll book vendor and equipment variety across all years."""

    # Track vendor-product combinations with source examples
    vendor_product_examples = {}  # (vendor, product) -> (year, filepath, row_data)
    model_to_vendors = defaultdict(set)
    vendor_to_equipment_types = defaultdict(set)

    print("Loading poll book data across all years...")

    for year in YEARS:
        df, filepath = load_machines_data(year)
        if df is None:
            continue

        # Filter for poll book equipment
        pollbook_df = df[df['Equipment Type'].str.contains('Poll Book', case=False, na=False)]

        if len(pollbook_df) == 0:
            continue

        print(f"  {year}: {len(pollbook_df)} poll book records found")

        # Extract unique vendors and models with examples
        for _, row in pollbook_df.iterrows():
            equipment_type = row['Equipment Type']
            vendor = row['Manufacturer']
            model = row['Model']

            # Skip if missing vendor
            if pd.isna(vendor) or vendor == '':
                continue

            # Normalize model
            model_str = str(model) if pd.notna(model) and model != '' else '[blank]'

            # Store example if not already captured
            key = (vendor, model_str)
            if key not in vendor_product_examples:
                vendor_product_examples[key] = (year, filepath, row)

            model_to_vendors[model_str].add(vendor)
            vendor_to_equipment_types[vendor].add(equipment_type)

    return {
        'vendor_product_examples': vendor_product_examples,
        'model_to_vendors': model_to_vendors,
        'vendor_to_equipment_types': vendor_to_equipment_types
    }

def generate_text_report(data, output_path):
    """Generate a concise text report with source data."""

    vendor_product_examples = data['vendor_product_examples']
    model_to_vendors = data['model_to_vendors']
    vendor_to_equipment_types = data['vendor_to_equipment_types']

    # Group by vendor
    vendor_products = defaultdict(list)
    for (vendor, product), example in vendor_product_examples.items():
        vendor_products[vendor].append((product, example))

    # Find multi-vendor products
    multi_vendor_products = {model: vendors for model, vendors in model_to_vendors.items()
                            if len(vendors) > 1}

    with open(output_path, 'w') as f:
        # Header
        f.write("POLL BOOK VENDOR AND EQUIPMENT ANALYSIS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*80 + "\n\n")

        # Summary
        f.write("SUMMARY\n")
        f.write("-"*80 + "\n")
        f.write(f"Total vendors: {len(vendor_products)}\n")
        f.write(f"Total products: {len(vendor_product_examples)}\n")
        f.write(f"Products appearing with multiple vendors: {len(multi_vendor_products)}\n")
        f.write("\n\n")

        # Products appearing with multiple vendors (if any)
        if multi_vendor_products:
            f.write("PRODUCTS APPEARING WITH MULTIPLE VENDORS\n")
            f.write("-"*80 + "\n")
            for product, vendors in sorted(multi_vendor_products.items()):
                f.write(f"\n{product}:\n")
                for vendor in sorted(vendors):
                    f.write(f"  - {vendor}\n")
            f.write("\n\n")

        # All vendors and products with source data
        f.write("ALL VENDORS AND PRODUCTS\n")
        f.write("-"*80 + "\n\n")

        for vendor in sorted(vendor_products.keys()):
            products = vendor_products[vendor]
            eq_types = vendor_to_equipment_types[vendor]

            f.write(f"{vendor} [{', '.join(sorted(eq_types))}]\n")
            f.write(f"  Products: {len(products)}\n\n")

            for product, (year, filepath, row) in sorted(products):
                f.write(f"  • {product}\n")
                f.write(f"    Source: {Path(filepath).name} ({year})\n")
                f.write(f"    Example: FIPS={row['FIPS code']}, Jurisdiction={row['Jurisdiction']}\n")
                f.write(f"             Equipment Type={row['Equipment Type']}\n")
                f.write(f"             Manufacturer={row['Manufacturer']}, Model={row['Model']}\n")
                f.write("\n")

            f.write("\n")

    print(f"\n✓ Report generated: {output_path}")

def main():
    """Main execution function."""
    print("="*80)
    print("POLL BOOK VENDOR AND EQUIPMENT ANALYSIS")
    print("="*80)
    print()

    # Analyze data
    data = analyze_pollbook_variety()

    # Generate report
    output_path = Path(__file__).parent / 'pollbook_vendor_equipment_report.txt'
    generate_text_report(data, output_path)

    print()
    print("="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nReport: {output_path}")
    print(f"Total vendors: {len(data['vendor_to_equipment_types'])}")
    print(f"Total vendor-product combinations: {len(data['vendor_product_examples'])}")
    print(f"Products with multiple vendors: {sum(1 for v in data['model_to_vendors'].values() if len(v) > 1)}")

if __name__ == '__main__':
    main()
