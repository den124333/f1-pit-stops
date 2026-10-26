"""Which circuits have the slowest pit lanes, and does a faster stop gain places?

duration is the full pit-lane time, not the two-second stop from TV.
A fast stop means the fastest quarter of pit-lane times at that circuit.
"""

import urllib.request
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA = Path("data/ergast")
CHARTS = Path("charts")
OUTPUT = Path("output")
SOURCE = "https://raw.githubusercontent.com/TracingInsights/RaceData/refs/heads/main/data"
FILES = ("pit_stops.csv", "lap_times.csv", "races.csv", "circuits.csv")

MIN_SECONDS = 12
MAX_SECONDS = 50
MIN_RACES = 8
# From 2012 on. Before that, refueling made the stops a different thing.
FIRST_YEAR = 2012
# The stop is logged on one lap, but the slow lap is the next one.
# If that lap is not at least 10 seconds slower, I treat it as a safety car or a bad row.
SLOW_LAP_SECONDS = 10
# More than 6 seconds under the circuit median is not a real pit-lane time.
MAX_FASTER_THAN_CIRCUIT = 6
QUARTILE_LABELS = (
    "Fastest quarter",
    "Second quarter",
    "Third quarter",
    "Slowest quarter",
)


def ensure_data():
    DATA.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        path = DATA / name
        if not path.exists():
            urllib.request.urlretrieve(f"{SOURCE}/{name}", path)


def to_seconds(value):
    text = str(value).strip()
    if text in {"", "\\N", "nan", "None"}:
        return np.nan
    if ":" in text:
        minutes, seconds = text.split(":", 1)
        return float(minutes) * 60 + float(seconds)
    return float(text)


def _lap_table():
    laps = pd.read_csv(
        DATA / "lap_times.csv",
        usecols=["raceId", "driverId", "lap", "position", "milliseconds"],
    )
    laps["position"] = pd.to_numeric(laps["position"], errors="coerce")
    laps["milliseconds"] = pd.to_numeric(laps["milliseconds"], errors="coerce")
    # 1988 and 1989 repeat a few laps. One row per driver per lap is enough.
    return laps.drop_duplicates(["raceId", "driverId", "lap"])


def load_stops():
    pits = pd.read_csv(DATA / "pit_stops.csv")
    races = pd.read_csv(DATA / "races.csv", usecols=["raceId", "year", "name", "circuitId", "date"])
    circuits = pd.read_csv(DATA / "circuits.csv", usecols=["circuitId", "name", "country"])
    laps = _lap_table()

    stops = pits.merge(races, on="raceId", how="left")
    stops = stops.merge(circuits.rename(columns={"name": "circuit"}), on="circuitId", how="left")
    stops["seconds"] = stops["duration"].map(to_seconds)

    before = laps.rename(
        columns={"lap": "lap_before", "position": "pos_before", "milliseconds": "ms_before"}
    )
    after = laps.rename(
        columns={"lap": "lap_after", "position": "pos_after", "milliseconds": "ms_after"}
    )
    stops["lap_before"] = stops["lap"] - 1
    stops["lap_after"] = stops["lap"] + 1
    stops = stops.merge(before, on=["raceId", "driverId", "lap_before"], how="left")
    stops = stops.merge(after, on=["raceId", "driverId", "lap_after"], how="left")
    # Positive means the car finished the next lap ahead of where it was before the stop.
    stops["places_gained"] = stops["pos_before"] - stops["pos_after"]
    stops["slow_lap_seconds"] = (stops["ms_after"] - stops["ms_before"]) / 1000
    return stops


def normal_pit_times(stops):
    """Stops with a normal pit-lane time. This is what the circuit chart uses.

    Safety-car stops still have a real pit-lane time, so I keep them here.
    Dropping them made some tracks look shorter than they are.
    """
    keep = stops["seconds"].between(MIN_SECONDS, MAX_SECONDS)
    keep &= stops["year"] >= FIRST_YEAR
    keep &= stops["lap"] > 1
    kept = stops.loc[keep].copy()
    usual = kept.groupby("circuitId")["seconds"].transform("median")
    return kept.loc[kept["seconds"] >= usual - MAX_FASTER_THAN_CIRCUIT].copy()


def stops_with_places(stops):
    """Stops where the next lap is clearly the pit, so I can count the places."""
    timed = normal_pit_times(stops)
    keep = timed["pos_before"].notna() & timed["pos_after"].notna()
    keep &= timed["slow_lap_seconds"] >= SLOW_LAP_SECONDS
    return timed.loc[keep].copy()


def add_quartiles(stops):
    stops = stops.copy()
    stops["speed_band"] = stops.groupby("circuitId")["seconds"].transform(
        lambda values: pd.qcut(values, 4, labels=QUARTILE_LABELS, duplicates="drop")
    )
    return stops


