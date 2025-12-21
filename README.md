# U.S. National Voting Equipment and Poll Book Analysis

Data analysis of U.S. voting equipment deployment, turnover patterns, vendor switching behavior, and poll book adoption across jurisdictions from 2006-2026 using data from Verified Voting's equipment database.

## Source Data

[Verified Voting](https://verifiedvoting.org/) tracks voting equipment - equipment used for marking ballots, tabulating ballots, or checking in voters - across all U.S. jurisdictions. You may explore and export their data geographically via their tool, [The Verifier](https://verifiedvoting.org/verifier/#mode/navigate/map/voteEquip/mapType/ppEquip/year/2026). The raw data used in this project was downloaded directly from The Verifier.

The Verifier is an exceptional tool for exploring the data in specific years, especially if you want to look at specific states or counties. For longitudinal analysis, however, the raw data requires significant cleaning and flattening to be useful. This project performs that cleaning and flattening, then analyzes the resulting data for trends in voting equipment usage.

### Source Data Structure

For each even year (i.e. federal election years), The Verifier provides two key CSV files:
- **Jurisdiction Data**: `verifier-jurisdictions.csv` - One row per jurisdiction. Contains metadata about the jurisdiction (name, state, FIPS code, number of registered voters, etc.) and high-level voting equipment usage (e.g. "Ballot Marking Device for all", "All Mail", etc.).
- **Equipment Data**: `verifier-machines.csv` - One row per piece of equipment in use in each jurisdiction. Contains information about each type of equipment in use (model, manufacturer, first year in use, and the context in which it's used).

The jurisdictions vary in size based on how each state runs elections. For example, Wisconsin, New Hampshire, and Vermont administrate elections at the municipal level, so each town or city is a jurisdiction. California and Texas, like most states, administrate elections at the county level, so each county is a jurisdiction. For states that manage voting equipment statewide, the jurisdictional data is still at the county level. An exception is Alaska, which is treated as a single jurisdiction. 

### Known Data Anomalies

There are many aspects of the data that are messy, as is typical of a large dataset collected from many different sources about a messy real-world situation. Some notable anomalies include:
- The "All Mail" tag for jurisdictions is notably incorrect in 2018 for many jurisdictions in Utah, Oregon, and North Dakota.
- The labels "DREs without VVPAT for all voters" and "DREs with VVPAT for all voters" seem to be inconsistent, and suggest that almost as many jurisdictions downgraded from VVPAT as upgraded to VVPAT over time, which seems unlikely.
- The "First Year In Use" field is often negative for older equipment.
- For closely related models (e.g. AccuVote OS vs AccuVote OSX), jurisdictions sometimes report one model and sometimes the other. Even different years for the same jurisdiction may report different models. These are treated as the same model family in this analysis.
- Some jurisdictions appear to use a machine in one election, not use it in the next, and then use it in the following. This may indicate that a jurisdiction is using equipment inconsistently, or it may be a data error.

### Supplementary Data

The HAVA funding levels by state and year, from 2002 to present, are scraped from EAC's [Funding by State page](https://www.eac.gov/funding-levels-by-state).

## Methods: Condensing The Data

The main challenge is to condense the normalized data (one jurisdiction and many machine records) into a single row per jurisdiction, to more easily analyze usage over time. To simplify the question, we ignore a few dimensions of the data:

- We only pay attention the primary voting system and voting system vendor. E.g. an AccuVote user that also has a DemLive BMD is just treated as an AccuVote user.
- We ignore the distinctions between equipment use on election day, vote centers, early voting, and absentee ballot processing, and just try to infer  which equipment matters the most.
- We treat poll book usage separately from voting equipment usage.

All of these are possible future extensions to the analysis.

### Step 1: Collapsing Machine Time Series Data

The raw Verified Voting machine data represents a time-series. We collapse each jurisdiction-machine-use into a single row in `./etl/generate_machine_lifetimes.py` for two reasons:

- Smoothes over data blips where a jurisdiction appears to drop and then re-adopt a machine.
- Makes it simple to generate distributions of equipment lifetime for each model. 

### Step 2: Create Augmented Jurisdiction Time Series

In `./etl/generate_jurisdictions_time_series.py`, we combine the original jurisdiction and the collapsed machine data to categorize each jurisdiction's voting system at each point in time. The time series has fields for the primary voting system, primary voting system vendor, primary vendor, and poll book type. 

### Step 3: Generate Transition Data

We extract the transition points from the jurisdiction time series to identify changes in the voting equipment in `./etl/generate_jurisdiction_transitions.py`. There are many different types of transitions, which are used to filter later analyses for different types of turnover: to_hand_count, from_hand_count, vendor, system, equipment, vvpat_upgrade, vvpat_downgrade, other, and baseline, which is used to identify the starting point for each jurisdiction.

We do an analogous but much simpler process for poll books in `./etl/generate_pollbook_transitions.py`.

## Analysis

The `analysis/` directory contains scripts that generate charts and reports from the processed data. All outputs go to `outputs/figures/` and `outputs/reports/`.

### Equipment Analysis (`analysis/equipment/`)

- **Adoption trends**: Tracks jurisdictions and voters using voting equipment vs hand count over time
- **Equipment survival**: Kaplan-Meier survival curves showing how long equipment stays in service before replacement
- **Model analysis**: When specific models (DS200, AccuVote, ExpressVote, etc.) were introduced and their survival rates
- **Vendor dynamics**: Market share trends, vendor retention rates, and switching patterns between ES&S, Dominion, Hart, and others
- **State recency**: Per-state analysis of when jurisdictions last upgraded their equipment

### Poll Book Analysis (`analysis/pollbook/`)

- **Adoption trends**: Growth of electronic poll books vs paper over time
- **Size analysis**: How jurisdiction size correlates with electronic poll book adoption
- **Vendor dynamics**: Market share and retention for poll book vendors (KNOWiNK, ES&S Expoll, Tenex, etc.)

### Trends Analysis (`analysis/trends/`)

- **Transition patterns**: Comprehensive analysis of vendor changes, system upgrades, and method transitions
- **Marking method evolution**: Sankey diagrams showing how jurisdictions moved between hand-marked ballots, BMDs, and DREs

## Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

To generate all data, analysis, and images:

```bash
# With Verified Voting zip archives in the ./data/downloads directory
python3 run_all.py

# Or, to run analysis only (skip ETL, assumes data already exists):
python3 run_all.py --analysis-only
```
