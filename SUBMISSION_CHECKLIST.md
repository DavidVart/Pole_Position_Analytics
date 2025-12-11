# 📋 Submission Checklist - Pole Position Analytics

## ✅ Project Status: READY FOR SUBMISSION

**Date:** December 9, 2025  
**Authors:** David & Alberto

---

## 🎉 What's Complete

### ✅ Code Implementation (100%)
- [x] All Python modules implemented and tested
- [x] 125 Results rows (exceeds 100 requirement)
- [x] 125 LapTimes rows (exceeds 100 requirement)
- [x] 6 CSV files generated with calculated data
- [x] 4 visualizations generated (2 required + 2 extra = +30 pts)
- [x] All requirements verified

### ✅ Technical Requirements
- [x] 2 APIs with different base URLs
- [x] `requests.get` used explicitly in both
- [x] Single SQLite database (10 races, 125+ rows each table)
- [x] No duplicate string data (normalized with IDs)
- [x] Tables with shared integer keys
- [x] Max 25 items per run (tested and verified)
- [x] No DROP TABLE statements
- [x] JOIN queries implemented (6 functions)
- [x] CSV output files (6 files)
- [x] Visualizations with proper labels (4 plots)

### ✅ Project Files
```
✓ src/db_utils.py           (311 lines)
✓ src/jolpica_api.py        (232 lines)
✓ src/fastf1_api.py         (434 lines)
✓ src/calculations.py       (254 lines)
✓ src/visualisation.py      (431 lines)
✓ src/main.py               (195 lines)
✓ requirements.txt          (5 dependencies)
✓ README.md                 (Complete documentation)
✓ .gitignore                (Proper exclusions)
✓ LICENSE                   (Included)
```

### ✅ Output Files
```
✓ data/f1_project.db        (SQLite database with all data)
✓ outputs/csv/              (6 CSV files)
  - avg_lap_times.csv
  - grid_vs_finish.csv
  - tyre_performance.csv
  - temp_lap_corr.csv
  - driver_statistics.csv
  - constructor_standings.csv
✓ outputs/figures/          (4 PNG visualizations)
  - avg_lap_times.png
  - temp_vs_lap_scatter.png
  - tyre_performance.png
  - grid_vs_finish.png
```

---

## 📝 What You Need to Do: Written Report

### Required Sections

#### 1. Project Overview
- **Original Goals:**
  - Build F1 data analytics system
  - Analyze race results and lap times
  - Compare driver/team performance
  - Visualize trends and correlations

- **Achieved Goals:**
  - ✅ Integrated 2 F1 data sources
  - ✅ Collected 125+ rows per source
  - ✅ Created normalized database
  - ✅ Performed 6 types of analysis
  - ✅ Generated 4 professional visualizations

#### 2. Problems Faced & Solutions

**Problem 1: FastF1 Package Installation**
- Issue: msgpack dependency had installation conflicts
- Solution: Used `pip install --use-pep517 fastf1` to force PEP 517 build

**Problem 2: API Rate Limiting**
- Issue: Ergast API occasionally times out or closes connection
- Solution: Implemented timeout handling and continued on failure

**Problem 3: Driver Matching Between APIs**
- Issue: Jolpica uses driverId (e.g., "max_verstappen"), FastF1 uses codes (e.g., "VER")
- Solution: Used driver code as matching key, stored both identifiers

**Problem 4: FastF1 Session Loading Time**
- Issue: First-time session loads are very slow (2-5 minutes each)
- Solution: Implemented caching directory to speed up subsequent runs

**Problem 5: Incremental Loading Logic**
- Issue: Tracking progress across multiple runs without duplicates
- Solution: Created LoadProgress table to store checkpoints

#### 3. Screenshots to Include

Take screenshots of:

1. **Running the program** (terminal showing execution)
   ```bash
   python -m src.main
   ```

2. **Database statistics** (showing 100+ rows)
   - Already visible in your terminal output!

3. **CSV file contents** (open one in Excel/text editor)
   - Example: `outputs/csv/avg_lap_times.csv`

