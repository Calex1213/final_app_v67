# Retraining Scripts v67 - FINAL all-tuned no-NA forecast outputs

This package keeps the old/direct multi-horizon model logic, but fixes the final app-facing CSV problems.

## What changed

- Trains using target years up to 2024 only.
- Predicts origins from 2025 week 1 through 2026 week 19.
- Includes 2025 week 53.
- Forecasts H+0 through H+12, so 2026 week 19 H+12 targets 2026 week 31.
- Uses project-relative paths:
  - `data/FINAL_DATASET.xlsx`
  - `data/cebu_city_barangays.zip`
- Completes app-facing output grids:
  - barangay files: `80 barangays × 72 origin weeks × 13 horizons = 74,880 rows`
  - city files: `72 origin weeks × 13 horizons = 936 rows`
- Forces app-facing alert fields for all four outputs:
  - `outbreak_probability`
  - `alert_threshold`
  - `alert_level`
  - `predicted_outbreak_from_cases`
  - `predicted_outbreak_from_probability`
- Adds `actual_cases_available` so true future weeks can be distinguished from zero-filled unknown actuals.
- Strict NA audit: each script stops if the final app-facing CSV would still contain any R `NA`.
- Tuning is enabled/saved for all model scripts instead of being suppressed.

## Scripts

```text
r_scripts/01_train_standard_barangay.R
r_scripts/02_train_standard_city.R
r_scripts/03_train_environmental_barangay.R
r_scripts/04_train_environmental_city_lightgbm.R
```

## Required project layout

```text
final_app_v67/
├─ data/
│  ├─ FINAL_DATASET.xlsx
│  └─ cebu_city_barangays.zip
├─ outputs/
└─ r_scripts/
   ├─ 01_train_standard_barangay.R
   ├─ 02_train_standard_city.R
   ├─ 03_train_environmental_barangay.R
   └─ 04_train_environmental_city_lightgbm.R
```

## Run in RStudio

```r
setwd("C:/Users/Christopher/Downloads/final_app_v67")

source("r_scripts/01_train_standard_barangay.R")
source("r_scripts/02_train_standard_city.R")
source("r_scripts/03_train_environmental_barangay.R")
source("r_scripts/04_train_environmental_city_lightgbm.R")
```

## Run in terminal

```bash
cd C:/Users/Christopher/Downloads/final_app_v67

Rscript r_scripts/01_train_standard_barangay.R
Rscript r_scripts/02_train_standard_city.R
Rscript r_scripts/03_train_environmental_barangay.R
Rscript r_scripts/04_train_environmental_city_lightgbm.R
```

## Final app-facing CSV outputs

```text
outputs/forecast_barangay_standard.csv
outputs/forecast_city_standard.csv
outputs/forecast_barangay_environmental_only.csv
outputs/forecast_city_environmental_only.csv
```

## NA audit outputs

```text
outputs/forecast_barangay_standard_na_audit.csv
outputs/forecast_city_standard_na_audit.csv
outputs/forecast_barangay_environmental_only_na_audit.csv
outputs/forecast_city_environmental_only_na_audit.csv
```

If any final CSV still has real R `NA` values, the relevant script stops and prints the affected columns.

## Tuning outputs

Tuning/diagnostic CSVs are now written to `outputs/` again. The exact filenames vary by script/horizon, but include lag tuning, regressor tuning, classifier tuning where applicable, selected lag reports, and feature lists.
