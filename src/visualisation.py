"""
Visualization module for F1 project.
Generates plots and charts using matplotlib and seaborn.
Reads calculated data from CSV files or DataFrames.

Authors: David & Alberto
"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Set up directories
CSV_DIR = Path("outputs/csv")
FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Set seaborn theme for better-looking plots
sns.set_theme(style="whitegrid", palette="husl")
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["font.size"] = 10


def plot_avg_lap_times(
    df: pd.DataFrame,
    race_filter: Optional[Tuple[int, int]] = None,
    output_filename: str = "avg_lap_times.png",
) -> None:
    """
    Create a bar chart of average lap times by driver for a specific race.

    Args:
        df: DataFrame with average lap time data
        race_filter: Optional tuple of (season, round) to filter to specific race
        output_filename: Output filename for the plot
    """
    if df.empty:
        return

    # Filter to specific race if requested
    if race_filter:
        season, round_num = race_filter
        df_filtered = df[(df["season"] == season) & (df["round"] == round_num)]
    else:
        # Use first race in the dataset
        if "season" in df.columns and "round" in df.columns:
            first_race = df.iloc[0]
            season = first_race["season"]
            round_num = first_race["round"]
            df_filtered = df[(df["season"] == season) & (df["round"] == round_num)]
        else:
            df_filtered = df.head(20)  # Limit to 20 drivers

    if df_filtered.empty:
        return

    # Sort by lap time
    df_filtered = df_filtered.sort_values("avg_lap_time_sec")

    # Create plot
    plt.figure(figsize=(14, 8))

    bars = plt.bar(
        range(len(df_filtered)),
        df_filtered["avg_lap_time_sec"],
        color=sns.color_palette("rocket", len(df_filtered)),
    )

    # Customize plot
    plt.xlabel("Driver", fontsize=12, fontweight="bold")
    plt.ylabel("Average Lap Time (seconds)", fontsize=12, fontweight="bold")

    if race_filter or "race_name" in df_filtered.columns:
        race_name = df_filtered.iloc[0].get("race_name", "Unknown Race")
        plt.title(
            f"Average Lap Times - {race_name} ({season})",
            fontsize=14,
            fontweight="bold",
            pad=20,
        )
    else:
        plt.title("Average Lap Times by Driver", fontsize=14, fontweight="bold", pad=20)

    # Set x-axis labels
    plt.xticks(
        range(len(df_filtered)), df_filtered["driver_code"], rotation=45, ha="right"
    )

    # Add value labels on bars
    for i, (bar, value) in enumerate(zip(bars, df_filtered["avg_lap_time_sec"])):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.1,
            f"{value:.2f}s",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    plt.tight_layout()

    # Save plot
    output_path = FIG_DIR / output_filename
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_temp_vs_lap_scatter(
    df: pd.DataFrame,
    correlation: float,
    output_filename: str = "temp_vs_lap_scatter.png",
) -> None:
    """
    Create a scatter plot with regression line showing track temp vs lap time.

    Args:
        df: DataFrame with temperature and lap time data
        correlation: Correlation coefficient to display
        output_filename: Output filename for the plot
    """
    if df.empty:
        return

    # Convert to seconds if not already done
    if "avg_lap_time_sec" not in df.columns and "avg_lap_time_ms" in df.columns:
        df["avg_lap_time_sec"] = df["avg_lap_time_ms"] / 1000

    # Create plot
    plt.figure(figsize=(12, 8))

    # Create scatter plot with regression line
    sns.regplot(
        data=df,
        x="track_temp",
        y="avg_lap_time_sec",
        scatter_kws={"alpha": 0.6, "s": 100, "edgecolors": "black", "linewidths": 0.5},
        line_kws={"color": "red", "linewidth": 2},
    )

    # Customize plot
    plt.xlabel("Track Temperature (°C)", fontsize=12, fontweight="bold")
    plt.ylabel("Average Lap Time (seconds)", fontsize=12, fontweight="bold")
    plt.title(
        f"Track Temperature vs Lap Time\nCorrelation: {correlation:.4f}",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )

    # Add grid
    plt.grid(True, alpha=0.3)

    # Add text box with correlation info
    textstr = f"Correlation Coefficient: {correlation:.4f}\nN = {len(df)} sessions"
    props = dict(boxstyle="round", facecolor="wheat", alpha=0.5)
    plt.text(
        0.05,
        0.95,
        textstr,
        transform=plt.gca().transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=props,
    )

    plt.tight_layout()

    # Save plot
    output_path = FIG_DIR / output_filename
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_lap_progression(
    conn: sqlite3.Connection,
    season: int,
    round_num: int,
    driver_codes: List[str],
    output_filename: str = "lap_progression.png",
) -> None:
    """
    Create a line plot showing lap time progression throughout a race.

    Args:
        conn: Database connection
        season: Season year
        round_num: Round number
        driver_codes: List of driver codes to plot
        output_filename: Output filename for the plot
    """
    # Query lap progression data
    placeholders = ",".join(["?" for _ in driver_codes])
    query = f"""
        SELECT
            D.code AS driver_code,
            L.lap_number,
            L.lap_time_ms
        FROM LapTimes L
        JOIN Sessions S ON L.session_id = S.session_id
        JOIN Races R ON S.race_id = R.race_id
        JOIN Drivers D ON L.driver_id = D.driver_id
        WHERE R.season = ? 
          AND R.round = ? 
          AND S.session_type = 'R'
          AND D.code IN ({placeholders})
          AND L.lap_time_ms IS NOT NULL
        ORDER BY L.lap_number
    """

    params = [season, round_num] + driver_codes
    df = pd.read_sql_query(query, conn, params=params)

    if df.empty:
        return

    # Convert to seconds
    df["lap_time_sec"] = df["lap_time_ms"] / 1000

    # Create plot
    plt.figure(figsize=(14, 8))

    # Plot line for each driver
    for driver in driver_codes:
        driver_data = df[df["driver_code"] == driver]
        if not driver_data.empty:
            plt.plot(
                driver_data["lap_number"],
                driver_data["lap_time_sec"],
                marker="o",
                markersize=4,
                linewidth=2,
                label=driver,
                alpha=0.8,
            )

    # Customize plot
    plt.xlabel("Lap Number", fontsize=12, fontweight="bold")
    plt.ylabel("Lap Time (seconds)", fontsize=12, fontweight="bold")
    plt.title(
        f"Lap Time Progression - Season {season} Round {round_num}",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    plt.legend(loc="best", fontsize=10, framealpha=0.9)
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save plot
    output_path = FIG_DIR / output_filename
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_tyre_performance(
    df: pd.DataFrame, output_filename: str = "tyre_performance.png"
) -> None:
    """
    Create a bar chart comparing tyre compound performance.

    Args:
        df: DataFrame with tyre performance data
        output_filename: Output filename for the plot
    """
    if df.empty:
        return

    # Sort by lap time
    df_sorted = df.sort_values("avg_lap_time_sec")

    # Create plot
    plt.figure(figsize=(12, 8))

    # Define colors for common compounds
    compound_colors = {
        "SOFT": "#FF0000",
        "MEDIUM": "#FFD700",
        "HARD": "#FFFFFF",
        "INTERMEDIATE": "#00FF00",
        "WET": "#0000FF",
    }

    colors = [compound_colors.get(c, "#808080") for c in df_sorted["compound"]]

    bars = plt.bar(
        range(len(df_sorted)),
        df_sorted["avg_lap_time_sec"],
        color=colors,
        edgecolor="black",
        linewidth=1.5,
    )

    # Customize plot
    plt.xlabel("Tyre Compound", fontsize=12, fontweight="bold")
    plt.ylabel("Average Lap Time (seconds)", fontsize=12, fontweight="bold")
    plt.title(
        "Tyre Compound Performance Comparison", fontsize=14, fontweight="bold", pad=20
    )

    # Set x-axis labels
    plt.xticks(range(len(df_sorted)), df_sorted["compound"], rotation=45, ha="right")

    # Add value labels and lap count
    for i, (bar, row) in enumerate(zip(bars, df_sorted.itertuples())):
        # Lap time label
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.1,
            f"{row.avg_lap_time_sec:.2f}s",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

        # Lap count label
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() / 2,
            f"{row.lap_count} laps",
            ha="center",
            va="center",
            fontsize=8,
            color="black",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.7),
        )

    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    # Save plot
    output_path = FIG_DIR / output_filename
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_grid_vs_finish(
    df: pd.DataFrame, top_n: int = 20, output_filename: str = "grid_vs_finish.png"
) -> None:
    """
    Create a visualization showing positions gained/lost from grid to finish.

    Args:
        df: DataFrame with grid vs finish data
        top_n: Number of top movers to show
        output_filename: Output filename for the plot
    """
    if df.empty:
        return

    # Get top movers (most positions gained)
    df_sorted = df.sort_values("positions_gained", ascending=False).head(top_n)

    # Create plot
    plt.figure(figsize=(14, 8))

    # Color bars based on positive/negative change
    colors = [
        "green" if x > 0 else "red" if x < 0 else "gray"
        for x in df_sorted["positions_gained"]
    ]

    bars = plt.barh(
        range(len(df_sorted)),
        df_sorted["positions_gained"],
        color=colors,
        alpha=0.7,
        edgecolor="black",
        linewidth=1,
    )

    # Customize plot
    plt.xlabel("Positions Gained/Lost", fontsize=12, fontweight="bold")
    plt.ylabel("Driver", fontsize=12, fontweight="bold")
    plt.title(
        "Top Position Changes: Grid to Finish", fontsize=14, fontweight="bold", pad=20
    )

    # Set y-axis labels
    labels = [
        f"{row.driver_code} - {row.race_name[:15]}" for row in df_sorted.itertuples()
    ]
    plt.yticks(range(len(df_sorted)), labels, fontsize=9)

    # Add value labels
    for i, (bar, value) in enumerate(zip(bars, df_sorted["positions_gained"])):
        label = f"+{int(value)}" if value > 0 else str(int(value))
        plt.text(
            value,
            bar.get_y() + bar.get_height() / 2,
            label,
            ha="left" if value > 0 else "right",
            va="center",
            fontsize=8,
            fontweight="bold",
        )

    plt.axvline(x=0, color="black", linestyle="-", linewidth=1)
    plt.grid(axis="x", alpha=0.3)
    plt.tight_layout()

    # Save plot
    output_path = FIG_DIR / output_filename
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def generate_all_visualizations(
    conn: sqlite3.Connection, calculation_results: dict
) -> None:
    """
    Generate all visualizations using calculated data.

    Args:
        conn: Database connection
        calculation_results: Dictionary with calculation results from calculations.py
    """
    # 1. Average lap times
    if not calculation_results["avg_lap_times"].empty:
        plot_avg_lap_times(calculation_results["avg_lap_times"])

    # 2. Temperature correlation
    if not calculation_results["temp_lap_data"].empty:
        plot_temp_vs_lap_scatter(
            calculation_results["temp_lap_data"],
            calculation_results["temp_correlation"],
        )

    # 3. Tyre performance
    if not calculation_results["tyre_performance"].empty:
        plot_tyre_performance(calculation_results["tyre_performance"])

    # 4. Grid vs finish
    if not calculation_results["grid_vs_finish"].empty:
        plot_grid_vs_finish(calculation_results["grid_vs_finish"])

    # 5. Lap progression (if we have lap data)
    if not calculation_results["avg_lap_times"].empty:
        df = calculation_results["avg_lap_times"]
        if not df.empty:
            # Get first race and top 2 drivers
            first_race = df.iloc[0]
            season = int(first_race["season"])
            round_num = int(first_race["round"])

            # Get top 2 drivers by lap time for that race
            race_data = df[(df["season"] == season) & (df["round"] == round_num)]
            top_drivers = race_data.nsmallest(2, "avg_lap_time_ms")[
                "driver_code"
            ].tolist()

            if len(top_drivers) >= 2:
                plot_lap_progression(conn, season, round_num, top_drivers)


if __name__ == "__main__":
    # Test the module independently
    from calculations import run_all_calculations
    from db_utils import get_connection

    conn = get_connection()
    calc_results = run_all_calculations(conn)
    generate_all_visualizations(conn, calc_results)
    conn.close()
