"""
Main orchestrator for the F1 Data Analytics Project.
Coordinates data gathering, calculations, and visualizations.

Run this script multiple times to accumulate data (25-row incremental loading).
After 5-10 runs, you should have 100+ rows per source for full analysis.

Authors: David & Alberto
"""

from calculations import OUTPUT_CSV_DIR, run_all_calculations
from db_utils import create_tables, get_connection
from fastf1_api import store_fastf1_data
from jolpica_api import store_jolpica_data
from visualisation import FIG_DIR, generate_all_visualizations


def print_database_stats(conn) -> None:
    """Print current database statistics."""
    cur = conn.cursor()

    # Count rows in each table
    tables = ["Drivers", "Constructors", "Races", "Results", "Sessions", "LapTimes"]

    print("\nCurrent Database Statistics:")
    print("-" * 40)

    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table:20s}: {count:6d} rows")

    print("-" * 40)


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

    print(" Database initialized successfully")

    # Show current stats
    print_database_stats(conn)

    # Step 2: Gather data from Jolpica API
    print("STEP 2: Data Gathering - Jolpica F1 API")

    try:
        jolpica_count = store_jolpica_data(conn)
        print(f"\n Added {jolpica_count} new Results rows from Jolpica API")
    except Exception as e:
        print(f"\n Error gathering Jolpica data: {e}")
        jolpica_count = 0

    # Step 3: Gather data from FastF1
    print("STEP 3: Data Gathering - FastF1")

    try:
        fastf1_count = store_fastf1_data(conn)
        print(f"\n Added {fastf1_count} new LapTimes rows from FastF1")
    except Exception as e:
        print(f"\n Error gathering FastF1 data: {e}")
        fastf1_count = 0

    # Show updated stats
    print_database_stats(conn)

    # Check requirements
    print("STEP 4: Requirements Check")

    req = check_data_requirements(conn)

    print("Data Requirements Status:")
    print("-" * 40)
    print(f"  Results rows:    {req['results_count']:6d} / 100 required")
    print(
        f"    Status: {' MET' if req['results_requirement_met'] else ' NOT MET (need more runs)'}"
    )
    print()
    print(f"  LapTimes rows:   {req['laps_count']:6d} / 100 required")
    print(
        f"    Status: {' MET' if req['laps_requirement_met'] else ' NOT MET (need more runs)'}"
    )
    print()
    print(f"  JOIN feasibility: {' YES' if req['join_feasible'] else ' NO'}")
    print("-" * 40)

    # Estimate runs needed
    if not req["results_requirement_met"] or not req["laps_requirement_met"]:
        results_needed = max(0, 100 - req["results_count"])
        laps_needed = max(0, 100 - req["laps_count"])

        results_runs = (results_needed + 24) // 25  # Round up
        laps_runs = (laps_needed + 24) // 25

        more_runs = max(results_runs, laps_runs)

        print(f"\n💡 Recommendation: Run this script {more_runs} more time(s)")

    # Step 5: Run calculations
    print("STEP 5: Data Analysis & Calculations")

    if req["results_count"] > 0 or req["laps_count"] > 0:
        try:
            calc_results = run_all_calculations(conn)
            print("\n All calculations completed successfully")
            print(f" CSV files written to: {OUTPUT_CSV_DIR}")
        except Exception as e:
            print(f"\n Error during calculations: {e}")
            calc_results = None
    else:
        print(" Skipping calculations - no data available yet")
        print("  Run this script to gather initial data first.")
        calc_results = None

    # Step 6: Generate visualizations
    print("STEP 6: Visualization Generation")

    if calc_results and req["laps_count"] > 0:
        try:
            generate_all_visualizations(conn, calc_results)
            print("\n All visualizations generated successfully")
            print(f" Figures saved to: {FIG_DIR}")
        except Exception as e:
            print(f"\n Error during visualization: {e}")
            import traceback

            traceback.print_exc()
    else:
        print(" Skipping visualizations - insufficient data")
        print("  Need lap time data for visualizations.")

    print("EXECUTION SUMMARY")
    print("Data Gathered This Run:")
    print(f"  • Jolpica Results: {jolpica_count} rows")
    print(f"  • FastF1 LapTimes: {fastf1_count} rows")
    print()
    print("Total Database Contents:")
    print(f"  • Results:   {req['results_count']} rows")
    print(f"  • LapTimes:  {req['laps_count']} rows")
    print(f"  • Races:     {req['total_races']} rows")
    print()

    # Close connection
    conn.close()
    print("\n Done!")


if __name__ == "__main__":
    main()
