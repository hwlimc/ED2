#!/usr/bin/env python3
"""Create filled staging examples from local ED2/EDTS/FLA datasets."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

import h5py


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "projects" / "data" / "staging_examples"
FLA_MET = REPO_ROOT / "projects" / "data" / "fla" / "met" / "BORSOU_MET_2011JAN.h5"
FLA_CHD = REPO_ROOT / "projects" / "data" / "fla" / "ed_inputs" / "chd" / "temp.chd.avg.dat"
FLA_DGD = REPO_ROOT / "projects" / "data" / "fla" / "ed_inputs" / "dgd" / "temp.dgd.avg.dat"
FLA_PHEN = REPO_ROOT / "projects" / "data" / "fla" / "phenology" / "phenology.lat42.5lon-72.5.txt"
BARTLETT_DIR = REPO_ROOT / "ED" / "src" / "test_cases" / "bartlett_soi"
HAR_DIR = REPO_ROOT / "projects" / "data" / "edts_datasets" / "inits" / "har"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def empty_csv(path: Path, fieldnames: list[str]) -> None:
    write_csv(path, fieldnames, [])


def nearest_month_row(path: Path, target_lat: float, target_lon: float) -> dict[str, object]:
    best: tuple[float, list[str]] | None = None
    with path.open() as handle:
        for line in handle:
            parts = line.split()
            if len(parts) < 14:
                continue
            lat = float(parts[0])
            lon = float(parts[1])
            dist = (lat - target_lat) ** 2 + (lon - target_lon) ** 2
            if best is None or dist < best[0]:
                best = (dist, parts)
    if best is None:
        raise SystemExit(f"No month-table rows found in {path}")
    parts = best[1]
    fields = ["lat", "lon", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    return dict(zip(fields, parts))


def create_fla_local_example() -> None:
    target = EXAMPLES / "fla_local_minimal"
    lat = 64.09
    lon = 19.42
    met_rows: list[dict[str, object]] = []
    variables = ["hgt", "tmp", "pres", "sh", "ugrd", "vgrd", "prate", "dlwrf", "nbdsf", "nddsf", "vbdsf", "vddsf"]
    start = datetime(2011, 1, 1, tzinfo=timezone.utc)
    with h5py.File(FLA_MET, "r") as handle:
        lon_value = float(handle["lon"][()].reshape(-1)[0])
        lat_value = float(handle["lat"][()].reshape(-1)[0])
        for hour in range(6):
            when = start + timedelta(hours=hour)
            row: dict[str, object] = {
                "time": when.isoformat().replace("+00:00", "Z"),
                "lon": lon_value,
                "lat": lat_value,
            }
            for variable in variables:
                row[variable] = float(handle[variable][0, 0, hour])
            met_rows.append(row)

    write_text(
        target / "README.md",
        """# FLA Local Minimal Staging Example

This example is generated from local files in `projects/data/fla`.

- `met.csv` uses the first six hourly records from `projects/data/fla/met/BORSOU_MET_2011JAN.h5`.
- `domain.csv` and `soil_constants.csv` mirror the current FLA namelist assumptions.
- `thermal_sums_chd.csv` and `thermal_sums_dgd.csv` use the nearest available local thermal-sum grid row to lon 19.42, lat 64.09.

