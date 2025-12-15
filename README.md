# Pole Position Analytics - F1 Data Analysis Project

A comprehensive Formula 1 data analytics system that pulls data from multiple sources, stores it in a normalized SQLite database, performs statistical analysis, and generates insightful visualizations.

## Project Overview

This project demonstrates advanced data engineering and analysis skills by:
- Fetching data from two distinct F1 APIs using `requests.get`
- Storing 100+ rows per data source in a normalized SQLite database
- Implementing incremental data loading (≤25 rows per run)
- Performing SQL-based calculations with JOIN operations
- Generating multiple data visualizations

## Data Sources

1. **Jolpica F1 API** (Ergast-compatible) - Race results, driver info, constructor data
2. **OpenF1 REST API** - Lap times, telemetry, and weather data

## Project Structure

```
Pole_Position_Analytics/
├── f1.db                     # SQLite database (gitignored)
├── outputs/
│   ├── csv/                 # Calculated data CSVs
│   └── figures/             # Visualization PNGs
├── src/
│   ├── db_utils.py          # Database setup and helpers
│   ├── jolpica_api.py       # Jolpica F1 API integration
│   ├── openf1_api.py        # OpenF1 REST API integration
│   ├── clean_data.py        # Data cleaning utilities
│   ├── calculations.py       # SQL queries with JOINs
│   ├── visualisation.py     # Matplotlib/Seaborn plots
│   └── main.py              # Main orchestration script
├── requirements.txt
├── .gitignore
└── README.md
```

## Setup Instructions

### 1. Create Virtual Environment

```bash
python3 -m venv .venv
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Project

```bash
python src/main.py
```

**Important:** Due to the 25-row incremental loading constraint, run the script multiple times (5-10 runs) to accumulate 100+ rows per data source. Plots will be generated after each run.

## Visualizations
- `avg_lap_times.png` - Bar chart of average lap times by driver
- `temp_vs_lap_scatter.png` - Scatter plot with regression line showing track temperature vs lap time
- `grid_vs_finish.png` - Horizontal bar chart showing position changes from grid to finish
- `tyre_distribution.png` - Pie chart showing total lap distribution by tyre compound


## Data Collection Strategy

The project collects data from the **2023 F1 season** (~22 races total).

Sessions collected:
- Race sessions (R)
- Qualifying sessions (Q)

The incremental loading system tracks progress per data source ('jolpica' and 'openf1') and ensures:
- No duplicate data
- Automatic continuation from last checkpoint
- No manual code changes between runs

## Authors

- David - Jolpica API integration
- Alberto - OpenF1 API integration
- Both - Calculations, visualizations, and orchestration
