"""
OpenF1 API integration module.
Fetches lap times and telemetry data directly from the OpenF1 REST API using requests.get.
Implements incremental loading with a 25-row limit per run.

Author: Alberto
"""

import sqlite3
from typing import Any, Dict, List, Optional

import requests

from clean_data import clean_float, clean_integer, clean_string
from db_utils import (
    create_tables,
    get_connection,
    get_driver_by_code,
    get_or_create_circuit,
    get_or_create_compound,
    get_or_create_driver,
    get_or_create_race,
    get_or_create_session_type,
    get_progress,
    update_progress,
)

MAX_NEW_LAPS_PER_RUN = 25
OPENF1_BASE_URL = "https://api.openf1.org/v1"

TARGET_YEAR = 2023

# Only process Race and Qualifying sessions
TARGET_SESSION_NAMES = ["Race", "Qualifying"]


def fetch_meetings(year: int) -> List[Dict]:
    """
    Fetch all meetings (Grand Prix weekends) for a given year.
    Uses requests.get as required by project specifications.

    Args:
        year: Season year

    Returns:
        List of meeting dictionaries sorted by date
    """
    url = f"{OPENF1_BASE_URL}/meetings"
    params = {"year": year}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        meetings = response.json()
        # Sort by date_start to determine round order
        meetings.sort(key=lambda x: x.get("date_start", ""))
        return meetings
    except requests.RequestException as e:
        print(f"Error fetching meetings for {year}: {e}")
        return []


def fetch_sessions_for_meeting(meeting_key: int) -> List[Dict]:
    """
    Fetch Race and Qualifying sessions for a given meeting.
    Uses requests.get as required by project specifications.

    Args:
        meeting_key: Unique identifier for the meeting

    Returns:
        List of session dictionaries (filtered to R and Q only)
    """
    url = f"{OPENF1_BASE_URL}/sessions"
    params = {"meeting_key": meeting_key}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        sessions = response.json()
        # Filter to only Race and Qualifying
        filtered = [
            s for s in sessions if s.get("session_name") in TARGET_SESSION_NAMES
        ]
        # Sort by session_key for consistent ordering
        filtered.sort(key=lambda x: x.get("session_key", 0))
        return filtered
    except requests.RequestException as e:
        print(f"Error fetching sessions for meeting {meeting_key}: {e}")
        return []


def fetch_drivers(session_key: int) -> List[Dict]:
    """
    Fetch driver information for a given session.
    Uses requests.get as required by project specifications.

    Args:
        session_key: Unique identifier for the session

    Returns:
        List of driver dictionaries
    """
    url = f"{OPENF1_BASE_URL}/drivers"
    params = {"session_key": session_key}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching drivers for session {session_key}: {e}")
        return []


def fetch_all_laps(session_key: int) -> List[Dict]:
    """
    Fetch all lap data for a session (all drivers at once).
    Uses requests.get as required by project specifications.

    Args:
        session_key: Unique identifier for the session

    Returns:
        List of lap dictionaries for all drivers
    """
    url = f"{OPENF1_BASE_URL}/laps"
    params = {"session_key": session_key}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching laps for session {session_key}: {e}")
        return []


def fetch_all_stints(session_key: int) -> List[Dict]:
    """
    Fetch all stint data for a session (all drivers at once).
    Uses requests.get as required by project specifications.

    Args:
        session_key: Unique identifier for the session

    Returns:
        List of stint dictionaries for all drivers
    """
    url = f"{OPENF1_BASE_URL}/stints"
    params = {"session_key": session_key}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching stints for session {session_key}: {e}")
        return []


def fetch_weather(session_key: int) -> List[Dict]:
    """
    Fetch weather data for a session.
    Uses requests.get as required by project specifications.

    Args:
        session_key: Unique identifier for the session

    Returns:
        List of weather dictionaries
    """
    url = f"{OPENF1_BASE_URL}/weather"
    params = {"session_key": session_key}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching weather for session {session_key}: {e}")
        return []