def circuit_table(stops):
    return (
        stops.groupby(["circuit", "country"], as_index=False)
        .agg(
            races=("raceId", "nunique"),
            stops=("seconds", "size"),
            median_seconds=("seconds", "median"),
        )
        .sort_values("median_seconds")
    )


def band_summary(stops):
    rows = []
    for label in QUARTILE_LABELS:
        part = stops[stops["speed_band"] == label]
        gained = part["places_gained"]
        rows.append(
            {
                "speed_band": label,
                "stops": int(len(part)),
                "mean_places_gained": gained.mean(),
                "median_places_gained": gained.median(),
                "share_gained_a_place": (gained >= 1).mean(),
                "share_held": (gained == 0).mean(),
                "share_lost_a_place": (gained <= -1).mean(),
            }
        )
    return pd.DataFrame(rows)


def style_axes(ax, grid="x"):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=10)
    ax.grid(axis=grid, color="#e7e5e4", zorder=0)


def chart_pit_lanes(table):
    shown = table[table["races"] >= MIN_RACES].sort_values("median_seconds")
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(shown["circuit"], shown["median_seconds"], color="#9a3412", zorder=2)
    style_axes(ax)
    ax.set_xlabel("Median pit-lane time (seconds)")
    fastest = shown.iloc[0]
    slowest = shown.iloc[-1]
    ax.set_title(
        f"Pit-lane time by circuit, from {fastest['median_seconds']:.0f} seconds "
        f"to {slowest['median_seconds']:.0f}."
    )
    fig.text(
        0.01,
        0.01,
        f"Stops of {MIN_SECONDS:.0f}–{MAX_SECONDS:.0f}s since {FIRST_YEAR}, "
        f"circuits with at least {MIN_RACES} races. "
        f"{fastest['circuit']} {fastest['median_seconds']:.1f}s, "
        f"{slowest['circuit']} {slowest['median_seconds']:.1f}s.",
        fontsize=8,
        color="#57534e",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(CHARTS / "pit_lane_by_circuit.png", dpi=140)
    plt.close(fig)


def chart_place_change(summary):
    lost = -summary["median_places_gained"]
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#0f766e", "#9a3412", "#9a3412", "#9a3412"]
    ax.bar(summary["speed_band"], lost, color=colors, zorder=2)
    style_axes(ax, grid="y")
    ax.set_ylabel("Median places lost")
    ax.set_ylim(0, max(lost.max() + 1, 4))
    fast = lost.iloc[0]
    slower = lost.iloc[1:]
    if slower.nunique() == 1:
        title = (
            f"Fastest quarter loses {fast:.0f} places. "
            f"The slower quarters lose {slower.iloc[0]:.0f}."
        )
    else:
        title = "Median places lost, compared with other stops at the same circuit."
    ax.set_title(title)
    fig.text(
        0.01,
        0.01,
        "From the lap before the stop to the end of the next lap. "
        f"Only when that next lap is at least {SLOW_LAP_SECONDS:.0f} seconds slower.",
        fontsize=8,
        color="#57534e",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(CHARTS / "fast_stops_and_places.png", dpi=140)
    plt.close(fig)


def main():
    CHARTS.mkdir(exist_ok=True)
    OUTPUT.mkdir(exist_ok=True)
    ensure_data()

    loaded = load_stops()
    timed = normal_pit_times(loaded)
    stops = add_quartiles(stops_with_places(loaded))
    table = circuit_table(timed)
    summary = band_summary(stops)

    table.to_csv(OUTPUT / "circuit_pit_times.csv", index=False)
    summary.to_csv(OUTPUT / "places_by_speed.csv", index=False)
    chart_pit_lanes(table)
    chart_place_change(summary)

    fast = summary.iloc[0]
    slow = summary.iloc[-1]
    lines = [
        f"timed_stops={len(timed)}",
        f"timed_races={timed['raceId'].nunique()}",
        f"stops_used={len(stops)}",
        f"races={stops['raceId'].nunique()}",
        f"years={int(stops['year'].min())}-{int(stops['year'].max())}",
        f"latest_race_date={stops['date'].max()}",
        f"mean_places_all={stops['places_gained'].mean():.4f}",
        f"median_places_all={stops['places_gained'].median():.4f}",
        f"fast_mean_places={fast['mean_places_gained']:.4f}",
        f"slow_mean_places={slow['mean_places_gained']:.4f}",
        f"fast_share_gained={fast['share_gained_a_place']:.4f}",
        f"slow_share_gained={slow['share_gained_a_place']:.4f}",
        f"fast_share_held={fast['share_held']:.4f}",
        f"slow_share_held={slow['share_held']:.4f}",
        f"fast_share_lost={fast['share_lost_a_place']:.4f}",
        f"slow_share_lost={slow['share_lost_a_place']:.4f}",
    ]
    (OUTPUT / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
