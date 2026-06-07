# ED2 FLA Large-Scale Input and Output Pipeline

This note is specific to this checkout under `/home/hlim/ED2`. It records what is already here, what the older utilities are for, and a practical path for preparing ED2 inputs and extracting outputs for FLA or a larger regional run.

## Local Inventory

### Main model and run files

- `ED/` is the standalone ED2 model.
- FLA namelists are in `ED/run/`:
  - `ED2IN-fla.smoke`: 2011-01-01 to 2011-02-01 point smoke run.
  - `ED2IN-fla`: 2011-01-01 to 2016-01-01 regional run over 63.94-64.34 N, 19.37-19.67 E at `GRID_RES=0.10`.
  - `ED2IN-fla-spinup-init`: initial near-bare-ground spinup.
  - `ED2IN-fla-spinup-history-2015-2511`: history continuation from the regional history prefix.
- `run_fla.sh` runs the serial/container smoke case with `ed2-intel.sif`.
- `run_fla_mpi.sh` runs MPI with `ed2-mpi-intel.sif` and defaults to 4 ranks.

### Current FLA input data

- `projects/data/fla/met/` contains 2011-2015 monthly ED2 meteorology files named `BORSOU_MET_YYYYMON.h5` and `ED_MET_DRIVER_HEADER`.
- The existing meteorology header points to one grid cell at lon 19.42, lat 64.09 and lists `lon`, `lat`, `hgt`, `tmp`, `pres`, `sh`, `ugrd`, `vgrd`, `prate`, `dlwrf`, `nbdsf`, `nddsf`, `vbdsf`, and `vddsf`.
- `projects/data/fla/veg_oge/` contains an OGE vegetation mask/header. In this run it is used as `VEG_DATABASE`, mainly for land/water masking.
- `projects/data/fla/ed_inputs/` contains thermal sum files and `fraction.plantation`.
- Soil, land-use, observations, soil-state, soil-depth, phenology, events, and XML config files are currently not active in the FLA namelists: most paths are empty, hard-coded constants, or placeholders.

### Existing output volume

The local FLA output tree has 340,668 HDF5 files:

- `scratch/fla/outputs/fla-smoke`: 1,964 files.
- `scratch/fla/outputs/fla`: 1,963 files.
- `scratch/fla/outputs/fla-regional`: 140,617 files.
- `scratch/fla/spinup`: 196,124 files.

This is too large for full expansion to CSV. Use variable-selective extraction.

## What The Utility Folders Are For

- `RAPP/`: legacy NCEP/NCAR reanalysis preprocessor. It creates ED2 meteorology HDF5 plus a met header. It is useful if the input source is old NCEP-style NetCDF and if you build the missing `rapp-1.0` executable. It is not a general converter for ERA5, observations, or arbitrary local datasets.
- `Ramspost/`: BRAMS atmospheric model postprocessor that creates GrADS files. It is not the right tool for standalone ED2 HDF5 analysis outputs.
- `BRAMS/`: coupled atmospheric model source. The ED2 README notes this coupled code has not been tested in a while. Use standalone ED2 first unless you explicitly need atmosphere-biosphere coupling.
- `R-utils/`: R helper scripts for ED/BRAMS pre- and post-processing. `R-utils/read.q.files.r` and `ED/Template/Template/read_monthly.r` can read monthly ED2 outputs into R workflows, but they are old workflow scripts, not minimal extraction tools.

## Recommended Workflow

### 0. Create a staging package

I added reusable staging templates in `projects/data/staging_templates/`. Create a new staging package for a region with:

```bash
scripts/build_ed2_inputs_from_staged.py init projects/data/<region>/staged
```

Then replace the sample rows in those CSV files with your data. The main files are `domain.csv`, `met.csv`, `soil_constants.csv`, optional `thermal_sums_chd.csv`, optional `thermal_sums_dgd.csv`, optional `plantation_fraction.csv`, optional `phenology_prescribed.csv`, and optional ED2.2 initial-state files `ed22_sites.csv`, `ed22_patches.csv`, and `ed22_cohorts.csv`.

Build ED-ready files and ED2IN fragments with:

```bash
scripts/build_ed2_inputs_from_staged.py build projects/data/<region>/staged projects/data/<region>/ed_ready \
  --region-name <region>
```