def group_by_driver(data: List[Dict]) -> Dict[int, List[Dict]]:
    """
    Group a list of dictionaries by driver_number.

    Args:
        data: List of dictionaries with driver_number field

    Returns:
        Dictionary mapping driver_number to list of records
    """
    grouped: Dict[int, List[Dict]] = {}
    for item in data:
        driver_num = item.get("driver_number")
        if driver_num is not None:
            if driver_num not in grouped:
                grouped[driver_num] = []
            grouped[driver_num].append(item)
    return grouped


def get_compound_for_lap(stints: List[Dict], lap_number: int) -> Optional[str]:
    """
    Determine the tyre compound for a specific lap based on stint data.

    Args:
        stints: List of stint dictionaries for a driver
        lap_number: The lap number to look up

    Returns:
        Compound name or None if not found
    """
    for stint in stints:
        lap_start = stint.get("lap_start")
        lap_end = stint.get("lap_end")

        if lap_start is not None and lap_end is not None:
            if lap_start <= lap_number <= lap_end:
                return clean_string(stint.get("compound"))

    return None


def is_fresh_tyre_for_lap(stints: List[Dict], lap_number: int) -> int:
    """
    Determine if the tyre was fresh for the entire stint containing this lap.

    Args:
        stints: List of stint dictionaries for a driver
        lap_number: The lap number to check

    Returns:
        1 if fresh tyre (tyre_age_at_start == 0 for the stint), 0 otherwise
    """
    for stint in stints:
        lap_start = stint.get("lap_start")
        lap_end = stint.get("lap_end")

        if lap_start is not None and lap_end is not None:
            if lap_start <= lap_number <= lap_end:
                return 1 if stint.get("tyre_age_at_start", 0) == 0 else 0

    return 0


def compute_average_weather(weather_data: List[Dict]) -> Dict[str, Optional[float]]:
    """
    Compute average weather metrics from weather data list.

    Args:
        weather_data: List of weather dictionaries

    Returns:
        Dictionary with average track_temp, humidity, wind_speed
    """
    result: Dict[str, Optional[float]] = {
        "track_temp": None,
        "humidity": None,
        "wind_speed": None,
    }

    if not weather_data:
        return result

    track_temps = []
    humidities = []
    wind_speeds = []

    for w in weather_data:
        if w.get("track_temperature") is not None:
            track_temps.append(w["track_temperature"])
        if w.get("humidity") is not None:
            humidities.append(w["humidity"])
        if w.get("wind_speed") is not None:
            wind_speeds.append(w["wind_speed"])

    if track_temps:
        result["track_temp"] = sum(track_temps) / len(track_temps)
    if humidities:
        result["humidity"] = sum(humidities) / len(humidities)
    if wind_speeds:
        result["wind_speed"] = sum(wind_speeds) / len(wind_speeds)

    return result


def map_session_type(session_name: str) -> str:
    """
    Map OpenF1 session names to session type codes.

    Args:
        session_name: OpenF1 session name (e.g., 'Race', 'Qualifying')

    Returns:
        Session type code (e.g., 'R', 'Q')
    """
    mapping = {
        "Race": "R",
        "Qualifying": "Q",
    }
    return mapping.get(session_name, session_name[:3].upper())


def get_or_create_session(
    conn: sqlite3.Connection,
    race_id: int,
    session_type_code: str,
    weather_data: Dict[str, Optional[float]],
) -> int:
    """
    Get or create a session record.

    Args:
        conn: Database connection
        race_id: Race ID
        session_type_code: Session type code ('R', 'Q')
        weather_data: Weather metrics dictionary

    Returns:
        session_id
    """
    cur = conn.cursor()

    # Get or create session type (normalized)
    session_type_id = get_or_create_session_type(conn, session_type_code)

    # Try to find existing session
    cur.execute(
        "SELECT session_id FROM Sessions WHERE race_id = ? AND session_type_id = ?",
        (race_id, session_type_id),
    )
    row = cur.fetchone()

    if row:
        return row[0]

    # Clean weather data
    track_temp = clean_float(weather_data.get("track_temp"))
    humidity = clean_float(weather_data.get("humidity"))
    wind_speed = clean_float(weather_data.get("wind_speed"))

    # Create new session
    cur.execute(
        """
        INSERT INTO Sessions (race_id, session_type_id, track_temp, humidity, wind_speed)
        VALUES (?, ?, ?, ?, ?)
        """,
        (race_id, session_type_id, track_temp, humidity, wind_speed),
    )

    conn.commit()
    return cur.lastrowid if cur.lastrowid is not None else 0


