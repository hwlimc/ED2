#!/usr/bin/env python3
"""Selectively extract ED2 HDF5 output datasets to CSV."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Iterable

import h5py
import numpy as np


DEFAULT_VARIABLES = (
    "MMEAN_GPP_PY",
    "MMEAN_NPP_PY",
    "MMEAN_NEP_PY",
    "MMEAN_RH_PY",
    "MMEAN_LAI_PY",
    "MMEAN_PCPG_PY",
    "MMEAN_ATM_TEMP_PY",
    "MMEAN_SOIL_WATER_PY",
    "AGB_PY",
    "BASAL_AREA_PY",
)

FILE_RE = re.compile(
    r"-(?P<kind>[A-Z])-(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})-"
    r"(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})-g(?P<grid>\d+)\.h5$"
)


def parse_variables(items: list[str] | None) -> list[str]:
    if not items:
        return list(DEFAULT_VARIABLES)
    variables: list[str] = []
    for item in items:
        variables.extend(part.strip() for part in item.split(",") if part.strip())
    return variables


def dataset_items(handle: h5py.File) -> list[tuple[str, h5py.Dataset]]:
    items: list[tuple[str, h5py.Dataset]] = []

    def visit(name: str, obj) -> None:
        if isinstance(obj, h5py.Dataset):
            items.append((name, obj))

    handle.visititems(visit)
    return items


def value_to_text(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, np.bytes_):
        return bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, np.generic):
        value = value.item()
    return str(value)


def first_values(array: np.ndarray, limit: int) -> str:
    flat = np.ravel(array)
    return ";".join(value_to_text(value) for value in flat[:limit])


def numeric_summary(array: np.ndarray) -> tuple[str, str, str]:
    if array.size == 0 or not np.issubdtype(array.dtype, np.number):
        return "", "", ""
    values = array.astype(float, copy=False)
    return str(np.nanmin(values)), str(np.nanmax(values)), str(np.nanmean(values))


def file_metadata(path: Path) -> dict[str, str]:
    match = FILE_RE.search(path.name)
    if not match:
        return {
            "kind": "",
            "year": "",
            "month": "",
            "day": "",
            "hour": "",
            "minute": "",
            "second": "",
            "grid": "",
            "timestamp": "",
        }
    data = match.groupdict()
    day = "01" if data["day"] == "00" else data["day"]
    hour = data["hour"]
    minute = data["minute"]
    second = data["second"]
    data["timestamp"] = f"{data['year']}-{data['month']}-{day}T{hour}:{minute}:{second}"
    return data


def shape_text(array: np.ndarray) -> str:
    return shape_text_from_shape(array.shape)


def shape_text_from_shape(shape: tuple[int, ...]) -> str:
    return "scalar" if shape == () else "x".join(str(dim) for dim in shape)


def iter_selected(handle: h5py.File, variables: Iterable[str], ignore_case: bool) -> list[tuple[str, h5py.Dataset]]:
    available = dict(dataset_items(handle))
    if not ignore_case:
        return [(name, available[name]) for name in variables if name in available]

    lower_lookup = {name.lower(): name for name in available}
    selected: list[tuple[str, h5py.Dataset]] = []
    for variable in variables:
        actual = lower_lookup.get(variable.lower())
        if actual is not None:
            selected.append((actual, available[actual]))
    return selected


def list_datasets(paths: list[Path], limit: int) -> int:
    writer = csv.writer(sys.stdout)
    writer.writerow(["file", "dataset", "shape", "dtype", "count"])
    for path in paths[:limit]:
        with h5py.File(path, "r") as handle:
            for name, dataset in dataset_items(handle):
                writer.writerow([path.name, name, shape_text_from_shape(dataset.shape), str(dataset.dtype), dataset.size])
    return 0


def write_summary_row(writer: csv.writer, path: Path, metadata: dict[str, str], name: str, dataset: h5py.Dataset) -> None:
    array = np.asarray(dataset[()])
    min_value, max_value, mean_value = numeric_summary(array)
    writer.writerow(
        [
            path.name,
            metadata["kind"],
            metadata["grid"],
            metadata["timestamp"],
            metadata["year"],
            metadata["month"],
            metadata["day"],
            metadata["hour"],
            name,
            shape_text(array),
            str(array.dtype),
            int(array.size),
            min_value,
            max_value,
            mean_value,
            first_values(array, 8),
        ]
    )


def write_value_rows(
    writer: csv.writer,
    path: Path,
    metadata: dict[str, str],
    name: str,
    dataset: h5py.Dataset,
    max_elements: int,
) -> None:
    array = np.asarray(dataset[()])
    if array.shape == ():
        writer.writerow(
            [
                path.name,
                metadata["kind"],
                metadata["grid"],
                metadata["timestamp"],
                metadata["year"],
                metadata["month"],
                metadata["day"],
                metadata["hour"],
                name,
                "",
                value_to_text(array.item()),
            ]
        )
        return

    written = 0
    for index in np.ndindex(array.shape):
        if max_elements and written >= max_elements:
            break
        writer.writerow(
            [
                path.name,
                metadata["kind"],
                metadata["grid"],
                metadata["timestamp"],
                metadata["year"],
                metadata["month"],
                metadata["day"],
                metadata["hour"],
                name,
                " ".join(str(item) for item in index),
                value_to_text(array[index]),
            ]
        )
        written += 1


def export(args: argparse.Namespace, paths: list[Path], variables: list[str]) -> int:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    missing_seen: set[str] = set()
    with args.output.open("w", newline="") as handle:
        writer = csv.writer(handle)
        if args.mode == "summary":
            writer.writerow(
                [
                    "file",
                    "type",
                    "grid",
                    "timestamp",
                    "year",
                    "month",
                    "day",
                    "hour",
                    "dataset",
                    "shape",
                    "dtype",
                    "count",
                    "min",
                    "max",
                    "mean",
                    "first_values",
                ]
            )
        else:
            writer.writerow(
                ["file", "type", "grid", "timestamp", "year", "month", "day", "hour", "dataset", "index", "value"]
            )

        for path in paths:
            metadata = file_metadata(path)
            with h5py.File(path, "r") as h5:
                selected = iter_selected(h5, variables, args.ignore_case)
                found = {name.lower() if args.ignore_case else name for name, _ in selected}
                for variable in variables:
                    key = variable.lower() if args.ignore_case else variable
                    if key not in found and variable not in missing_seen:
                        message = f"missing dataset {variable!r}; first noticed in {path.name}"
                        if args.fail_missing:
                            raise SystemExit(message)
                        print(f"warning: {message}", file=sys.stderr)
                        missing_seen.add(variable)
                for name, dataset in selected:
                    if args.mode == "summary":
                        write_summary_row(writer, path, metadata, name, dataset)
                    else:
                        write_value_rows(writer, path, metadata, name, dataset, args.max_elements_per_dataset)
    print(f"wrote {args.output}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path, help="Directory containing ED2 .h5 outputs.")
    parser.add_argument("output", type=Path, help="CSV file to write.")
    parser.add_argument("--pattern", default="analysis-E-*.h5", help="Glob pattern inside input_dir.")
    parser.add_argument(
        "--variables",
        action="append",
        help="Comma-separated datasets to extract. Default is a small common monthly set.",
    )
    parser.add_argument("--mode", choices=("values", "summary"), default="values")
    parser.add_argument("--ignore-case", action="store_true")
    parser.add_argument("--fail-missing", action="store_true")
    parser.add_argument("--max-files", type=int, default=0, help="Limit number of files processed. 0 means no limit.")
    parser.add_argument(
        "--max-elements-per-dataset",
        type=int,
        default=0,
        help="In values mode, limit flattened values per dataset per file. 0 means no limit.",
    )
    parser.add_argument("--list-datasets", action="store_true", help="Print dataset inventory as CSV to stdout.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    paths = sorted(args.input_dir.glob(args.pattern))
    if args.max_files:
        paths = paths[: args.max_files]
    if not paths:
        raise SystemExit(f"No files matched {args.input_dir / args.pattern}")

    if args.list_datasets:
        return list_datasets(paths, limit=len(paths))

    return export(args, paths, parse_variables(args.variables))


if __name__ == "__main__":
    raise SystemExit(main())
