"""
Database utilities for F1 project.
Handles SQLite connection, table creation, and helper functions for data insertion.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Tuple

DB_PATH = Path("f1.db")


def get_connection() -> sqlite3.Connection:
    """
    Create and return a SQLite database connection with foreign keys enabled.

    Returns:
        sqlite3.Connection: Database connection object
    """
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
            source TEXT PRIMARY KEY,    
            last_season INTEGER,
            last_round INTEGER,
            last_event TEXT             
        );
    """)

    # Normalized lookup tables to avoid duplicate strings
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Nationalities (
            nationality_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nationality_name TEXT UNIQUE NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Circuits (
            circuit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            circuit_name TEXT UNIQUE NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Statuses (
            status_id INTEGER PRIMARY KEY AUTOINCREMENT,
            status_text TEXT UNIQUE NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS SessionTypes (
            session_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_type_code TEXT UNIQUE NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Compounds (
            compound_id INTEGER PRIMARY KEY AUTOINCREMENT,
            compound_name TEXT UNIQUE NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS RaceNames (
            race_name_id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_name TEXT UNIQUE NOT NULL
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
            nationality_id INTEGER,
            FOREIGN KEY (nationality_id) REFERENCES Nationalities(nationality_id)
        );
    """)

    # Normalized constructor table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Constructors (
            constructor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_constructor_id TEXT UNIQUE NOT NULL,
            name TEXT,
            nationality_id INTEGER,
            FOREIGN KEY (nationality_id) REFERENCES Nationalities(nationality_id)
        );
    """)

    # Races table with unique season/round combination
    # Date stored as INTEGER (YYYYMMDD) to avoid duplicate date strings
    # Race name normalized to avoid duplicate strings
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Races (
            race_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season INTEGER NOT NULL,
            round INTEGER NOT NULL,
            race_name_id INTEGER,
            date INTEGER,  -- Stored as YYYYMMDD integer to avoid duplicate strings
            circuit_id INTEGER,
            UNIQUE (season, round),
            FOREIGN KEY (race_name_id) REFERENCES RaceNames(race_name_id),
            FOREIGN KEY (circuit_id) REFERENCES Circuits(circuit_id)
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
            status_id INTEGER,
            UNIQUE (race_id, driver_id),
            FOREIGN KEY (race_id) REFERENCES Races(race_id),
            FOREIGN KEY (driver_id) REFERENCES Drivers(driver_id),
            FOREIGN KEY (constructor_id) REFERENCES Constructors(constructor_id),
            FOREIGN KEY (status_id) REFERENCES Statuses(status_id)
        );
    """)

    # Sessions table for practice, qualifying, and race sessions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_id INTEGER NOT NULL,
            session_type_id INTEGER NOT NULL,
            track_temp REAL,
            humidity REAL,
            wind_speed REAL,
            UNIQUE (race_id, session_type_id),
            FOREIGN KEY (race_id) REFERENCES Races(race_id),
            FOREIGN KEY (session_type_id) REFERENCES SessionTypes(session_type_id)
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
            compound_id INTEGER,
            fresh_tyre INTEGER,
            FOREIGN KEY (session_id) REFERENCES Sessions(session_id),
            FOREIGN KEY (driver_id) REFERENCES Drivers(driver_id),
            FOREIGN KEY (compound_id) REFERENCES Compounds(compound_id)
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

    # Get or create nationality
    nationality_id = get_or_create_nationality(conn, nationality)

    # Create new driver
    cur.execute(
        """
        INSERT INTO Drivers (api_driver_id, code, forename, surname, nationality_id)
        VALUES (?, ?, ?, ?, ?)
    """,
        (api_driver_id, code, forename, surname, nationality_id),
    )

    conn.commit()
    return cur.lastrowid if cur.lastrowid is not None else 0


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

    # Get or create nationality
    nationality_id = get_or_create_nationality(conn, nationality)

    # Create new constructor
    cur.execute(
        """
        INSERT INTO Constructors (api_constructor_id, name, nationality_id)
        VALUES (?, ?, ?)
    """,
        (api_constructor_id, name, nationality_id),
    )

    conn.commit()
    return cur.lastrowid if cur.lastrowid is not None else 0


def get_or_create_race(
    conn: sqlite3.Connection,
    season: int,
    round_num: int,
    race_name: Optional[str] = None,
    date: Optional[int] = None,
    circuit_id: Optional[int] = None,
) -> int:
    """
    Get existing race_id or create new race record.
    Uses (season, round) as unique identifier.

    Args:
        conn: Database connection
        season: Season year
        round_num: Round number in season
        race_name: Name of the race/Grand Prix
        date: Race date as INTEGER (YYYYMMDD format)
        circuit_id: Circuit ID (foreign key)

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

    # Get or create normalized race name
    race_name_id = get_or_create_race_name(conn, race_name)

    # Create new race
    cur.execute(
        """
        INSERT INTO Races (season, round, race_name_id, date, circuit_id)
        VALUES (?, ?, ?, ?, ?)
    """,
        (season, round_num, race_name_id, date, circuit_id),
    )

    conn.commit()
    return cur.lastrowid if cur.lastrowid is not None else 0


def get_progress(
    conn: sqlite3.Connection, source: str
) -> Optional[Tuple[int, int, Optional[str]]]:
    """
    Get the last progress checkpoint for a data source.

    Args:
        conn: Database connection
        source: Data source name

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
        source: Data source name
        season: Last processed season
        round_num: Last processed round
        event: Last processed event name
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


def get_or_create_nationality(
    conn: sqlite3.Connection, nationality_name: Optional[str]
) -> Optional[int]:
    """
    Get existing nationality_id or create new nationality record.

    Args:
        conn: Database connection
        nationality_name: Nationality name

    Returns:
        int: nationality_id or None if nationality_name is None/empty
    """
    if nationality_name is None or nationality_name.strip() == "":
        return None

    cur = conn.cursor()
    nationality_name = nationality_name.strip()

    # Try to find existing nationality
    cur.execute(
        "SELECT nationality_id FROM Nationalities WHERE nationality_name = ?",
        (nationality_name,),
    )
    row = cur.fetchone()

    if row:
        return row[0]

    # Create new nationality
    cur.execute(
        "INSERT INTO Nationalities (nationality_name) VALUES (?)", (nationality_name,)
    )

    conn.commit()
    return cur.lastrowid if cur.lastrowid is not None else None


def get_or_create_circuit(
    conn: sqlite3.Connection, circuit_name: Optional[str]
) -> Optional[int]:
    """
    Get existing circuit_id or create new circuit record.

    Args:
        conn: Database connection
        circuit_name: Circuit name

    Returns:
        int: circuit_id or None if circuit_name is None/empty
    """
    if circuit_name is None or circuit_name.strip() == "":
        return None

    cur = conn.cursor()
    circuit_name = circuit_name.strip()

    # Try to find existing circuit
    cur.execute(
        "SELECT circuit_id FROM Circuits WHERE circuit_name = ?", (circuit_name,)
    )
    row = cur.fetchone()

    if row:
        return row[0]

    # Create new circuit
    cur.execute("INSERT INTO Circuits (circuit_name) VALUES (?)", (circuit_name,))

    conn.commit()
    return cur.lastrowid if cur.lastrowid is not None else None


def get_or_create_status(
    conn: sqlite3.Connection, status_text: Optional[str]
) -> Optional[int]:
    """
    Get existing status_id or create new status record.

    Args:
        conn: Database connection
        status_text: Status text (e.g., 'Finished', 'Retired')

    Returns:
        int: status_id or None if status_text is None/empty
    """
    if status_text is None or status_text.strip() == "":
        return None

    cur = conn.cursor()
    status_text = status_text.strip()

    # Try to find existing status
    cur.execute("SELECT status_id FROM Statuses WHERE status_text = ?", (status_text,))
    row = cur.fetchone()

    if row:
        return row[0]

    # Create new status
    cur.execute("INSERT INTO Statuses (status_text) VALUES (?)", (status_text,))

    conn.commit()
    return cur.lastrowid if cur.lastrowid is not None else None


def get_or_create_session_type(conn: sqlite3.Connection, session_type_code: str) -> int:
    """
    Get existing session_type_id or create new session type record.

    Args:
        conn: Database connection
        session_type_code: Session type code (e.g., 'R', 'Q', 'FP1')

    Returns:
        int: session_type_id
    """
    cur = conn.cursor()
    session_type_code = session_type_code.strip().upper()

    # Try to find existing session type
    cur.execute(
        "SELECT session_type_id FROM SessionTypes WHERE session_type_code = ?",
        (session_type_code,),
    )
    row = cur.fetchone()

    if row:
        return row[0]

    # Create new session type
    cur.execute(
        "INSERT INTO SessionTypes (session_type_code) VALUES (?)", (session_type_code,)
    )

    conn.commit()
    return cur.lastrowid if cur.lastrowid is not None else 0


def get_or_create_compound(
    conn: sqlite3.Connection, compound_name: Optional[str]
) -> Optional[int]:
    """
    Get existing compound_id or create new compound record.

    Args:
        conn: Database connection
        compound_name: Tyre compound name (e.g., 'SOFT', 'MEDIUM', 'HARD')

    Returns:
        int: compound_id or None if compound_name is None/empty
    """
    if compound_name is None or compound_name.strip() == "":
        return None

    cur = conn.cursor()
    compound_name = compound_name.strip().upper()

    # Try to find existing compound
    cur.execute(
        "SELECT compound_id FROM Compounds WHERE compound_name = ?", (compound_name,)
    )
    row = cur.fetchone()

    if row:
        return row[0]

    # Create new compound
    cur.execute("INSERT INTO Compounds (compound_name) VALUES (?)", (compound_name,))

    conn.commit()
    return cur.lastrowid if cur.lastrowid is not None else None


def get_or_create_race_name(
    conn: sqlite3.Connection, race_name: Optional[str]
) -> Optional[int]:
    """
    Get existing race_name_id or create new race name record.

    Args:
        conn: Database connection
        race_name: Race name (e.g., 'Bahrain Grand Prix')

    Returns:
        int: race_name_id or None if race_name is None/empty
    """
    if race_name is None or race_name.strip() == "":
        return None

    cur = conn.cursor()
    race_name = race_name.strip()

    # Try to find existing race name
    cur.execute("SELECT race_name_id FROM RaceNames WHERE race_name = ?", (race_name,))
    row = cur.fetchone()

    if row:
        return row[0]

    # Create new race name
    cur.execute("INSERT INTO RaceNames (race_name) VALUES (?)", (race_name,))

    conn.commit()
    return cur.lastrowid if cur.lastrowid is not None else None
