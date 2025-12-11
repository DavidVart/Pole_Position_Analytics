"""
Database utilities for F1 project.
Handles SQLite connection, table creation, and helper functions for data insertion.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Tuple

DB_PATH = Path("data/f1_project.db")


def get_connection() -> sqlite3.Connection:
    """
    Create and return a SQLite database connection with foreign keys enabled.
    Creates the data directory if it doesn't exist.

    Returns:
        sqlite3.Connection: Database connection object
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    """
    Create all required tables for the F1 project if they don't exist.
    Tables are normalized to avoid duplicate string data.

    Args:
        conn: SQLite database connection
    """
    cur = conn.cursor()

    # Meta table for tracking progress to enforce 25-row limit
    cur.execute("""
        CREATE TABLE IF NOT EXISTS LoadProgress (
            source TEXT PRIMARY KEY,    -- 'jolpica' or 'fastf1'
            last_season INTEGER,
            last_round INTEGER,
            last_event TEXT             -- For FastF1 event names
        );
    """)

    # Normalized driver table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Drivers (
            driver_id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_driver_id TEXT UNIQUE NOT NULL,
            code TEXT,
            forename TEXT,
            surname TEXT,
            nationality TEXT
        );
    """)

    # Normalized constructor table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Constructors (
            constructor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_constructor_id TEXT UNIQUE NOT NULL,
            name TEXT,
            nationality TEXT
        );
    """)

    # Races table with unique season/round combination
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Races (
            race_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season INTEGER NOT NULL,
            round INTEGER NOT NULL,
            race_name TEXT,
            date TEXT,
            circuit_name TEXT,
            UNIQUE (season, round)
        );
    """)

    # Results table linking races, drivers, and constructors
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_id INTEGER NOT NULL,
            driver_id INTEGER NOT NULL,
            constructor_id INTEGER NOT NULL,
            grid INTEGER,
            position INTEGER,
            points REAL,
            status TEXT,
            UNIQUE (race_id, driver_id),
            FOREIGN KEY (race_id) REFERENCES Races(race_id),
            FOREIGN KEY (driver_id) REFERENCES Drivers(driver_id),
            FOREIGN KEY (constructor_id) REFERENCES Constructors(constructor_id)
        );
    """)

    # Sessions table for practice, qualifying, and race sessions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_id INTEGER NOT NULL,
            session_type TEXT NOT NULL,
            track_temp REAL,
            humidity REAL,
            wind_speed REAL,
            UNIQUE (race_id, session_type),
            FOREIGN KEY (race_id) REFERENCES Races(race_id)
        );
    """)

    # Lap times table with telemetry data
    cur.execute("""
        CREATE TABLE IF NOT EXISTS LapTimes (
            lap_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            driver_id INTEGER NOT NULL,
            lap_number INTEGER,
            lap_time_ms INTEGER,
            sector1_ms INTEGER,
            sector2_ms INTEGER,
            sector3_ms INTEGER,
            compound TEXT,
            fresh_tyre INTEGER,
            FOREIGN KEY (session_id) REFERENCES Sessions(session_id),
            FOREIGN KEY (driver_id) REFERENCES Drivers(driver_id)
        );
    """)

    conn.commit()


def get_or_create_driver(
    conn: sqlite3.Connection,
    api_driver_id: str,
    code: Optional[str] = None,
    forename: Optional[str] = None,
    surname: Optional[str] = None,
    nationality: Optional[str] = None,
) -> int:
    """
    Get existing driver_id or create new driver record.
    Uses api_driver_id as unique identifier to avoid duplicates.

    Args:
        conn: Database connection
        api_driver_id: Unique driver ID from API
        code: Driver code (e.g., 'VER', 'HAM')
        forename: Driver first name
        surname: Driver last name
        nationality: Driver nationality

    Returns:
        int: driver_id
    """
    cur = conn.cursor()

    # Try to find existing driver
    cur.execute(
        "SELECT driver_id FROM Drivers WHERE api_driver_id = ?", (api_driver_id,)
    )
    row = cur.fetchone()

    if row:
        return row[0]

    # Create new driver
    cur.execute(
        """
        INSERT INTO Drivers (api_driver_id, code, forename, surname, nationality)
        VALUES (?, ?, ?, ?, ?)
    """,
        (api_driver_id, code, forename, surname, nationality),
    )

    conn.commit()
    return cur.lastrowid


def get_or_create_constructor(
    conn: sqlite3.Connection,
    api_constructor_id: str,
    name: Optional[str] = None,
    nationality: Optional[str] = None,
) -> int:
    """
    Get existing constructor_id or create new constructor record.

    Args:
        conn: Database connection
        api_constructor_id: Unique constructor ID from API
        name: Constructor name
        nationality: Constructor nationality

    Returns:
        int: constructor_id
    """
    cur = conn.cursor()

    # Try to find existing constructor
    cur.execute(
        "SELECT constructor_id FROM Constructors WHERE api_constructor_id = ?",
        (api_constructor_id,),
    )
    row = cur.fetchone()

    if row:
        return row[0]

    # Create new constructor
    cur.execute(
        """
        INSERT INTO Constructors (api_constructor_id, name, nationality)
        VALUES (?, ?, ?)
    """,
        (api_constructor_id, name, nationality),
    )

    conn.commit()
    return cur.lastrowid


def get_or_create_race(
    conn: sqlite3.Connection,
    season: int,
    round_num: int,
    race_name: Optional[str] = None,
    date: Optional[str] = None,
    circuit_name: Optional[str] = None,
) -> int:
    """
    Get existing race_id or create new race record.
    Uses (season, round) as unique identifier.

    Args:
        conn: Database connection
        season: Season year
        round_num: Round number in season
        race_name: Name of the race/Grand Prix
        date: Race date
        circuit_name: Circuit name

    Returns:
        int: race_id
    """
    cur = conn.cursor()

    # Try to find existing race
    cur.execute(
        "SELECT race_id FROM Races WHERE season = ? AND round = ?", (season, round_num)
    )
    row = cur.fetchone()

    if row:
        return row[0]

    # Create new race
    cur.execute(
        """
        INSERT INTO Races (season, round, race_name, date, circuit_name)
        VALUES (?, ?, ?, ?, ?)
    """,
        (season, round_num, race_name, date, circuit_name),
    )

    conn.commit()
    return cur.lastrowid


def get_progress(
    conn: sqlite3.Connection, source: str
) -> Optional[Tuple[int, int, Optional[str]]]:
    """
    Get the last progress checkpoint for a data source.

    Args:
        conn: Database connection
        source: Data source name ('jolpica' or 'fastf1')

    Returns:
        Tuple of (last_season, last_round, last_event) or None if no progress exists
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT last_season, last_round, last_event FROM LoadProgress WHERE source = ?",
        (source,),
    )
    row = cur.fetchone()
    return row if row else None


def update_progress(
    conn: sqlite3.Connection,
    source: str,
    season: int,
    round_num: int,
    event: Optional[str] = None,
) -> None:
    """
    Update the progress checkpoint for a data source.

    Args:
        conn: Database connection
        source: Data source name ('jolpica' or 'fastf1')
        season: Last processed season
        round_num: Last processed round
        event: Last processed event name (for FastF1)
    """
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO LoadProgress (source, last_season, last_round, last_event)
        VALUES (?, ?, ?, ?)
    """,
        (source, season, round_num, event),
    )
    conn.commit()


def get_driver_by_code(conn: sqlite3.Connection, code: str) -> Optional[int]:
    """
    Get driver_id by driver code.

    Args:
        conn: Database connection
        code: Driver code (e.g., 'VER', 'HAM')

    Returns:
        int: driver_id or None if not found
    """
    cur = conn.cursor()
    cur.execute("SELECT driver_id FROM Drivers WHERE code = ?", (code,))
    row = cur.fetchone()
    return row[0] if row else None