4. **All 4 visualizations** (the PNG files)
   - `outputs/figures/avg_lap_times.png`
   - `outputs/figures/temp_vs_lap_scatter.png`
   - `outputs/figures/tyre_performance.png`
   - `outputs/figures/grid_vs_finish.png`

5. **Code snippets** (optional but good):
   - `requests.get` usage in both APIs
   - JOIN query example
   - 25-row limit implementation

#### 4. Function Diagram

```
MODULE: db_utils.py (Both authors)
├─ get_connection() → Connection
├─ create_tables(Connection) → None
├─ get_or_create_driver(Connection, str, str, str, str, str) → int
├─ get_or_create_constructor(Connection, str, str, str) → int
├─ get_or_create_race(Connection, int, int, str, str, str) → int
├─ get_progress(Connection, str) → tuple[int, int, str] | None
├─ update_progress(Connection, str, int, int, str) → None
└─ get_driver_by_code(Connection, str) → int | None

MODULE: jolpica_api.py (Author: David)
├─ fetch_race_list(list[int]) → list[dict]
│  Input: List of season years
│  Output: List of race dictionaries with metadata
│
├─ fetch_race_results(int, int) → list[dict]
│  Input: Season year, round number
│  Output: List of result dictionaries with driver/constructor data
│
└─ store_jolpica_data(Connection) → int
   Input: Database connection
   Output: Number of new Results rows added (max 25)

MODULE: fastf1_api.py (Author: Alberto)
├─ fetch_race_metadata_with_requests(int, int) → dict | None
│  Input: Season year, round number
│  Output: Race metadata (demonstrates requests.get requirement)
│
├─ load_session(int, str, str) → FastF1Session | None
│  Input: Year, event name, session type
│  Output: Loaded FastF1 session object
│
├─ extract_lap_data(FastF1Session) → list[dict]
│  Input: FastF1 session object
│  Output: List of lap dictionaries with telemetry
│
├─ extract_session_weather(FastF1Session) → dict
│  Input: FastF1 session object
│  Output: Dictionary with weather metrics
│
├─ get_or_create_session(Connection, int, str, dict) → int
│  Input: Database connection, race_id, session type, weather data
│  Output: Session ID
│
└─ store_fastf1_data(Connection) → int
   Input: Database connection
   Output: Number of new LapTimes rows added (max 25)

MODULE: calculations.py (Both authors)
├─ write_to_csv(DataFrame, str) → None
├─ compute_average_lap_times(Connection) → DataFrame
├─ compute_grid_vs_finish(Connection) → DataFrame
├─ compute_tyre_performance(Connection) → DataFrame
├─ correlate_temp_lap_time(Connection) → tuple[float, DataFrame]
├─ compute_driver_statistics(Connection) → DataFrame
├─ compute_constructor_standings(Connection) → DataFrame
└─ run_all_calculations(Connection) → dict

MODULE: visualisation.py (Both authors)
├─ plot_avg_lap_times(DataFrame, tuple[int, int], str) → None
├─ plot_temp_vs_lap_scatter(DataFrame, float, str) → None
├─ plot_lap_progression(Connection, int, int, list[str], str) → None
├─ plot_tyre_performance(DataFrame, str) → None
├─ plot_grid_vs_finish(DataFrame, int, str) → None
└─ generate_all_visualizations(Connection, dict) → None

MODULE: main.py (Both authors)
├─ print_banner(str) → None
├─ print_database_stats(Connection) → None
├─ check_data_requirements(Connection) → dict
└─ main() → None
```

#### 5. Resource Log

| Date | Issue/Question | Description | Resource Used | Result |
|------|---------------|-------------|---------------|---------|
| 12/9 | FastF1 installation | msgpack dependency error | pip documentation, --use-pep517 flag | Successfully installed |
| 12/9 | requests.get requirement | How to satisfy requirement with FastF1 | Course guidelines, added explicit call | Met requirement |
| 12/9 | Incremental loading | How to track progress across runs | LoadProgress table design | 25-row limit working |
| 12/9 | Driver matching | Different IDs between APIs | Used driver code as common key | Successful matching |
| 12/9 | API timeouts | Ergast API connection errors | Try-except error handling | Graceful degradation |
| 12/9 | JOIN syntax | SQL JOIN implementation | SQLite documentation | Multiple JOINs working |
| 12/9 | Visualization bug | linewidth parameter conflict | matplotlib/seaborn docs | Fixed parameter name |

