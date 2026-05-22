# Retraining Scripts v67 - No-NA App Output Fix

These scripts keep the original model training logic and patch the final app-facing forecast CSVs so they do not contain NA values that can break the Streamlit app.

## Important behavior

- Models still train only on target years up to 2024.
- Prediction origins are 2025 week 1 through 2026 week 19.
- Forecast horizons are H+0 through H+12, so the latest target is 2026 week 31.
- 2025 has 53 morbidity weeks.
- App-facing prediction CSVs are completed to the full origin × horizon grid.
- App-facing alert fields are guaranteed:
  - `outbreak_probability`
  - `alert_threshold`
  - `alert_level`
  - `predicted_outbreak_from_cases`
  - `predicted_outbreak_from_probability`
- Remaining NA/NaN/Inf values in saved forecast CSVs are zero/blank/Low-filled.
- A flag named `actual_cases_available` is included because true future target weeks do not yet have observed dengue counts. Those unknown actuals are zero-filled only in the CSV to avoid app NA issues.
- Each script also saves an NA audit CSV beside the forecast CSV. All `na_count` values should be 0.

## Folder layout

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

## Run from RStudio

```r
setwd("C:/Users/Christopher/Downloads/final_app_v67")

source("r_scripts/01_train_standard_barangay.R")
source("r_scripts/02_train_standard_city.R")
source("r_scripts/03_train_environmental_barangay.R")
source("r_scripts/04_train_environmental_city_lightgbm.R")
```

## Run from terminal

```bash
cd C:/Users/Christopher/Downloads/final_app_v67
Rscript r_scripts/01_train_standard_barangay.R
Rscript r_scripts/02_train_standard_city.R
Rscript r_scripts/03_train_environmental_barangay.R
Rscript r_scripts/04_train_environmental_city_lightgbm.R
```

## Expected forecast row counts

- Barangay files: `80 × 72 origin weeks × 13 horizons = 74,880 rows`
- City files: `72 origin weeks × 13 horizons = 936 rows`

## Output files

```text
outputs/forecast_barangay_standard.csv
outputs/forecast_city_standard.csv
outputs/forecast_barangay_environmental_only.csv
outputs/forecast_city_environmental_only.csv
```

NA audit files:

```text
outputs/forecast_barangay_standard_na_audit.csv
outputs/forecast_city_standard_na_audit.csv
outputs/forecast_barangay_environmental_only_na_audit.csv
outputs/forecast_city_environmental_only_na_audit.csv
```
