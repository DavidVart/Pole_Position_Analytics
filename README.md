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
2. **FastF1 Python Library** - Lap times, telemetry, and weather data

## Project Structure

```
Pole_Position_Analytics/
├── data/                     # SQLite DB + FastF1 cache (gitignored)
├── outputs/
│   ├── csv/                 # Calculated data CSVs
│   └── figures/             # Visualization PNGs
├── src/
│   ├── db_utils.py          # Database setup and helpers
│   ├── jolpica_api.py       # Jolpica F1 API integration
│   ├── fastf1_api.py        # FastF1 integration
│   ├── calculations.py      # SQL queries with JOINs
│   ├── visualisation.py     # Matplotlib/Seaborn plots
│   └── main.py              # Main orchestration script
├── requirements.txt
├── .gitignore
└── README.md
```

## Database Schema

The project uses a normalized SQLite database with the following tables:

- **LoadProgress** - Tracks incremental data loading progress
- **Drivers** - Normalized driver information
- **Constructors** - Team/constructor data
- **Races** - Race metadata (season, round, date, circuit)
- **Results** - Race results linking drivers, constructors, and races
- **Sessions** - Session metadata including weather conditions
- **LapTimes** - Detailed lap telemetry data

All tables use integer foreign keys to avoid duplicate string data across tables.

## Setup Instructions

### 1. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Project

```bash
python -m src.main
```

**Important:** Due to the 25-row incremental loading constraint, you need to run the script **multiple times** (5-10 runs) to accumulate 100+ rows per data source.

Each run will:
- Add up to 25 new Results rows from Jolpica API
- Add up to 25 new LapTimes rows from FastF1
- Regenerate calculations and visualizations with updated data

## Output Files

### CSV Files (outputs/csv/)
- `avg_lap_times.csv` - Average lap time per driver per race
- `grid_vs_finish.csv` - Grid position vs final position analysis
- `tyre_performance.csv` - Average lap times by tyre compound
- `temp_lap_corr.csv` - Track temperature vs lap time correlation

### Visualizations (outputs/figures/)
- `avg_lap_times.png` - Bar chart of average lap times by driver
- `temp_vs_lap_scatter.png` - Scatter plot with regression line
- `lap_progression.png` - Line chart showing lap time progression
- `tyre_performance.png` - Bar chart comparing tyre compounds

## Requirements Compliance Checklist

This project meets all SI 201 requirements:

- ✅ Two distinct APIs with different base URLs
- ✅ `requests.get` used for both data sources
- ✅ 100+ rows per API source
- ✅ Single SQLite database for all tables
- ✅ No duplicate string data (normalized with integer IDs)
- ✅ Multiple tables sharing integer keys with different row counts
- ✅ Incremental loading: ≤25 new rows per run
- ✅ No `DROP TABLE` statements in code
- ✅ Separate calculations file with JOIN queries
- ✅ Calculated data written to well-formatted CSV files
- ✅ Multiple visualizations with proper labels and titles

## Data Collection Strategy

The project collects data from the **2022 and 2023 F1 seasons** (~44 races total).

Sessions collected:
- Race sessions (R)
- Qualifying sessions (Q)

The incremental loading system tracks progress and ensures:
- No duplicate data
- Automatic continuation from last checkpoint
- No manual code changes between runs

## Authors

- David - Jolpica API integration
- Alberto - FastF1 integration
- Both - Calculations, visualizations, and orchestration

## License

See LICENSE file for details.