def ensure_driver_exists(conn: sqlite3.Connection, driver_info: Dict[str, Any]) -> int:
    """
    Ensure driver exists in database, create if not.
    First checks for existing driver by code (name_acronym) to avoid duplicates
    when drivers were already created by another data source (e.g., Jolpica).

    Args:
        conn: Database connection
        driver_info: Driver information from OpenF1

    Returns:
        driver_id
    """
    driver_number = driver_info.get("driver_number")
    name_acronym = clean_string(driver_info.get("name_acronym"))
    first_name = clean_string(driver_info.get("first_name"))
    last_name = clean_string(driver_info.get("last_name"))
    country_code = clean_string(driver_info.get("country_code"))

    # First, try to find existing driver by code (may have been created by Jolpica)
    if name_acronym:
        existing_driver_id = get_driver_by_code(conn, name_acronym)
        if existing_driver_id is not None:
            return existing_driver_id

    # If not found by code, create new driver with OpenF1 prefix
    api_driver_id = f"openf1_{driver_number}"

    return get_or_create_driver(
        conn,
        api_driver_id=api_driver_id,
        code=name_acronym,
        forename=first_name,
        surname=last_name,
        nationality=country_code,
    )


def store_openf1_data(conn: sqlite3.Connection) -> int:
    """
    Main function to fetch and store OpenF1 data with 25-lap limit.
    Uses explicit requests.get calls to satisfy project requirements.

    Args:
        conn: Database connection

    Returns:
        Number of new LapTimes rows added
    """
    # Get current progress
    progress = get_progress(conn, "openf1")

    last_season = 0
    last_round = 0

    if progress:
        last_season = progress[0] or 0
        last_round = progress[1] or 0

    # Fetch all meetings for target year, sorted by date
    meetings = fetch_meetings(TARGET_YEAR)

    if not meetings:
        print(f"No meetings found for {TARGET_YEAR}")
        return 0

    # Build meeting_key to round_num mapping based on sorted order
    meeting_round_map = {
        m["meeting_key"]: idx + 1
        for idx, m in enumerate(meetings)
        if "meeting_key" in m
    }

    new_laps_inserted = 0
    cur = conn.cursor()

    for meeting in meetings:
        meeting_key = meeting.get("meeting_key")

        if meeting_key is None:
            continue

        # Get round number from mapping
        round_num = meeting_round_map.get(meeting_key, 0)

        if round_num == 0:
            continue

        # Skip already processed rounds within the target season
        if TARGET_YEAR == last_season and round_num <= last_round:
            continue

        if new_laps_inserted >= MAX_NEW_LAPS_PER_RUN:
            break

        # Get circuit name (normalized via get_or_create_circuit)
        circuit_name = clean_string(meeting.get("circuit_short_name"))
        circuit_id = get_or_create_circuit(conn, circuit_name)

        # Get meeting name for race name
        meeting_name = clean_string(meeting.get("meeting_name"))

        # Get or create race record
        race_id = get_or_create_race(
            conn,
            season=TARGET_YEAR,
            round_num=round_num,
            race_name=meeting_name,
            date=None,
            circuit_id=circuit_id,
        )

        # Fetch sessions for this meeting (only Race and Qualifying)
        sessions = fetch_sessions_for_meeting(meeting_key)

        if not sessions:
            # Update progress even if no sessions found
            update_progress(conn, "openf1", TARGET_YEAR, round_num, meeting_name)
            continue

        for session in sessions:
            session_key = session.get("session_key")
            session_name = session.get("session_name")

            if session_key is None or session_name is None:
                continue

            if new_laps_inserted >= MAX_NEW_LAPS_PER_RUN:
                break

            # Map session type
            session_type_code = map_session_type(session_name)

            # Fetch weather data and compute averages
            weather_list = fetch_weather(session_key)
            weather_avg = compute_average_weather(weather_list)

            # Get or create session record
            db_session_id = get_or_create_session(
                conn, race_id, session_type_code, weather_avg
            )

            # Fetch all drivers, laps, and stints for this session (batched)
            drivers = fetch_drivers(session_key)
            all_laps = fetch_all_laps(session_key)
            all_stints = fetch_all_stints(session_key)

            if not drivers or not all_laps:
                continue

            # Group laps and stints by driver_number
            laps_by_driver = group_by_driver(all_laps)
            stints_by_driver = group_by_driver(all_stints)

            # Build driver_number to driver_id mapping
            driver_id_map: Dict[int, int] = {}
            for driver_info in drivers:
                driver_number = driver_info.get("driver_number")
                if driver_number is not None:
                    driver_id_map[driver_number] = ensure_driver_exists(
                        conn, driver_info
                    )

            # Process laps for each driver
            for driver_number, laps in laps_by_driver.items():
                if new_laps_inserted >= MAX_NEW_LAPS_PER_RUN:
                    break

                driver_id = driver_id_map.get(driver_number)
                if driver_id is None:
                    continue

                stints = stints_by_driver.get(driver_number, [])

                for lap in laps:
                    if new_laps_inserted >= MAX_NEW_LAPS_PER_RUN:
                        break

                    # Skip pit-out laps (often have invalid/slow times)
                    if lap.get("is_pit_out_lap"):
                        continue

                    lap_number = clean_integer(lap.get("lap_number"))
                    raw_lap_duration = lap.get("lap_duration")

                    # Normalize lap duration first to safely handle strings and numbers
                    lap_duration_sec = clean_float(raw_lap_duration)

                    # Skip laps without valid data
                    if lap_number is None or lap_duration_sec is None:
                        continue

                    # Convert lap duration from seconds to milliseconds
                    lap_time_ms = clean_integer(lap_duration_sec * 1000)

                    # Convert sector times from seconds to milliseconds
                    sector1_ms = None
                    sector2_ms = None
                    sector3_ms = None

                    raw_sector1 = lap.get("duration_sector_1")
                    raw_sector2 = lap.get("duration_sector_2")
                    raw_sector3 = lap.get("duration_sector_3")

                    sector1_sec = clean_float(raw_sector1)
                    sector2_sec = clean_float(raw_sector2)
                    sector3_sec = clean_float(raw_sector3)

                    if sector1_sec is not None:
                        sector1_ms = clean_integer(sector1_sec * 1000)
                    if sector2_sec is not None:
                        sector2_ms = clean_integer(sector2_sec * 1000)
                    if sector3_sec is not None:
                        sector3_ms = clean_integer(sector3_sec * 1000)

                    # Get compound from stints (normalized via get_or_create_compound)
                    compound_name = get_compound_for_lap(stints, lap_number)
                    compound_id = get_or_create_compound(conn, compound_name)

                    # Determine if fresh tyre
                    fresh_tyre = is_fresh_tyre_for_lap(stints, lap_number)

                    # Insert lap time
                    try:
                        cur.execute(
                            """
                            INSERT INTO LapTimes 
                            (session_id, driver_id, lap_number, lap_time_ms, 
                             sector1_ms, sector2_ms, sector3_ms, compound_id, fresh_tyre)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                db_session_id,
                                driver_id,
                                lap_number,
                                lap_time_ms,
                                sector1_ms,
                                sector2_ms,
                                sector3_ms,
                                compound_id,
                                fresh_tyre,
                            ),
                        )

                        if cur.rowcount > 0:
                            new_laps_inserted += 1

                    except sqlite3.IntegrityError:
                        # Skip duplicate laps
                        continue

        # Update progress after each meeting/round
        update_progress(conn, "openf1", TARGET_YEAR, round_num, meeting_name)

        if new_laps_inserted >= MAX_NEW_LAPS_PER_RUN:
            break

    conn.commit()
    return new_laps_inserted


if __name__ == "__main__":
    # Test the module independently
    conn = get_connection()
    create_tables(conn)
    count = store_openf1_data(conn)
    print(f"Completed: {count} new laps added")
    conn.close()
