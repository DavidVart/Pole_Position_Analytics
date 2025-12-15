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
CSV_DIR.mkdir(parents=True, exist_ok=True)
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
    Create a bar chart of average lap times across races.
    Shows driver performance across multiple races for better insights.

    Args:
        df: DataFrame with average lap time data
        race_filter: Optional tuple of (season, round) to filter to specific race
        output_filename: Output filename for the plot
    """
    if df.empty:
        return

    # Get unique drivers and races
    unique_drivers = df["driver_code"].unique()
    unique_races = df[["season", "round", "race_name"]].drop_duplicates()

    # If only one driver, create a race-by-race comparison
    if len(unique_drivers) == 1:
        # Single driver across multiple races
        df_sorted = df.sort_values(["season", "round"])

        plt.figure(figsize=(16, 8))

        # Create bar chart
        x_labels = [
            f"{row.race_name}\n({row.season} R{row.round})"
            for row in df_sorted.itertuples()
        ]

        colors = sns.color_palette("viridis", len(df_sorted))
        bars = plt.bar(
            range(len(df_sorted)),
            df_sorted["avg_lap_time_sec"],
            color=colors,
            edgecolor="black",
            linewidth=1.5,
        )

        # Customize plot
        plt.xlabel("Race", fontsize=14, fontweight="bold")
        plt.ylabel("Average Lap Time (seconds)", fontsize=14, fontweight="bold")
        plt.title(
            f"Average Lap Time Performance - {unique_drivers[0]} (2023 Season)",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )

        plt.xticks(
            range(len(df_sorted)), x_labels, rotation=45, ha="right", fontsize=10
        )

        # Add value labels on bars
        for i, (bar, row) in enumerate(zip(bars, df_sorted.itertuples())):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.5,
                f"{row.avg_lap_time_sec:.2f}s\n({row.lap_count} laps)",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

            # Add fastest lap annotation
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() * 0.5,
                f"Best: {row.fastest_lap_sec:.2f}s",
                ha="center",
                va="center",
                fontsize=8,
                color="white",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="black", alpha=0.7),
            )

        plt.grid(axis="y", alpha=0.3, linestyle="--")
        plt.tight_layout()

    else:
        # Multiple drivers - show single race comparison
        if race_filter:
            season, round_num = race_filter
            df_filtered = df[(df["season"] == season) & (df["round"] == round_num)]
        else:
            # Use first race in the dataset
            first_race = df.iloc[0]
            season = first_race["season"]
            round_num = first_race["round"]
            df_filtered = df[(df["season"] == season) & (df["round"] == round_num)]

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
            edgecolor="black",
            linewidth=1.5,
        )

        # Customize plot
        plt.xlabel("Driver", fontsize=12, fontweight="bold")
        plt.ylabel("Average Lap Time (seconds)", fontsize=12, fontweight="bold")

        race_name = df_filtered.iloc[0].get("race_name", "Unknown Race")
        plt.title(
            f"Average Lap Times - {race_name} ({season})",
            fontsize=14,
            fontweight="bold",
            pad=20,
        )

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

        plt.grid(axis="y", alpha=0.3)
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
        JOIN SessionTypes ST ON S.session_type_id = ST.session_type_id
        JOIN Races R ON S.race_id = R.race_id
        JOIN Drivers D ON L.driver_id = D.driver_id
        WHERE R.season = ? 
          AND R.round = ? 
          AND ST.session_type_code = 'R'
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
    df: pd.DataFrame, top_n: int = 15, output_filename: str = "grid_vs_finish.png"
) -> None:
    """
    Create a dual visualization showing top gainers and losers from grid to finish.
    More impactful for presentations by showing both extremes.

    Args:
        df: DataFrame with grid vs finish data
        top_n: Number of top movers to show (for gainers and losers combined)
        output_filename: Output filename for the plot
    """
    if df.empty:
        return

    # Split into gainers and losers
    gainers = df[df["positions_gained"] > 0].nlargest(
        top_n // 2 + 1, "positions_gained"
    )
    losers = df[df["positions_gained"] < 0].nsmallest(
        top_n // 2 + 1, "positions_gained"
    )

    # Combine and sort
    df_selected = pd.concat([gainers, losers]).sort_values(
        "positions_gained", ascending=True
    )

    if df_selected.empty:
        # Fallback to original behavior
        df_selected = df.sort_values("positions_gained", ascending=False).head(top_n)

    # Create plot
    plt.figure(figsize=(16, 10))

    # Enhanced color scheme with gradient
    colors = []
    for x in df_selected["positions_gained"]:
        if x > 5:
            colors.append("#006400")  # Dark green for big gains
        elif x > 0:
            colors.append("#90EE90")  # Light green for small gains
        elif x < -5:
            colors.append("#8B0000")  # Dark red for big losses
        elif x < 0:
            colors.append("#FFB6C6")  # Light red for small losses
        else:
            colors.append("#808080")  # Gray for no change

    bars = plt.barh(
        range(len(df_selected)),
        df_selected["positions_gained"],
        color=colors,
        alpha=0.85,
        edgecolor="black",
        linewidth=1.5,
    )

    # Customize plot
    plt.xlabel("Positions Gained/Lost", fontsize=14, fontweight="bold")
    plt.ylabel("Driver & Race", fontsize=14, fontweight="bold")
    plt.title(
        "Position Changes: Grid to Finish (2023 Season)\nTop Gainers vs Biggest Losers",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )

    # Enhanced y-axis labels with more info
    labels = []
    for row in df_selected.itertuples():
        race_abbrev = row.race_name.replace("Grand Prix", "GP").replace(
            "Saudi Arabian", "Saudi"
        )
        label = f"{row.driver_code} ({row.constructor[:12]})\n{race_abbrev[:20]}"
        labels.append(label)

    plt.yticks(range(len(df_selected)), labels, fontsize=9)

    # Enhanced value labels with grid/finish positions
    for i, (bar, row) in enumerate(zip(bars, df_selected.itertuples())):
        value = row.positions_gained
        label = f"+{int(value)}" if value > 0 else str(int(value))

        # Position info
        position_info = f"P{row.grid} → P{row.position}"

        # Place label outside the bar
        x_pos = value + (0.3 if value > 0 else -0.3)
        plt.text(
            x_pos,
            bar.get_y() + bar.get_height() / 2,
            f"{label} ({position_info})",
            ha="left" if value > 0 else "right",
            va="center",
            fontsize=9,
            fontweight="bold",
        )

    # Add separating line at zero
    plt.axvline(x=0, color="black", linestyle="-", linewidth=2.5, zorder=3)

    # Add grid
    plt.grid(axis="x", alpha=0.3, linestyle="--")

    # Add legend
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(
            facecolor="#006400", edgecolor="black", label="Major Gain (>5 positions)"
        ),
        Patch(
            facecolor="#90EE90", edgecolor="black", label="Minor Gain (1-5 positions)"
        ),
        Patch(
            facecolor="#FFB6C6", edgecolor="black", label="Minor Loss (1-5 positions)"
        ),
        Patch(
            facecolor="#8B0000", edgecolor="black", label="Major Loss (>5 positions)"
        ),
    ]
    plt.legend(handles=legend_elements, loc="lower right", fontsize=10, framealpha=0.9)

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
