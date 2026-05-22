# ============================================================
# CITY-WEEK ENVIRONMENTAL-ONLY LIGHTGBM PURE REGRESSOR
# H+0 TO H+12 DIRECT FORECASTS
#
# Purpose:
#   Builds a city-wide weekly dengue forecasting model using ONLY
#   environmental / non-autocorrelation predictors.
#
# This is the city-week counterpart of the winning barangay-week
# environmental-only pure LightGBM regressor.
#
# Key rule:
#   This script DOES NOT use dengue/case/incidence/outbreak lags as predictors.
#   Dengue cases are used only as the prediction target and for evaluation.
#
# Environmental/non-case predictors include:
#   - area-weighted city environmental variables
#   - environmental lags and rolling means
#   - non-case static / spatial variables, if available
#   - seasonality and city size/population descriptors
#
# Main outputs:
#   - city_week_environmental_only_lightgbm_H0_TO_H12_metrics_*.csv
#   - city_week_environmental_only_lightgbm_H0_TO_H12_predictions_*.csv
#   - city_week_environmental_only_lightgbm_H0_TO_H12_selected_settings_*.csv
#   - city_week_environmental_only_lightgbm_H0_TO_H12_feature_importance_*.csv
#   - city_week_environmental_only_lightgbm_H0_TO_H12_compact_summary_*.csv
# ============================================================


# ============================================================
# 0. USER SETTINGS
# ============================================================


# ============================================================
# PROJECT-RELATIVE PATHS FOR FINAL APP V2
# ============================================================
args0 <- commandArgs(trailingOnly = FALSE)
file_arg <- args0[grepl("^--file=", args0)]
SCRIPT_DIR <- if (length(file_arg) > 0) {
  dirname(normalizePath(sub("^--file=", "", file_arg[1]), mustWork = FALSE))
} else {
  getwd()
}
PROJECT_DIR <- if (basename(SCRIPT_DIR) == "r_scripts") {
  normalizePath(file.path(SCRIPT_DIR, ".."), mustWork = FALSE)
} else {
  normalizePath(SCRIPT_DIR, mustWork = FALSE)
}
setwd(PROJECT_DIR)

