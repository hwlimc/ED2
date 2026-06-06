#!/usr/bin/env python3
"""Export ED2 HDF5 output files to readable CSV files."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import h5py
import numpy as np


def dataset_items(handle: h5py.File):
    items = []

    def visit(name: str, obj):
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


def first_values_text(array: np.ndarray, limit: int = 8) -> str:
    flat = np.ravel(array)
    return ";".join(value_to_text(v) for v in flat[:limit])


def numeric_summary(array: np.ndarray):
    if array.size == 0 or not np.issubdtype(array.dtype, np.number):
        return "", "", ""
    values = array.astype(float, copy=False)
    return np.nanmin(values), np.nanmax(values), np.nanmean(values)


def write_dataset_values(writer: csv.writer, dataset: str, data) -> None:
    array = np.asarray(data)
    if array.shape == ():
        writer.writerow([dataset, "", value_to_text(array.item())])
        return

    for index in np.ndindex(array.shape):
        writer.writerow([dataset, " ".join(str(i) for i in index), value_to_text(array[index])])


def export_file(h5_path: Path, csv_path: Path, summary_writer: csv.writer, manifest_writer: csv.writer) -> None:
    with h5py.File(h5_path, "r") as handle, csv_path.open("w", newline="") as out:
        value_writer = csv.writer(out)
        value_writer.writerow(["dataset", "index", "value"])

        for name, dataset in dataset_items(handle):
            data = dataset[()]
            array = np.asarray(data)
            shape = "x".join(str(dim) for dim in array.shape) if array.shape else "scalar"
            dtype = str(array.dtype)
            count = int(array.size)
            min_value, max_value, mean_value = numeric_summary(array)

            manifest_writer.writerow([h5_path.name, name, shape, dtype, count])
            summary_writer.writerow(
                [
                    h5_path.name,
                    name,
                    shape,
                    dtype,
                    count,
                    min_value,
                    max_value,
                    mean_value,
                    first_values_text(array),
                ]
            )
            write_dataset_values(value_writer, name, data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path, help="Directory containing ED2 .h5 output files")
    parser.add_argument("output_dir", type=Path, help="Directory for readable CSV exports")
    args = parser.parse_args()

    h5_files = sorted(args.input_dir.glob("*.h5"))
    if not h5_files:
        raise SystemExit(f"No .h5 files found in {args.input_dir}")

    csv_dir = args.output_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    with (args.output_dir / "manifest.csv").open("w", newline="") as manifest_file, (
        args.output_dir / "summary.csv"
    ).open("w", newline="") as summary_file:
        manifest_writer = csv.writer(manifest_file)
        summary_writer = csv.writer(summary_file)
        manifest_writer.writerow(["file", "dataset", "shape", "dtype", "count"])
        summary_writer.writerow(["file", "dataset", "shape", "dtype", "count", "min", "max", "mean", "first_values"])

        for h5_path in h5_files:
            csv_path = csv_dir / f"{h5_path.stem}.csv"
            export_file(h5_path, csv_path, summary_writer, manifest_writer)
            print(f"exported {h5_path.name} -> {csv_path.name}")

    print(f"wrote {len(h5_files)} file exports to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