This is a format example, not a complete production forcing dataset. For a real run, `met.csv`
must contain every lon/lat/time combination for every hour of every simulated month.
""",
    )
    write_csv(
        target / "domain.csv",
        [
            "run_name",
            "mode",
            "start_time",
            "end_time",
            "grid_type",
            "n_ed_region",
            "grid_res",
            "lat_min",
            "lat_max",
            "lon_min",
            "lon_max",
            "n_poi",
            "poi_lat",
            "poi_lon",
            "poi_res",
            "met_prefix",
        ],
        [
            {
                "run_name": "fla_local_minimal",
                "mode": "region",
                "start_time": "2011-01-01T00:00:00Z",
                "end_time": "2011-01-01T06:00:00Z",
                "grid_type": 0,
                "n_ed_region": 1,
                "grid_res": 0.10,
                "lat_min": 63.94,
                "lat_max": 64.34,
                "lon_min": 19.37,
                "lon_max": 19.67,
                "n_poi": 0,
                "poi_lat": lat,
                "poi_lon": lon,
                "poi_res": 1.00,
                "met_prefix": "FLA_EXAMPLE_MET_",
            }
        ],
    )
    write_csv(
        target / "met.csv",
        ["time", "lon", "lat", *variables],
        met_rows,
    )
    write_csv(
        target / "soil_constants.csv",
        [
            "profile_id",
            "nzg",
            "nzs",
            "isoilflg",
            "islcolflg",
            "nslcon",
            "isoilcol",
            "slxclay",
            "slxsand",
            "slsoc",
            "slph",
            "slcec",
            "sldbd",
            "slz",
            "slmstr",
            "stgoff",
            "soil_hydro_scheme",
            "isoilbc",
            "sldrain",
            "isoilstateinit",
            "isoildepthflg",
        ],
        [
            {
                "profile_id": "fla_constant",
                "nzg": 12,
                "nzs": 1,
                "isoilflg": 2,
                "islcolflg": 2,
                "nslcon": 5,
                "isoilcol": 21,
                "slxclay": 0.345,
                "slxsand": 0.562,
                "slsoc": 0.0266,
                "slph": 4.7,
                "slcec": 0.124,
                "sldbd": 1192.0,
                "slz": "-9.00,-8.00,-6.00,-4.00,-2.00,-1.00,-0.60,-0.32,-0.16,-0.08,-0.04,-0.02",
                "slmstr": "0.80,0.80,0.80,0.80,0.80,0.80,0.80,0.80,0.80,0.80,0.80,0.80",
                "stgoff": "0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00",
                "soil_hydro_scheme": 0,
                "isoilbc": 3,
                "sldrain": 0.0,
                "isoilstateinit": 0,
                "isoildepthflg": 0,
            }
        ],
    )
    month_fields = ["lat", "lon", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    write_csv(target / "thermal_sums_chd.csv", month_fields, [nearest_month_row(FLA_CHD, lat, lon)])
    write_csv(target / "thermal_sums_dgd.csv", month_fields, [nearest_month_row(FLA_DGD, lat, lon)])
    empty_csv(target / "plantation_fraction.csv", ["lat", "lon", "fracplant"])
    empty_csv(target / "phenology_prescribed.csv", ["lat", "lon", "year", "flush_a", "flush_b", "color_a", "color_b"])
    empty_csv(
        target / "ed22_sites.csv",
        ["sname", "area", "depth", "nscol", "ntext", "sand", "clay", "slsoc", "slph", "slcec", "sldbd", "elevation", "slope", "aspect", "tci", "moist_f", "moist_w"],
    )
    empty_csv(
        target / "ed22_patches.csv",
        ["time", "sname", "pname", "dtype", "age", "area", "fgc", "fsc", "stgc", "stgl", "stsc", "stsl", "msc", "ssc", "psc", "fsn", "msn", "dummy1", "dummy2", "dummy3", "dummy4"],
    )
    empty_csv(
        target / "ed22_cohorts.csv",
        ["time", "sname", "pname", "cname", "dbh", "height", "pft", "nplant", "bdead", "balive", "dummy1", "dummy2"],
    )
    empty_csv(target / "observations.csv", ["time", "lon", "lat", "variable", "value", "unit", "source"])


def parse_space_table(path: Path, fieldnames: list[str], max_rows: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open() as handle:
        header = handle.readline().split()
        for line in handle:
            parts = line.split()
            if not parts:
                continue
            data = dict(zip(header, parts))
            rows.append({field: data.get(field, "") for field in fieldnames})
            if len(rows) >= max_rows:
                break
    return rows


def parse_position_table(path: Path, fieldnames: list[str], max_rows: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open() as handle:
        next(handle, None)
        for line in handle:
            parts = line.split()
            if not parts:
                continue
            rows.append({field: parts[idx] if idx < len(parts) else "" for idx, field in enumerate(fieldnames)})
            if len(rows) >= max_rows:
                break
    return rows


def create_edts_bartlett_example() -> None:
    target = EXAMPLES / "edts_bartlett_native_initial"
    write_text(
        target / "README.md",
        """# EDTS/Bartlett Native Initial-State Example

This example uses real local files from `ED/src/test_cases/bartlett_soi` and
`projects/data/edts_datasets/inits/har`.

Important distinction:

- `ed20_site_native.csv`, `ed20_patches_native.csv`, and `ed20_cohorts_native.csv` show
  the older ED-2.0/Bartlett-style SITE/PSS/CSS input shape used by `IED_INIT_MODE=3`.
- The generic builder currently writes ED2.2-style `.sss/.pss/.css` from
  `ed22_sites.csv`, `ed22_patches.csv`, and `ed22_cohorts.csv`.