The builder writes `met/ED_MET_DRIVER_HEADER`, monthly met HDF5 files, optional `ed_inputs/` files, optional prescribed phenology text files, optional ED2.2 `.sss/.pss/.css` initial files, `fragments/*.nml` snippets for an ED2IN copy, and `MANIFEST.txt`.

### 1. Stage source data into a canonical layout

Use one project directory per region:

```text
projects/data/<region>/
  raw/
  staged/
  met/
  veg_oge/
  soil/
  land_use/
  phenology/
  observations/
  ed_inputs/
```

Keep all staged data in WGS84 lon/lat, UTC timestamps, and ED2 units before writing ED2 files. Do unit conversions outside ED2:

- `tmp`: K
- `pres`: Pa
- `sh`: kg/kg
- `ugrd`, `vgrd`: m/s
- `prate`: kg/m2/s
- `dlwrf`, `nbdsf`, `nddsf`, `vbdsf`, `vddsf`: W/m2
- `hgt`: m reference height

### 2. Meteorology input path

For arbitrary observation/reanalysis data, convert to ED2 monthly HDF5 and header. I added:

```bash
scripts/csv_to_ed2_met.py source_met.csv projects/data/<region>/met --prefix REGION_MET_
```

Expected staging CSV columns:

```text
time,lon,lat,hgt,tmp,pres,sh,ugrd,vgrd,prate,dlwrf,nbdsf,nddsf,vbdsf,vddsf
```

The script writes files like `REGION_MET_2011JAN.h5` and `ED_MET_DRIVER_HEADER`. For a point run, there is one lon/lat per time. For a region, provide one row for every lon/lat/time combination on a regular grid.

In the ED2IN file, set:

```text
NL%ED_MET_DRIVER_DB = '/absolute/or/run-relative/path/to/ED_MET_DRIVER_HEADER'
NL%METCYC1 = first_met_year
NL%METCYCF = last_met_year
NL%IMETTYPE = 1
```

Use `RAPP` only when you want to reproduce the old NCEP workflow. Its documented local flow is: edit `RAPP/run/download.sh`, download NCEP variables, build/link `rapp-1.0` into `RAPP/run`, edit `RAPP/run/RAPP_IN`, run it, then point `NL%ED_MET_DRIVER_DB` to the generated header.

### 3. Vegetation and initial state

There are three practical levels:

1. Near-bare-ground spinup: use `NL%IED_INIT_MODE=0`, set `INCLUDE_THESE_PFT`, and spin up for long enough to produce a history restart. This is what the current FLA setup mostly does.
2. History restart: run `RUNTYPE='HISTORY'`, set `NL%SFILIN` to the previous `history` prefix, and choose `IYEARH/IMONTHH/IDATEH/ITIMEH` to match an existing `-S-` file.
3. Observation-initialized vegetation: create ED2 PSS/CSS/SITE files or ED2 history files from forest inventory, lidar, or plot data. This is the most realistic option but also the most format-sensitive; use PEcAn.ED2 or ED2 test-suite examples as references before relying on a custom converter.

For regional FLA realism, do not jump straight from the current single-cell meteorology to a 0.10 degree regional run unless you also have gridded meteorology and gridded/point-appropriate initial vegetation. Otherwise every polygon is driven by the same meteorology and simplified soil.

### 4. Soil and edaphic inputs

The current FLA namelists use constant soil settings:

```text
NL%ISOILFLG = 2
NL%ISLCOLFLG = 2
NL%NSLCON = 5
NL%ISOILCOL = 21
NL%SLXCLAY = .345
NL%SLXSAND = .562
NL%SLSOC = 0.0266
NL%SLPH = 4.7
NL%SLCEC = 0.124
NL%SLDBD = 1192.
```

This is acceptable for debugging and a first controlled experiment. For a regional simulation, prepare gridded soil texture/colour/depth inputs and switch:

```text
NL%ISOILFLG = 1
NL%SOIL_DATABASE = 'path/prefix'
NL%ISLCOLFLG = 1
NL%SLCOL_DATABASE = 'path/prefix'
NL%ISOILDEPTHFLG = 2
NL%SOILDEPTH_DB = 'path/prefix_or_header'
```

If you do not have these databases yet, keep the constant soil case but document it as a simplifying assumption.

### 5. Phenology, land use, and events