DATA_PATH <- file.path(PROJECT_DIR, "data", "FINAL_DATASET.xlsx")
OUTPUT_DIR <- file.path(PROJECT_DIR, "outputs")
MODEL_ROOT_DIR <- file.path(PROJECT_DIR, "models")
METADATA_DIR <- file.path(PROJECT_DIR, "model_metadata")
dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(MODEL_ROOT_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(METADATA_DIR, showWarnings = FALSE, recursive = TRUE)


TRAIN_END_YEAR <- 2024
TEST_YEARS <- c(2025, 2026)

# Validation stays inside the training era so the final model can still be trained up to 2024.
VALIDATION_YEARS <- c(2023, 2024)
TRAIN_CORE_END_YEAR <- min(VALIDATION_YEARS) - 1

# Current surveillance origin and required forecast reach.
# H+12 from 2026 week 19 should reach 2026 week 31.
CURRENT_FORECAST_ORIGIN_YEAR <- 2026L
CURRENT_FORECAST_ORIGIN_WEEK <- 19L
FORECAST_TARGET_END_YEAR <- 2026L
FORECAST_TARGET_END_WEEK <- 31L

MAX_LAG_TO_TEST <- 20
MAX_LAGS_KEPT_PER_ENV_VARIABLE <- 2
ENV_ROLL_WINDOWS <- c(4, 8)
FORECAST_HORIZONS <- 0:12
DISPLAY_HORIZONS <- c(0, 1, 2, 3, 4, 8, 12)

POP_DENSITY_UNIT <- "per_km2"
USE_PEAK_WEIGHTS <- TRUE
INCLUDE_STATIC_AND_SEASONAL_NON_CASE_FEATURES <- TRUE

CITY_OUTBREAK_THRESHOLD_METHOD <- "train_quantile"
CITY_OUTBREAK_QUANTILE <- 0.75
CITY_LARGE_OUTBREAK_QUANTILE <- 0.90
CITY_FIXED_OUTBREAK_THRESHOLD_CASES <- 100
CITY_FIXED_LARGE_OUTBREAK_THRESHOLD_CASES <- 200

OUTPUT_PREFIX <- "CITY_WEEK_ENVIRONMENTAL_ONLY_LIGHTGBM_REGRESSOR_H0_TO_H12"
PLOT_DIR <- file.path(OUTPUT_DIR, paste0("dengue_city_week_plots_", OUTPUT_PREFIX))
MODEL_DIR <- file.path(MODEL_ROOT_DIR, "environmental_city")
dir.create(MODEL_DIR, showWarnings = FALSE, recursive = TRUE)

SEED <- 123
set.seed(SEED)

dir.create(PLOT_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)


# ============================================================
# 1. PACKAGES
# ============================================================

needed_packages <- c(
  "readxl", "dplyr", "tidyr", "stringr", "janitor", "purrr",
  "lightgbm", "Matrix", "tibble", "ggplot2", "scales", "zoo",
  "pROC", "readr"
)

installed <- rownames(installed.packages())
for (p in needed_packages) {
  if (!(p %in% installed)) install.packages(p, dependencies = TRUE)
}

library(readxl)
library(dplyr)
library(tidyr)
library(stringr)
library(janitor)
library(purrr)
library(lightgbm)
library(Matrix)
library(tibble)
library(ggplot2)
library(scales)
library(zoo)
library(pROC)
library(readr)

# ============================================================
# OUTPUT POLICY FOR APP PACKAGE
# ============================================================
# Keep model/training logic unchanged AND keep tuning outputs.
# IMPORTANT: do not override readr::write_csv/write.csv here.
# The scripts save final forecasts plus tuning/diagnostic CSVs for audit.



# ============================================================
# 2. BARANGAY AREA TABLE
# ============================================================

area_text <- "
barangay,barangay_area_m2
Adlaon,10568289.49
Agsungot,3141145.937
Apas,1924622.783
Babag,9127305.301
Basak Pardo,2280016.225
Bacayan,1247466.647
Banilad,2361932.924
Basak San Nicolas,1482442.104
Binaliw,5160478.223
Bonbon,9335589.991
Budla-an (Pob.),5528415.047
Buhisan,7362349.884
Bulacao,4458308.598
Buot-Taup Pardo,6309902.571
Busay (Pob.),9073669.846
Calamba,461260.8167
Cambinocot,5404029.229
Capitol Site (Pob.),794266.9439
Carreta,944504.2462
Central (Pob.),295179.9903
Cogon Ramos (Pob.),295106.1074
Cogon Pardo,1534001.407
Day-as,106105.5372
Duljo (Pob.),403621.5959
Ermita (Pob.),379645.5962
Guadalupe,7364428.349
Guba,10821331.27
Hippodromo,430684.893
Inayawan,2753267.116
Kalubihan (Pob.),161379.8344
Kalunasan,1420118.552
Kamagayan (Pob.),117092.5693
Camputhaw (Pob.),1215505.455
Kasambagan,1832657.268
Kinasang-an Pardo,1509429.505
Labangon,1122041.116
Lahug (Pob.),4239264.538
Lorega (Lorega San Miguel),199630.1232
Lusaran,11205979.19
Luz,560240.7135
Mabini,5611102.651
Mabolo,1946308.241
Malubog,8555676.09
Mambaling,1249056.385
Pahina Central (Pob.),257598.4505
Pahina San Nicolas,75403.24046
Pamutan,11375185.98
Pardo (Pob.),2034673.842
Pari-an,97305.23716
Paril,3223325.36
Pasil,79951.38113
Pit-os,1653568.117
Pulangbato,5234284.92
Pung-ol-Sibugay,14616354.74
Punta Princesa,1276947.168
Quiot Pardo,761372.7629
Sambag I (Pob.),516257.1623
Sambag II (Pob.),447417.6939
San Antonio (Pob.),128340.3764
San Jose,2869390.311
San Nicolas Central,281010.9574
San Roque (Ciudad),455039.6854
Santa Cruz (Pob.),229062.3109
Sawang Calero (Pob.),242699.2115
Sinsin,8122060.059
Sirao,7704545.516
Suba Pob. (Suba San Nicolas),96693.99165
Sudlon I,3206182.493
Sapangdaku,8393868.225
T. Padilla,165106.4826
Tabunan,15861577.93
Tagbao,10534037.02
Talamban,4629709.911
Taptap,7570183.845
Tejero (Villa Gonzalo),538422.355
Tinago,229802.9203
Tisa,2436056.449
To-ong Pardo,6814618.803
Zapatera,335615.5369
Sudlon II,16116531.07
"

area_df <- read.csv(text = area_text, stringsAsFactors = FALSE) %>%
  mutate(barangay_clean = toupper(str_squish(barangay))) %>%
  select(barangay_clean, barangay_area_m2)


# ============================================================
# FORECAST WINDOW + FUTURE POPULATION ROW HELPERS
# ============================================================
# These helpers keep the original model logic intact, but let the
# scripts generate target population rows through 2026 week 31.
# Dengue cases for those extra future rows remain blank.

clean_int <- function(x) {
  suppressWarnings(as.integer(as.character(x)))
}

weeks_in_year <- function(y) {
  ifelse(as.integer(y) == 2025L, 53L, 52L)
}

make_calendar_range <- function(start_year, end_year) {
  dplyr::bind_rows(lapply(seq.int(as.integer(start_year), as.integer(end_year)), function(yy) {
    tibble(year = as.integer(yy), week = seq_len(weeks_in_year(yy)))
  })) %>%
    arrange(year, week) %>%
    mutate(time_index = row_number())
}

year_week_on_or_before <- function(year, week, end_year, end_week) {
  !is.na(year) & !is.na(week) &
    (year < end_year | (year == end_year & week <= end_week))
}

year_week_on_or_after <- function(year, week, start_year, start_week) {
  !is.na(year) & !is.na(week) &
    (year > start_year | (year == start_year & week >= start_week))
}

is_prediction_origin_window <- function(year, week) {
  year_week_on_or_after(year, week, TRAIN_END_YEAR + 1L, 1L) &
    year_week_on_or_before(year, week, CURRENT_FORECAST_ORIGIN_YEAR, CURRENT_FORECAST_ORIGIN_WEEK)
}

is_prediction_target_window <- function(year, week) {
  year_week_on_or_before(year, week, FORECAST_TARGET_END_YEAR, FORECAST_TARGET_END_WEEK)
}

ensure_forecast_extension_rows <- function(data) {
  data <- data %>%
    mutate(
      year = clean_int(year),
      week = clean_int(week),
      pop_density = as.numeric(pop_density),
      dengue_cases = as.numeric(dengue_cases)
    ) %>%
    distinct(barangay, year, week, .keep_all = TRUE)

  start_year <- min(data$year, na.rm = TRUE)
  calendar_tbl <- make_calendar_range(start_year, FORECAST_TARGET_END_YEAR)

  data_idx <- data %>%
    left_join(calendar_tbl, by = c("year", "week"))

  last_observed <- data_idx %>%
    group_by(barangay) %>%
    summarise(
      max_time_index = max(time_index, na.rm = TRUE),
      .groups = "drop"
    )

  future_grid <- tidyr::crossing(
    tibble(barangay = sort(unique(data$barangay))),
    calendar_tbl
  ) %>%
    left_join(last_observed, by = "barangay") %>%
    filter(
      !is.na(max_time_index),
      time_index > max_time_index,
      year_week_on_or_before(year, week, FORECAST_TARGET_END_YEAR, FORECAST_TARGET_END_WEEK)
    )

  if (nrow(future_grid) == 0) {
    return(data %>% arrange(barangay, year, week))
  }

  pop_model <- data_idx %>%
    filter(!is.na(time_index), !is.na(pop_density), pop_density > 0) %>%
    arrange(barangay, time_index) %>%
    group_by(barangay) %>%
    group_modify(~ {
      train <- .x
      if (nrow(train) == 0) {
        return(tibble(
          last_time_index = NA_real_,
          last_pop_density = NA_real_,
          weekly_log_growth_rate = NA_real_
        ))
      }

      last_time <- dplyr::last(train$time_index)
      last_pop <- dplyr::last(train$pop_density)

      if (nrow(train) == 1) {
        rate <- 0
      } else {
        rate <- tryCatch(
          as.numeric(coef(lm(log(pop_density) ~ time_index, data = train))["time_index"]),
          error = function(e) 0
        )
        if (is.na(rate) || is.nan(rate) || is.infinite(rate)) rate <- 0
      }

      tibble(
        last_time_index = last_time,
        last_pop_density = last_pop,
        weekly_log_growth_rate = rate
      )
    }) %>%
    ungroup()

  environmental_dynamic_cols <- c(
    "rainfall", "rh", "humidity", "relative_humidity",
    "temp_c", "temperature", "t_mean", "tmin", "tmax", "t_min", "t_max",
    "u_component_of_wind_10m", "v_component_of_wind_10m",
    "wind_speed_10m", "wind_speed",
    "flood_depth", "flood_duration", "flood_extent", "water_level"
  )

  static_name_pattern <- regex(
    "flood_risk_index|barangay_classification|^percent_|^x_percent_|annual_crop|brush|built|open_forest|perennial_crop|open_barren|fishpond|grassland|mangrove|inland_water|landcover",
    ignore_case = TRUE
  )

  static_cols <- names(data)[str_detect(names(data), static_name_pattern)]
  static_cols <- setdiff(static_cols, c("year", "week", "dengue_cases", "pop_density", environmental_dynamic_cols))
  static_cols <- unique(c("barangay_area_m2", static_cols))
  static_cols <- static_cols[static_cols %in% names(data)]

  latest_static <- data_idx %>%
    arrange(barangay, time_index) %>%
    group_by(barangay) %>%
    slice_tail(n = 1) %>%
    ungroup() %>%
    select(barangay, all_of(static_cols))

  future_rows <- future_grid %>%
    select(barangay, year, week, time_index) %>%
    left_join(pop_model, by = "barangay") %>%
    left_join(latest_static, by = "barangay") %>%
    mutate(
      pop_density = ifelse(
        is.na(last_pop_density) | is.na(weekly_log_growth_rate),
        NA_real_,
        last_pop_density * exp(weekly_log_growth_rate * (time_index - last_time_index))
      ),
      dengue_cases = NA_real_
    )

  for (cc in setdiff(names(data), names(future_rows))) {
    future_rows[[cc]] <- NA
  }

  future_rows <- future_rows %>%
    select(all_of(names(data)))

  bind_rows(data, future_rows) %>%
    arrange(barangay, year, week)
}



# ============================================================
# 3. BASIC HELPERS
# ============================================================

weighted_mean_safe <- function(x, w) {
  x <- as.numeric(x)
  w <- as.numeric(w)
  ok <- !is.na(x) & !is.na(w) & w > 0
  if (sum(ok) == 0) return(NA_real_)
  weighted.mean(x[ok], w[ok], na.rm = TRUE)
}

sum_safe <- function(x) {
  sum(as.numeric(x), na.rm = TRUE)
}

sum_cases_safe <- function(x) {
  x <- as.numeric(x)
  if (all(is.na(x))) return(NA_real_)
  sum(x, na.rm = TRUE)
}

safe_rmse <- function(actual, pred) sqrt(mean((actual - pred)^2, na.rm = TRUE))
safe_mae <- function(actual, pred) mean(abs(actual - pred), na.rm = TRUE)

safe_r2 <- function(actual, pred) {
  ss_res <- sum((actual - pred)^2, na.rm = TRUE)
  ss_tot <- sum((actual - mean(actual, na.rm = TRUE))^2, na.rm = TRUE)
  if (is.na(ss_tot) || ss_tot == 0) return(NA_real_)
  1 - ss_res / ss_tot
}

safe_cor <- function(actual, pred) suppressWarnings(cor(actual, pred, use = "complete.obs"))

city_loginc_to_cases <- function(pred_log_incidence, estimated_population) {
  pred_incidence <- expm1(pred_log_incidence)
  pred_cases <- (pred_incidence / 10000) * estimated_population
  pred_cases <- ifelse(is.na(pred_cases), 0, pred_cases)
  pmax(pred_cases, 0)
}

city_cases_to_loginc <- function(cases, estimated_population) {
  incidence <- (cases / estimated_population) * 10000
  incidence <- ifelse(is.na(incidence) | incidence < 0, 0, incidence)
  log1p(incidence)
}

classification_metrics_from_cases_city <- function(actual_cases, pred_cases, threshold_cases) {
  actual_class <- actual_cases >= threshold_cases
  pred_class <- pred_cases >= threshold_cases

  tp <- sum(actual_class & pred_class, na.rm = TRUE)
  tn <- sum(!actual_class & !pred_class, na.rm = TRUE)
  fp <- sum(!actual_class & pred_class, na.rm = TRUE)
  fn <- sum(actual_class & !pred_class, na.rm = TRUE)

  precision <- ifelse((tp + fp) == 0, NA_real_, tp / (tp + fp))
  recall <- ifelse((tp + fn) == 0, NA_real_, tp / (tp + fn))
  f1 <- ifelse(is.na(precision) | is.na(recall) | (precision + recall) == 0, NA_real_, 2 * precision * recall / (precision + recall))
  false_alarm_rate <- ifelse((fp + tn) == 0, NA_real_, fp / (fp + tn))
  specificity <- ifelse((tn + fp) == 0, NA_real_, tn / (tn + fp))

  tibble(
    Precision = precision,
    Recall = recall,
    Outbreak_F1_count_threshold = f1,
    False_alarm_rate = false_alarm_rate,
    Specificity = specificity,
    TP = tp,
    TN = tn,
    FP = fp,
    FN = fn
  )
}

make_alert_level_from_cases <- function(pred_cases, threshold_cases) {
  ratio <- pred_cases / threshold_cases
  case_when(
    is.na(ratio) ~ NA_character_,
    ratio < 0.50 ~ "Low",
    ratio < 0.80 ~ "Watch",
    ratio < 1.00 ~ "Moderate",
    ratio < 1.50 ~ "High",
    TRUE ~ "Very high"
  )
}


make_alert_level_from_probability <- function(probability) {
  probability <- pmin(pmax(as.numeric(probability), 0), 1)
  case_when(
    is.na(probability) ~ "Low",
    probability < 0.30 ~ "Low",
    probability < 0.50 ~ "Watch",
    probability < 0.70 ~ "Moderate",
    probability < 0.85 ~ "High",
    TRUE ~ "Very high"
  )
}

city_environmental_probability_from_cases <- function(pred_cases, threshold_cases) {
  threshold <- as.numeric(threshold_cases)
  threshold[is.na(threshold) | threshold <= 0] <- NA_real_
  fallback <- suppressWarnings(stats::median(threshold, na.rm = TRUE))
  if (is.na(fallback) || is.nan(fallback) || is.infinite(fallback) || fallback <= 0) fallback <- 1
  threshold <- ifelse(is.na(threshold) | threshold <= 0, fallback, threshold)
  prob <- 1 - exp(-pmax(as.numeric(pred_cases), 0) / threshold)
  pmin(pmax(prob, 0), 1)
}

city_make_reg_weights <- function(cases) {
  if (!USE_PEAK_WEIGHTS) return(rep(1, length(cases)))

  q75 <- quantile(cases, 0.75, na.rm = TRUE)
  q90 <- quantile(cases, 0.90, na.rm = TRUE)
  q95 <- quantile(cases, 0.95, na.rm = TRUE)

  case_when(
    cases >= q95 ~ 8,
    cases >= q90 ~ 5,
    cases >= q75 ~ 3,
    cases > 0 ~ 1.5,
    TRUE ~ 1
  )
}

is_case_related_feature <- function(feature_names) {
  str_detect(
    feature_names,
    regex(
      paste(
        c(
          "dengue", "case", "cases", "incidence", "target", "outbreak",
          "positive", "classifier", "probability"
        ),
        collapse = "|"
      ),
      ignore_case = TRUE
    )
  )
}


# ============================================================
# 4. READ DATA AND CREATE BARANGAY BASE VARIABLES
# ============================================================

if (!file.exists(DATA_PATH)) {
  stop(paste0("DATA_PATH not found: ", DATA_PATH, "
Edit DATA_PATH at the top of this script."))
}

raw_df <- read_excel(DATA_PATH) %>% clean_names()

cat("
Columns found in FINAL_DATASET:
")
print(names(raw_df))

required_cols <- c("barangay", "year", "week", "pop_density", "dengue_cases")
missing_cols <- setdiff(required_cols, names(raw_df))
if (length(missing_cols) > 0) {
  stop(paste0("Missing required columns: ", paste(missing_cols, collapse = ", ")))
}

df <- raw_df %>%
  mutate(
    barangay = toupper(str_squish(as.character(barangay))),
    year = as.integer(year),
    week = as.integer(week),
    dengue_cases = as.numeric(dengue_cases),
    pop_density = as.numeric(pop_density)
  ) %>%
  left_join(area_df, by = c("barangay" = "barangay_clean"))

if (any(is.na(df$barangay_area_m2))) {
  cat("
Barangays without matched area:
")
  print(unique(df$barangay[is.na(df$barangay_area_m2)]))
  stop("Some barangays did not match the area table.")
}

df <- ensure_forecast_extension_rows(df)

cat("\nRows after in-memory forecast extension through ", FORECAST_TARGET_END_YEAR, " week ", FORECAST_TARGET_END_WEEK, ": ", nrow(df), "\n", sep = "")

df <- df %>%
  mutate(barangay_area_km2 = barangay_area_m2 / 1e6)

if (POP_DENSITY_UNIT == "per_km2") {
  df <- df %>% mutate(estimated_population = pop_density * barangay_area_km2)
} else if (POP_DENSITY_UNIT == "per_m2") {
  df <- df %>% mutate(estimated_population = pop_density * barangay_area_m2)
} else {
  stop("POP_DENSITY_UNIT must be either 'per_km2' or 'per_m2'.")
}

df <- df %>%
  mutate(
    estimated_population = ifelse(estimated_population <= 0 | is.na(estimated_population), NA_real_, estimated_population)
  ) %>%
  arrange(barangay, year, week)


# ============================================================
# 5. AGGREGATE BARANGAY-WEEK TO CITY-WEEK
# ============================================================

env_candidates <- c(
  "rainfall", "rh", "humidity", "relative_humidity",
  "temp_c", "temperature", "t_mean", "tmin", "tmax", "t_min", "t_max",
  "u_component_of_wind_10m", "v_component_of_wind_10m", "wind_speed_10m", "wind_speed",
  "flood_depth", "flood_duration", "flood_extent", "water_level"
)

env_vars <- env_candidates[env_candidates %in% names(df)]
if (length(env_vars) == 0) {
  stop("No environmental variables were found. Check column names after clean_names().")
}

static_candidates <- c(
  "pop_density",
  "flood_risk_index",
  names(df)[str_detect(names(df), "^percent_|^x_percent_|annual_crop|brush|built|forest|crop|barren|fishpond|grassland|mangrove|water|landcover")]
)

static_vars <- unique(static_candidates[static_candidates %in% names(df)])
weighted_vars <- unique(c(env_vars, static_vars))
weighted_vars <- weighted_vars[!is_case_related_feature(weighted_vars)]

cat("
Environmental/non-case variables area-weighted into city-week features:
")
print(weighted_vars)

barangay_week_clean <- df %>%
  group_by(barangay, year, week) %>%
  summarise(
    dengue_cases = sum_safe(dengue_cases),
    estimated_population = mean(estimated_population, na.rm = TRUE),
    barangay_area_m2 = mean(barangay_area_m2, na.rm = TRUE),
    barangay_area_km2 = mean(barangay_area_km2, na.rm = TRUE),
    across(all_of(weighted_vars), ~ mean(as.numeric(.x), na.rm = TRUE), .names = "{.col}"),
    .groups = "drop"
  ) %>%
  mutate(
    estimated_population = ifelse(is.nan(estimated_population), NA_real_, estimated_population)
  )

city_weighted_features <- barangay_week_clean %>%
  group_by(year, week) %>%
  summarise(
    across(
      all_of(weighted_vars),
      ~ weighted_mean_safe(.x, barangay_area_m2),
      .names = "city_area_weighted_{.col}"
    ),
    .groups = "drop"
  )

city_week_df <- barangay_week_clean %>%
  group_by(year, week) %>%
  summarise(
    city_dengue_cases = sum_cases_safe(dengue_cases),
    city_estimated_population = sum_safe(estimated_population),
    city_area_m2 = sum_safe(barangay_area_m2),
    city_area_km2 = sum_safe(barangay_area_km2),
    n_barangays_reported = n_distinct(barangay),
    .groups = "drop"
  ) %>%
  left_join(city_weighted_features, by = c("year", "week")) %>%
  mutate(
    city_area_m2 = median(city_area_m2, na.rm = TRUE),
    city_area_km2 = median(city_area_km2, na.rm = TRUE),
    city_pop_density = city_estimated_population / city_area_km2,
    city_incidence_10000 = ifelse(
      is.na(city_dengue_cases),
      NA_real_,
      (city_dengue_cases / city_estimated_population) * 10000
    ),
    city_incidence_10000 = ifelse(
      is.na(city_dengue_cases),
      NA_real_,
      ifelse(is.na(city_incidence_10000) | city_incidence_10000 < 0, 0, city_incidence_10000)
    ),
    target_log_incidence_city = log1p(city_incidence_10000),
    week_sin = sin(2 * pi * week / 52),
    week_cos = cos(2 * pi * week / 52)
  ) %>%
  arrange(year, week)

if (CITY_OUTBREAK_THRESHOLD_METHOD == "train_quantile") {
  city_outbreak_threshold_cases_value <- as.numeric(
    quantile(city_week_df$city_dengue_cases[city_week_df$year <= TRAIN_END_YEAR], probs = CITY_OUTBREAK_QUANTILE, na.rm = TRUE)
  )
  city_large_outbreak_threshold_cases_value <- as.numeric(
    quantile(city_week_df$city_dengue_cases[city_week_df$year <= TRAIN_END_YEAR], probs = CITY_LARGE_OUTBREAK_QUANTILE, na.rm = TRUE)
  )
} else {
  city_outbreak_threshold_cases_value <- CITY_FIXED_OUTBREAK_THRESHOLD_CASES
  city_large_outbreak_threshold_cases_value <- CITY_FIXED_LARGE_OUTBREAK_THRESHOLD_CASES
}

city_week_df <- city_week_df %>%
  mutate(
    city_outbreak_threshold_cases = city_outbreak_threshold_cases_value,
    city_large_outbreak_threshold_cases = city_large_outbreak_threshold_cases_value,
    outbreak_actual_city = as.integer(city_dengue_cases >= city_outbreak_threshold_cases),
    large_outbreak_actual_city = as.integer(city_dengue_cases >= city_large_outbreak_threshold_cases)
  )

cat("
City outbreak threshold cases:", city_outbreak_threshold_cases_value, "
")
cat("City large outbreak threshold cases:", city_large_outbreak_threshold_cases_value, "
")
cat("City-week rows:", nrow(city_week_df), "
")


# ============================================================
# 6. ENVIRONMENTAL-ONLY CITY FEATURE ENGINEERING
# ============================================================

make_city_lags <- function(data, cols, lags) {
  out <- data
  for (cc in cols) {
    if (cc %in% names(out)) {
      for (ll in lags) {
        new_name <- paste0(cc, "_lag", ll)
        out <- out %>%
          arrange(year, week) %>%
          mutate(!!new_name := dplyr::lag(.data[[cc]], ll))
      }
    }
  }
  out
}

make_city_rolls <- function(data, cols, windows) {
  out <- data
  for (cc in cols) {
    if (cc %in% names(out)) {
      for (ww in windows) {
        new_name <- paste0(cc, "_rollmean_lag1_w", ww)
        out <- out %>%
          arrange(year, week) %>%
          mutate(
            !!new_name := zoo::rollapplyr(
              dplyr::lag(.data[[cc]], 1),
              width = ww,
              FUN = function(z) mean(z, na.rm = TRUE),
              fill = NA_real_,
              partial = FALSE
            )
          )
      }
    }
  }
  out
}

select_best_city_env_lags_for_horizon <- function(data, base_vars, max_lag = 20, keep_per_var = 2, train_end_year = TRAIN_END_YEAR) {
  train_only <- data %>% filter(target_year <= train_end_year)
  selected <- c()
  reports <- list()

  for (v in base_vars) {
    lag_cols <- paste0(v, "_lag", 1:max_lag)
    lag_cols <- lag_cols[lag_cols %in% names(train_only)]
    if (length(lag_cols) == 0) next

    scores <- purrr::map_df(lag_cols, function(col) {
      ok <- !is.na(train_only[[col]]) &
        !is.na(train_only$target_log_incidence) &
        !is.na(train_only$target_cases) &
        !is.na(train_only$target_outbreak) &
        !is.na(train_only$target_large_outbreak)

      if (sum(ok) < 20 || sd(train_only[[col]][ok], na.rm = TRUE) == 0) {
        return(tibble(
          variable = v,
          feature = col,
          lag = as.integer(str_extract(col, "\\d+$")),
          cor_log_incidence = NA_real_,
          cor_cases = NA_real_,
          cor_outbreak = NA_real_,
          cor_large_outbreak = NA_real_,
          selection_score = NA_real_
        ))
      }

      x <- train_only[[col]][ok]
      y_log <- train_only$target_log_incidence[ok]
      y_cases <- train_only$target_cases[ok]
      y_out <- train_only$target_outbreak[ok]
      y_large <- train_only$target_large_outbreak[ok]

      cor_log <- suppressWarnings(abs(cor(x, y_log, use = "complete.obs")))
      cor_cases <- suppressWarnings(abs(cor(x, y_cases, use = "complete.obs")))
      cor_out <- suppressWarnings(abs(cor(x, y_out, use = "complete.obs")))
      cor_large <- suppressWarnings(abs(cor(x, y_large, use = "complete.obs")))

      score <- 0.40 * ifelse(is.na(cor_log), 0, cor_log) +
        0.35 * ifelse(is.na(cor_cases), 0, cor_cases) +
        0.15 * ifelse(is.na(cor_out), 0, cor_out) +
        0.10 * ifelse(is.na(cor_large), 0, cor_large)

      tibble(
        variable = v,
        feature = col,
        lag = as.integer(str_extract(col, "\\d+$")),
        cor_log_incidence = cor_log,
        cor_cases = cor_cases,
        cor_outbreak = cor_out,
        cor_large_outbreak = cor_large,
        selection_score = score
      )
    }) %>%
      arrange(desc(selection_score), lag)

    chosen <- scores %>%
      filter(!is.na(selection_score)) %>%
      slice_head(n = keep_per_var) %>%
      pull(feature)

    selected <- c(selected, chosen)
    reports[[v]] <- scores %>% mutate(selected = feature %in% chosen)
  }

  list(
    selected_features = unique(selected),
    lag_report = bind_rows(reports)
  )
}

city_env_base_vars <- names(city_week_df)[
  str_detect(names(city_week_df), "^city_area_weighted_") &
    !is_case_related_feature(names(city_week_df))
]

# Rolling means should be environmental/weighted city variables only.
city_week_lagged <- city_week_df %>%
  make_city_lags(city_env_base_vars, 1:MAX_LAG_TO_TEST) %>%
  make_city_rolls(city_env_base_vars, ENV_ROLL_WINDOWS)

city_roll_feature_cols <- names(city_week_lagged)[str_detect(names(city_week_lagged), "_rollmean_lag1_w")]
city_roll_feature_cols <- city_roll_feature_cols[!is_case_related_feature(city_roll_feature_cols)]

city_static_feature_cols <- c(
  "week_sin",
  "week_cos",
  "city_estimated_population",
  "city_area_m2",
  "city_area_km2",
  "city_pop_density",
  "n_barangays_reported"
)
city_static_feature_cols <- city_static_feature_cols[city_static_feature_cols %in% names(city_week_lagged)]
city_static_feature_cols <- city_static_feature_cols[!is_case_related_feature(city_static_feature_cols)]

cat("
City environmental base variables for lagging/rolling:
")
print(city_env_base_vars)
cat("
Number of city environmental base variables:", length(city_env_base_vars), "
")



# ============================================================
# 7. MATRIX, LIGHTGBM MODEL, AND EVALUATION HELPERS
# ============================================================


prepare_matrix_features <- function(train_x_raw, pred_x_raw) {
  combined <- bind_rows(train_x_raw, pred_x_raw)

  # Keep the row count stable. model.matrix() can silently drop rows with NA
  # categorical values, which then causes prediction/probability vector length
  # mismatches. We explicitly encode missing categorical values and impute
  # missing numeric/logical values using the training portion only.
  for (nm in names(combined)) {
    train_col <- train_x_raw[[nm]]

    if (is.logical(combined[[nm]])) {
      combined[[nm]] <- as.integer(combined[[nm]])
      train_numeric <- as.numeric(train_col)
      fill_value <- stats::median(train_numeric, na.rm = TRUE)
      if (is.na(fill_value) || is.nan(fill_value) || is.infinite(fill_value)) fill_value <- 0
      combined[[nm]][is.na(combined[[nm]])] <- fill_value
    } else if (is.numeric(combined[[nm]]) || is.integer(combined[[nm]])) {
      combined[[nm]] <- as.numeric(combined[[nm]])
      train_numeric <- as.numeric(train_col)
      fill_value <- stats::median(train_numeric, na.rm = TRUE)
      if (is.na(fill_value) || is.nan(fill_value) || is.infinite(fill_value)) fill_value <- 0
      combined[[nm]][is.na(combined[[nm]])] <- fill_value
    } else {
      combined[[nm]] <- as.character(combined[[nm]])
      combined[[nm]][is.na(combined[[nm]]) | stringr::str_squish(combined[[nm]]) == ""] <- "missing"
      combined[[nm]] <- as.factor(combined[[nm]])
    }
  }

  combined
}

make_city_matrix <- function(train_data, pred_data, features) {
  train_x_raw <- train_data %>% select(all_of(features))
  pred_x_raw <- pred_data %>% select(all_of(features))

  combined <- prepare_matrix_features(train_x_raw, pred_x_raw)
  mm <- model.matrix(~ . - 1, data = combined, na.action = stats::na.pass)

  train_mat <- mm[1:nrow(train_x_raw), , drop = FALSE]
  pred_mat <- mm[(nrow(train_x_raw) + 1):nrow(mm), , drop = FALSE]

  if (nrow(pred_mat) != nrow(pred_x_raw)) {
    stop("Prediction matrix row mismatch: expected ", nrow(pred_x_raw), " rows but got ", nrow(pred_mat), ".")
  }

  list(train = train_mat, pred = pred_mat, feature_names = colnames(mm))
}

make_city_horizon_dataset <- function(data, horizon, require_targets = TRUE) {
  shift_n <- horizon
  out <- data %>%
    arrange(year, week) %>%
    mutate(
      origin_year = year,
      origin_week = week,
      target_year = dplyr::lead(year, shift_n),
      target_week = dplyr::lead(week, shift_n),
      target_cases = dplyr::lead(city_dengue_cases, shift_n),
      target_incidence_10000 = dplyr::lead(city_incidence_10000, shift_n),
      target_log_incidence = dplyr::lead(target_log_incidence_city, shift_n),
      target_population = dplyr::lead(city_estimated_population, shift_n),
      target_outbreak = dplyr::lead(outbreak_actual_city, shift_n),
      target_large_outbreak = dplyr::lead(large_outbreak_actual_city, shift_n)
    ) %>%
    filter(
      !is.na(target_year),
      !is.na(target_week),
      !is.na(target_population)
    )

  if (require_targets) {
    out <- out %>%
      filter(
        !is.na(target_cases),
        !is.na(target_log_incidence),
        !is.na(target_outbreak),
        !is.na(target_large_outbreak)
      )
  }

  out %>%
    mutate(
      forecast_horizon = horizon,
      forecast_horizon_label = paste0("H+", horizon)
    )
}

build_city_env_horizon_features <- function(horizon, keep_per_var, lag_train_end_year, require_targets = TRUE) {
  h_df <- make_city_horizon_dataset(city_week_lagged, horizon, require_targets = require_targets)

  env_lag_selection <- select_best_city_env_lags_for_horizon(
    data = h_df,
    base_vars = city_env_base_vars,
    max_lag = MAX_LAG_TO_TEST,
    keep_per_var = keep_per_var,
    train_end_year = lag_train_end_year
  )

  selected_env_lag_features <- env_lag_selection$selected_features

  if (INCLUDE_STATIC_AND_SEASONAL_NON_CASE_FEATURES) {
    city_feature_cols <- unique(c(city_static_feature_cols, selected_env_lag_features, city_roll_feature_cols))
  } else {
    city_feature_cols <- unique(c(selected_env_lag_features, city_roll_feature_cols))
  }

  city_feature_cols <- city_feature_cols[city_feature_cols %in% names(h_df)]
  city_feature_cols <- city_feature_cols[!is_case_related_feature(city_feature_cols)]
  city_feature_cols <- city_feature_cols[!str_detect(city_feature_cols, "geometry|geom|shape|objectid")]

  # Required columns are only the target population and, when training/tuning,
  # observed target outcomes. Feature NAs are intentionally allowed and imputed
  # inside make_city_matrix(), so prediction weeks are not dropped.
  city_required_complete_cols <- c("target_population")

  if (require_targets) {
    city_required_complete_cols <- unique(c(
      "target_cases", "target_incidence_10000", "target_log_incidence",
      "target_outbreak", "target_large_outbreak",
      city_required_complete_cols
    ))
  }
  city_required_complete_cols <- city_required_complete_cols[city_required_complete_cols %in% names(h_df)]

  city_model_df <- h_df %>%
    arrange(year, week) %>%
    filter(if_all(all_of(city_required_complete_cols), ~ !is.na(.x)))

  list(
    data = city_model_df,
    features = city_feature_cols,
    selected_env_lag_features = selected_env_lag_features,
    lag_report = env_lag_selection$lag_report
  )
}

lgb_regression_grid <- tibble::tribble(
  ~learning_rate, ~num_leaves, ~max_depth, ~min_data_in_leaf, ~feature_fraction, ~bagging_fraction, ~bagging_freq, ~lambda_l1, ~lambda_l2, ~nrounds,
  0.03, 15, 3, 5, 0.85, 0.85, 1, 0.05, 1.00, 700,
  0.03, 31, 4, 8, 0.85, 0.85, 1, 0.05, 1.00, 800,
  0.02, 31, 4, 8, 0.80, 0.90, 1, 0.10, 1.50, 900,
  0.05, 15, 3, 8, 0.85, 0.85, 1, 0.05, 1.00, 600,
  0.05, 31, 4, 12, 0.80, 0.80, 1, 0.10, 2.00, 650,
  0.03, 63, 5, 12, 0.80, 0.80, 1, 0.20, 2.00, 800
)

get_lgb_best_iter <- function(fit, fallback_nrounds) {
  best_iter <- fit$best_iter
  if (is.null(best_iter) || length(best_iter) == 0 || is.na(best_iter) || best_iter < 20) {
    best_iter <- fit$best_iteration
  }
  if (is.null(best_iter) || length(best_iter) == 0 || is.na(best_iter) || best_iter < 20) {
    best_iter <- fallback_nrounds
  }
  as.integer(best_iter)
}

tune_city_env_lgbm_regressor <- function(train_core, validation, features, horizon_label) {
  mats <- make_city_matrix(train_core, validation, features)

  dtrain <- lightgbm::lgb.Dataset(
    data = mats$train,
    label = train_core$target_log_incidence,
    weight = city_make_reg_weights(train_core$target_cases)
  )
  dval <- lightgbm::lgb.Dataset(data = mats$pred, label = validation$target_log_incidence)

  tuning_results <- purrr::map_df(seq_len(nrow(lgb_regression_grid)), function(i) {
    g <- lgb_regression_grid[i, ]

    params <- list(
      objective = "regression",
      metric = "rmse",
      learning_rate = g$learning_rate,
      num_leaves = as.integer(g$num_leaves),
      max_depth = as.integer(g$max_depth),
      min_data_in_leaf = as.integer(g$min_data_in_leaf),
      feature_fraction = g$feature_fraction,
      bagging_fraction = g$bagging_fraction,
      bagging_freq = as.integer(g$bagging_freq),
      lambda_l1 = g$lambda_l1,
      lambda_l2 = g$lambda_l2,
      verbosity = -1,
      force_col_wise = TRUE
    )

    fit <- lightgbm::lgb.train(
      params = params,
      data = dtrain,
      nrounds = as.integer(g$nrounds),
      valids = list(validation = dval),
      early_stopping_rounds = 40,
      verbose = -1
    )

    best_iter <- get_lgb_best_iter(fit, fallback_nrounds = as.integer(g$nrounds))
    pred_log <- predict(fit, mats$pred, num_iteration = best_iter)
    pred_cases <- city_loginc_to_cases(pred_log, validation$target_population)

    tibble(
      forecast_horizon_label = horizon_label,
      model_part = "regressor",
      grid_id = i,
      learning_rate = g$learning_rate,
      num_leaves = g$num_leaves,
      max_depth = g$max_depth,
      min_data_in_leaf = g$min_data_in_leaf,
      feature_fraction = g$feature_fraction,
      bagging_fraction = g$bagging_fraction,
      bagging_freq = g$bagging_freq,
      lambda_l1 = g$lambda_l1,
      lambda_l2 = g$lambda_l2,
      nrounds = g$nrounds,
      best_nrounds = best_iter,
      validation_RMSE_raw = safe_rmse(validation$target_cases, pred_cases),
      validation_MAE_raw = safe_mae(validation$target_cases, pred_cases),
      validation_R2_raw = safe_r2(validation$target_cases, pred_cases),
      validation_Correlation_raw = safe_cor(validation$target_cases, pred_cases),
      validation_score = safe_rmse(validation$target_cases, pred_cases) + 0.20 * safe_mae(validation$target_cases, pred_cases)
    )
  })

  tuning_results %>% arrange(validation_score, validation_RMSE_raw)
}

fit_final_city_env_lgbm_regressor <- function(train_data, pred_data, features, best_params) {
  mats <- make_city_matrix(train_data, pred_data, features)

  dtrain <- lightgbm::lgb.Dataset(
    data = mats$train,
    label = train_data$target_log_incidence,
    weight = city_make_reg_weights(train_data$target_cases)
  )

  nrounds <- if ("best_nrounds" %in% names(best_params)) best_params$best_nrounds[1] else best_params$nrounds[1]
  if (is.null(nrounds) || is.na(nrounds) || nrounds < 20) nrounds <- 500
  nrounds <- as.integer(nrounds)

  params <- list(
    objective = "regression",
    metric = "rmse",
    learning_rate = best_params$learning_rate[1],
    num_leaves = as.integer(best_params$num_leaves[1]),
    max_depth = as.integer(best_params$max_depth[1]),
    min_data_in_leaf = as.integer(best_params$min_data_in_leaf[1]),
    feature_fraction = best_params$feature_fraction[1],
    bagging_fraction = best_params$bagging_fraction[1],
    bagging_freq = as.integer(best_params$bagging_freq[1]),
    lambda_l1 = best_params$lambda_l1[1],
    lambda_l2 = best_params$lambda_l2[1],
    verbosity = -1,
    force_col_wise = TRUE
  )

  fit <- lightgbm::lgb.train(
    params = params,
    data = dtrain,
    nrounds = nrounds,
    verbose = -1
  )

  pred_log <- predict(fit, mats$pred, num_iteration = nrounds)
  pred_cases <- city_loginc_to_cases(pred_log, pred_data$target_population)

  list(
    model = fit,
    pred_log = pred_log,
    pred_cases = pmax(pred_cases, 0),
    feature_names = mats$feature_names,
    nrounds = nrounds
  )
}

evaluate_city_env_regressor <- function(model_name, horizon, base_df, pred_cases) {
  pred_cases <- pmax(pred_cases, 0)
  pred_log <- city_cases_to_loginc(pred_cases, base_df$target_population)

  eval_df <- base_df %>%
    mutate(
      actual_cases = target_cases,
      pred_cases = pred_cases,
      actual_log_incidence = target_log_incidence,
      pred_log_incidence = pred_log
    )

  threshold_cases_vec <- eval_df$city_outbreak_threshold_cases

  raw_reg <- tibble(
    Model = model_name,
    forecast_horizon = horizon,
    forecast_horizon_label = paste0("H+", horizon),
    RMSE_raw = safe_rmse(eval_df$actual_cases, eval_df$pred_cases),
    MAE_raw = safe_mae(eval_df$actual_cases, eval_df$pred_cases),
    R2_raw = safe_r2(eval_df$actual_cases, eval_df$pred_cases),
    Correlation_raw = safe_cor(eval_df$actual_cases, eval_df$pred_cases),
    Bias_raw = mean(eval_df$pred_cases - eval_df$actual_cases, na.rm = TRUE),
    Mean_pred_raw = mean(eval_df$pred_cases, na.rm = TRUE),
    Mean_actual_raw = mean(eval_df$actual_cases, na.rm = TRUE),
    RMSE_log_incidence = safe_rmse(eval_df$actual_log_incidence, eval_df$pred_log_incidence),
    MAE_log_incidence = safe_mae(eval_df$actual_log_incidence, eval_df$pred_log_incidence),
    R2_log_incidence = safe_r2(eval_df$actual_log_incidence, eval_df$pred_log_incidence),
    Correlation_log_incidence = safe_cor(eval_df$actual_log_incidence, eval_df$pred_log_incidence)
  )

  cls_cases <- classification_metrics_from_cases_city(
    eval_df$actual_cases,
    eval_df$pred_cases,
    threshold_cases_vec
  )

  high_week_threshold <- quantile(eval_df$actual_cases, 0.75, na.rm = TRUE)
  high_week_df <- eval_df %>% filter(actual_cases >= high_week_threshold)

  high_week_metrics <- if (nrow(high_week_df) > 0) {
    tibble(
      High_week_RMSE_raw = safe_rmse(high_week_df$actual_cases, high_week_df$pred_cases),
      High_week_MAE_raw = safe_mae(high_week_df$actual_cases, high_week_df$pred_cases),
      High_week_Bias_raw = mean(high_week_df$pred_cases - high_week_df$actual_cases, na.rm = TRUE),
      High_week_Underprediction_rate = mean(high_week_df$pred_cases < high_week_df$actual_cases, na.rm = TRUE)
    )
  } else {
    tibble(
      High_week_RMSE_raw = NA_real_,
      High_week_MAE_raw = NA_real_,
      High_week_Bias_raw = NA_real_,
      High_week_Underprediction_rate = NA_real_
    )
  }

  bind_cols(raw_reg, cls_cases, high_week_metrics)
}


# ============================================================
# 8. RUN ONE HORIZON
# ============================================================

run_one_city_env_horizon <- function(horizon) {
  set.seed(SEED + horizon)
  horizon_label <- paste0("H+", horizon)

  cat("\n============================================================\n")
  cat("CITY-WEEK ENVIRONMENTAL-ONLY LIGHTGBM REGRESSOR: ", horizon_label, "\n", sep = "")
  cat("============================================================\n")

  feat_obj <- build_city_env_horizon_features(
    horizon = horizon,
    keep_per_var = MAX_LAGS_KEPT_PER_ENV_VARIABLE,
    lag_train_end_year = TRAIN_CORE_END_YEAR
  )

  h_df <- feat_obj$data
  features <- feat_obj$features

  train_core <- h_df %>% filter(target_year <= TRAIN_CORE_END_YEAR)
  validation <- h_df %>% filter(target_year %in% VALIDATION_YEARS)

  if (nrow(train_core) == 0 || nrow(validation) == 0 || length(features) == 0) {
    stop(paste0("Validation split failed for city environmental model ", horizon_label))
  }

  reg_tuning_results <- tune_city_env_lgbm_regressor(train_core, validation, features, horizon_label)
  best_reg_params <- reg_tuning_results %>% slice(1)

  cat("\nBest city environmental LightGBM regressor params for ", horizon_label, ":\n", sep = "")
  print(best_reg_params)

  final_feat_obj <- build_city_env_horizon_features(
    horizon = horizon,
    keep_per_var = MAX_LAGS_KEPT_PER_ENV_VARIABLE,
    lag_train_end_year = TRAIN_END_YEAR,
    require_targets = FALSE
  )

  final_df <- final_feat_obj$data
  final_features <- final_feat_obj$features

  train_final <- final_df %>% filter(target_year <= TRAIN_END_YEAR)
  test_final <- final_df %>%
    filter(
      is_prediction_origin_window(origin_year, origin_week),
      is_prediction_target_window(target_year, target_week)
    )

  if (nrow(train_final) == 0 || nrow(test_final) == 0 || length(final_features) == 0) {
    stop(paste0("Final train/test split failed for city environmental model ", horizon_label))
  }

  final_reg <- fit_final_city_env_lgbm_regressor(
    train_data = train_final,
    pred_data = test_final,
    features = final_features,
    best_params = best_reg_params
  )

  final_metrics <- evaluate_city_env_regressor(
    model_name = "City-week environmental-only LightGBM regressor",
    horizon = horizon,
    base_df = test_final,
    pred_cases = final_reg$pred_cases
  )

  final_predictions <- test_final %>%
    select(
      origin_year,
      origin_week,
      target_year,
      target_week,
      forecast_horizon,
      forecast_horizon_label,
      city_dengue_cases,
      city_incidence_10000,
      target_cases,
      target_incidence_10000,
      target_log_incidence,
      target_population,
      city_outbreak_threshold_cases,
      city_large_outbreak_threshold_cases
    ) %>%
    mutate(
      actual_cases = target_cases,
      actual_incidence_10000 = target_incidence_10000,
      actual_log_incidence = target_log_incidence,
      actual_outbreak = actual_cases >= city_outbreak_threshold_cases,
      environmental_lightgbm_cases = final_reg$pred_cases,
      predicted_cases = final_reg$pred_cases,
      environmental_lightgbm_log_incidence = final_reg$pred_log,
      predicted_log_incidence = final_reg$pred_log,
      predicted_outbreak_from_cases = as.integer(predicted_cases >= city_outbreak_threshold_cases),
      outbreak_probability = city_environmental_probability_from_cases(predicted_cases, city_outbreak_threshold_cases),
      alert_threshold = 0.50,
      predicted_outbreak_from_probability = as.integer(outbreak_probability >= alert_threshold),
      alert_level = make_alert_level_from_probability(outbreak_probability),
      alert_level_from_cases = make_alert_level_from_cases(predicted_cases, city_outbreak_threshold_cases),
      error = predicted_cases - actual_cases,
      absolute_error = abs(error),
      display_in_app_default = forecast_horizon %in% DISPLAY_HORIZONS,
      model_type = "City-week environmental-only LightGBM regressor",
      uses_autocorrelation_features = FALSE,
      includes_citywide_environmental_features = TRUE
    )

  by_year <- final_predictions %>%
    group_by(target_year) %>%
    group_split() %>%
    purrr::map_df(function(d) {
      eval_base <- d %>%
        mutate(
          target_population = target_population,
          target_cases = actual_cases,
          target_log_incidence = actual_log_incidence,
          city_outbreak_threshold_cases = city_outbreak_threshold_cases
        )

      evaluate_city_env_regressor(
        model_name = paste0("City-week environmental-only LightGBM H+", horizon, " - target year ", unique(d$target_year)),
        horizon = horizon,
        base_df = eval_base,
        pred_cases = d$predicted_cases
      ) %>%
        mutate(target_year = unique(d$target_year), .after = forecast_horizon_label)
    })

  reg_importance <- tryCatch(
    {
      lightgbm::lgb.importance(model = final_reg$model) %>%
        as_tibble() %>%
        mutate(
          forecast_horizon = horizon,
          forecast_horizon_label = horizon_label,
          Component = "City-week environmental-only LightGBM regressor"
        )
    },
    error = function(e) {
      tibble(
        Feature = character(),
        Gain = numeric(),
        Cover = numeric(),
        Frequency = numeric(),
        forecast_horizon = integer(),
        forecast_horizon_label = character(),
        Component = character()
      )
    }
  )

  selected_settings <- tibble(
    forecast_horizon = horizon,
    forecast_horizon_label = horizon_label,
    final_feature_count = length(final_features),
    max_lags_kept_per_env_variable = MAX_LAGS_KEPT_PER_ENV_VARIABLE,
    reg_learning_rate = best_reg_params$learning_rate,
    reg_num_leaves = best_reg_params$num_leaves,
    reg_max_depth = best_reg_params$max_depth,
    reg_min_data_in_leaf = best_reg_params$min_data_in_leaf,
    reg_feature_fraction = best_reg_params$feature_fraction,
    reg_bagging_fraction = best_reg_params$bagging_fraction,
    reg_bagging_freq = best_reg_params$bagging_freq,
    reg_lambda_l1 = best_reg_params$lambda_l1,
    reg_lambda_l2 = best_reg_params$lambda_l2,
    reg_best_nrounds = final_reg$nrounds
  )

  booster_path <- file.path(MODEL_DIR, paste0("h", horizon, "_regressor.txt"))
  lightgbm::lgb.save(final_reg$model, booster_path)

  reg_bundle <- list(
    model_path = booster_path,
    model_family = "environmental_city_lightgbm",
    model_part = "regressor",
    horizon = horizon,
    horizon_label = horizon_label,
    feature_cols = final_features,
    matrix_feature_names = final_reg$feature_names,
    best_params = as.data.frame(best_reg_params),
    target = "target_log_incidence",
    uses_autocorrelation_features = FALSE,
    trained_on_years = paste0("<=", TRAIN_END_YEAR)
  )
  saveRDS(reg_bundle, file.path(MODEL_DIR, paste0("h", horizon, "_regressor.rds")))
  saveRDS(
    list(
      feature_cols = final_features,
      matrix_feature_names = final_reg$feature_names,
      horizon = horizon,
      horizon_label = horizon_label,
      uses_autocorrelation_features = FALSE
    ),
    file.path(MODEL_DIR, paste0("h", horizon, "_feature_spec.rds"))
  )

  write_csv(reg_tuning_results, file.path(OUTPUT_DIR, paste0("city_week_environmental_lightgbm_regressor_tuning_H", horizon, "_", OUTPUT_PREFIX, ".csv")))
  write_csv(final_feat_obj$lag_report, file.path(OUTPUT_DIR, paste0("city_week_environmental_lightgbm_selected_lag_report_H", horizon, "_", OUTPUT_PREFIX, ".csv")))
  write_csv(tibble(feature = final_features), file.path(OUTPUT_DIR, paste0("city_week_environmental_lightgbm_final_feature_list_H", horizon, "_", OUTPUT_PREFIX, ".csv")))
  write_csv(final_predictions, file.path(OUTPUT_DIR, paste0("city_week_environmental_lightgbm_predictions_H", horizon, "_", OUTPUT_PREFIX, ".csv")))
  write_csv(final_metrics, file.path(OUTPUT_DIR, paste0("city_week_environmental_lightgbm_metrics_H", horizon, "_", OUTPUT_PREFIX, ".csv")))

  cat("\nFinal city environmental LightGBM ", horizon_label, " metrics:\n", sep = "")
  print(as.data.frame(final_metrics))

  list(
    metrics = final_metrics,
    predictions = final_predictions,
    by_year = by_year,
    settings = selected_settings,
    importance = reg_importance
  )
}


# ============================================================
# 9. RUN H+0 TO H+12
# ============================================================

city_horizon_results <- purrr::map(FORECAST_HORIZONS, run_one_city_env_horizon)

city_horizon_metrics <- purrr::map_df(city_horizon_results, "metrics") %>% arrange(forecast_horizon)
city_horizon_predictions <- purrr::map_df(city_horizon_results, "predictions") %>% arrange(forecast_horizon, target_year, target_week)
city_horizon_by_year <- purrr::map_df(city_horizon_results, "by_year") %>% arrange(forecast_horizon, target_year)
city_horizon_settings <- purrr::map_df(city_horizon_results, "settings") %>% arrange(forecast_horizon)
city_horizon_importance <- purrr::map_df(city_horizon_results, "importance") %>% arrange(forecast_horizon, desc(Gain))


# ============================================================
# 10. SAVE FINAL OUTPUTS
# ============================================================
# App package policy: save only the prediction CSV in OUTPUT.
# Metrics are printed to the console for audit/review and are not saved as CSV.

metric_lookup <- city_horizon_metrics %>%
  transmute(
    forecast_horizon,
    mae = MAE_raw,
    rmse = RMSE_raw,
    r2 = R2_raw
  )

app_predictions <- city_horizon_predictions %>%
  left_join(metric_lookup, by = "forecast_horizon") %>%
  mutate(
    mode = "environmental_only",
    model_scope = "city",
    horizon = forecast_horizon,
    total_predicted_cases = predicted_cases,
    uses_autocorrelation_features = FALSE
  ) %>%
  arrange(mode, origin_year, origin_week, horizon, target_year, target_week)

# Final output safety repair:
# Environmental-only city is a pure regressor, so alert fields are derived from predicted cases.
# This guarantees app-facing alert_level/outbreak_probability are never blank.
.city_threshold_fallback <- suppressWarnings(stats::median(app_predictions$city_outbreak_threshold_cases, na.rm = TRUE))
if (is.na(.city_threshold_fallback) || is.nan(.city_threshold_fallback) || is.infinite(.city_threshold_fallback) || .city_threshold_fallback <= 0) {
  .city_threshold_fallback <- 1
}

app_predictions <- app_predictions %>%
  mutate(
    city_outbreak_threshold_cases = ifelse(
      is.na(city_outbreak_threshold_cases) | city_outbreak_threshold_cases <= 0,
      .city_threshold_fallback,
      city_outbreak_threshold_cases
    ),
    predicted_cases = pmax(as.numeric(predicted_cases), 0),
    predicted_cases = ifelse(is.na(predicted_cases), 0, predicted_cases),
    total_predicted_cases = predicted_cases,
    outbreak_probability = city_environmental_probability_from_cases(predicted_cases, city_outbreak_threshold_cases),
    alert_threshold = 0.50,
    predicted_outbreak_from_cases = as.integer(predicted_cases >= city_outbreak_threshold_cases),
    predicted_outbreak_from_probability = as.integer(outbreak_probability >= alert_threshold),
    alert_level_from_cases = make_alert_level_from_cases(predicted_cases, city_outbreak_threshold_cases),
    alert_level = make_alert_level_from_probability(outbreak_probability)
  )


# Row-completion safety net:
# The model should already predict every city-origin-horizon row. If a row is
# still missing because of unexpected data completeness issues, keep the app
# table complete and mark the missing forecast conservatively as zero/Low.
.complete_expected_targets <- function(origin_calendar, horizons) {
  .calendar <- make_calendar_range(min(origin_calendar$year, na.rm = TRUE), FORECAST_TARGET_END_YEAR)
  .origin_idx <- origin_calendar %>%
    left_join(.calendar, by = c("year", "week")) %>%
    transmute(origin_year = year, origin_week = week, origin_time_index = time_index)

  tidyr::crossing(
    .origin_idx,
    tibble(horizon = as.integer(horizons))
  ) %>%
    mutate(target_time_index = origin_time_index + horizon) %>%
    left_join(
      .calendar %>% transmute(target_time_index = time_index, target_year = year, target_week = week),
      by = "target_time_index"
    ) %>%
    filter(
      !is.na(target_year),
      !is.na(target_week),
      year_week_on_or_before(target_year, target_week, FORECAST_TARGET_END_YEAR, FORECAST_TARGET_END_WEEK)
    ) %>%
    select(origin_year, origin_week, horizon, target_year, target_week)
}

.expected_origin_calendar_for_completion <- bind_rows(
  tibble(year = 2025L, week = 1:weeks_in_year(2025L)),
  tibble(year = 2026L, week = 1:CURRENT_FORECAST_ORIGIN_WEEK)
)

.expected_prediction_keys <- .complete_expected_targets(.expected_origin_calendar_for_completion, FORECAST_HORIZONS)

.missing_prediction_keys <- .expected_prediction_keys %>%
  anti_join(
    app_predictions %>%
      transmute(
        origin_year = as.integer(origin_year),
        origin_week = as.integer(origin_week),
        horizon = as.integer(horizon),
        target_year = as.integer(target_year),
        target_week = as.integer(target_week)
      ),
    by = c("origin_year", "origin_week", "horizon", "target_year", "target_week")
  )

if (nrow(.missing_prediction_keys) > 0) {
  warning("Adding ", nrow(.missing_prediction_keys), " conservative fallback rows so the app has a complete city forecast table.")
  .missing_rows <- app_predictions[rep(NA_integer_, nrow(.missing_prediction_keys)), , drop = FALSE]

  .set_if_exists <- function(tbl, col, value) {
    if (col %in% names(tbl)) tbl[[col]] <- value
    tbl
  }

  .missing_rows <- .set_if_exists(.missing_rows, "year", .missing_prediction_keys$origin_year)
  .missing_rows <- .set_if_exists(.missing_rows, "week", .missing_prediction_keys$origin_week)
  .missing_rows <- .set_if_exists(.missing_rows, "origin_year", .missing_prediction_keys$origin_year)
  .missing_rows <- .set_if_exists(.missing_rows, "origin_week", .missing_prediction_keys$origin_week)
  .missing_rows <- .set_if_exists(.missing_rows, "horizon", .missing_prediction_keys$horizon)
  .missing_rows <- .set_if_exists(.missing_rows, "forecast_horizon", .missing_prediction_keys$horizon)
  .missing_rows <- .set_if_exists(.missing_rows, "forecast_horizon_label", paste0("H+", .missing_prediction_keys$horizon))
  .missing_rows <- .set_if_exists(.missing_rows, "target_year", .missing_prediction_keys$target_year)
  .missing_rows <- .set_if_exists(.missing_rows, "target_week", .missing_prediction_keys$target_week)
  .missing_rows <- .set_if_exists(.missing_rows, "predicted_cases", 0)
  .missing_rows <- .set_if_exists(.missing_rows, "total_predicted_cases", 0)
  .missing_rows <- .set_if_exists(.missing_rows, "pure_lightgbm_cases", 0)
  .missing_rows <- .set_if_exists(.missing_rows, "environmental_lightgbm_cases", 0)
  .missing_rows <- .set_if_exists(.missing_rows, "outbreak_probability", 0)
  .missing_rows <- .set_if_exists(.missing_rows, "alert_threshold", 0.50)
  .missing_rows <- .set_if_exists(.missing_rows, "predicted_outbreak_from_cases", 0L)
  .missing_rows <- .set_if_exists(.missing_rows, "predicted_outbreak_from_probability", 0L)
  .missing_rows <- .set_if_exists(.missing_rows, "alert_level", "Low")
  .missing_rows <- .set_if_exists(.missing_rows, "alert_level_from_cases", "Low")
  .missing_rows <- .set_if_exists(.missing_rows, "display_in_app_default", .missing_prediction_keys$horizon %in% DISPLAY_HORIZONS)

  app_predictions <- bind_rows(app_predictions, .missing_rows)
}

app_predictions <- app_predictions %>%
  arrange(mode, origin_year, origin_week, horizon, target_year, target_week)

expected_origin_calendar <- bind_rows(
  tibble(year = 2025L, week = 1:weeks_in_year(2025L)),
  tibble(year = 2026L, week = 1:CURRENT_FORECAST_ORIGIN_WEEK)
)
expected_prediction_rows <- nrow(expected_origin_calendar) * length(FORECAST_HORIZONS)
actual_prediction_rows <- nrow(app_predictions)
cat("
Expected city environmental-only prediction rows:", expected_prediction_rows, "
")
cat("Actual city environmental-only prediction rows:", actual_prediction_rows, "
")
if (actual_prediction_rows < expected_prediction_rows) {
  warning("City environmental-only output has fewer rows than expected. Check feature/target completeness messages above.")
}



# ============================================================
# FINAL APP OUTPUT SANITIZER
# ============================================================
# Purpose: keep the saved app CSV usable. Future target weeks do not have real
# observed dengue counts yet, so we preserve that truth using *_available flags,
# then zero-fill remaining NA cells so Streamlit/pandas does not display NA or
# break maps/tables.
.coalesce_numeric_cols <- function(tbl, cols, default = 0) {
  out <- rep(NA_real_, nrow(tbl))
  for (cc in cols) {
    if (cc %in% names(tbl)) {
      out <- dplyr::coalesce(out, suppressWarnings(as.numeric(tbl[[cc]])))
    }
  }
  out[is.na(out) | is.nan(out) | is.infinite(out)] <- default
  out
}

.prob_from_cases_poisson <- function(pred_cases, threshold_cases = 1) {
  lambda <- suppressWarnings(as.numeric(pred_cases))
  lambda[is.na(lambda) | is.nan(lambda) | is.infinite(lambda) | lambda < 0] <- 0
  threshold_cases <- suppressWarnings(as.numeric(threshold_cases))
  if (length(threshold_cases) == 1) threshold_cases <- rep(threshold_cases, length(lambda))
  threshold_cases[is.na(threshold_cases) | threshold_cases <= 0 | is.infinite(threshold_cases)] <- 1
  prob <- 1 - stats::ppois(pmax(threshold_cases - 1, 0), lambda = lambda)
  prob[is.na(prob) | is.nan(prob) | is.infinite(prob)] <- 0
  pmin(pmax(prob, 0), 1)
}

.fill_all_remaining_na_for_app <- function(tbl) {
  for (nm in names(tbl)) {
    if (is.factor(tbl[[nm]])) tbl[[nm]] <- as.character(tbl[[nm]])

    if (is.numeric(tbl[[nm]]) || is.integer(tbl[[nm]])) {
      x <- suppressWarnings(as.numeric(tbl[[nm]]))
      x[is.na(x) | is.nan(x) | is.infinite(x)] <- 0
      tbl[[nm]] <- x
    } else if (is.logical(tbl[[nm]])) {
      x <- tbl[[nm]]
      x[is.na(x)] <- FALSE
      tbl[[nm]] <- x
    } else if (is.character(tbl[[nm]])) {
      x <- tbl[[nm]]
      x[is.na(x)] <- ""
      x[stringr::str_squish(x) == "NA"] <- ""
      tbl[[nm]] <- x
    }
  }

  if ("alert_level" %in% names(tbl)) {
    tbl$alert_level[is.na(tbl$alert_level) | stringr::str_squish(tbl$alert_level) == ""] <- "Low"
  }
  if ("alert_level_from_cases" %in% names(tbl)) {
    tbl$alert_level_from_cases[is.na(tbl$alert_level_from_cases) | stringr::str_squish(tbl$alert_level_from_cases) == ""] <- "Low"
  }
  tbl
}

sanitize_city_app_predictions <- function(tbl, expected_mode, uses_autocorrelation) {
  if (!"mode" %in% names(tbl)) tbl$mode <- expected_mode
  tbl$mode[is.na(tbl$mode) | stringr::str_squish(as.character(tbl$mode)) == ""] <- expected_mode

  if (!"model_scope" %in% names(tbl)) tbl$model_scope <- "city"
  tbl$model_scope[is.na(tbl$model_scope) | stringr::str_squish(as.character(tbl$model_scope)) == ""] <- "city"

  actual_candidate <- .coalesce_numeric_cols(
    tbl,
    c("actual_cases", "target_cases", "target_cases_h", "city_dengue_cases_target", "city_cases_target", "city_dengue_cases"),
    default = NA_real_
  )
  tbl$actual_cases_available <- !is.na(actual_candidate)

  tbl$predicted_cases <- .coalesce_numeric_cols(
    tbl,
    c(
      "predicted_cases",
      "total_predicted_cases",
      "pure_lightgbm_cases",
      "environmental_lightgbm_cases",
      "xgb_regressor_cases",
      "lightgbm_cases"
    ),
    default = 0
  )
  tbl$predicted_cases <- pmax(tbl$predicted_cases, 0)
  tbl$total_predicted_cases <- tbl$predicted_cases

  if ("pure_lightgbm_cases" %in% names(tbl)) {
    tbl$pure_lightgbm_cases <- .coalesce_numeric_cols(tbl, c("pure_lightgbm_cases", "predicted_cases"), 0)
  }
  if ("environmental_lightgbm_cases" %in% names(tbl)) {
    tbl$environmental_lightgbm_cases <- .coalesce_numeric_cols(tbl, c("environmental_lightgbm_cases", "predicted_cases"), 0)
  }

  threshold <- .coalesce_numeric_cols(tbl, c("city_outbreak_threshold_cases"), default = NA_real_)
  threshold_fallback <- suppressWarnings(stats::median(threshold[!is.na(threshold) & threshold > 0], na.rm = TRUE))
  if (is.na(threshold_fallback) || is.nan(threshold_fallback) || is.infinite(threshold_fallback) || threshold_fallback <= 0) threshold_fallback <- 1
  threshold[is.na(threshold) | threshold <= 0 | is.infinite(threshold)] <- threshold_fallback
  tbl$city_outbreak_threshold_cases <- threshold

  if (!"alert_threshold" %in% names(tbl)) tbl$alert_threshold <- 0.50
  tbl$alert_threshold <- .coalesce_numeric_cols(tbl, c("alert_threshold"), 0.50)
  tbl$alert_threshold[tbl$alert_threshold <= 0 | tbl$alert_threshold > 1] <- 0.50

  prob_existing <- .coalesce_numeric_cols(tbl, c("outbreak_probability"), default = NA_real_)
  prob_fallback <- .prob_from_cases_poisson(tbl$predicted_cases, tbl$city_outbreak_threshold_cases)
  prob <- dplyr::coalesce(prob_existing, prob_fallback)
  prob[is.na(prob) | is.nan(prob) | is.infinite(prob)] <- 0
  tbl$outbreak_probability <- pmin(pmax(prob, 0), 1)

  tbl$predicted_outbreak_from_cases <- as.integer(tbl$predicted_cases >= tbl$city_outbreak_threshold_cases)
  tbl$predicted_outbreak_from_probability <- as.integer(tbl$outbreak_probability >= tbl$alert_threshold)
  tbl$alert_level <- make_alert_level_from_probability(tbl$outbreak_probability)
  tbl$alert_level[is.na(tbl$alert_level) | stringr::str_squish(tbl$alert_level) == ""] <- "Low"
  tbl$alert_level_from_cases <- make_alert_level_from_cases(tbl$predicted_cases, tbl$city_outbreak_threshold_cases)
  tbl$alert_level_from_cases[is.na(tbl$alert_level_from_cases) | stringr::str_squish(tbl$alert_level_from_cases) == ""] <- "Low"

  if (!"horizon" %in% names(tbl)) tbl$horizon <- .coalesce_numeric_cols(tbl, c("forecast_horizon", "Horizon_number"), 0)
  tbl$horizon <- .coalesce_numeric_cols(tbl, c("horizon", "forecast_horizon", "Horizon_number"), 0)
  if ("forecast_horizon" %in% names(tbl)) tbl$forecast_horizon <- tbl$horizon
  if (!"forecast_horizon_label" %in% names(tbl)) tbl$forecast_horizon_label <- paste0("H+", tbl$horizon)
  tbl$forecast_horizon_label[is.na(tbl$forecast_horizon_label) | stringr::str_squish(tbl$forecast_horizon_label) == ""] <- paste0("H+", tbl$horizon[is.na(tbl$forecast_horizon_label) | stringr::str_squish(tbl$forecast_horizon_label) == ""])

  if (!"uses_autocorrelation_features" %in% names(tbl)) tbl$uses_autocorrelation_features <- uses_autocorrelation
  tbl$uses_autocorrelation_features[is.na(tbl$uses_autocorrelation_features)] <- uses_autocorrelation

  tbl$forecast_available <- TRUE
  tbl <- .fill_all_remaining_na_for_app(tbl)
  tbl
}

app_predictions <- sanitize_city_app_predictions(app_predictions, expected_mode = "environmental_only", uses_autocorrelation = FALSE)

.na_audit_file <- file.path(OUTPUT_DIR, "forecast_city_environmental_only_na_audit.csv")
.na_audit <- tibble::tibble(column = names(app_predictions), na_count = vapply(app_predictions, function(x) sum(is.na(x)), integer(1)))
readr::write_csv(.na_audit, .na_audit_file)
cat("\nNA audit saved to: ", .na_audit_file, "\n", sep = "")
if (any(.na_audit$na_count > 0)) {
  print(.na_audit %>% dplyr::filter(na_count > 0), n = Inf)
  stop("Final app forecast CSV still has NA values. See NA audit above: ", .na_audit_file)
}

prediction_file <- file.path(OUTPUT_DIR, "forecast_city_environmental_only.csv")
readr::write_csv(app_predictions, prediction_file)

city_horizon_summary <- city_horizon_metrics %>%
  select(
    forecast_horizon,
    forecast_horizon_label,
    RMSE_raw,
    MAE_raw,
    R2_raw,
    Correlation_raw,
    Bias_raw,
    Mean_pred_raw,
    Mean_actual_raw,
    RMSE_log_incidence,
    MAE_log_incidence,
    R2_log_incidence,
    Correlation_log_incidence,
    Precision,
    Recall,
    Outbreak_F1_count_threshold,
    False_alarm_rate,
    Specificity,
    High_week_RMSE_raw,
    High_week_MAE_raw,
    High_week_Bias_raw,
    High_week_Underprediction_rate
  ) %>%
  arrange(forecast_horizon)

cat("
============================================================
")
cat("CITY-WEEK ENVIRONMENTAL-ONLY LIGHTGBM H+0 TO H+12 METRICS
")
cat("============================================================
")
print(as.data.frame(city_horizon_summary))

cat("
============================================================
")
cat("SAVED OUTPUT CSV
")
cat("============================================================
")
cat("- ", prediction_file, "
", sep = "")
cat("
App interpretation:
")
cat("Use predicted_cases or environmental_lightgbm_cases as the final citywide environmental-only case forecast.
")
cat("This model is a pure environmental-only regressor, so outbreak_probability is derived from predicted_cases relative to the city outbreak threshold.
")
cat("Use alert_level as the app-facing environmental-only alert category.
")
cat("Use display_in_app_default to show selected week, +1, +2, +3, +4, +8, and +12 in the app.
")
