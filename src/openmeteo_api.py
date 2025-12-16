"""
Open-Meteo API integration module.
Fetches historical weather data from the Open-Meteo Historical Weather API.
Implements incremental loading with a 30-observation limit per run.

Author: Alberto
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests

from clean_data import clean_float, clean_string
from db_utils import (
    get_circuit_coordinates,
    get_progress,
    update_circuit_coordinates,
    update_progress,
)

OPENMETEO_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
MAX_NEW_OBSERVATIONS_PER_RUN = 25
TARGET_YEAR = 2023

# Jolpica base URL to fetch circuit coordinates from metadata
JOLPICA_BASE_URL = "https://api.jolpi.ca/ergast/f1"


def fetch_weather_data(
    latitude: float, longitude: float, start_date: str, end_date: str
) -> List[Dict]:
    """
    Fetch hourly weather data from Open-Meteo Historical Weather API.
    Uses requests.get as required by project specifications.

    Args:
        latitude: Circuit latitude
        longitude: Circuit longitude
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of hourly weather observation dictionaries
    """
    url = OPENMETEO_BASE_URL
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,windspeed_10m,precipitation",
        "timezone": "auto",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Extract hourly data
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temperatures = hourly.get("temperature_2m", [])
        wind_speeds = hourly.get("windspeed_10m", [])
        precipitations = hourly.get("precipitation", [])

        observations = []
        for i, timestamp in enumerate(times):
            observation = {
                "timestamp": timestamp,
                "temperature_c": temperatures[i] if i < len(temperatures) else None,
                "wind_speed": wind_speeds[i] if i < len(wind_speeds) else None,
                "precipitation_mm": precipitations[i]
                if i < len(precipitations)
                else None,
            }
            observations.append(observation)

        return observations

    except requests.RequestException as e:
        print(f"Error fetching weather data for {latitude},{longitude}: {e}")
        return []


def date_int_to_string(date_int: Optional[int]) -> Optional[str]:
    """
    Convert date integer (YYYYMMDD) to string (YYYY-MM-DD).

    Args:
        date_int: Date as integer in YYYYMMDD format

    Returns:
        Date string in YYYY-MM-DD format or None
    """
    if date_int is None:
        return None

    date_str = str(date_int)
    if len(date_str) != 8:
        return None

    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"


def fetch_circuit_coords_from_jolpica(
    season: int, round_num: int
) -> Optional[Tuple[float, float]]:
    """
    Fetch circuit coordinates for a given race from the Jolpica API.

    Args:
        season: Season year
        round_num: Round number

    Returns:
        Tuple of (latitude, longitude) or None if not available
    """
    url = f"{JOLPICA_BASE_URL}/{season}/{round_num}.json"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        if not races:
            return None

        circuit = races[0].get("Circuit", {})
        location = circuit.get("Location", {})

        lat = clean_float(location.get("lat"))
        lon = clean_float(location.get("long"))

        if lat is None or lon is None:
            return None

        return lat, lon
    except requests.RequestException as e:
        print(f"Error fetching circuit coordinates for {season} round {round_num}: {e}")
        return None


def ensure_circuit_coordinates_from_jolpica(
    conn: sqlite3.Connection, circuit_id: int, season: int, round_num: int
) -> bool:
    """
    Ensure that a circuit has coordinates by fetching them from Jolpica if missing.

    Args:
        conn: Database connection
        circuit_id: Circuit ID
        season: Season year
        round_num: Round number

    Returns:
        True if coordinates are present or successfully updated, False otherwise
    """
    # If we already have coordinates, nothing to do
    coords = get_circuit_coordinates(conn, circuit_id)
    if coords is not None:
        return True

    # Try to fetch coordinates from Jolpica
    new_coords = fetch_circuit_coords_from_jolpica(season, round_num)
    if new_coords is None:
        return False

    # Look up circuit name for the given circuit_id
    cur = conn.cursor()
    cur.execute("SELECT circuit_name FROM Circuits WHERE circuit_id = ?", (circuit_id,))
    row = cur.fetchone()

    if not row or row[0] is None:
        return False

    circuit_name = row[0]

    # Update coordinates in the Circuits table
    updated = update_circuit_coordinates(
        conn, circuit_name, new_coords[0], new_coords[1]
    )

    return updated


def get_race_weekend_dates(
    conn: sqlite3.Connection, race_id: int
) -> Optional[Tuple[str, str]]:
    """
    Determine start and end dates for race weekend.
    Start: Friday before race (or race date if not available)
    End: Sunday after race (or race date + 1 day)

    Args:
        conn: Database connection
        race_id: Race ID

    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format, or None if race not found
    """
    cur = conn.cursor()
    cur.execute("SELECT date FROM Races WHERE race_id = ?", (race_id,))
    row = cur.fetchone()

    if not row or row[0] is None:
        return None

    race_date_int = row[0]
    race_date_str = date_int_to_string(race_date_int)

    if race_date_str is None:
        return None

    try:
        race_date = datetime.strptime(race_date_str, "%Y-%m-%d")
        # Start: Friday before race (3 days before)
        start_date = race_date - timedelta(days=3)
        # End: Sunday after race (1 day after)
        end_date = race_date + timedelta(days=1)

        return (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    except ValueError:
        return None


def store_openmeteo_data(conn: sqlite3.Connection) -> int:
    """
    Main function to fetch and store Open-Meteo weather data with 30-observation limit.
    Uses explicit requests.get calls to satisfy project requirements.

    Args:
        conn: Database connection

    Returns:
        Number of new weather observation rows added
    """
    # Get current progress
    progress = get_progress(conn, "openmeteo")

    last_season = 0
    last_round = 0

    if progress:
        last_season = progress[0] or 0
        last_round = progress[1] or 0

    # Get all races for target year, ordered by season and round
    cur = conn.cursor()
    cur.execute(
        """
        SELECT race_id, season, round, circuit_id
        FROM Races
        WHERE season = ?
        ORDER BY season, round
        """,
        (TARGET_YEAR,),
    )
    races = cur.fetchall()

    if not races:
        print(f"No races found for {TARGET_YEAR}")
        return 0

    new_observations_inserted = 0

    for race_id, season, round_num, circuit_id in races:
        # Skip already processed races
        if season == last_season and round_num <= last_round:
            continue

        if new_observations_inserted >= MAX_NEW_OBSERVATIONS_PER_RUN:
            break

        # Get circuit coordinates
        if circuit_id is None:
            continue

        coords = get_circuit_coordinates(conn, circuit_id)
        if coords is None:
            # Try to backfill coordinates from Jolpica metadata
            if ensure_circuit_coordinates_from_jolpica(
                conn, circuit_id, season, round_num
            ):
                coords = get_circuit_coordinates(conn, circuit_id)
            else:
                print(
                    f"Warning: No coordinates for circuit_id {circuit_id}, "
                    f"skipping race {season} R{round_num}"
                )
                # Update progress even if skipped
                update_progress(conn, "openmeteo", season, round_num)
                continue

        if coords is None:
            # Extra safety check to satisfy type checkers
            continue

        latitude, longitude = coords

        # Get race weekend date range
        date_range = get_race_weekend_dates(conn, race_id)
        if date_range is None:
            print(f"Warning: Could not determine dates for race {season} R{round_num}")
            update_progress(conn, "openmeteo", season, round_num)
            continue

        start_date, end_date = date_range

        # Fetch weather data
        observations = fetch_weather_data(latitude, longitude, start_date, end_date)

        if not observations:
            print(f"No weather data fetched for race {season} R{round_num}")
            update_progress(conn, "openmeteo", season, round_num)
            continue

        # Store observations (respecting limit)
        for obs in observations:
            if new_observations_inserted >= MAX_NEW_OBSERVATIONS_PER_RUN:
                break

            timestamp = clean_string(obs.get("timestamp"))
            temperature_c = clean_float(obs.get("temperature_c"))
            wind_speed = clean_float(obs.get("wind_speed"))
            precipitation_mm = clean_float(obs.get("precipitation_mm"))

            if timestamp is None:
                continue

            try:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO Weather
                    (race_id, timestamp, temperature_c, wind_speed, precipitation_mm, source)
                    VALUES (?, ?, ?, ?, ?, 'open-meteo')
                    """,
                    (race_id, timestamp, temperature_c, wind_speed, precipitation_mm),
                )

                if cur.rowcount > 0:
                    new_observations_inserted += 1

            except sqlite3.IntegrityError:
                # Skip duplicate observations
                continue

        # Update progress after each race
        update_progress(conn, "openmeteo", season, round_num)

        if new_observations_inserted >= MAX_NEW_OBSERVATIONS_PER_RUN:
            break

    conn.commit()
    return new_observations_inserted


if __name__ == "__main__":
    # Test the module independently
    from db_utils import create_tables, get_connection

    conn = get_connection()
    create_tables(conn)
    count = store_openmeteo_data(conn)
    print(f"Completed: {count} new weather observations added")
    conn.close()