- Current FLA has `NL%IPHEN_SCHEME=0`, so phenology is predicted internally.
- To prescribe cold-deciduous phenology, set `NL%IPHEN_SCHEME=1`, fill `NL%PHENPATH`, and set `IPHENYS1/IPHENYSF/IPHENYF1/IPHENYFF`.
- Land-use disturbance requires `NL%IANTH_DISTURB=1` or `2`, valid `NL%LU_DATABASE`, and optionally `NL%PLANTATION_FILE`.
- Management/disturbance event files are XML and attached through `NL%EVENT_FILE`.

### 6. MPI run scale

For a realistic MPI run:

1. Start with `ED2IN-fla.smoke` until it completes.
2. Run `ED2IN-fla-spinup-init` to create a stable history file.
3. Continue with a history run only after verifying that `SFILIN` matches an existing `history-S-YYYY-MM-DD-HHNNSS-g01.h5`.
4. For MPI, use:

```bash
ED2_INPUT=ED2IN-fla ED2_MPI_RANKS=8 ./run_fla_mpi.sh
```

Before increasing region size, reduce output volume:

```text
NL%IFOUTPUT = 0
NL%IDOUTPUT = 0 or 3 only when daily output is needed
NL%IMOUTPUT = 3
NL%IQOUTPUT = 0 unless diel cycle is needed
NL%IYOUTPUT = 3 for long spinups
NL%ISOUTPUT = 3, but keep history frequency coarse
NL%IADD_COHORT_MEANS = 0 for large regional production unless cohort output is essential
```

The ED2 wiki explicitly warns not to use state/history files for research analysis; they are for reproducible restart. Use analysis files (`-D-`, `-E-`, `-Q-`, `-Y-`) for science outputs.

## Extracting Outputs

Use the new selective extractor instead of exporting every value from every HDF5 file:

```bash
scripts/extract_ed2_outputs.py scratch/fla/outputs/fla-smoke scratch/fla/outputs/fla-smoke_monthly_summary.csv \
  --pattern 'analysis-E-*.h5' \
  --variables MMEAN_GPP_PY,MMEAN_NPP_PY,MMEAN_LAI_PY,AGB_PY \
  --mode summary
```

For a direct time series of all values:

```bash
scripts/extract_ed2_outputs.py scratch/fla/outputs/fla-smoke scratch/fla/outputs/fla-smoke_monthly_values.csv \
  --pattern 'analysis-E-*.h5' \
  --variables MMEAN_GPP_PY,MMEAN_LAI_PY \
  --mode values
```

To see available datasets in representative files:

```bash
scripts/extract_ed2_outputs.py scratch/fla/outputs/fla-smoke /tmp/unused.csv \
  --pattern 'analysis-E-*.h5' \
  --max-files 1 \
  --list-datasets
```

The older `scripts/export_h5_to_csv.py` still works for small directories, but it expands every dataset from every file. Do not run it on `scratch/fla/spinup` or `scratch/fla/outputs/fla-regional` unless you intentionally want a very large export.

## Checklist Before A Production Regional Run

- Meteorology grid covers the full ED2 region plus enough margin for interpolation.
- `ED_MET_DRIVER_HEADER` has the correct path prefix as seen from `ED/run`.
- `METCYC1/METCYCF` match available meteorology years.
- `N_ED_REGION`, `GRID_TYPE`, `GRID_RES`, and region bounds match the intended domain.
- Soil settings are either documented constants or valid gridded databases.
- Initial vegetation is either a deliberate near-bare-ground spinup or valid PSS/CSS/SITE/history input.
- Output flags are coarse enough that the run will not create hundreds of thousands of unneeded files.
- `ATTACH_METADATA=1` for new production runs if storage overhead is acceptable; this makes HDF5 outputs easier to interpret.

## Sources Checked

- ED2 wiki home and topic index: https://github.com/EDmodel/ED2/wiki
- ED2 output files wiki: https://github.com/EDmodel/ED2/wiki/Output-files
- ED2 repository README, including folder roles and notes about BRAMS/RAPP/Ramspost: https://github.com/EDmodel/ED2
- PEcAn ED2 documentation for ED2IN/input concepts and PFT/config handling: https://pecanproject.github.io/pecan-documentation/master/models-ed.html
- PEcAn.ED2 reference for ED met header format and ED2 input helper functions: https://pecanproject.r-universe.dev/PEcAn.ED2/doc/manual.html
