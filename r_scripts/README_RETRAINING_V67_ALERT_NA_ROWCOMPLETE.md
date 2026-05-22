# V67 retraining scripts - alert and row-completeness fix

This package keeps the original forecasting logic structure, but fixes app-facing output issues:

1. Standard city now has nonblank app alert fields:
   - outbreak_probability
   - alert_threshold
   - alert_level
   - alert_level_from_cases
   - predicted_outbreak_from_cases
   - predicted_outbreak_from_probability

2. Environmental-only city/barangay alert fields are forced to be nonblank.
   Environmental-only models are pure regressors, so their alert probability is derived from predicted cases relative to the outbreak threshold.

3. Final app-facing CSVs are checked against the expected full output grid:
   - Barangay files: 80 barangays x 72 origin weeks x 13 horizons = 74,880 rows
   - City files: 72 origin weeks x 13 horizons = 936 rows

4. If a forecast row is unexpectedly missing after modeling, the script adds a conservative fallback row so the app table remains complete. The script prints a warning if this fallback is used.

5. Paths are project-relative. Run from the project root:

```r
setwd("C:/Users/Christopher/Downloads/final_app_v67")
source("r_scripts/01_train_standard_barangay.R")
source("r_scripts/02_train_standard_city.R")
source("r_scripts/03_train_environmental_barangay.R")
source("r_scripts/04_train_environmental_city_lightgbm.R")
```

Expected data files:

```text
data/FINAL_DATASET.xlsx
data/cebu_city_barangays.zip
```

Expected outputs:

```text
outputs/forecast_barangay_standard.csv
outputs/forecast_city_standard.csv
outputs/forecast_barangay_environmental_only.csv
outputs/forecast_city_environmental_only.csv
```
