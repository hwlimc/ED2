#!/usr/bin/env python3
"""Create ED2 meteorology HDF5 files and an ED_MET_DRIVER_HEADER from CSV data.

The CSV is expected to be in a clean staging format: one row per UTC timestamp,
longitude, and latitude. Variables must already be in ED2 units.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np


MONTH_NAMES = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")

DEFAULT_VARIABLES = (
    "hgt",
    "tmp",
    "pres",
    "sh",
    "ugrd",
    "vgrd",
    "prate",
    "dlwrf",
    "nbdsf",
    "nddsf",
    "vbdsf",
    "vddsf",
)

DEFAULT_FLAGS = {
    "lon": 2,
    "lat": 2,
    "hgt": 1,
    "tmp": 1,
    "pres": 1,
    "sh": 1,
    "ugrd": 1,
    "vgrd": 1,
    "prate": 0,
    "dlwrf": 1,
    "nbdsf": 1,
    "nddsf": 1,
    "vbdsf": 1,
    "vddsf": 1,
    "co2": 1,
    "ustar": 1,
    "land": 2,
}


@dataclass(frozen=True)
class Record:
    time: datetime
    lon: float
    lat: float
    values: dict[str, float]


def parse_time(text: str) -> datetime:
    value = text.strip()
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(tzinfo=timezone.utc)


def parse_variables(text: str) -> list[str]:
    variables = [item.strip().lower() for item in text.split(",") if item.strip()]
    if not variables:
        raise SystemExit("At least one meteorology variable is required.")
    return variables


def parse_flags(text: str) -> dict[str, int]:
    flags: dict[str, int] = {}
    if not text:
        return flags
    for item in text.split(","):
        if not item.strip():
            continue
        try:
            name, value = item.split("=", 1)
        except ValueError as exc:
            raise SystemExit(f"Invalid --flags item {item!r}; expected name=value") from exc
        flags[name.strip().lower()] = int(value)
    return flags


def spacing(values: list[float], fallback: float, name: str) -> float:
    if len(values) == 1:
        return fallback
    diffs = np.diff(np.asarray(values, dtype=float))
    if np.any(diffs <= 0):
        raise SystemExit(f"{name} coordinates must be strictly increasing.")
    if float(np.max(diffs) - np.min(diffs)) > 1.0e-6:
        raise SystemExit(f"{name} coordinates are not regular enough for an ED2 header.")
    return float(np.mean(diffs))


def infer_frequency_seconds(times: list[datetime]) -> float:
    unique_times = sorted(set(times))
    if len(unique_times) < 2:
        return 3600.0
    diffs = {
        int((right - left).total_seconds())
        for left, right in zip(unique_times[:-1], unique_times[1:])
        if right > left
    }
    if len(diffs) != 1:
        raise SystemExit("Could not infer one fixed input frequency; set --frequency-seconds explicitly.")
    return float(diffs.pop())


def read_records(args: argparse.Namespace, variables: list[str]) -> tuple[list[Record], list[float], list[float]]:
    records: list[Record] = []
    lons: set[float] = set()
    lats: set[float] = set()

    with args.csv.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter=args.delimiter)
        if not reader.fieldnames:
            raise SystemExit(f"{args.csv} has no header row.")
        fields = set(reader.fieldnames)

        required_columns = {args.time_column, args.lon_column, args.lat_column}
        missing_required = sorted(required_columns - fields)
        if missing_required:
            raise SystemExit(f"Missing required CSV columns: {', '.join(missing_required)}")

        missing_vars = [
            variable
            for variable in variables
            if variable not in fields and not (variable == "hgt" and args.height is not None)
        ]
        if missing_vars:
            raise SystemExit(f"Missing variable columns: {', '.join(missing_vars)}")

        for line_number, row in enumerate(reader, start=2):
            try:
                when = parse_time(row[args.time_column])
                lon = float(row[args.lon_column])
                lat = float(row[args.lat_column])
                values: dict[str, float] = {}
                for variable in variables:
                    if variable == "hgt" and variable not in row:
                        values[variable] = float(args.height)
                    elif variable == "hgt" and row.get(variable, "") == "":
                        values[variable] = float(args.height)
                    else:
                        values[variable] = float(row[variable])
            except Exception as exc:  # noqa: BLE001 - report CSV line context to user.
                raise SystemExit(f"Could not parse {args.csv}:{line_number}: {exc}") from exc

            records.append(Record(time=when, lon=lon, lat=lat, values=values))
            lons.add(lon)
            lats.add(lat)

    if not records:
        raise SystemExit(f"{args.csv} contains no data rows.")
    return records, sorted(lons), sorted(lats)


def write_month_file(
    path: Path,
    month_records: list[Record],
    variables: list[str],
    lons: list[float],
    lats: list[float],
    allow_missing: bool,
) -> None:
    times = sorted({record.time for record in month_records})
    lon_index = {value: idx for idx, value in enumerate(lons)}
    lat_index = {value: idx for idx, value in enumerate(lats)}
    time_index = {value: idx for idx, value in enumerate(times)}

    shape = (len(lons), len(lats), len(times))
    arrays = {variable: np.full(shape, np.nan, dtype=np.float64) for variable in variables}
    seen: set[tuple[int, int, int]] = set()

    for record in month_records:
        key = (lon_index[record.lon], lat_index[record.lat], time_index[record.time])
        if key in seen:
            raise SystemExit(
                f"Duplicate row for lon={record.lon}, lat={record.lat}, time={record.time.isoformat()}"
            )
        seen.add(key)
        for variable in variables:
            arrays[variable][key] = record.values[variable]

    expected = len(lons) * len(lats) * len(times)
    if len(seen) != expected and not allow_missing:
        raise SystemExit(
            f"{path.name} is missing {expected - len(seen)} lon/lat/time combinations; "
            "use --allow-missing only after deciding how ED2 should handle NaNs."
        )

    if not allow_missing:
        for variable, values in arrays.items():
            if np.isnan(values).any():
                raise SystemExit(f"{path.name} has missing values for {variable}.")

    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as handle:
        lon_grid = np.repeat(np.asarray(lons, dtype=np.float64)[:, None], len(lats), axis=1)
        lat_grid = np.repeat(np.asarray(lats, dtype=np.float64)[None, :], len(lons), axis=0)
        handle.create_dataset("lon", data=lon_grid)
        handle.create_dataset("lat", data=lat_grid)
        for variable in variables:
            handle.create_dataset(variable, data=arrays[variable])


def write_header(
    path: Path,
    header_prefix: str,
    variables: list[str],
    lons: list[float],
    lats: list[float],
    dx: float,
    dy: float,
    frequency_seconds: float,
    avgtype: int,
    flag_overrides: dict[str, int],
) -> None:
    all_variables = ["lon", "lat", *variables]
    flags = [flag_overrides.get(variable, DEFAULT_FLAGS.get(variable, 1)) for variable in all_variables]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="\n") as handle:
        handle.write("# ED meteorology header generated by scripts/csv_to_ed2_met.py\n")
        handle.write("1\n")
        handle.write(f"{header_prefix}\n")
        handle.write(f"{len(lons)} {len(lats)} {dx:.10g} {dy:.10g} {min(lons):.10g} {min(lats):.10g}\n")
        handle.write(f"{avgtype}\n")
        handle.write(f"{len(all_variables)}\n")
        handle.write(" ".join(f"'{variable}'" for variable in all_variables) + "\n")
        handle.write(" ".join(f"{frequency_seconds:.10g}" for _ in all_variables) + "\n")
        handle.write(" ".join(str(flag) for flag in flags) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="Staging CSV file in ED2-ready units.")
    parser.add_argument("output_dir", type=Path, help="Directory for monthly HDF5 files and header.")
    parser.add_argument("--prefix", default="ED_MET_", help="Output file prefix before YYYYMON.h5.")
    parser.add_argument("--header", type=Path, help="Header path. Default: output_dir/ED_MET_DRIVER_HEADER.")
    parser.add_argument(
        "--header-prefix",
        help="Path and prefix written inside the header. Default: absolute output_dir/prefix.",
    )
    parser.add_argument("--variables", default=",".join(DEFAULT_VARIABLES), help="Comma-separated ED2 variables.")
    parser.add_argument("--flags", default="", help="Comma-separated interpolation flags, e.g. prate=0,tmp=1.")
    parser.add_argument("--delimiter", default=",", help="CSV delimiter.")
    parser.add_argument("--time-column", default="time")
    parser.add_argument("--lon-column", default="lon")
    parser.add_argument("--lat-column", default="lat")
    parser.add_argument("--height", type=float, default=30.0, help="Reference height if hgt is absent or blank.")
    parser.add_argument("--single-cell-dx", type=float, default=1.0)
    parser.add_argument("--single-cell-dy", type=float, default=1.0)
    parser.add_argument("--frequency-seconds", type=float, help="Input update frequency. Default: infer from times.")
    parser.add_argument("--avgtype", type=int, default=0, help="ED2 met_avgtype line in ED_MET_DRIVER_HEADER.")
    parser.add_argument("--allow-missing", action="store_true", help="Allow NaNs for missing lon/lat/time cells.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    variables = parse_variables(args.variables)
    flag_overrides = parse_flags(args.flags)
    records, lons, lats = read_records(args, variables)

    frequency_seconds = args.frequency_seconds or infer_frequency_seconds([record.time for record in records])
    dx = spacing(lons, args.single_cell_dx, "Longitude")
    dy = spacing(lats, args.single_cell_dy, "Latitude")

    by_month: dict[tuple[int, int], list[Record]] = defaultdict(list)
    for record in records:
        by_month[(record.time.year, record.time.month)].append(record)

    for (year, month), month_records in sorted(by_month.items()):
        out = args.output_dir / f"{args.prefix}{year:04d}{MONTH_NAMES[month - 1]}.h5"
        write_month_file(out, month_records, variables, lons, lats, args.allow_missing)
        print(f"wrote {out}", file=sys.stderr)

    header_path = args.header or args.output_dir / "ED_MET_DRIVER_HEADER"
    header_prefix = args.header_prefix
    if header_prefix is None:
        header_prefix = str((args.output_dir.resolve() / args.prefix))
    write_header(header_path, header_prefix, variables, lons, lats, dx, dy, frequency_seconds, args.avgtype, flag_overrides)
    print(f"wrote {header_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
