# ED2 Project Runtime

This project directory is self-contained for local ED2 runs. The runner scripts
resolve paths from their own location, so a copied project can run without
editing script internals.

Expected layout:

```text
config/   ED2 namelists
scripts/  run_ed2.sh and run_ed2_mpi.sh
data/     project-local meteorology and input data
outputs/  analysis/history output for normal runs
runs/     long-run or spinup output groups
```

Typical usage from `config/`:

```bash
../scripts/run_ed2.sh ED2IN-name
../scripts/run_ed2_mpi.sh 4 ED2IN-name
```

Namelist paths should stay relative to `config/`, for example
`../data/met/ED_MET_DRIVER_HEADER`, `../data/inputs/...`, and
`../outputs/...`.