Use this directory as a reference for the ecological meaning of site, patch, and cohort
columns. Do not mix the ED-2.0 native columns into the ED2.2 builder columns without an
explicit mapping step.
""",
    )
    write_csv(
        target / "domain.csv",
        [
            "run_name",
            "mode",
            "start_time",
            "end_time",
            "grid_type",
            "n_ed_region",
            "grid_res",
            "lat_min",
            "lat_max",
            "lon_min",
            "lon_max",
            "n_poi",
            "poi_lat",
            "poi_lon",
            "poi_res",
            "met_prefix",
        ],
        [
            {
                "run_name": "bartlett_native_initial",
                "mode": "poi",
                "start_time": "2002-06-01T12:00:00Z",
                "end_time": "2003-06-01T00:00:00Z",
                "grid_type": 0,
                "n_ed_region": 0,
                "grid_res": 1.0,
                "lat_min": 44.5,
                "lat_max": 44.5,
                "lon_min": -71.5,
                "lon_max": -71.5,
                "n_poi": 1,
                "poi_lat": 44.5,
                "poi_lon": -71.5,
                "poi_res": 1.0,
                "met_prefix": "BARTLETT_EXAMPLE_MET_",
            }
        ],
    )
    write_csv(
        target / "ed20_site_native.csv",
        ["sitenum", "area", "tci", "elev", "slope", "aspect", "soil1", "soil2", "soil3", "soil4", "soil5", "soil6", "soil7", "soil8", "soil9"],
        [{"sitenum": 2, "area": 1.0, "tci": -6.3, "elev": 784.818, "slope": 0.0, "aspect": 0.0, "soil1": 3, "soil2": 3, "soil3": 3, "soil4": 3, "soil5": 3, "soil6": 3, "soil7": 3, "soil8": 3, "soil9": 12}],
    )
    write_csv(
        target / "ed20_patches_native.csv",
        ["site", "year", "patch", "dst", "age", "area", "water", "fsc", "stsc", "stsl", "ssc", "psc", "msn", "fsn"],
        parse_space_table(BARTLETT_DIR / "bartlett.lat44.5lon-71.5.pss", ["site", "year", "patch", "dst", "age", "area", "water", "fsc", "stsc", "stsl", "ssc", "psc", "msn", "fsn"], 8),
    )
    write_csv(
        target / "ed20_cohorts_native.csv",
        ["time", "patch", "cohort", "dbh", "height", "pft", "nplant", "bdead", "balive", "avgRg"],
        parse_position_table(BARTLETT_DIR / "bartlett.lat44.5lon-71.5.css", ["time", "patch", "cohort", "dbh", "height", "pft", "nplant", "bdead", "balive", "avgRg"], 12),
    )
    phen_rows: list[dict[str, object]] = []
    with (BARTLETT_DIR / "phenology.lat44.5lon-71.5.txt").open() as handle:
        handle.readline()
        for line in handle:
            year, flush_a, flush_b, color_a, color_b = line.split()
            phen_rows.append(
                {
                    "lat": 44.5,
                    "lon": -71.5,
                    "year": year,
                    "flush_a": flush_a,
                    "flush_b": flush_b,
                    "color_a": color_a,
                    "color_b": color_b,
                }
            )
    write_csv(target / "phenology_prescribed.csv", ["lat", "lon", "year", "flush_a", "flush_b", "color_a", "color_b"], phen_rows)
    write_csv(
        target / "harvard_edts_patches_native.csv",
        ["time", "patch", "trk", "age", "area", "water", "fsc", "stsc", "stsl", "ssc", "psc", "msn", "fsn"],
        parse_space_table(HAR_DIR / "ems.lat42.5378lon-72.1715.pss", ["time", "patch", "trk", "age", "area", "water", "fsc", "stsc", "stsl", "ssc", "psc", "msn", "fsn"], 8),
    )
    write_csv(
        target / "harvard_edts_cohorts_native.csv",
        ["time", "patch", "cohort", "dbh", "height", "pft", "nplant", "bdead", "balive", "avgRg"],
        parse_position_table(HAR_DIR / "ems.lat42.5378lon-72.1715.css", ["time", "patch", "cohort", "dbh", "height", "pft", "nplant", "bdead", "balive", "avgRg"], 12),
    )


def create_units_reference() -> None:
    rows = [
        ("domain.csv", "run_name", "text", "Short simulation name used in ED2 fragments."),
        ("domain.csv", "mode", "region|poi", "Human-readable mode label; builder uses n_ed_region and n_poi."),
        ("domain.csv", "start_time,end_time", "UTC ISO-8601", "Simulation start and end times."),
        ("domain.csv", "grid_type", "integer", "0 lon/lat grid; 1 polar stereographic."),
        ("domain.csv", "grid_res,poi_res", "degree", "Grid or POI resolution for lon/lat runs."),
        ("domain.csv", "lat_min,lat_max,lon_min,lon_max,poi_lat,poi_lon", "degree", "WGS84 coordinates."),
        ("met.csv", "time", "UTC ISO-8601", "Meteorology timestamp."),
        ("met.csv", "lon,lat", "degree", "WGS84 grid-cell coordinate."),
        ("met.csv", "hgt", "m", "Meteorological reference height."),
        ("met.csv", "tmp", "K", "Air temperature."),
        ("met.csv", "pres", "Pa", "Air pressure."),
        ("met.csv", "sh", "kg/kg", "Specific humidity."),
        ("met.csv", "ugrd,vgrd", "m/s", "Zonal and meridional wind."),
        ("met.csv", "prate", "kg/m2/s", "Precipitation rate."),
        ("met.csv", "dlwrf,nbdsf,nddsf,vbdsf,vddsf", "W/m2", "Downwelling longwave and split shortwave radiation."),
        ("soil_constants.csv", "nzg,nzs", "count", "Soil and snow/water layer counts."),
        ("soil_constants.csv", "isoilflg,islcolflg,nslcon,isoilcol", "integer code", "ED2 soil texture/colour mode and classes."),
        ("soil_constants.csv", "slxclay,slxsand,slsoc", "fraction 0-1", "Clay, sand, and soil organic carbon mass fraction."),
        ("soil_constants.csv", "slph", "pH", "Soil pH."),
        ("soil_constants.csv", "slcec", "mol/kg", "Cation exchange capacity."),
        ("soil_constants.csv", "sldbd", "kg/m3", "Dry bulk density."),
        ("soil_constants.csv", "slz", "m", "Negative soil-layer bottom depths, deepest to shallowest."),
        ("soil_constants.csv", "slmstr", "index", "Initial soil moisture index: 0 wilting, 1 field capacity, 2 saturation."),
        ("soil_constants.csv", "stgoff", "K", "Initial soil temperature offset from air temperature."),
        ("thermal_sums_chd.csv", "jan..dec", "day or model thermal-sum unit", "Monthly chilling-degree state used by ED cold-deciduous phenology."),
        ("thermal_sums_dgd.csv", "jan..dec", "day or model thermal-sum unit", "Monthly growing-degree state used by ED cold-deciduous phenology."),
        ("plantation_fraction.csv", "fracplant", "fraction 0-1", "Forest plantation fraction at lon/lat."),
        ("phenology_prescribed.csv", "flush_a,flush_b,color_a,color_b", "ED phenology parameter", "Prescribed phenology curve parameters read by ED."),
        ("ed22_sites.csv", "area", "fraction", "Fractional site area inside polygon; builder normalises during ED initialisation."),
        ("ed22_sites.csv", "depth", "m", "Site soil depth."),
        ("ed22_sites.csv", "nscol,ntext", "integer code", "Soil colour and texture class."),
        ("ed22_sites.csv", "sand,clay,slsoc", "fraction 0-1", "Site-level soil fractions."),
        ("ed22_sites.csv", "elevation", "m", "Site elevation."),
        ("ed22_sites.csv", "slope", "degree", "Terrain slope."),
        ("ed22_sites.csv", "aspect", "degree", "Terrain aspect."),
        ("ed22_sites.csv", "tci", "index", "Topographic convergence index."),
        ("ed22_patches.csv", "area", "fraction", "Patch fractional area in site."),
        ("ed22_patches.csv", "age", "year", "Patch age."),
        ("ed22_patches.csv", "fgc,fsc,stgc,stgl,stsc,stsl,msc,ssc,psc", "kgC/m2", "Patch carbon pools used by ED initialisation."),
        ("ed22_patches.csv", "fsn,msn", "kgN/m2", "Patch nitrogen pools."),
        ("ed22_cohorts.csv", "dbh", "cm", "Diameter at breast height."),
        ("ed22_cohorts.csv", "height", "m", "Cohort height."),
        ("ed22_cohorts.csv", "pft", "integer code", "ED plant functional type."),
        ("ed22_cohorts.csv", "nplant", "plants/m2", "Cohort plant density."),
        ("ed22_cohorts.csv", "bdead,balive", "kgC/plant", "Dead and live biomass pools, optional initial values."),
        ("observations.csv", "value,unit", "as supplied", "Observation value and its unit for later model-data comparison."),
    ]
    write_csv(
        EXAMPLES / "field_units.csv",
        ["template", "column", "unit", "description"],
        [{"template": a, "column": b, "unit": c, "description": d} for a, b, c, d in rows],
    )


def main() -> int:
    create_fla_local_example()
    create_edts_bartlett_example()
    create_units_reference()
    write_text(
        EXAMPLES / "README.md",
        """# ED2 Staging Examples

These examples are filled from local datasets and test cases.

- `fla_local_minimal/`: ED2-ready staging CSVs generated from local FLA meteorology and namelist assumptions.
- `edts_bartlett_native_initial/`: native EDTS/Bartlett-style site, patch, cohort, and phenology examples.
- `field_units.csv`: unit and meaning reference for the staging columns.

For a complete simulation, use the same columns but provide full spatial and temporal
coverage, not just the short sample rows included here.
""",
    )
    print(f"wrote {EXAMPLES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
