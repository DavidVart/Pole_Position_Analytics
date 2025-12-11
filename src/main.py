"""
Main orchestrator for the F1 Data Analytics Project.
Coordinates data gathering, calculations, and visualizations.

Run this script multiple times to accumulate data (25-row incremental loading).
After 5-10 runs, you should have 100+ rows per source for full analysis.

Authors: David & Alberto
"""

from calculations import run_all_calculations
from db_utils import create_tables, get_connection
from fastf1_api import store_fastf1_data
from jolpica_api import store_jolpica_data
from visualisation import generate_all_visualizations


def print_database_stats(conn) -> None:
    """Print current database statistics."""
    cur = conn.cursor()

    # Count rows in each table
    tables = ["Drivers", "Constructors", "Races", "Results", "Sessions", "LapTimes"]

    print("\nDatabase Statistics:")

    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count} rows")


def check_data_requirements(conn) -> dict:
    """
    Check if we have met the project requirements.

    Returns:
        Dictionary with requirement status
    """
    cur = conn.cursor()

    # Check Results count (from Jolpica API)
    cur.execute("SELECT COUNT(*) FROM Results")
    results_count = cur.fetchone()[0]

    # Check LapTimes count (from FastF1 API)
    cur.execute("SELECT COUNT(*) FROM LapTimes")
    laps_count = cur.fetchone()[0]

    # Check for JOIN feasibility (different row counts in related tables)
    cur.execute("SELECT COUNT(DISTINCT race_id) FROM Results")
    races_with_results = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM Races")
    total_races = cur.fetchone()[0]

    requirements = {
        "results_count": results_count,
        "results_requirement_met": results_count >= 100,
        "laps_count": laps_count,
        "laps_requirement_met": laps_count >= 100,
        "total_races": total_races,
        "races_with_results": races_with_results,
        "join_feasible": races_with_results > 0 and total_races > 0,
    }

    return requirements


def main():
    """Main execution function."""

    conn = get_connection()
    create_tables(conn)

    print_database_stats(conn)

    try:
        jolpica_count = store_jolpica_data(conn)
    except Exception as e:
        print(f"Error gathering Jolpica data: {e}")
        jolpica_count = 0

    try:
        fastf1_count = store_fastf1_data(conn)
    except Exception as e:
        print(f"Error gathering FastF1 data: {e}")
        fastf1_count = 0

    print_database_stats(conn)

    req = check_data_requirements(conn)

    if req["results_count"] > 0 or req["laps_count"] > 0:
        try:
            calc_results = run_all_calculations(conn)
        except Exception as e:
            print(f"Error during calculations: {e}")
            calc_results = None
    else:
        print("Skipping calculations - no data available")
        calc_results = None

    if calc_results and req["laps_count"] > 0:
        try:
            generate_all_visualizations(conn, calc_results)
        except Exception as e:
            print(f"Error during visualization: {e}")

    print("\nExecution Summary:")
    print(f"  New data: {jolpica_count} Results, {fastf1_count} LapTimes")
    print(
        f"  Total: {req['results_count']} Results, {req['laps_count']} LapTimes, {req['total_races']} Races"
    )

    conn.close()


if __name__ == "__main__":
    main()