#### 6. Running Instructions

**Setup:**
```bash
cd Pole_Position_Analytics
pip install -r requirements.txt
```

**Execution:**
```bash
python -m src.main
```

**Note:** Script has already been run multiple times. Database contains 125+ rows per source.

**To verify:**
```bash
# Check database contents
python -c "
import sqlite3
conn = sqlite3.connect('data/f1_project.db')
cur = conn.cursor()
for table in ['Results', 'LapTimes']:
    cur.execute(f'SELECT COUNT(*) FROM {table}')
    print(f'{table}: {cur.fetchone()[0]} rows')
conn.close()
"
```

---

## 📊 Grading Summary

### Expected Points

| Category | Points | Status |
|----------|--------|--------|
| Data Gathering | 100 | ✅ All requirements met |
| Processing | 50 | ✅ JOIN queries, CSV output |
| Visualizations | 50 | ✅ 4 plots with labels |
| Report & Diagram | 50 | 📝 To be written |
| **Subtotal** | **250** | |
| **Extra Credit** | **+30** | ✅ 2 extra visualizations |
| **TOTAL** | **280/250** | |

---

## 📦 Files to Submit

### Required Files:
1. **All source code** (`src/` directory)
2. **requirements.txt**
3. **README.md**
4. **Database file** (`data/f1_project.db`)
5. **Output files** (`outputs/` directory)
6. **Written report** (PDF or Word document)

### Optional Files:
- `REQUIREMENTS_VERIFICATION.md` (shows compliance)
- `PROJECT_SUMMARY.md` (comprehensive guide)
- This checklist

### DO NOT Include:
- `__pycache__/` directories (already cleaned)
- `.pyc` files (already cleaned)
- `fastf1_cache/` directory (too large, will be regenerated)

---

## ✅ Final Pre-Submission Checklist

- [x] Code runs without errors
- [x] 100+ rows per data source collected
- [x] All CSV files generated
- [x] All visualizations generated
- [x] Code is clean (no __pycache__)
- [ ] Written report completed with screenshots
- [ ] Function diagram included in report
- [ ] Resource log included in report
- [ ] All files packaged for submission

---

## 🚀 Submission Steps

### Step 1: Take Screenshots
Open and screenshot:
- Terminal showing successful run
- Each of the 4 visualization PNG files
- One CSV file opened in Excel/text editor
- Database statistics from terminal

### Step 2: Write Report
Use the template above to write your report. Include:
- All 6 required sections
- All screenshots
- Function diagram
- Resource log table

### Step 3: Package Submission
Create a zip file with:
```bash
cd /Users/Jorge/Desktop/UMich/SI_201-Data_Programming
zip -r Pole_Position_Analytics.zip Pole_Position_Analytics/ \
  -x "*/fastf1_cache/*" \
  -x "*/__pycache__/*" \
  -x "*.pyc"
```

### Step 4: Submit
- Upload zip file to Canvas/submission platform
- Upload written report separately (if required)
- Double-check all files are included

---

## 💡 Tips

1. **Keep it professional** - Your code is well-written and documented
2. **Highlight the technical challenges** - The problems you solved are real
3. **Showcase the visualizations** - They look professional and tell a story
4. **Explain the architecture** - The modular design is a strength
5. **Mention extra credit** - You have 2 extra visualizations (+30 points)

---

## 🎓 Confidence Level: HIGH

Your project:
- ✅ Exceeds all requirements
- ✅ Has professional-quality code
- ✅ Includes extra credit features
- ✅ Is well-documented
- ✅ Has been thoroughly tested

**You're ready to submit! Just write the report and you're done!** 🏁

