# Voting Equipment and Poll Book Analysis

Analysis of U.S. voting equipment deployment, turnover patterns, vendor switching behavior, and poll book adoption across jurisdictions from 2006-2026.

## Data Source

**Primary Data**: Verified Voting - Equipment Verifier. Data

Verified Voting has tracked all equipment for marking or  for voting equipment certification and deployment data across all U.S. election jurisdictions. Raw verifier data contains detailed, machine-level records for each jurisdiction, listing every piece of voting equipment in use.

**Supplementary Data**:
- **HAVA Funding**: EAC HAVA funding levels by state and year (2002-2020+)
- **Poll Books**: Equipment type classifications from EAC verifier data

## Data Time Range

**Equipment Data**: 2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026 (even years)

**HAVA Funding Data**: 2002-2020 (aggregated by even years)

**Baseline**: 2006 is the baseline year. Where available, "First Year In Use" metadata extends equipment deployment history back to 2000.

## Condensing Methodology

### Problem
Raw EAC verifier data contains **multiple rows per jurisdiction** (one per piece of equipment). To analyze jurisdictions as units, we must identify each jurisdiction's **primary voting system**.

### Solution: Voter-Weighted Plurality

The condensing process (`condense_jurisdictions.py`) identifies a jurisdiction's primary voting system by determining which equipment type serves the **most registered voters**:

1. **Load machine-level data**: Read `{YEAR}_verifier-machines.csv` for equipment assignments per jurisdiction
2. **Calculate voter weights**: For each equipment type, sum the registered voters it serves
3. **Identify plurality winner**: The equipment type serving the most voters becomes the jurisdiction's "primary voting equipment"
4. **Classify equipment family**: Group related equipment models into families (e.g., "ES&S DS200 Generation" includes DS200, ExpressVote, etc.)
5. **Extract metadata**:
   - **Primary Marking Method**: Paper (hand-marked) vs Machine (BMD/DRE)
   - **DRE Status**: Yes/No indicator
   - **Vendor**: ES&S, Dominion, Hart InterCivic, etc.
   - **First Year In Use**: Earliest deployment year from equipment records

### Equipment Classification

Equipment is classified by **Election Day marking method**:

- **Machine**: BMDs (Ballot Marking Devices), DREs (Direct Recording Electronic), Mechanical Lever Machines
- **Precinct Scan**: Hand-fed optical scanners (hand-marked paper ballots scanned at precinct)
- **Central Scan**: Batch-fed scanners, punch card systems (ballots scanned centrally)
- **Hand Count**: Explicit hand count equipment or small jurisdictions (<500 voters)

### Poll Book Classification

Poll books are classified as:
- **Paper**: Traditional paper poll books
- **Commercial Electronic**: Manufacturer-branded e-poll books (KNOWiNK, Tenex, Robis, etc.)
- **In-House**: Custom/in-house electronic poll book systems

Priority logic: Paper > In-House > Commercial (if multiple types present, the highest priority wins)

### Output

For each year, condensing produces:
- **`{YEAR}_verifier-jurisdictions-condensed.csv`**: One row per jurisdiction with primary voting system fields
- **`{YEAR}_summary_report.md`**: Statistical summary of equipment distribution for the year

## Turnover Analysis

### Overview

The turnover analysis (`identify_voting_equipment_turnover.py`) tracks **equipment changes** across consecutive election cycles (2006→2008, 2008→2010, etc.).

### Three Types of Jurisdictions

#### 1. Between-System Turnovers
**Definition**: Jurisdictions that changed their **equipment family** (vendor switch or major system upgrade)

**Examples**:
- ES&S DS200 → Dominion ImageCast (vendor switch)
- AccuVote TS (DRE) → ES&S DS200 (optical scan)
- Hart eSeries → Hart Verity (same vendor, different generation)

**Output**: `data/between_system_turnovers.csv`

**Key Fields**:
- `From_Equipment`, `To_Equipment`: Full equipment names
- `From_Vendor`, `To_Vendor`: Vendor names
- `From_Family`, `To_Family`: Equipment family classifications
- `Vendor_Retained`: Boolean indicating if vendor stayed the same
- `Years_Between`: Time elapsed between changes

