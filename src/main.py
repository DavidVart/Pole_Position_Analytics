"""
Main orchestrator for the F1 Data Analytics Project.
Coordinates data gathering, calculations, and visualizations.

Run this script multiple times to accumulate data (25-row incremental loading).
After 5-10 runs, you should have 100+ rows per source for full analysis.

Authors: David & Alberto
"""

import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from . import calculations, db_utils, fastf1_api, jolpica_api, visualisation


def print_banner(text: str) -> None:
    """Print a formatted banner."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


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

    print_banner("F1 DATA ANALYTICS PROJECT")
    print("Pole Position Analytics")
    print("Authors: David & Alberto")

    # Step 1: Initialize database
    print_banner("STEP 1: Database Setup")

    conn = db_utils.get_connection()
    db_utils.create_tables(conn)
    print("✓ Database initialized successfully")

    # Show current stats
    print_database_stats(conn)

    # Step 2: Gather data from Jolpica API
    print_banner("STEP 2: Data Gathering - Jolpica F1 API")

    try:
        jolpica_count = jolpica_api.store_jolpica_data(conn)
        print(f"\n✓ Added {jolpica_count} new Results rows from Jolpica API")
    except Exception as e:
        print(f"\n✗ Error gathering Jolpica data: {e}")
        jolpica_count = 0

    # Step 3: Gather data from FastF1
    print_banner("STEP 3: Data Gathering - FastF1")

    try:
        fastf1_count = fastf1_api.store_fastf1_data(conn)
        print(f"\n✓ Added {fastf1_count} new LapTimes rows from FastF1")
    except Exception as e:
        print(f"\n✗ Error gathering FastF1 data: {e}")
        fastf1_count = 0

    # Show updated stats
    print_database_stats(conn)

    # Check requirements
    print_banner("STEP 4: Requirements Check")

    req = check_data_requirements(conn)

    print("Data Requirements Status:")
    print("-" * 40)
    print(f"  Results rows:    {req['results_count']:6d} / 100 required")
    print(
        f"    Status: {'✓ MET' if req['results_requirement_met'] else '✗ NOT MET (need more runs)'}"
    )
    print()
    print(f"  LapTimes rows:   {req['laps_count']:6d} / 100 required")
    print(
        f"    Status: {'✓ MET' if req['laps_requirement_met'] else '✗ NOT MET (need more runs)'}"
    )
    print()
    print(f"  JOIN feasibility: {'✓ YES' if req['join_feasible'] else '✗ NO'}")
    print("-" * 40)

    # Estimate runs needed
    if not req["results_requirement_met"] or not req["laps_requirement_met"]:
        results_needed = max(0, 100 - req["results_count"])
        laps_needed = max(0, 100 - req["laps_count"])

        results_runs = (results_needed + 24) // 25  # Round up
        laps_runs = (laps_needed + 24) // 25

        more_runs = max(results_runs, laps_runs)

        print(f"\n💡 Recommendation: Run this script {more_runs} more time(s)")
        print("   to meet the 100-row requirement for both data sources.")

    # Step 5: Run calculations
    print_banner("STEP 5: Data Analysis & Calculations")

    if req["results_count"] > 0 or req["laps_count"] > 0:
        try:
            calc_results = calculations.run_all_calculations(conn)
            print("\n✓ All calculations completed successfully")
            print(f"✓ CSV files written to: {calculations.OUTPUT_CSV_DIR}")
        except Exception as e:
            print(f"\n✗ Error during calculations: {e}")
            calc_results = None
    else:
        print("⚠ Skipping calculations - no data available yet")
        print("  Run this script to gather initial data first.")
        calc_results = None

    # Step 6: Generate visualizations
    print_banner("STEP 6: Visualization Generation")

    if calc_results and req["laps_count"] > 0:
        try:
            visualisation.generate_all_visualizations(conn, calc_results)
            print("\n✓ All visualizations generated successfully")
            print(f"✓ Figures saved to: {visualisation.FIG_DIR}")
        except Exception as e:
            print(f"\n✗ Error during visualization: {e}")
            import traceback

            traceback.print_exc()
    else:
        print("⚠ Skipping visualizations - insufficient data")
        print("  Need lap time data for visualizations.")

    # Final summary
    print_banner("EXECUTION SUMMARY")

    print("Data Gathered This Run:")
    print(f"  • Jolpica Results: {jolpica_count} rows")
    print(f"  • FastF1 LapTimes: {fastf1_count} rows")
    print()
    print("Total Database Contents:")
    print(f"  • Results:   {req['results_count']} rows")
    print(f"  • LapTimes:  {req['laps_count']} rows")
    print(f"  • Races:     {req['total_races']} rows")
    print()

    if req["results_requirement_met"] and req["laps_requirement_met"]:
        print("🎉 SUCCESS: All data requirements met!")
        print("   Your project is ready for submission.")
        print()
        print("Output locations:")
        print("  • Database:      data/f1_project.db")
        print("  • CSV files:     outputs/csv/")
        print("  • Visualizations: outputs/figures/")
    else:
        print("📊 In Progress: Continue running to gather more data")
        print()
        print("Next steps:")
        print("  1. Run this script again (no code changes needed)")
        print("  2. Each run adds up to 25 rows per source")
        print("  3. Repeat until both sources have 100+ rows")

    # Close connection
    conn.close()
    print("\n" + "=" * 70)
    print("Done!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
