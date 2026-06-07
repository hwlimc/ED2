# ED2 Staging Templates

Use this directory as the format contract for raw or processed datasets before converting
them to ED2 inputs. Copy the templates to a project staging directory, replace the sample
rows with your data, then run:

```bash
scripts/build_ed2_inputs_from_staged.py build projects/data/<region>/staged projects/data/<region>/ed_ready --region-name <region>
```

You can create a fresh staging directory with:

```bash
scripts/build_ed2_inputs_from_staged.py init projects/data/<region>/staged
```

## Filled Examples

Filled examples are in `projects/data/staging_examples/`. Start with `fla_local_minimal/` for a buildable ED2-ready example and `field_units.csv` for column units.

## Required First

- `domain.csv`: run domain, time period, and grid/POI settings.
- `met.csv`: meteorology in ED2 units. This is the main required dataset for a realistic
  regional run.
- `soil_constants.csv`: constant-soil fallback used when you do not yet have a gridded
  ED2 soil database.

## Optional

These optional template files are header-only by default. Fill them only when you want the builder to create the corresponding ED2 input.

- `thermal_sums_chd.csv` and `thermal_sums_dgd.csv`: converted to
  `ed_inputs/chd/temp.chd.avg.dat` and `ed_inputs/dgd/temp.dgd.avg.dat`.
- `plantation_fraction.csv`: converted to `ed_inputs/fraction.plantation`.
- `phenology_prescribed.csv`: converted to ED2 `phenology.lat...lon....txt` files and an
  ED2IN fragment for `IPHEN_SCHEME=1`.
- `ed22_sites.csv`, `ed22_patches.csv`, `ed22_cohorts.csv`: optional native ED2.2 initial
  state text files. Use these only if you already know how to map your inventory/remote
  sensing data into ED site, patch, and cohort quantities.
- `observations.csv`: not consumed by ED2 directly here; it is a clean staging format for
  later model-data comparison.

## Main Unit Contract

- Times are UTC ISO-8601 strings.
- Coordinates are WGS84 decimal degrees.
- `tmp` is K, `pres` is Pa, `sh` is kg/kg.
- `ugrd` and `vgrd` are m/s.
- `prate` is kg/m2/s.
- `dlwrf`, `nbdsf`, `nddsf`, `vbdsf`, and `vddsf` are W/m2.
- Soil fractions are 0-1.
- ED soil layers in `slz` are negative depths from deepest to shallowest.

## Local Examples Used

- `ED/src/test_cases/harvard_soi/HARVARD_MET`
- `ED/src/test_cases/amazon_soi/AMAZON_MET`
- `ED/src/test_cases/bartlett_soi/bartlett.lat44.5lon-71.5.site`
- `ED/src/test_cases/bartlett_soi/bartlett.lat44.5lon-71.5.pss`
- `ED/src/test_cases/bartlett_soi/bartlett.lat44.5lon-71.5.css`
- `projects/data/edts_datasets`
- `BRAMS/Template/RAMSIN`

