"""
Jolpica F1 API integration module.
Fetches race results from the Jolpica F1 API (Ergast-compatible) using requests.get.
Implements incremental loading with a 25-row limit per run.

Author: David
"""

import sqlite3
from typing import Dict, List

import requests

from db_utils import (
    create_tables,
    get_connection,
    get_or_create_constructor,
    get_or_create_driver,
    get_or_create_race,
    get_progress,
    update_progress,
)

BASE_URL = "https://api.jolpi.ca/ergast/f1"
MAX_NEW_RESULTS_PER_RUN = 25
TARGET_SEASONS = [2022, 2023]


def fetch_race_list(seasons: List[int]) -> List[Dict]:
    """
    Fetch the list of races for given seasons from Jolpica F1 API.
    Uses requests.get as required by project specifications.

    Args:
        seasons: List of season years to fetch

    Returns:
        List of race dictionaries with season, round, name, date, circuit info
    """
    all_races = []

    for season in seasons:
        url = f"{BASE_URL}/{season}.json"
        print(f"Fetching race list for {season} from {url}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])

            for race in races:
                race_info = {
                    "season": int(race.get("season")),
                    "round": int(race.get("round")),
                    "race_name": race.get("raceName"),
                    "date": race.get("date"),
                    "circuit_name": race.get("Circuit", {}).get("circuitName"),
                }
                all_races.append(race_info)

            print(f"  Found {len(races)} races for {season}")

        except requests.RequestException as e:
            print(f"Error fetching race list for {season}: {e}")
            continue

    # Sort by season and round
    all_races.sort(key=lambda x: (x["season"], x["round"]))
    return all_races


def fetch_race_results(season: int, round_num: int) -> List[Dict]:
    """
    Fetch race results for a specific race using requests.get.

    Args:
        season: Season year
        round_num: Round number

    Returns:
        List of result dictionaries with driver, constructor, and result info
    """
    url = f"{BASE_URL}/{season}/{round_num}/results.json"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        race_data = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        if not race_data:
            return []

        results = race_data[0].get("Results", [])

        parsed_results = []
        for result in results:
            driver = result.get("Driver", {})
            constructor = result.get("Constructor", {})

            result_info = {
                # Driver info
                "driver_id": driver.get("driverId"),
                "driver_code": driver.get("code"),
                "driver_forename": driver.get("givenName"),
                "driver_surname": driver.get("familyName"),
                "driver_nationality": driver.get("nationality"),
                # Constructor info
                "constructor_id": constructor.get("constructorId"),
                "constructor_name": constructor.get("name"),
                "constructor_nationality": constructor.get("nationality"),
                # Result info
                "grid": int(result.get("grid", 0)),
                "position": int(result.get("position", 0))
                if result.get("position")
                else None,
                "points": float(result.get("points", 0)),
                "status": result.get("status"),
            }
            parsed_results.append(result_info)

        return parsed_results

    except requests.RequestException as e:
        print(f"Error fetching results for {season} round {round_num}: {e}")
        return []


def store_jolpica_data(conn: sqlite3.Connection) -> int:
    """
    Main function to fetch and store Jolpica F1 data with 25-row limit.
    Tracks progress to ensure incremental loading without duplicates.

    Args:
        conn: Database connection

    Returns:
        Number of new Results rows added
    """
    # Get current progress
    progress = get_progress(conn, "jolpica")

    if progress:
        start_season, start_round, _ = progress
        print(f"Resuming from season {start_season}, round {start_round + 1}")
    else:
        start_season = TARGET_SEASONS[0]
        start_round = 0
        print(f"Starting fresh from season {start_season}")

    # Fetch all races for target seasons
    all_races = fetch_race_list(TARGET_SEASONS)

    # Filter races to process (from last checkpoint)
    races_to_process = []
    for race in all_races:
        if race["season"] > start_season or (
            race["season"] == start_season and race["round"] > start_round
        ):
            races_to_process.append(race)

    if not races_to_process:
        print("No new races to process")
        return 0

    print(f"Processing up to {MAX_NEW_RESULTS_PER_RUN} new results...")

    new_rows_inserted = 0
    cur = conn.cursor()

    for race in races_to_process:
        season = race["season"]
        round_num = race["round"]

        # Check if we've hit the limit
        if new_rows_inserted >= MAX_NEW_RESULTS_PER_RUN:
            print(f"Reached limit of {MAX_NEW_RESULTS_PER_RUN} new rows")
            break

        print(f"Processing {season} Round {round_num}: {race['race_name']}")

        # Get or create race record
        race_id = get_or_create_race(
            conn,
            season=season,
            round_num=round_num,
            race_name=race["race_name"],
            date=race["date"],
            circuit_name=race["circuit_name"],
        )

        # Fetch results for this race
        results = fetch_race_results(season, round_num)

        if not results:
            print("  No results found, skipping")
            continue

        # Process each result
        for result in results:
            # Check limit again
            if new_rows_inserted >= MAX_NEW_RESULTS_PER_RUN:
                break

            # Get or create driver
            driver_id = get_or_create_driver(
                conn,
                api_driver_id=result["driver_id"],
                code=result["driver_code"],
                forename=result["driver_forename"],
                surname=result["driver_surname"],
                nationality=result["driver_nationality"],
            )

            # Get or create constructor
            constructor_id = get_or_create_constructor(
                conn,
                api_constructor_id=result["constructor_id"],
                name=result["constructor_name"],
                nationality=result["constructor_nationality"],
            )

            # Insert result (INSERT OR IGNORE handles duplicates)
            cur.execute(
                """
                INSERT OR IGNORE INTO Results 
                (race_id, driver_id, constructor_id, grid, position, points, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    race_id,
                    driver_id,
                    constructor_id,
                    result["grid"],
                    result["position"],
                    result["points"],
                    result["status"],
                ),
            )

            # Check if a row was actually inserted
            if cur.rowcount > 0:
                new_rows_inserted += 1

        # Update progress after each race
        update_progress(conn, "jolpica", season, round_num)

        print(f"  Added {cur.rowcount} results (total new: {new_rows_inserted})")

        # If we hit the limit, stop processing more races
        if new_rows_inserted >= MAX_NEW_RESULTS_PER_RUN:
            break

    conn.commit()
    print(f"Total new Results rows added: {new_rows_inserted}")
    return new_rows_inserted


if __name__ == "__main__":
    # Test the module independently
    conn = get_connection()
    create_tables(conn)
    count = store_jolpica_data(conn)
    print(f"Completed: {count} new rows added")
    conn.close()
