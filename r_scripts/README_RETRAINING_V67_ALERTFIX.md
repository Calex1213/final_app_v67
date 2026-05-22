# Retraining scripts v67 - alert/prediction coverage fix

Run from the project root:

```r
setwd("C:/Users/Christopher/Downloads/final_app_v67")
source("r_scripts/01_train_standard_barangay.R")
source("r_scripts/02_train_standard_city.R")
source("r_scripts/03_train_environmental_barangay.R")
source("r_scripts/04_train_environmental_city_lightgbm.R")
```

Or from Command Prompt / Terminal:

```bash
cd C:/Users/Christopher/Downloads/final_app_v67
Rscript r_scripts/01_train_standard_barangay.R
Rscript r_scripts/02_train_standard_city.R
Rscript r_scripts/03_train_environmental_barangay.R
Rscript r_scripts/04_train_environmental_city_lightgbm.R
```

Required files:

```text
data/FINAL_DATASET.xlsx
data/cebu_city_barangays.zip
```

Outputs:

```text
outputs/forecast_barangay_standard.csv
outputs/forecast_city_standard.csv
outputs/forecast_barangay_environmental_only.csv
outputs/forecast_city_environmental_only.csv
```

Important fixes in this version:

1. Environmental-only barangay predictions now include `outbreak_probability`, `alert_threshold`, `alert_level`, `predicted_outbreak_from_cases`, and `predicted_outbreak_from_probability`.
2. Environmental-only city predictions now include a derived `outbreak_probability`, `alert_threshold`, `alert_level`, and a separate `alert_level_from_cases` column for audit.
3. Prediction feature rows are no longer dropped just because lag/rolling/environmental feature values are missing. Missing feature values are imputed during matrix construction, so the app-facing CSVs should contain the full expected origin-week coverage.
4. The scripts use project-relative paths instead of hardcoded Windows absolute paths.
5. Training remains capped at target years through 2024, while prediction origins are 2025 week 1 through 2026 week 19. Forecast targets can reach 2026 week 31 through H+12.

Expected app-facing row counts:

```text
Barangay outputs: 80 barangays * 72 origin weeks * 13 horizons = 74,880 rows each
City outputs: 72 origin weeks * 13 horizons = 936 rows each
```

The scripts print expected vs actual prediction row counts before saving each final CSV.
