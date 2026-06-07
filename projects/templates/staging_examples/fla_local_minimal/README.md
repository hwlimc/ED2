# FLA Local Minimal Staging Example

This example is generated from local files in `projects/data/fla`.

- `met.csv` uses the first six hourly records from `projects/data/fla/met/BORSOU_MET_2011JAN.h5`.
- `domain.csv` and `soil_constants.csv` mirror the current FLA namelist assumptions.
- `thermal_sums_chd.csv` and `thermal_sums_dgd.csv` use the nearest available local thermal-sum grid row to lon 19.42, lat 64.09.

This is a format example, not a complete production forcing dataset. For a real run, `met.csv`
must contain every lon/lat/time combination for every hour of every simulated month.
