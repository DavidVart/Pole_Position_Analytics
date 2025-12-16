"""
Calculations module for F1 project.
Performs SQL queries with JOINs, computes statistics, and writes results to CSV files.
Does not fetch new data - only processes existing database data.

Authors: David & Alberto
"""

import sqlite3
from pathlib import Path
from typing import Tuple

import pandas as pd

from db_utils import get_connection

OUTPUT_CSV_DIR = Path("outputs/csv")
OUTPUT_CSV_DIR.mkdir(parents=True, exist_ok=True)


def write_to_csv(df: pd.DataFrame, filename: str) -> None:
    """
    Write a DataFrame to a CSV file in the output directory.

    Args:
        df: DataFrame to write
        filename: Output filename (without path)
    """
    output_path = OUTPUT_CSV_DIR / filename
    df.to_csv(output_path, index=False)


def compute_average_lap_times(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Calculate average lap time per driver per race using JOIN queries.
    This satisfies the requirement for JOIN-based calculations.

    Args:
        conn: Database connection

    Returns:
        DataFrame with average lap times
    """
    query = """
        SELECT
            R.season,
            R.round,
            RN.race_name,
            D.code AS driver_code,
            D.forename,
            D.surname,
            AVG(L.lap_time_ms) AS avg_lap_time_ms,
            COUNT(*) AS lap_count,
            MIN(L.lap_time_ms) AS fastest_lap_ms,
            MAX(L.lap_time_ms) AS slowest_lap_ms
        FROM LapTimes L
        JOIN Sessions S ON L.session_id = S.session_id
        JOIN SessionTypes ST ON S.session_type_id = ST.session_type_id
        JOIN Races R ON S.race_id = R.race_id
        LEFT JOIN RaceNames RN ON R.race_name_id = RN.race_name_id
        JOIN Drivers D ON L.driver_id = D.driver_id
        WHERE L.lap_time_ms IS NOT NULL
        GROUP BY R.season, R.round, D.driver_id
        ORDER BY R.season, R.round, avg_lap_time_ms
    """

    df = pd.read_sql_query(query, conn)

    if not df.empty:
        # Convert milliseconds to seconds for readability
        df["avg_lap_time_sec"] = df["avg_lap_time_ms"] / 1000
        df["fastest_lap_sec"] = df["fastest_lap_ms"] / 1000
        df["slowest_lap_sec"] = df["slowest_lap_ms"] / 1000

        write_to_csv(df, "avg_lap_times.csv")

    return df


def compute_grid_vs_finish(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Calculate position changes from grid to finish for each driver.
    Uses JOIN to combine Results, Races, and Drivers tables.

    Args:
        conn: Database connection

    Returns:
        DataFrame with grid vs finish analysis
    """
    query = """
        SELECT
            R.season,
            R.round,
            RN.race_name,
            D.code AS driver_code,
            D.forename,
            D.surname,
            C.name AS constructor,
            Res.grid,
            Res.position,
            (Res.grid - Res.position) AS positions_gained,
            Res.points,
            Stat.status_text AS status
        FROM Results Res
        JOIN Races R ON Res.race_id = R.race_id
        LEFT JOIN RaceNames RN ON R.race_name_id = RN.race_name_id
        JOIN Drivers D ON Res.driver_id = D.driver_id
        JOIN Constructors C ON Res.constructor_id = C.constructor_id
        LEFT JOIN Statuses Stat ON Res.status_id = Stat.status_id
        WHERE Res.grid > 0 AND Res.position IS NOT NULL
        ORDER BY R.season, R.round, Res.position
    """

    df = pd.read_sql_query(query, conn)

    if not df.empty:
        write_to_csv(df, "grid_vs_finish.csv")

    return df


def compute_tyre_performance(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Calculate average lap time by tyre compound.

    Args:
        conn: Database connection

    Returns:
        DataFrame with tyre performance statistics
    """
    query = """
        SELECT
            C.compound_name AS compound,
            AVG(L.lap_time_ms) AS avg_lap_time_ms,
            MIN(L.lap_time_ms) AS fastest_lap_ms,
            MAX(L.lap_time_ms) AS slowest_lap_ms,
            COUNT(*) AS lap_count,
            COUNT(DISTINCT L.driver_id) AS driver_count
        FROM LapTimes L
        JOIN Compounds C ON L.compound_id = C.compound_id
        WHERE L.compound_id IS NOT NULL AND L.lap_time_ms IS NOT NULL
        GROUP BY C.compound_id
        ORDER BY avg_lap_time_ms
    """

    df = pd.read_sql_query(query, conn)

    if not df.empty:
        # Convert to seconds
        df["avg_lap_time_sec"] = df["avg_lap_time_ms"] / 1000
        df["fastest_lap_sec"] = df["fastest_lap_ms"] / 1000
        df["slowest_lap_sec"] = df["slowest_lap_ms"] / 1000

        write_to_csv(df, "tyre_performance.csv")

    return df


def correlate_temp_lap_time(conn: sqlite3.Connection) -> Tuple[float, pd.DataFrame]:
    """
    Calculate correlation between air temperature (Open-Meteo) and average lap time.
    Uses JOIN to combine Weather, Races, Sessions, and LapTimes data.

    Args:
        conn: Database connection

    Returns:
        Tuple of (correlation coefficient, DataFrame with data)
    """
    query = """
        SELECT
            R.race_id,
            R.season,
            R.round,
            RN.race_name,
            AVG(WO.temperature_c) AS avg_temperature_c,
            AVG(L.lap_time_ms) AS avg_lap_time_ms,
            COUNT(DISTINCT WO.weather_id) AS weather_obs_count,
            COUNT(*) AS lap_count
        FROM Weather WO
        JOIN Races R ON WO.race_id = R.race_id
        LEFT JOIN RaceNames RN ON R.race_name_id = RN.race_name_id
        JOIN Sessions S ON R.race_id = S.race_id
        JOIN SessionTypes ST ON S.session_type_id = ST.session_type_id
        JOIN LapTimes L ON S.session_id = L.session_id
        WHERE ST.session_type_code = 'R'
          AND WO.temperature_c IS NOT NULL
          AND L.lap_time_ms IS NOT NULL
        GROUP BY R.race_id
        ORDER BY R.season, R.round
    """

    df = pd.read_sql_query(query, conn)

    correlation = 0.0

    if not df.empty and len(df) > 1:
        # Convert to seconds
        df["avg_lap_time_sec"] = df["avg_lap_time_ms"] / 1000

        # Calculate correlation
        correlation = df["avg_temperature_c"].corr(df["avg_lap_time_ms"])
        write_to_csv(df, "temp_vs_lap_openmeteo.csv")

    return correlation, df


def compute_driver_statistics(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Calculate overall driver statistics across all races.
    Combines data from multiple tables using JOINs.

    Args:
        conn: Database connection

    Returns:
        DataFrame with driver statistics
    """
    query = """
        SELECT
            D.code AS driver_code,
            D.forename,
            D.surname,
            N.nationality_name AS nationality,
            COUNT(DISTINCT Res.race_id) AS races_entered,
            SUM(Res.points) AS total_points,
            AVG(Res.position) AS avg_finish_position,
            COUNT(CASE WHEN Res.position = 1 THEN 1 END) AS wins,
            COUNT(CASE WHEN Res.position <= 3 THEN 1 END) AS podiums,
            COUNT(CASE WHEN Res.position <= 10 THEN 1 END) AS points_finishes
        FROM Drivers D
        LEFT JOIN Nationalities N ON D.nationality_id = N.nationality_id
        JOIN Results Res ON D.driver_id = Res.driver_id
        WHERE Res.position IS NOT NULL
        GROUP BY D.driver_id
        ORDER BY total_points DESC
    """

    df = pd.read_sql_query(query, conn)

    if not df.empty:
        write_to_csv(df, "driver_statistics.csv")

    return df


def compute_constructor_standings(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Calculate constructor championship standings.

    Args:
        conn: Database connection

    Returns:
        DataFrame with constructor standings
    """
    query = """
        SELECT
            C.name AS constructor,
            N.nationality_name AS nationality,
            COUNT(DISTINCT R.race_id) AS races,
            SUM(Res.points) AS total_points,
            COUNT(CASE WHEN Res.position = 1 THEN 1 END) AS wins,
            COUNT(CASE WHEN Res.position <= 3 THEN 1 END) AS podiums
        FROM Constructors C
        LEFT JOIN Nationalities N ON C.nationality_id = N.nationality_id
        JOIN Results Res ON C.constructor_id = Res.constructor_id
        JOIN Races R ON Res.race_id = R.race_id
        WHERE Res.position IS NOT NULL
        GROUP BY C.constructor_id
        ORDER BY total_points DESC
    """

    df = pd.read_sql_query(query, conn)

    if not df.empty:
        write_to_csv(df, "constructor_standings.csv")

    return df


def run_all_calculations(conn: sqlite3.Connection) -> dict:
    """
    Run all calculation functions and return results.

    Args:
        conn: Database connection

    Returns:
        Dictionary with all calculation results
    """
    results = {
        "avg_lap_times": compute_average_lap_times(conn),
        "grid_vs_finish": compute_grid_vs_finish(conn),
        "tyre_performance": compute_tyre_performance(conn),
        "driver_statistics": compute_driver_statistics(conn),
        "constructor_standings": compute_constructor_standings(conn),
    }

    # Temperature correlation returns tuple
    corr, temp_df = correlate_temp_lap_time(conn)
    results["temp_correlation"] = corr
    results["temp_lap_data"] = temp_df

    return results


if __name__ == "__main__":
    # Test the module independently
    conn = get_connection()
    results = run_all_calculations(conn)

    # Print summary
    print("\nSummary:")
    for key, value in results.items():
        if isinstance(value, pd.DataFrame):
            print(f"  {key}: {len(value)} rows")
        else:
            print(f"  {key}: {value}")

    conn.close()
