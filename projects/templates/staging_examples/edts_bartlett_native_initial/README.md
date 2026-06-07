# EDTS/Bartlett Native Initial-State Example

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
