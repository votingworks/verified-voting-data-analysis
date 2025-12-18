#!/usr/bin/env python3
"""
Vendor lock-in analysis for poll book market (2006-2026).

Analyzes switching behavior and retention rates for major commercial
poll book vendors: KNOWiNK, ES&S, Tenex, and Other Electronic.

Focuses on commercial vendor lock-in by excluding Paper→Electronic adoption transitions.

Outputs:
1. Retention rates over time (CSV + line chart)
2. Switching matrix (CSV + heatmap)
3. Average tenure (CSV + bar chart)
4. Survival curves (CSV + Kaplan-Meier chart)
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
from utilities import load_all_years, merge_years_on_fips

print("="*80)
print("VENDOR LOCK-IN ANALYSIS: POLL BOOK MARKET (2006-2026)")
print("="*80)

# ============================================================================
# SECTION 1: DATA PREPARATION
# ============================================================================

print("\n[1/6] Loading and preparing data...")

# 1.1 Load all years
dfs = load_all_years()
print(f"   Loaded {len(dfs)} years of data (2006-2026)")

# 1.2 Merge on FIPS code
merged = merge_years_on_fips(dfs, columns=['Poll Book Status'])
print(f"   Merged {len(merged)} jurisdictions across all years")

# 1.3 Vendor categorization function
def categorize_pollbook_vendor(status):
    """Normalize poll book status into vendor categories."""
    if pd.isna(status) or status == '' or status.strip() == '' or status == 'Data Unavailable':
        return None

    status_clean = status.strip()

    # Non-commercial
    if status_clean == 'Paper':
        return 'Paper'
    if status_clean == 'In-House':
        return 'In-House'

    # Major commercial vendors (focus of lock-in analysis)
    if 'KNOWiNK' in status_clean or 'Knowink' in status_clean:
        return 'KNOWiNK'
    if 'ES&S' in status_clean:
        return 'ES&S'
    if 'Tenex' in status_clean:
        return 'Tenex'

    # All other electronic vendors grouped together
    if status_clean in ['Hand Count', 'Optical Scan', 'Data Unavailable']:
        return None

    # Everything else is "Other Electronic"
    return 'Other Electronic'

# 1.4 Apply vendor categorization to all years
years = list(range(2006, 2027, 2))
for year in years:
    col_name = f'Poll Book Status_{year}'
    if col_name in merged.columns:
        merged[f'Vendor_{year}'] = merged[col_name].apply(categorize_pollbook_vendor)

print(f"   Categorized vendors for all years")

# Save vendor timeline
vendor_cols = ['FIPS code', 'State', 'Jurisdiction'] + [f'Vendor_{y}' for y in years]
vendor_timeline = merged[vendor_cols].copy()
vendor_timeline.to_csv('analysis_output/data/pollbook_vendor_timeline_all_jurisdictions.csv', index=False)
print(f"   Saved vendor timeline to analysis_output/data/vendor_timeline_all_jurisdictions.csv")

# 1.5 Detect vendor switches
print("\n   Detecting vendor switches...")
year_pairs = [(years[i], years[i+1]) for i in range(len(years)-1)]

switches = []
for idx, row in merged.iterrows():
    fips = row['FIPS code']

    for year_from, year_to in year_pairs:
        vendor_from = row[f'Vendor_{year_from}']
        vendor_to = row[f'Vendor_{year_to}']

        # Only track if both years have valid vendor data
        if vendor_from is not None and vendor_to is not None:
            is_switch = (vendor_from != vendor_to)
            switches.append({
                'FIPS code': fips,
                'State': row['State'],
                'Jurisdiction': row['Jurisdiction'],
                'year_from': year_from,
                'year_to': year_to,
                'vendor_from': vendor_from,
                'vendor_to': vendor_to,
                'is_switch': is_switch
            })

switches_df = pd.DataFrame(switches)

# Filter to commercial vendor analysis (vendor_from must be commercial)
commercial_vendors = ['KNOWiNK', 'ES&S', 'Tenex', 'Other Electronic']
commercial_switches_df = switches_df[switches_df['vendor_from'].isin(commercial_vendors)].copy()

print(f"   Total transitions detected: {len(switches_df):,}")
print(f"   Commercial vendor transitions: {len(commercial_switches_df):,}")
print(f"   Switches from commercial vendors: {commercial_switches_df['is_switch'].sum():,}")

# Save all switches
switches_df.to_csv('analysis_output/data/pollbook_vendor_switches_all_transitions.csv', index=False)
print(f"   Saved switches to analysis_output/data/vendor_switches_all_transitions.csv")

# ============================================================================
# SECTION 2: RETENTION RATE ANALYSIS
# ============================================================================

print("\n[2/6] Calculating retention rates...")

retention_data = []

for vendor in commercial_vendors:
    for year_from, year_to in year_pairs:
        # Jurisdictions using this vendor in year_from
        cohort = commercial_switches_df[
            (commercial_switches_df['year_from'] == year_from) &
            (commercial_switches_df['vendor_from'] == vendor)
        ]

        if len(cohort) == 0:
            continue

        # How many stayed with the same vendor?
        retained = cohort[cohort['is_switch'] == False]
        retention_rate = len(retained) / len(cohort) * 100

        retention_data.append({
            'vendor': vendor,
            'year_from': year_from,
            'year_to': year_to,
            'cohort_size': len(cohort),
            'retained': len(retained),
            'switched': len(cohort) - len(retained),
            'retention_rate': retention_rate
        })

retention_df = pd.DataFrame(retention_data)
retention_df.to_csv('analysis_output/data/pollbook_vendor_retention_rates.csv', index=False)
print(f"   Calculated retention rates for {len(retention_df)} vendor-year pairs")
print(f"   Saved to analysis_output/data/vendor_retention_rates.csv")

# Create retention rate line chart
print("   Creating retention rate chart...")
fig, ax = plt.subplots(figsize=(14, 8))

# Vendor colors (consistent with other charts)
vendor_colors = {
    'KNOWiNK': '#FFD700',
    'ES&S': '#2C5AA0',
    'Tenex': '#2E7D32',
    'Other Electronic': '#FF8C00'
}

for vendor in commercial_vendors:
    vendor_retention = retention_df[retention_df['vendor'] == vendor]

    if len(vendor_retention) > 0:
        ax.plot(
            vendor_retention['year_from'],
            vendor_retention['retention_rate'],
            marker='o',
            linewidth=2.5,
            markersize=8,
            label=vendor,
            color=vendor_colors[vendor]
        )

ax.set_xlabel('Year', fontsize=14)
ax.set_ylabel('Retention Rate (%)', fontsize=14)
ax.set_title('Poll Book Vendor Retention Rates (2006-2026)\n(Commercial Vendors Only)',
             fontsize=16, fontweight='bold', pad=20)
ax.set_ylim(0, 100)
ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5, linewidth=1)
ax.grid(True, alpha=0.3)
ax.legend(fontsize=12, loc='lower right')
ax.set_xticks(years[:-1])

plt.tight_layout()
plt.savefig('analysis_output/charts/pollbook/pollbook_vendor_retention_rates_timeseries.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Chart saved to analysis_output/charts/vendor_retention_rates_timeseries.png")

# ============================================================================
# SECTION 3: SWITCHING MATRIX
# ============================================================================

print("\n[3/6] Building switching matrix...")

# Build transition count matrix (all vendors including Paper and In-House)
all_vendors = ['Paper', 'In-House', 'KNOWiNK', 'ES&S', 'Tenex', 'Other Electronic']
transition_matrix = pd.DataFrame(0, index=all_vendors, columns=all_vendors)

for _, row in commercial_switches_df.iterrows():
    vendor_from = row['vendor_from']
    vendor_to = row['vendor_to']
    transition_matrix.loc[vendor_from, vendor_to] += 1

# Convert to percentages (row sums = 100%)
transition_probs = transition_matrix.div(transition_matrix.sum(axis=1), axis=0) * 100

# Handle any NaN (vendors with zero transitions)
transition_probs = transition_probs.fillna(0)

# Save matrix
transition_probs.to_csv('analysis_output/data/pollbook_vendor_switching_matrix_overall.csv')
print(f"   Calculated switching probabilities")
print(f"   Saved to analysis_output/data/vendor_switching_matrix_overall.csv")

# Create heatmap
print("   Creating switching matrix heatmap...")
fig, ax = plt.subplots(figsize=(10, 8))

sns.heatmap(
    transition_probs,
    annot=True,
    fmt='.1f',
    cmap='YlOrRd',
    cbar_kws={'label': 'Transition Probability (%)'},
    linewidths=0.5,
    linecolor='gray',
    ax=ax,
    vmin=0,
    vmax=100
)

ax.set_xlabel('Vendor TO', fontsize=14)
ax.set_ylabel('Vendor FROM (Commercial Only)', fontsize=14)
ax.set_title('Poll Book Vendor Switching Matrix (2006-2026)\n(FROM: Commercial Vendors Only)',
             fontsize=16, fontweight='bold', pad=20)

plt.tight_layout()
plt.savefig('analysis_output/charts/pollbook/pollbook_vendor_switching_matrix_heatmap.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Chart saved to analysis_output/charts/vendor_switching_matrix_heatmap.png")

# ============================================================================
# SECTION 4: AVERAGE TENURE ANALYSIS
# ============================================================================

print("\n[4/6] Calculating average tenure...")

# For each jurisdiction, calculate "spells" with each vendor
tenure_data = []

for idx, row in merged.iterrows():
    fips = row['FIPS code']
    state = row['State']
    jurisdiction = row['Jurisdiction']

    vendor_sequence = [row[f'Vendor_{y}'] for y in years]

    # Identify continuous "spells" with each vendor
    current_vendor = None
    spell_start_year = None
    spell_start_idx = None

    for i, (year, vendor) in enumerate(zip(years, vendor_sequence)):
        if vendor is None:
            # Missing data, end current spell if any
            if current_vendor is not None and current_vendor in commercial_vendors:
                # Incomplete spell due to missing data
                tenure_data.append({
                    'FIPS code': fips,
                    'State': state,
                    'Jurisdiction': jurisdiction,
                    'vendor': current_vendor,
                    'start_year': spell_start_year,
                    'end_year': year,
                    'tenure_years': year - spell_start_year,
                    'spell_type': 'incomplete_data',
                    'censored': True
                })
            current_vendor = None
            spell_start_year = None
            spell_start_idx = None
            continue

        if vendor != current_vendor:
            # End of previous spell
            if current_vendor is not None and current_vendor in commercial_vendors:
                # Determine if spell is left-censored (started in 2006)
                left_censored = (spell_start_idx == 0)

                # Determine if spell ended (switched) or is ongoing (right-censored)
                if vendor in commercial_vendors or vendor in ['Paper', 'In-House']:
                    # Switched to different vendor
                    tenure_data.append({
                        'FIPS code': fips,
                        'State': state,
                        'Jurisdiction': jurisdiction,
                        'vendor': current_vendor,
                        'start_year': spell_start_year,
                        'end_year': year,
                        'tenure_years': year - spell_start_year,
                        'spell_type': 'left_censored' if left_censored else 'completed',
                        'censored': left_censored
                    })

            # Start new spell
            current_vendor = vendor
            spell_start_year = year
            spell_start_idx = i

    # Handle spell that extends to 2026 (right-censored)
    if current_vendor is not None and current_vendor in commercial_vendors:
        left_censored = (spell_start_idx == 0)
        tenure_data.append({
            'FIPS code': fips,
            'State': state,
            'Jurisdiction': jurisdiction,
            'vendor': current_vendor,
            'start_year': spell_start_year,
            'end_year': 2026,
            'tenure_years': 2026 - spell_start_year,
            'spell_type': 'left_censored' if left_censored else 'ongoing',
            'censored': True
        })

tenure_df = pd.DataFrame(tenure_data)
tenure_df.to_csv('analysis_output/data/pollbook_vendor_tenure_all_spells.csv', index=False)
print(f"   Identified {len(tenure_df)} vendor spells")

# Calculate summary statistics (exclude left-censored)
tenure_summary_data = []

for vendor in commercial_vendors:
    vendor_spells = tenure_df[tenure_df['vendor'] == vendor]

    # Completed spells (not left-censored, not ongoing)
    completed = vendor_spells[vendor_spells['spell_type'] == 'completed']

    # Ongoing spells (right-censored, but not left-censored)
    ongoing = vendor_spells[vendor_spells['spell_type'] == 'ongoing']

    tenure_summary_data.append({
        'vendor': vendor,
        'n_completed': len(completed),
        'mean_tenure_completed': completed['tenure_years'].mean() if len(completed) > 0 else np.nan,
        'median_tenure_completed': completed['tenure_years'].median() if len(completed) > 0 else np.nan,
        'std_tenure_completed': completed['tenure_years'].std() if len(completed) > 0 else np.nan,
        'n_ongoing': len(ongoing),
        'mean_tenure_ongoing': ongoing['tenure_years'].mean() if len(ongoing) > 0 else np.nan,
        'median_tenure_ongoing': ongoing['tenure_years'].median() if len(ongoing) > 0 else np.nan,
        'std_tenure_ongoing': ongoing['tenure_years'].std() if len(ongoing) > 0 else np.nan
    })

tenure_summary_df = pd.DataFrame(tenure_summary_data)
tenure_summary_df.to_csv('analysis_output/data/pollbook_vendor_tenure_summary.csv', index=False)
print(f"   Saved tenure summary to analysis_output/data/vendor_tenure_summary.csv")

# Create tenure bar chart
print("   Creating average tenure chart...")
fig, ax = plt.subplots(figsize=(12, 7))

x = np.arange(len(commercial_vendors))
width = 0.35

completed_means = []
completed_stds = []
ongoing_means = []
ongoing_stds = []

for vendor in commercial_vendors:
    summary = tenure_summary_df[tenure_summary_df['vendor'] == vendor].iloc[0]
    completed_means.append(summary['mean_tenure_completed'] if not pd.isna(summary['mean_tenure_completed']) else 0)
    completed_stds.append(summary['std_tenure_completed'] if not pd.isna(summary['std_tenure_completed']) else 0)
    ongoing_means.append(summary['mean_tenure_ongoing'] if not pd.isna(summary['mean_tenure_ongoing']) else 0)
    ongoing_stds.append(summary['std_tenure_ongoing'] if not pd.isna(summary['std_tenure_ongoing']) else 0)

bars1 = ax.bar(x - width/2, completed_means, width,
               yerr=completed_stds, label='Completed Tenure',
               color='#87CEEB', edgecolor='black', capsize=5)
bars2 = ax.bar(x + width/2, ongoing_means, width,
               yerr=ongoing_stds, label='Ongoing Tenure (as of 2026)',
               color='#4169E1', edgecolor='black', capsize=5)

ax.set_xlabel('Vendor', fontsize=14)
ax.set_ylabel('Average Tenure (Years)', fontsize=14)
ax.set_title('Average Poll Book Vendor Tenure\n(Excludes Left-Censored Spells)',
             fontsize=16, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(commercial_vendors)
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('analysis_output/charts/pollbook/pollbook_vendor_average_tenure.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Chart saved to analysis_output/charts/vendor_average_tenure.png")

# ============================================================================
# SECTION 5: SURVIVAL ANALYSIS (KAPLAN-MEIER)
# ============================================================================

print("\n[5/6] Performing survival analysis...")

# Prepare survival data: for each first adoption of a commercial vendor,
# track how long they stayed before switching
survival_data = []

for idx, row in merged.iterrows():
    fips = row['FIPS code']
    state = row['State']
    jurisdiction = row['Jurisdiction']

    vendor_sequence = [row[f'Vendor_{y}'] for y in years]

    # Find first adoption of each commercial vendor
    for vendor in commercial_vendors:
        first_adoption_idx = None
        for i, v in enumerate(vendor_sequence):
            if v == vendor:
                first_adoption_idx = i
                break

        if first_adoption_idx is None:
            continue  # Never adopted this vendor

        # Skip if left-censored (already using in 2006)
        if first_adoption_idx == 0:
            continue

        # Track how long they stayed with this vendor
        adoption_year = years[first_adoption_idx]
        duration = 0
        switched = False

        for i in range(first_adoption_idx, len(vendor_sequence)):
            if vendor_sequence[i] is None:
                # Missing data - censor here
                duration = years[i] - adoption_year
                switched = False
                break
            elif vendor_sequence[i] != vendor:
                # Switched away
                switched = True
                duration = years[i] - adoption_year
                break

        if not switched and duration == 0:
            # Still using vendor as of 2026 (right-censored)
            duration = 2026 - adoption_year

        survival_data.append({
            'FIPS code': fips,
            'State': state,
            'Jurisdiction': jurisdiction,
            'vendor': vendor,
            'adoption_year': adoption_year,
            'duration': duration,
            'switched': switched  # Event indicator (1 = switched, 0 = censored)
        })

survival_df = pd.DataFrame(survival_data)
print(f"   Prepared survival data for {len(survival_df)} adoption events (excluding left-censored)")

# Fit Kaplan-Meier curves for each vendor
km_fits = {}
survival_curves = {}

for vendor in commercial_vendors:
    vendor_data = survival_df[survival_df['vendor'] == vendor]

    if len(vendor_data) == 0:
        print(f"   Warning: No survival data for {vendor}")
        continue

    kmf = KaplanMeierFitter()
    kmf.fit(
        durations=vendor_data['duration'],
        event_observed=vendor_data['switched'],
        label=vendor
    )
    km_fits[vendor] = kmf

    # Save survival curve
    survival_curve = kmf.survival_function_
    survival_curve.to_csv(f'analysis_output/data/pollbook_survival_curve_{vendor.replace(" ", "_")}.csv')
    survival_curves[vendor] = survival_curve

    print(f"   Fitted Kaplan-Meier curve for {vendor} (n={len(vendor_data)})")

# Create survival curve chart
print("   Creating survival curve chart...")
fig, ax = plt.subplots(figsize=(14, 8))

for vendor in commercial_vendors:
    if vendor in km_fits:
        km_fits[vendor].plot_survival_function(ax=ax, ci_show=True,
                                                color=vendor_colors[vendor],
                                                linewidth=2.5)

ax.set_xlabel('Years Since Adoption', fontsize=14)
ax.set_ylabel('Probability Still With Vendor', fontsize=14)
ax.set_title('Poll Book Vendor Survival Curves (Kaplan-Meier)\n(Excludes Left-Censored Adoptions)',
             fontsize=16, fontweight='bold', pad=20)
ax.set_ylim(0, 1)
ax.grid(True, alpha=0.3)
ax.legend(fontsize=12, loc='upper right')

# Add median survival time annotations
for vendor in commercial_vendors:
    if vendor in km_fits:
        median_survival = km_fits[vendor].median_survival_time_
        if not pd.isna(median_survival) and median_survival > 0:
            ax.axvline(x=median_survival, color=vendor_colors[vendor],
                      linestyle=':', alpha=0.5, linewidth=1.5)

plt.tight_layout()
plt.savefig('analysis_output/charts/pollbook/pollbook_vendor_survival_curves.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Chart saved to analysis_output/charts/vendor_survival_curves.png")

# Log-rank test to compare survival curves
if len(km_fits) > 1:
    print("\n   Running log-rank test to compare survival curves...")
    try:
        results = multivariate_logrank_test(
            survival_df['duration'],
            survival_df['vendor'],
            survival_df['switched']
        )
        print(f"   Log-rank test p-value: {results.p_value:.4f}")
        if results.p_value < 0.05:
            print(f"   → Survival curves differ significantly across vendors (p < 0.05)")
        else:
            print(f"   → No significant difference in survival curves (p >= 0.05)")
    except Exception as e:
        print(f"   Warning: Could not perform log-rank test: {e}")

# ============================================================================
# SECTION 6: CONSOLE SUMMARY
# ============================================================================

print("\n" + "="*80)
print("VENDOR LOCK-IN ANALYSIS SUMMARY (2006-2026)")
print("="*80)

print("\n1. RETENTION RATES (2020-2026 period average):")
for vendor in commercial_vendors:
    recent_retention = retention_df[
        (retention_df['vendor'] == vendor) &
        (retention_df['year_from'] >= 2020)
    ]['retention_rate'].mean()

    if not pd.isna(recent_retention):
        print(f"   {vendor:20s}: {recent_retention:>5.1f}%")
    else:
        print(f"   {vendor:20s}: No data")

print("\n2. SWITCHING PATTERNS (Top 5 switches FROM commercial vendors):")
top_switches = commercial_switches_df[
    commercial_switches_df['is_switch'] == True
].groupby(['vendor_from', 'vendor_to']).size().nlargest(5)

for (v_from, v_to), count in top_switches.items():
    print(f"   {v_from} → {v_to}: {count} jurisdictions")

print("\n3. AVERAGE TENURE (Completed spells only):")
for vendor in commercial_vendors:
    summary = tenure_summary_df[tenure_summary_df['vendor'] == vendor].iloc[0]
    mean_tenure = summary['mean_tenure_completed']
    n_completed = summary['n_completed']

    if not pd.isna(mean_tenure) and n_completed > 0:
        print(f"   {vendor:20s}: {mean_tenure:>5.1f} years (n={int(n_completed)})")
    else:
        print(f"   {vendor:20s}: No completed spells")

print("\n4. MEDIAN SURVIVAL TIME (50% switch away point):")
for vendor in commercial_vendors:
    if vendor in km_fits:
        median_survival = km_fits[vendor].median_survival_time_
        if not pd.isna(median_survival) and median_survival > 0:
            print(f"   {vendor:20s}: {median_survival:>5.1f} years")
        else:
            print(f"   {vendor:20s}: Not reached (>50% still using vendor)")
    else:
        print(f"   {vendor:20s}: No data")

print("\n5. LOCK-IN STRENGTH RANKING:")
print("   (Based on retention rate + tenure composite score)")
lock_in_scores = {}

for vendor in commercial_vendors:
    # Average retention rate (2014-2026 to avoid sparse early data)
    retention_score = retention_df[
        (retention_df['vendor'] == vendor) &
        (retention_df['year_from'] >= 2014)
    ]['retention_rate'].mean()

    # Average ongoing tenure (proxy for lock-in strength)
    summary = tenure_summary_df[tenure_summary_df['vendor'] == vendor].iloc[0]
    tenure_score = summary['mean_tenure_ongoing']

    if not pd.isna(retention_score) and not pd.isna(tenure_score):
        # Composite: weight both equally, normalize tenure to 0-100 scale
        composite = (retention_score + min(tenure_score * 5, 100)) / 2
        lock_in_scores[vendor] = composite

ranked_vendors = sorted(lock_in_scores.items(), key=lambda x: x[1], reverse=True)
for i, (vendor, score) in enumerate(ranked_vendors, 1):
    print(f"   {i}. {vendor:20s} (score: {score:>5.1f})")

print("\n" + "="*80)
print("✓ Analysis complete! Files saved to analysis_output/")
print("="*80)
print("\nKey Findings:")
print(f"  - {len(commercial_switches_df):,} total commercial vendor transitions analyzed")
print(f"  - {commercial_switches_df['is_switch'].sum():,} switches from commercial vendors")
print(f"  - Switch rate: {commercial_switches_df['is_switch'].sum() / len(commercial_switches_df) * 100:.1f}%")
print(f"  - {len(survival_df):,} adoption events in survival analysis (excluding left-censored)")
print("="*80)