#### 2. Within-System Turnovers
**Definition**: Jurisdictions that changed **equipment model** within the **same family**

**Examples**:
- ES&S Model 100 → ES&S DS200 (same ES&S DS200 Generation family)
- Hart InterCivic eScan → Hart InterCivic eSlate (same Hart eSeries family)

**Output**: `data/within_system_turnovers.csv`

**Note**: These represent incremental upgrades or replacements within an existing vendor relationship.

#### 3. No-Turnover Jurisdictions
**Definition**: Jurisdictions that used the **same equipment** across the entire 2006-2026 period

**Output**: `data/no_system_turnovers.csv`

**Key Insight**: These jurisdictions represent equipment that has been in service for 20+ years without replacement.

### Backfilled Initial Deployments (2000-2006)

For years before 2008, turnover data is **inferred** from the "First Year In Use" field in the 2006 verifier data:
- If a jurisdiction's equipment was first used in 2002, it's counted as a 2002 "deployment"
- This extends the analysis backwards to capture **HAVA-era equipment purchases** (2002-2004)
- Odd years are rounded down to even years (2003→2002, 2005→2004) for consistency

## Key Outputs

### Turnover Data Files
- **`data/between_system_turnovers.csv`**: System family changes (vendor switches, major upgrades)
- **`data/within_system_turnovers.csv`**: Same-family equipment changes (incremental upgrades)
- **`data/no_system_turnovers.csv`**: Jurisdictions with no equipment changes (2006-2026)

### Analysis Visualizations

#### Equipment Lifecycle Analysis (`equipment_analysis/`)
- **`lifecycle_distribution_all.png`**: Distribution of equipment lifecycle lengths (all turnovers)
- **`lifecycle_distribution_from_paper.png`**: Lifecycle for HMPB (hand-marked paper ballot) systems
- **`lifecycle_distribution_from_bmd.png`**: Lifecycle for BMD systems
- **`lifecycle_distribution_from_dre.png`**: Lifecycle for DRE systems

#### Vendor Turnover Analysis (`equipment_analysis/`)
- **`turnover_volume_by_year.png`**: Total number of turnovers per year
- **`turnover_percentage_jurisdictions.png`**: Turnover as % of all jurisdictions
- **`turnover_percentage_voters.png`**: Turnover as % of registered voters
- **`turnover_and_hava_funding.png`**: Dual-axis chart comparing turnover % with HAVA funding levels
- **`vendor_switching_matrix.png`**: Heatmap showing vendor retention and switching patterns
- **`vendor_retention_timeline.png`**: Vendor retention rates over time (2006-2026)

#### Jurisdiction Trends (`data_quality_tools/jurisdiction_trends/`)
- **Marking Method Trends**: Evolution of hand-marked vs machine-marked voting over time
- **Tabulation Trends**: Precinct vs central tabulation patterns
- **All-Mail Ballot Trends**: Adoption of all-mail voting
- **Voting Location Trends**: Vote center vs precinct-based voting

Each trend is visualized in two ways:
1. **By jurisdiction count**: Each jurisdiction counted equally
2. **Weighted by registered voters**: Larger jurisdictions weighted more heavily

## Data Quality Tools

The `data_quality_tools/` directory contains scripts for exploring and validating the data:

### `/jurisdiction_condensed_values/`
Tools for analyzing field values in condensed jurisdiction data:
- **`report_unique_condensed_values.py`**: Lists all unique values for each condensed field
- **`report_anomaly_details.py`**: Identifies and reports data anomalies across years

### `/jurisdiction_trends/`
Visualization tools for tracking field values over time:
- **`analyze_jurisdiction_trends.py`**: Generates stacked bar charts showing how marking methods, tabulation, and voting locations change over time

### `/machines/`
Machine-level data analysis:
- **`find_duplicate_equipment.py`**: Identifies duplicate equipment records

### `/turnover/`
Turnover pattern investigation:
- **`inspect_no_turnover.py`**: Analyzes jurisdictions with no equipment changes
- **`inspect_quick_turnover.py`**: Identifies unusually short equipment lifecycles
- **`analyze_within_system_patterns.py`**: Studies patterns in same-family equipment changes

**Usage**: Run any script to generate detailed reports and identify data quality issues or interesting patterns.

## Usage

### Generate Condensed Jurisdiction Data

```bash
# Condense a single year
python3 condense_jurisdictions.py 2024

# Condense all years (batch processing)
for year in 2006 2008 2010 2012 2014 2016 2018 2020 2022 2024 2026; do
    python3 condense_jurisdictions.py $year
done
```

**Output**: `data/verifier-condensed/{YEAR}_verifier-jurisdictions-condensed.csv`

### Identify Equipment Turnovers

```bash
# Identify all three types of turnovers/no-turnovers
python3 identify_voting_equipment_turnover.py
```

**Output**:
- `data/between_system_turnovers.csv` (system family changes)
- `data/within_system_turnovers.csv` (same-family upgrades)
- `data/no_system_turnovers.csv` (no equipment changes 2006-2026)

### Run Equipment Lifecycle Analysis

```bash
# Generate lifecycle distribution charts
python3 equipment_analysis/analyze_lifecycle_distribution.py
```

**Output**: `equipment_analysis/lifecycle_distribution_*.png` (4 charts)

### Run Vendor Turnover Analysis

```bash
# Generate vendor turnover and HAVA funding analysis
python3 equipment_analysis/analyze_vendor_turnover.py
```

**Output**: `equipment_analysis/turnover_*.png` and `vendor_*.png` (6 charts)

### Explore Jurisdiction Trends

```bash
# Generate jurisdiction trend visualizations
python3 data_quality_tools/jurisdiction_trends/analyze_jurisdiction_trends.py
```

**Output**: `data_quality_tools/jurisdiction_trends/*_trends.png` (8 charts)

## Key Findings

### Equipment Lifecycle
- **Median lifecycle**: Equipment typically serves for 8-12 years before replacement
- **HMPB systems**: Longest lifecycles (10-14 years)
- **DRE systems**: Shorter lifecycles (6-10 years) due to security concerns and VVPAT requirements
- **No-turnover jurisdictions**: ~1,300+ jurisdictions still using 20+ year old equipment

### Vendor Dynamics
- **ES&S**: Highest retention rate (~74%) among major vendors
- **Dominion**: Significant market share gains (2010-2020)
- **Hart InterCivic**: High retention (~76%) but smaller market share
- **Vendor switching**: ~40% of turnovers involve vendor changes

### HAVA Funding Impact
- **2002-2004**: Massive equipment deployment following HAVA Act passage (~$3.1B funding)
- **2018-2020**: Second wave of federal funding for election security improvements (~$1.4B)
- **Correlation**: Clear relationship between federal funding and equipment turnover rates

### Technology Trends
- **DRE decline**: Steady decrease in DRE usage (especially without VVPAT)
- **BMD growth**: Increasing adoption of ballot marking devices
- **All-mail voting**: Significant expansion (2016-2024), especially accelerated by COVID-19
- **Electronic poll books**: Rapid adoption, now majority of jurisdictions

## Project Structure

```
.
├── data/
│   ├── verifier-condensed/          # Condensed jurisdiction data (2006-2026)
│   ├── between_system_turnovers.csv # Vendor/family changes
│   ├── within_system_turnovers.csv  # Same-family upgrades
│   ├── no_system_turnovers.csv      # No-change jurisdictions
│   └── hava_funding.csv             # HAVA funding by state/year
│
├── equipment_analysis/              # Lifecycle and vendor analysis
│   ├── analyze_lifecycle_distribution.py
│   ├── analyze_vendor_turnover.py
│   └── *.png                        # Generated visualizations
│
├── data_quality_tools/              # Data exploration and validation
│   ├── jurisdiction_condensed_values/
│   ├── jurisdiction_trends/
│   ├── machines/
│   └── turnover/
│
├── condense_jurisdictions.py        # Main condensing script
├── identify_voting_equipment_turnover.py  # Turnover identification (all 3 types)
└── README.md                        # This file
```

## Future Work

- **Poll book analysis**: Deep dive into electronic poll book adoption and vendor dynamics
- **Temporal patterns**: Seasonal/cyclical patterns in equipment turnover
- **Geographic analysis**: Regional trends in equipment choices and turnover rates
- **Cost analysis**: Equipment costs and total cost of ownership modeling

