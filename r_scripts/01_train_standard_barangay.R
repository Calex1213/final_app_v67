# ============================================================
# ISOLATED SOFT-GATED XGBOOST HYBRID MODEL
# ALPHA = 0.50
# H+0 TO H+12 DIRECT FORECASTS
#
# Final model:
#   Soft-gated XGBoost hybrid:
#     predicted_cases = xgboost_regressor_cases * (xgboost_classifier_probability ^ 0.50)
#
# Includes tuning for:
#   - number of selected lags per variable
#   - XGBoost regressor hyperparameters
#   - XGBoost classifier hyperparameters
#
# Correct horizon definition:
#   H+0  = same-week/current-week target, shift = 0
#   H+1  = 1 week ahead
#   H+2  = 2 weeks ahead
#   ...
#   H+12 = 12 weeks ahead
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
SHAPE_ZIP_PATH <- file.path(PROJECT_DIR, "data", "cebu_city_barangays.zip")
OUTPUT_DIR <- file.path(PROJECT_DIR, "outputs")
MODEL_ROOT_DIR <- file.path(PROJECT_DIR, "models")
METADATA_DIR <- file.path(PROJECT_DIR, "model_metadata")
dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(MODEL_ROOT_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(METADATA_DIR, showWarnings = FALSE, recursive = TRUE)


TRAIN_END_YEAR <- 2022
TEST_YEARS <- c(2023, 2024)

# Validation stays inside the training era so the final model can still be trained up to 2024.
VALIDATION_YEARS <- c(2021, 2022)
TRAIN_CORE_END_YEAR <- min(VALIDATION_YEARS) - 1

# Current surveillance origin and required forecast reach.
# H+12 from 2026 week 19 should reach 2026 week 31.
CURRENT_FORECAST_ORIGIN_YEAR <- 2024L
CURRENT_FORECAST_ORIGIN_WEEK <- 52L
FORECAST_TARGET_END_YEAR <- 2025L
FORECAST_TARGET_END_WEEK <- 12L

OUTBREAK_COUNT_THRESHOLD <- 2
LARGE_OUTBREAK_THRESHOLD <- 5
LEAD_LOOKBACK_WEEKS <- 4

MAX_LAG_TO_TEST <- 20
LAG_KEEP_GRID <- c(1, 2, 3, 4, 5)

ENV_ROLL_WINDOWS <- c(4, 8)

POP_DENSITY_UNIT <- "per_km2"
USE_PEAK_WEIGHTS <- TRUE

FORECAST_HORIZONS <- 0:12

SOFT_ALPHA <- 0.50
ALERT_PROB_THRESHOLD <- 0.50

OUTPUT_PREFIX <- "ISOLATED_SOFT_GATED_XGBOOST_ALPHA_0_50_H0_TO_H12"
PLOT_DIR <- file.path(OUTPUT_DIR, paste0("dengue_plots_", OUTPUT_PREFIX))
MODEL_DIR <- file.path(MODEL_ROOT_DIR, "standard_barangay")
dir.create(MODEL_DIR, showWarnings = FALSE, recursive = TRUE)

SEED <- 123
set.seed(SEED)

dir.create(PLOT_DIR, showWarnings = FALSE)


# ============================================================
# 1. PACKAGES
# ============================================================

needed_packages <- c(
  "readxl", "dplyr", "tidyr", "stringr", "janitor", "purrr",
  "xgboost", "Matrix", "sf", "spdep", "tibble",
  "ggplot2", "scales", "zoo", "pROC", "readr"
)

installed <- rownames(installed.packages())

for (p in needed_packages) {
  if (!(p %in% installed)) {
    install.packages(p, dependencies = TRUE)
  }
}

library(readxl)
library(dplyr)
library(tidyr)
library(stringr)
library(janitor)
library(purrr)
library(xgboost)
library(Matrix)
library(sf)
library(spdep)
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
# 3. READ DATA
# ============================================================

if (!file.exists(DATA_PATH)) {
  stop(paste0("DATA_PATH not found: ", DATA_PATH))
}

if (!file.exists(SHAPE_ZIP_PATH)) {
  stop(paste0("SHAPE_ZIP_PATH not found: ", SHAPE_ZIP_PATH))
}

raw_df <- read_excel(DATA_PATH) %>%
  clean_names()

cat("\nColumns found in dataset:\n")
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
  cat("\nBarangays without matched area:\n")
  print(unique(df$barangay[is.na(df$barangay_area_m2)]))
  stop("Some barangays did not match the area table.")
}

df <- ensure_forecast_extension_rows(df)

cat("\nRows after in-memory forecast extension through ", FORECAST_TARGET_END_YEAR, " week ", FORECAST_TARGET_END_WEEK, ": ", nrow(df), "\n", sep = "")

df <- df %>%
  mutate(
    barangay_area_km2 = barangay_area_m2 / 1e6,
    estimated_population = case_when(
      POP_DENSITY_UNIT == "per_km2" ~ pop_density * barangay_area_km2,
      POP_DENSITY_UNIT == "per_m2" ~ pop_density * barangay_area_m2,
      TRUE ~ NA_real_
    ),
    estimated_population = ifelse(
      estimated_population <= 0 | is.na(estimated_population),
      NA_real_,
      estimated_population
    ),
    dengue_incidence_10000 = ifelse(
      is.na(dengue_cases),
      NA_real_,
      (dengue_cases / estimated_population) * 10000
    ),
    dengue_incidence_10000 = ifelse(
      is.na(dengue_cases),
      NA_real_,
      ifelse(is.na(dengue_incidence_10000) | dengue_incidence_10000 < 0, 0, dengue_incidence_10000)
    ),
    target_log_incidence = log1p(dengue_incidence_10000),
    outbreak_actual = ifelse(is.na(dengue_cases), NA_integer_, as.integer(dengue_cases >= OUTBREAK_COUNT_THRESHOLD)),
    large_outbreak_actual = ifelse(is.na(dengue_cases), NA_integer_, as.integer(dengue_cases >= LARGE_OUTBREAK_THRESHOLD)),
    week_sin = sin(2 * pi * week / 52),
    week_cos = cos(2 * pi * week / 52)
  ) %>%
  arrange(barangay, year, week)


# ============================================================
# 4. SHAPEFILE NEIGHBOR STRUCTURE
# ============================================================

shape_dir <- file.path(tempdir(), "cebu_city_barangays_shape")
dir.create(shape_dir, showWarnings = FALSE, recursive = TRUE)

unzip(SHAPE_ZIP_PATH, exdir = shape_dir)

shp_file <- list.files(shape_dir, pattern = "\\.shp$", full.names = TRUE)[1]

if (is.na(shp_file)) {
  stop("No .shp file found inside the zip.")
}

barangay_sf <- st_read(shp_file, quiet = TRUE) %>%
  clean_names()

possible_name_cols <- c(
  "barangay", "brgy", "name", "adm4_en", "adm4_name",
  "bgy_name", "barangay_n", "brgy_name"
)

name_col <- possible_name_cols[possible_name_cols %in% names(barangay_sf)][1]

if (is.na(name_col)) {
  stop("Could not detect barangay name column in shapefile.")
}

barangay_sf <- barangay_sf %>%
  mutate(barangay = toupper(str_squish(as.character(.data[[name_col]])))) %>%
  filter(barangay %in% unique(df$barangay)) %>%
  arrange(barangay)

barangay_sf <- st_make_valid(barangay_sf)

nb <- poly2nb(barangay_sf, queen = TRUE)
names(nb) <- barangay_sf$barangay

neighbor_pairs <- tibble(
  barangay = rep(names(nb), lengths(nb)),
  neighbor = names(nb)[unlist(nb)]
) %>%
  filter(!is.na(neighbor))

cat("\nNeighbor pairs created:", nrow(neighbor_pairs), "\n")


# ============================================================
# 5. FEATURE ENGINEERING HELPERS
# ============================================================

make_lags <- function(data, cols, lags, group_col = "barangay") {
  out <- data

  for (cc in cols) {
    if (cc %in% names(out)) {
      for (ll in lags) {
        new_name <- paste0(cc, "_lag", ll)

        out <- out %>%
          group_by(.data[[group_col]]) %>%
          arrange(year, week, .by_group = TRUE) %>%
          mutate(!!new_name := dplyr::lag(.data[[cc]], ll)) %>%
          ungroup()
      }
    }
  }

  out
}

make_rolls <- function(data, cols, windows, group_col = "barangay") {
  out <- data

  for (cc in cols) {
    if (cc %in% names(out)) {
      for (ww in windows) {
        new_name <- paste0(cc, "_rollmean_lag1_w", ww)

        out <- out %>%
          group_by(.data[[group_col]]) %>%
          arrange(year, week, .by_group = TRUE) %>%
          mutate(
            !!new_name := zoo::rollapplyr(
              dplyr::lag(.data[[cc]], 1),
              width = ww,
              FUN = function(z) mean(z, na.rm = TRUE),
              fill = NA_real_,
              partial = FALSE
            )
          ) %>%
          ungroup()
      }
    }
  }

  out
}

select_best_lags_for_horizon <- function(data,
                                         base_vars,
                                         max_lag = 20,
                                         keep_per_var = 2,
                                         train_end_year = TRAIN_END_YEAR,
                                         target_log_col = "target_log_incidence_h",
                                         target_cases_col = "target_cases_h",
                                         target_outbreak_col = "target_outbreak_h",
                                         target_large_col = "target_large_outbreak_h") {
  train_only <- data %>%
    filter(!is.na(target_year_h), target_year_h <= train_end_year)

  selected <- c()
  reports <- list()

  for (v in base_vars) {
    lag_cols <- paste0(v, "_lag", 1:max_lag)
    lag_cols <- lag_cols[lag_cols %in% names(train_only)]

    if (length(lag_cols) == 0) next

    scores <- purrr::map_df(lag_cols, function(col) {
      ok <- !is.na(train_only[[col]]) &
        !is.na(train_only[[target_log_col]]) &
        !is.na(train_only[[target_cases_col]]) &
        !is.na(train_only[[target_outbreak_col]]) &
        !is.na(train_only[[target_large_col]])

      if (sum(ok) < 30 || sd(train_only[[col]][ok], na.rm = TRUE) == 0) {
        return(tibble(
          variable = v,
          feature = col,
          lag = as.integer(str_extract(col, "\\d+$")),
          cor_log_incidence = NA_real_,
          cor_cases = NA_real_,
          cor_outbreak = NA_real_,
          cor_large_outbreak = NA_real_,
          peak_lift = NA_real_,
          selection_score = NA_real_
        ))
      }

      x <- train_only[[col]][ok]
      y_log <- train_only[[target_log_col]][ok]
      y_cases <- train_only[[target_cases_col]][ok]
      y_out <- train_only[[target_outbreak_col]][ok]
      y_large <- train_only[[target_large_col]][ok]

      cor_log <- suppressWarnings(abs(cor(x, y_log, use = "complete.obs")))
      cor_cases <- suppressWarnings(abs(cor(x, y_cases, use = "complete.obs")))
      cor_out <- suppressWarnings(abs(cor(x, y_out, use = "complete.obs")))
      cor_large <- suppressWarnings(abs(cor(x, y_large, use = "complete.obs")))

      peak_lift <- NA_real_

      if (sum(y_large == 1, na.rm = TRUE) >= 5 &&
          sum(y_large == 0, na.rm = TRUE) >= 5) {
        peak_lift <- abs(
          mean(x[y_large == 1], na.rm = TRUE) -
            mean(x[y_large == 0], na.rm = TRUE)
        ) / (sd(x, na.rm = TRUE) + 1e-9)
      }

      score <- 0.35 * ifelse(is.na(cor_log), 0, cor_log) +
        0.30 * ifelse(is.na(cor_cases), 0, cor_cases) +
        0.20 * ifelse(is.na(cor_out), 0, cor_out) +
        0.10 * ifelse(is.na(cor_large), 0, cor_large) +
        0.05 * ifelse(is.na(peak_lift), 0, min(peak_lift, 3) / 3)

      tibble(
        variable = v,
        feature = col,
        lag = as.integer(str_extract(col, "\\d+$")),
        cor_log_incidence = cor_log,
        cor_cases = cor_cases,
        cor_outbreak = cor_out,
        cor_large_outbreak = cor_large,
        peak_lift = peak_lift,
        selection_score = score
      )
    }) %>%
      arrange(desc(selection_score), lag)

    chosen <- scores %>%
      filter(!is.na(selection_score)) %>%
      slice_head(n = keep_per_var) %>%
      pull(feature)

    selected <- c(selected, chosen)

    reports[[v]] <- scores %>%
      mutate(selected = feature %in% chosen)
  }

  list(
    selected_features = unique(selected),
    lag_report = bind_rows(reports)
  )
}


# ============================================================
# 6. CREATE CANDIDATE FEATURES
# ============================================================

env_candidates <- c(
  "rainfall", "rh", "humidity", "relative_humidity",
  "temp_c", "temperature", "t_mean", "tmin", "tmax", "t_min", "t_max",
  "u_component_of_wind_10m", "v_component_of_wind_10m",
  "wind_speed_10m", "wind_speed",
  "flood_depth", "flood_duration", "flood_extent", "water_level"
)

env_vars <- env_candidates[env_candidates %in% names(df)]

cat("\nEnvironmental variables found and used:\n")
print(env_vars)

static_candidates <- c(
  "pop_density",
  "barangay_area_m2",
  "barangay_area_km2",
  "flood_risk_index",
  "barangay_classification",
  names(df)[
    str_detect(
      names(df),
      "^percent_|^x_percent_|annual_crop|brush|built|forest|crop|barren|fishpond|grassland|mangrove|water|landcover"
    )
  ]
)

static_vars <- unique(static_candidates[static_candidates %in% names(df)])

city_week <- df %>%
  group_by(year, week) %>%
  summarise(
    city_cases = sum(dengue_cases, na.rm = TRUE),
    city_incidence_mean = mean(dengue_incidence_10000, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  arrange(year, week)

for (ll in 1:MAX_LAG_TO_TEST) {
  city_week <- city_week %>%
    mutate(
      !!paste0("city_cases_lag", ll) := dplyr::lag(city_cases, ll),
      !!paste0("city_incidence_mean_lag", ll) := dplyr::lag(city_incidence_mean, ll)
    )
}

city_lag_cols <- names(city_week)[
  str_detect(names(city_week), "^city_cases_lag|^city_incidence_mean_lag")
]

city_week_lagged <- city_week %>%
  select(year, week, all_of(city_lag_cols))

df2 <- df %>%
  left_join(city_week_lagged, by = c("year", "week"))

neighbor_activity <- df %>%
  select(year, week, neighbor = barangay, dengue_cases, dengue_incidence_10000) %>%
  inner_join(neighbor_pairs, by = "neighbor") %>%
  group_by(barangay, year, week) %>%
  summarise(
    neighbor_cases_mean = mean(dengue_cases, na.rm = TRUE),
    neighbor_incidence_mean = mean(dengue_incidence_10000, na.rm = TRUE),
    .groups = "drop"
  )

df2 <- df2 %>%
  left_join(neighbor_activity, by = c("barangay", "year", "week")) %>%
  mutate(
    neighbor_cases_mean = ifelse(is.na(neighbor_cases_mean), 0, neighbor_cases_mean),
    neighbor_incidence_mean = ifelse(is.na(neighbor_incidence_mean), 0, neighbor_incidence_mean)
  )

case_vars <- c(
  "dengue_cases",
  "dengue_incidence_10000",
  "target_log_incidence"
)

neighbor_vars <- c(
  "neighbor_cases_mean",
  "neighbor_incidence_mean"
)

city_base_vars <- c(
  "city_cases",
  "city_incidence_mean"
)

df2 <- df2 %>%
  make_lags(case_vars, 1:MAX_LAG_TO_TEST) %>%
  make_lags(env_vars, 1:MAX_LAG_TO_TEST) %>%
  make_lags(neighbor_vars, 1:MAX_LAG_TO_TEST) %>%
  make_rolls(env_vars, ENV_ROLL_WINDOWS)

roll_feature_cols <- names(df2)[str_detect(names(df2), "_rollmean_lag1_w")]


# ============================================================
# 7. MATRIX, WEIGHTS, AND METRICS
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

make_matrix <- function(train_data, test_data, features) {
  train_x_raw <- train_data %>% select(all_of(features))
  test_x_raw <- test_data %>% select(all_of(features))

  combined <- prepare_matrix_features(train_x_raw, test_x_raw)
  mm <- model.matrix(~ . - 1, data = combined, na.action = stats::na.pass)

  train_mat <- mm[1:nrow(train_x_raw), , drop = FALSE]
  test_mat <- mm[(nrow(train_x_raw) + 1):nrow(mm), , drop = FALSE]

  if (nrow(test_mat) != nrow(test_x_raw)) {
    stop("Prediction matrix row mismatch: expected ", nrow(test_x_raw), " rows but got ", nrow(test_mat), ".")
  }

  list(
    train = train_mat,
    test = test_mat
  )
}

safe_rmse <- function(actual, pred) {
  sqrt(mean((actual - pred)^2, na.rm = TRUE))
}

safe_mae <- function(actual, pred) {
  mean(abs(actual - pred), na.rm = TRUE)
}

safe_r2 <- function(actual, pred) {
  ss_res <- sum((actual - pred)^2, na.rm = TRUE)
  ss_tot <- sum((actual - mean(actual, na.rm = TRUE))^2, na.rm = TRUE)

  if (ss_tot == 0) return(NA_real_)

  1 - ss_res / ss_tot
}

safe_cor <- function(actual, pred) {
  suppressWarnings(cor(actual, pred, use = "complete.obs"))
}

safe_auc <- function(actual_class, prob) {
  actual_class <- as.integer(actual_class)

  if (length(unique(actual_class[!is.na(actual_class)])) < 2) {
    return(NA_real_)
  }

  tryCatch(
    as.numeric(pROC::auc(actual_class, prob)),
    error = function(e) NA_real_
  )
}

cases_to_loginc <- function(cases, estimated_population) {
  incidence <- (cases / estimated_population) * 10000
  incidence <- ifelse(is.na(incidence) | incidence < 0, 0, incidence)

  log1p(incidence)
}

loginc_to_cases <- function(pred_log_incidence, estimated_population) {
  pred_incidence <- expm1(pred_log_incidence)
  pred_cases <- (pred_incidence / 10000) * estimated_population
  pred_cases <- ifelse(is.na(pred_cases), 0, pred_cases)

  pmax(pred_cases, 0)
}

make_reg_weights <- function(cases) {
  if (!USE_PEAK_WEIGHTS) {
    return(rep(1, length(cases)))
  }

  case_when(
    cases >= 10 ~ 8,
    cases >= LARGE_OUTBREAK_THRESHOLD ~ 5,
    cases >= OUTBREAK_COUNT_THRESHOLD ~ 3,
    cases > 0 ~ 1.5,
    TRUE ~ 1
  )
}

make_class_weights <- function(outbreak_actual) {
  if (!USE_PEAK_WEIGHTS) {
    return(rep(1, length(outbreak_actual)))
  }

  ifelse(outbreak_actual == 1, 3, 1)
}

make_soft_gate_pred <- function(prob, reg_cases, alpha = 0.50) {
  pmax(reg_cases, 0) * (pmin(pmax(prob, 0), 1) ^ alpha)
}

classification_metrics_from_cases <- function(actual_cases, pred_cases, threshold) {
  actual_class <- actual_cases >= threshold
  pred_class <- pred_cases >= threshold

  tp <- sum(actual_class & pred_class, na.rm = TRUE)
  tn <- sum(!actual_class & !pred_class, na.rm = TRUE)
  fp <- sum(!actual_class & pred_class, na.rm = TRUE)
  fn <- sum(actual_class & !pred_class, na.rm = TRUE)

  precision <- ifelse((tp + fp) == 0, NA_real_, tp / (tp + fp))
  recall <- ifelse((tp + fn) == 0, NA_real_, tp / (tp + fn))

  f1 <- ifelse(
    is.na(precision) | is.na(recall) | (precision + recall) == 0,
    NA_real_,
    2 * precision * recall / (precision + recall)
  )

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

classification_metrics_from_prob <- function(actual_outbreak, prob, threshold = 0.50) {
  actual_class <- as.integer(actual_outbreak)
  pred_class <- prob >= threshold

  tp <- sum(actual_class == 1 & pred_class, na.rm = TRUE)
  tn <- sum(actual_class == 0 & !pred_class, na.rm = TRUE)
  fp <- sum(actual_class == 0 & pred_class, na.rm = TRUE)
  fn <- sum(actual_class == 1 & !pred_class, na.rm = TRUE)

  precision <- ifelse((tp + fp) == 0, NA_real_, tp / (tp + fp))
  recall <- ifelse((tp + fn) == 0, NA_real_, tp / (tp + fn))

  f1 <- ifelse(
    is.na(precision) | is.na(recall) | (precision + recall) == 0,
    NA_real_,
    2 * precision * recall / (precision + recall)
  )

  false_alarm_rate <- ifelse((fp + tn) == 0, NA_real_, fp / (fp + tn))
  specificity <- ifelse((tn + fp) == 0, NA_real_, tn / (tn + fp))

  tibble(
    Alert_threshold = threshold,
    Alert_Precision = precision,
    Alert_Recall = recall,
    Alert_F1 = f1,
    Alert_False_alarm_rate = false_alarm_rate,
    Alert_Specificity = specificity,
    Alert_TP = tp,
    Alert_TN = tn,
    Alert_FP = fp,
    Alert_FN = fn,
    Alert_AUC = safe_auc(actual_class, prob),
    Brier_score = mean((prob - actual_class)^2, na.rm = TRUE)
  )
}

evaluate_predictions <- function(model_name,
                                 horizon,
                                 data,
                                 pred_cases,
                                 pred_log,
                                 prob) {
  eval_df <- data %>%
    mutate(
      actual_cases = target_cases_h,
      pred_cases = pmax(pred_cases, 0),
      actual_log_incidence = target_log_incidence_h,
      pred_log_incidence = pmax(pred_log, 0),
      actual_outbreak = target_outbreak_h
    )

  raw <- tibble(
    Model = model_name,
    Horizon = paste0("H+", horizon),
    Horizon_number = horizon,
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

  cls_cases <- classification_metrics_from_cases(
    actual_cases = eval_df$actual_cases,
    pred_cases = eval_df$pred_cases,
    threshold = OUTBREAK_COUNT_THRESHOLD
  )

  cls_prob <- classification_metrics_from_prob(
    actual_outbreak = eval_df$actual_outbreak,
    prob = prob,
    threshold = ALERT_PROB_THRESHOLD
  )

  outbreak_df <- eval_df %>%
    filter(actual_cases >= OUTBREAK_COUNT_THRESHOLD)

  outbreak_metrics <- if (nrow(outbreak_df) > 0) {
    tibble(
      Outbreak_week_RMSE = safe_rmse(outbreak_df$actual_cases, outbreak_df$pred_cases),
      Outbreak_week_MAE = safe_mae(outbreak_df$actual_cases, outbreak_df$pred_cases),
      Outbreak_week_Bias = mean(outbreak_df$pred_cases - outbreak_df$actual_cases, na.rm = TRUE),
      Outbreak_week_Underprediction_rate = mean(outbreak_df$pred_cases < outbreak_df$actual_cases, na.rm = TRUE)
    )
  } else {
    tibble(
      Outbreak_week_RMSE = NA_real_,
      Outbreak_week_MAE = NA_real_,
      Outbreak_week_Bias = NA_real_,
      Outbreak_week_Underprediction_rate = NA_real_
    )
  }

  large_df <- eval_df %>%
    filter(actual_cases >= LARGE_OUTBREAK_THRESHOLD)

  large_metrics <- if (nrow(large_df) > 0) {
    tibble(
      Large_outbreak_RMSE = safe_rmse(large_df$actual_cases, large_df$pred_cases),
      Large_outbreak_MAE = safe_mae(large_df$actual_cases, large_df$pred_cases),
      Large_outbreak_Bias = mean(large_df$pred_cases - large_df$actual_cases, na.rm = TRUE),
      Large_outbreak_Underprediction_rate = mean(large_df$pred_cases < large_df$actual_cases, na.rm = TRUE)
    )
  } else {
    tibble(
      Large_outbreak_RMSE = NA_real_,
      Large_outbreak_MAE = NA_real_,
      Large_outbreak_Bias = NA_real_,
      Large_outbreak_Underprediction_rate = NA_real_
    )
  }

  bind_cols(raw, cls_cases, cls_prob, outbreak_metrics, large_metrics)
}

validation_score <- function(metrics_row) {
  m <- metrics_row

  over_bias <- pmax(
    ifelse(is.na(m$Mean_pred_raw - m$Mean_actual_raw), 0, m$Mean_pred_raw - m$Mean_actual_raw),
    0
  )

  score <- m$RMSE_raw +
    0.20 * m$MAE_raw +
    0.60 * (1 - ifelse(is.na(m$Recall), 0, m$Recall)) +
    4.00 * ifelse(is.na(m$False_alarm_rate), 0, m$False_alarm_rate) +
    0.20 * ifelse(is.na(m$Large_outbreak_MAE), 0, m$Large_outbreak_MAE) +
    0.50 * over_bias

  as.numeric(score)
}


# ============================================================
# 8. HORIZON TARGETS
# ============================================================

add_horizon_targets <- function(data, horizon) {
  shift_n <- horizon

  data %>%
    group_by(barangay) %>%
    arrange(year, week, .by_group = TRUE) %>%
    mutate(
      origin_year = year,
      origin_week = week,

      target_year_h = dplyr::lead(year, shift_n),
      target_week_h = dplyr::lead(week, shift_n),

      target_cases_h = dplyr::lead(dengue_cases, shift_n),
      target_incidence_10000_h = dplyr::lead(dengue_incidence_10000, shift_n),
      target_log_incidence_h = dplyr::lead(target_log_incidence, shift_n),
      target_estimated_population_h = dplyr::lead(estimated_population, shift_n),

      target_outbreak_h = as.integer(target_cases_h >= OUTBREAK_COUNT_THRESHOLD),
      target_large_outbreak_h = as.integer(target_cases_h >= LARGE_OUTBREAK_THRESHOLD)
    ) %>%
    ungroup()
}

make_alert_level <- function(prob) {
  prob <- pmin(pmax(as.numeric(prob), 0), 1)
  case_when(
    is.na(prob) ~ "Low",
    prob < 0.30 ~ "Low",
    prob < 0.50 ~ "Watch",
    prob < 0.70 ~ "Moderate",
    prob < 0.85 ~ "High",
    TRUE ~ "Very high"
  )
}


# ============================================================
# 9. XGBOOST PARAMETER GRIDS
# ============================================================

reg_grid <- expand.grid(
  eta = c(0.03, 0.05),
  max_depth = c(3, 4),
  min_child_weight = c(3, 5),
  subsample = c(0.85),
  colsample_bytree = c(0.85),
  lambda = c(1),
  alpha = c(0.05),
  nrounds = c(400, 500, 600),
  stringsAsFactors = FALSE
)

cls_grid <- expand.grid(
  eta = c(0.03, 0.05),
  max_depth = c(3, 4),
  min_child_weight = c(3, 5),
  subsample = c(0.85),
  colsample_bytree = c(0.85),
  lambda = c(1),
  alpha = c(0.05),
  nrounds = c(400, 500),
  stringsAsFactors = FALSE
)


# ============================================================
# 10. MODEL FITTING FUNCTIONS
# ============================================================

fit_xgb_regressor <- function(train_data, pred_data, features, params) {
  params <- as.list(params)
  mats <- make_matrix(train_data, pred_data, features)

  x_tr <- mats$train
  x_pr <- mats$test

  dtrain <- xgb.DMatrix(
    data = x_tr,
    label = train_data$target_log_incidence_h,
    weight = make_reg_weights(train_data$target_cases_h)
  )

  dtest <- xgb.DMatrix(data = x_pr)

  model <- xgb.train(
    params = list(
      objective = "reg:squarederror",
      eval_metric = "rmse",
      eta = params$eta,
      max_depth = params$max_depth,
      min_child_weight = params$min_child_weight,
      subsample = params$subsample,
      colsample_bytree = params$colsample_bytree,
      lambda = params$lambda,
      alpha = params$alpha
    ),
    data = dtrain,
    nrounds = params$nrounds,
    verbose = 0
  )

  pred_log <- predict(model, dtest)
  pred_cases <- loginc_to_cases(pred_log, pred_data$target_estimated_population_h)

  list(
    model = model,
    pred_log = pred_log,
    pred_cases = pmax(pred_cases, 0),
    feature_names = colnames(x_tr)
  )
}

fit_xgb_classifier <- function(train_data, pred_data, features, params) {
  params <- as.list(params)
  mats <- make_matrix(train_data, pred_data, features)

  x_tr <- mats$train
  x_pr <- mats$test

  y <- train_data$target_outbreak_h

  pos <- sum(y == 1, na.rm = TRUE)
  neg <- sum(y == 0, na.rm = TRUE)

  scale_pos <- ifelse(pos > 0, neg / pos, 1)
  scale_pos <- min(scale_pos, 10)

  dtrain <- xgb.DMatrix(
    data = x_tr,
    label = y,
    weight = make_class_weights(y)
  )

  dtest <- xgb.DMatrix(data = x_pr)

  model <- xgb.train(
    params = list(
      objective = "binary:logistic",
      eval_metric = "logloss",
      eta = params$eta,
      max_depth = params$max_depth,
      min_child_weight = params$min_child_weight,
      subsample = params$subsample,
      colsample_bytree = params$colsample_bytree,
      scale_pos_weight = scale_pos,
      lambda = params$lambda,
      alpha = params$alpha
    ),
    data = dtrain,
    nrounds = params$nrounds,
    verbose = 0
  )

  prob <- predict(model, dtest)
  prob <- pmin(pmax(prob, 0), 1)

  list(
    model = model,
    prob = prob,
    feature_names = colnames(x_tr)
  )
}


# ============================================================
# 11. FEATURE BUILDER FOR A GIVEN HORIZON AND LAG KEEP
# ============================================================

build_horizon_feature_data <- function(horizon,
                                       keep_per_var,
                                       lag_train_end_year,
                                       require_targets = TRUE) {
  df_h_all <- add_horizon_targets(df2, horizon) %>%
    filter(
      !is.na(target_year_h),
      !is.na(target_week_h),
      !is.na(target_estimated_population_h)
    )

  # Lag selection must use rows with observed target outcomes only.
  df_h_for_selection <- df_h_all %>%
    filter(
      !is.na(target_cases_h),
      !is.na(target_log_incidence_h),
      !is.na(target_outbreak_h),
      !is.na(target_large_outbreak_h)
    )

  case_lag_selection <- select_best_lags_for_horizon(
    data = df_h_for_selection,
    base_vars = case_vars,
    max_lag = MAX_LAG_TO_TEST,
    keep_per_var = keep_per_var,
    train_end_year = lag_train_end_year
  )

  env_lag_selection <- select_best_lags_for_horizon(
    data = df_h_for_selection,
    base_vars = env_vars,
    max_lag = MAX_LAG_TO_TEST,
    keep_per_var = keep_per_var,
    train_end_year = lag_train_end_year
  )

  neighbor_lag_selection <- select_best_lags_for_horizon(
    data = df_h_for_selection,
    base_vars = neighbor_vars,
    max_lag = MAX_LAG_TO_TEST,
    keep_per_var = keep_per_var,
    train_end_year = lag_train_end_year
  )

  city_lag_selection <- select_best_lags_for_horizon(
    data = df_h_for_selection,
    base_vars = city_base_vars,
    max_lag = MAX_LAG_TO_TEST,
    keep_per_var = keep_per_var,
    train_end_year = lag_train_end_year
  )

  selected_lag_features <- unique(c(
    case_lag_selection$selected_features,
    env_lag_selection$selected_features,
    neighbor_lag_selection$selected_features,
    city_lag_selection$selected_features
  ))

  lag_report <- bind_rows(
    case_lag_selection$lag_report %>% mutate(group = "case"),
    env_lag_selection$lag_report %>% mutate(group = "environment"),
    neighbor_lag_selection$lag_report %>% mutate(group = "neighbor"),
    city_lag_selection$lag_report %>% mutate(group = "city")
  )

  feature_cols <- unique(c(
    "barangay",
    "week_sin",
    "week_cos",
    static_vars,
    selected_lag_features,
    roll_feature_cols
  ))

  feature_cols <- feature_cols[feature_cols %in% names(df_h_all)]

  feature_cols <- setdiff(
    feature_cols,
    c(
      "target_log_incidence",
      "dengue_incidence_10000",
      "dengue_cases",
      "outbreak_actual",
      "large_outbreak_actual",
      "target_cases_h",
      "target_incidence_10000_h",
      "target_log_incidence_h",
      "target_outbreak_h",
      "target_large_outbreak_h"
    )
  )

  feature_cols <- feature_cols[!str_detect(feature_cols, "geometry|geom|shape|objectid")]
  feature_cols <- unique(feature_cols)

  # Required columns are only the target population and, when training/tuning,
  # observed target outcomes. Feature NAs are intentionally allowed and imputed
  # inside make_matrix(), so prediction rows are not dropped just because a lag
  # or rolling environmental feature is missing.
  required_complete <- c("target_estimated_population_h")

  if (require_targets) {
    required_complete <- unique(c(
      "target_cases_h",
      "target_incidence_10000_h",
      "target_log_incidence_h",
      "target_outbreak_h",
      "target_large_outbreak_h",
      required_complete
    ))
  }

  required_complete <- required_complete[required_complete %in% names(df_h_all)]

  df_h_model <- df_h_all %>%
    arrange(barangay, year, week) %>%
    filter(if_all(all_of(required_complete), ~ !is.na(.x))) %>%
    mutate(
      barangay = as.factor(barangay),
      barangay_classification = if ("barangay_classification" %in% names(.)) {
        as.factor(barangay_classification)
      } else {
        factor("unknown")
      }
    )

  list(
    data = df_h_model,
    features = feature_cols,
    selected_lag_features = selected_lag_features,
    lag_report = lag_report
  )
}


# ============================================================
# 12. TUNE AND TRAIN ONE HORIZON
# ============================================================

run_one_horizon <- function(horizon) {
  set.seed(SEED + horizon)

  cat("\n============================================================\n")
  cat("RUNNING SOFT-GATED XGBOOST HYBRID: H+", horizon, "\n", sep = "")
  cat("============================================================\n")

  default_reg_params <- tibble(
    eta = 0.03,
    max_depth = 4,
    min_child_weight = 5,
    subsample = 0.85,
    colsample_bytree = 0.85,
    lambda = 1,
    alpha = 0.05,
    nrounds = 500
  )

  default_cls_params <- tibble(
    eta = 0.03,
    max_depth = 4,
    min_child_weight = 5,
    subsample = 0.85,
    colsample_bytree = 0.85,
    lambda = 1,
    alpha = 0.05,
    nrounds = 500
  )

  # ----------------------------------------------------------
  # Step 1. Tune number of lags using validation years.
  # ----------------------------------------------------------

  lag_tuning_results <- purrr::map_df(LAG_KEEP_GRID, function(k) {
    cat("\nTuning lag count:", k, "\n")

    feat_obj <- build_horizon_feature_data(
      horizon = horizon,
      keep_per_var = k,
      lag_train_end_year = TRAIN_CORE_END_YEAR
    )

    df_h <- feat_obj$data
    features <- feat_obj$features

    train_core <- df_h %>%
      filter(target_year_h <= TRAIN_CORE_END_YEAR)

    validation <- df_h %>%
      filter(target_year_h %in% VALIDATION_YEARS)

    if (nrow(train_core) == 0 || nrow(validation) == 0 || length(features) == 0) {
      return(tibble(
        horizon = horizon,
        keep_per_var = k,
        score = NA_real_,
        RMSE_raw = NA_real_,
        MAE_raw = NA_real_,
        R2_raw = NA_real_,
        F1 = NA_real_,
        Alert_AUC = NA_real_,
        feature_count = length(features)
      ))
    }

    reg_fit <- fit_xgb_regressor(train_core, validation, features, default_reg_params)
    cls_fit <- fit_xgb_classifier(train_core, validation, features, default_cls_params)

    soft_cases <- make_soft_gate_pred(
      prob = cls_fit$prob,
      reg_cases = reg_fit$pred_cases,
      alpha = SOFT_ALPHA
    )

    metrics <- evaluate_predictions(
      model_name = paste0("Validation lag keep ", k),
      horizon = horizon,
      data = validation,
      pred_cases = soft_cases,
      pred_log = cases_to_loginc(soft_cases, validation$target_estimated_population_h),
      prob = cls_fit$prob
    )

    tibble(
      horizon = horizon,
      keep_per_var = k,
      score = validation_score(metrics),
      RMSE_raw = metrics$RMSE_raw,
      MAE_raw = metrics$MAE_raw,
      R2_raw = metrics$R2_raw,
      F1 = metrics$Outbreak_F1_count_threshold,
      Alert_AUC = metrics$Alert_AUC,
      feature_count = length(features)
    )
  }) %>%
    filter(!is.na(score)) %>%
    arrange(score)

  if (nrow(lag_tuning_results) == 0) {
    stop(paste0("Lag tuning failed for H+", horizon))
  }

  selected_keep <- lag_tuning_results$keep_per_var[1]

  cat("\nSelected keep_per_var for H+", horizon, ": ", selected_keep, "\n", sep = "")

  # ----------------------------------------------------------
  # Step 2. Build validation feature set using selected lag count.
  # ----------------------------------------------------------

  val_feat_obj <- build_horizon_feature_data(
    horizon = horizon,
    keep_per_var = selected_keep,
    lag_train_end_year = TRAIN_CORE_END_YEAR
  )

  val_df <- val_feat_obj$data
  val_features <- val_feat_obj$features

  train_core <- val_df %>%
    filter(target_year_h <= TRAIN_CORE_END_YEAR)

  validation <- val_df %>%
    filter(target_year_h %in% VALIDATION_YEARS)

  if (nrow(train_core) == 0 || nrow(validation) == 0) {
    stop(paste0("Validation split failed for H+", horizon))
  }

  # ----------------------------------------------------------
  # Step 3. Tune regressor hyperparameters.
  # ----------------------------------------------------------

  reg_tuning_results <- purrr::pmap_df(reg_grid, function(
    eta, max_depth, min_child_weight, subsample, colsample_bytree,
    lambda, alpha, nrounds
  ) {
    params <- tibble(
      eta = eta,
      max_depth = max_depth,
      min_child_weight = min_child_weight,
      subsample = subsample,
      colsample_bytree = colsample_bytree,
      lambda = lambda,
      alpha = alpha,
      nrounds = nrounds
    )

    reg_fit <- fit_xgb_regressor(train_core, validation, val_features, params)

    metrics <- evaluate_predictions(
      model_name = "regressor tuning",
      horizon = horizon,
      data = validation,
      pred_cases = reg_fit$pred_cases,
      pred_log = reg_fit$pred_log,
      prob = rep(mean(train_core$target_outbreak_h, na.rm = TRUE), nrow(validation))
    )

    tibble(
      horizon = horizon,
      eta = eta,
      max_depth = max_depth,
      min_child_weight = min_child_weight,
      subsample = subsample,
      colsample_bytree = colsample_bytree,
      lambda = lambda,
      alpha = alpha,
      nrounds = nrounds,
      RMSE_raw = metrics$RMSE_raw,
      MAE_raw = metrics$MAE_raw,
      R2_raw = metrics$R2_raw,
      score = metrics$RMSE_raw + 0.20 * metrics$MAE_raw
    )
  }) %>%
    arrange(score)

  best_reg_params <- reg_tuning_results %>%
    slice(1)

  cat("\nBest regressor params for H+", horizon, ":\n", sep = "")
  print(best_reg_params)

  # ----------------------------------------------------------
  # Step 4. Tune classifier hyperparameters.
  # ----------------------------------------------------------

  cls_tuning_results <- purrr::pmap_df(cls_grid, function(
    eta, max_depth, min_child_weight, subsample, colsample_bytree,
    lambda, alpha, nrounds
  ) {
    params <- tibble(
      eta = eta,
      max_depth = max_depth,
      min_child_weight = min_child_weight,
      subsample = subsample,
      colsample_bytree = colsample_bytree,
      lambda = lambda,
      alpha = alpha,
      nrounds = nrounds
    )

    cls_fit <- fit_xgb_classifier(train_core, validation, val_features, params)

    prob_metrics <- classification_metrics_from_prob(
      actual_outbreak = validation$target_outbreak_h,
      prob = cls_fit$prob,
      threshold = ALERT_PROB_THRESHOLD
    )

    tibble(
      horizon = horizon,
      eta = eta,
      max_depth = max_depth,
      min_child_weight = min_child_weight,
      subsample = subsample,
      colsample_bytree = colsample_bytree,
      lambda = lambda,
      alpha = alpha,
      nrounds = nrounds,
      Alert_AUC = prob_metrics$Alert_AUC,
      Brier_score = prob_metrics$Brier_score,
      Alert_F1 = prob_metrics$Alert_F1,
      Alert_Recall = prob_metrics$Alert_Recall,
      Alert_Precision = prob_metrics$Alert_Precision,
      score = ifelse(is.na(prob_metrics$Alert_AUC), 999, -prob_metrics$Alert_AUC) +
        0.50 * prob_metrics$Brier_score
    )
  }) %>%
    arrange(score)

  best_cls_params <- cls_tuning_results %>%
    slice(1)

  cat("\nBest classifier params for H+", horizon, ":\n", sep = "")
  print(best_cls_params)

  # ----------------------------------------------------------
  # Step 5. Final feature selection using full training period.
  # ----------------------------------------------------------

  final_feat_obj <- build_horizon_feature_data(
    horizon = horizon,
    keep_per_var = selected_keep,
    lag_train_end_year = TRAIN_END_YEAR,
    require_targets = FALSE
  )

  final_df <- final_feat_obj$data
  final_features <- final_feat_obj$features

  train_final <- final_df %>%
    filter(target_year_h <= TRAIN_END_YEAR)

  test_final <- final_df %>%
    filter(
      is_prediction_origin_window(origin_year, origin_week),
      is_prediction_target_window(target_year_h, target_week_h)
    )

  if (nrow(train_final) == 0 || nrow(test_final) == 0) {
    stop(paste0("Final train/test split failed for H+", horizon))
  }

  # ----------------------------------------------------------
  # Step 6. Train final regressor and classifier.
  # ----------------------------------------------------------

  final_reg <- fit_xgb_regressor(
    train_data = train_final,
    pred_data = test_final,
    features = final_features,
    params = best_reg_params
  )

  final_cls <- fit_xgb_classifier(
    train_data = train_final,
    pred_data = test_final,
    features = final_features,
    params = best_cls_params
  )

  final_soft_cases <- make_soft_gate_pred(
    prob = final_cls$prob,
    reg_cases = final_reg$pred_cases,
    alpha = SOFT_ALPHA
  )

  final_soft_log <- cases_to_loginc(
    final_soft_cases,
    test_final$target_estimated_population_h
  )

  final_metrics <- evaluate_predictions(
    model_name = paste0("Soft-gated XGBoost hybrid alpha=", SOFT_ALPHA),
    horizon = horizon,
    data = test_final,
    pred_cases = final_soft_cases,
    pred_log = final_soft_log,
    prob = final_cls$prob
  )

  final_predictions <- test_final %>%
    select(
      barangay,
      year,
      week,
      origin_year,
      origin_week,
      target_year_h,
      target_week_h,
      dengue_cases,
      dengue_incidence_10000,
      target_cases_h,
      target_incidence_10000_h,
      target_log_incidence_h,
      target_estimated_population_h,
      target_outbreak_h,
      target_large_outbreak_h
    ) %>%
    mutate(
      Horizon = paste0("H+", horizon),
      Horizon_number = horizon,
      actual_cases = target_cases_h,
      actual_incidence_10000 = target_incidence_10000_h,
      actual_log_incidence = target_log_incidence_h,
      actual_outbreak = target_outbreak_h,
      xgb_regressor_cases = final_reg$pred_cases,
      xgb_regressor_log_incidence = final_reg$pred_log,
      outbreak_probability = final_cls$prob,
      soft_gated_xgboost_cases = final_soft_cases,
      soft_gated_xgboost_log_incidence = final_soft_log,
      alert_level = make_alert_level(outbreak_probability),
      predicted_outbreak_from_cases = as.integer(soft_gated_xgboost_cases >= OUTBREAK_COUNT_THRESHOLD),
      predicted_outbreak_from_probability = as.integer(outbreak_probability >= ALERT_PROB_THRESHOLD),
      error = soft_gated_xgboost_cases - actual_cases,
      absolute_error = abs(error),
      soft_alpha = SOFT_ALPHA,
      selected_keep_per_var = selected_keep
    )

  reg_importance <- xgb.importance(
    feature_names = final_reg$feature_names,
    model = final_reg$model
  ) %>%
    mutate(
      Horizon = paste0("H+", horizon),
      Horizon_number = horizon,
      Component = "XGBoost regressor"
    )

  cls_importance <- xgb.importance(
    feature_names = final_cls$feature_names,
    model = final_cls$model
  ) %>%
    mutate(
      Horizon = paste0("H+", horizon),
      Horizon_number = horizon,
      Component = "XGBoost classifier"
    )

  selected_settings <- tibble(
    Horizon = paste0("H+", horizon),
    Horizon_number = horizon,
    soft_alpha = SOFT_ALPHA,
    selected_keep_per_var = selected_keep,
    final_feature_count = length(final_features),

    reg_eta = best_reg_params$eta,
    reg_max_depth = best_reg_params$max_depth,
    reg_min_child_weight = best_reg_params$min_child_weight,
    reg_subsample = best_reg_params$subsample,
    reg_colsample_bytree = best_reg_params$colsample_bytree,
    reg_lambda = best_reg_params$lambda,
    reg_alpha = best_reg_params$alpha,
    reg_nrounds = best_reg_params$nrounds,

    cls_eta = best_cls_params$eta,
    cls_max_depth = best_cls_params$max_depth,
    cls_min_child_weight = best_cls_params$min_child_weight,
    cls_subsample = best_cls_params$subsample,
    cls_colsample_bytree = best_cls_params$colsample_bytree,
    cls_lambda = best_cls_params$lambda,
    cls_alpha = best_cls_params$alpha,
    cls_nrounds = best_cls_params$nrounds
  )

  write_csv(
    lag_tuning_results,
    paste0("lag_tuning_H", horizon, "_", OUTPUT_PREFIX, ".csv")
  )

  write_csv(
    reg_tuning_results,
    paste0("regressor_tuning_H", horizon, "_", OUTPUT_PREFIX, ".csv")
  )

  write_csv(
    cls_tuning_results,
    paste0("classifier_tuning_H", horizon, "_", OUTPUT_PREFIX, ".csv")
  )

  write_csv(
    final_feat_obj$lag_report,
    paste0("selected_lag_report_H", horizon, "_", OUTPUT_PREFIX, ".csv")
  )

  write_csv(
    tibble(feature = final_features),
    paste0("final_feature_list_H", horizon, "_", OUTPUT_PREFIX, ".csv")
  )

  cat("\nFinal H+", horizon, " metrics:\n", sep = "")
  print(as.data.frame(final_metrics))

  reg_bundle <- list(
    model = final_reg$model,
    model_family = "standard_barangay_soft_gated_xgboost",
    model_part = "regressor",
    horizon = horizon,
    horizon_label = paste0("H+", horizon),
    feature_cols = final_features,
    matrix_feature_names = final_reg$feature_names,
    selected_keep_per_var = selected_keep,
    best_params = as.data.frame(best_reg_params),
    target = "target_log_incidence_h",
    trained_on_years = paste0("<=", TRAIN_END_YEAR)
  )

  cls_bundle <- list(
    model = final_cls$model,
    model_family = "standard_barangay_soft_gated_xgboost",
    model_part = "classifier",
    horizon = horizon,
    horizon_label = paste0("H+", horizon),
    feature_cols = final_features,
    matrix_feature_names = final_cls$feature_names,
    selected_keep_per_var = selected_keep,
    best_params = as.data.frame(best_cls_params),
    target = "target_outbreak_h",
    alert_probability_threshold = ALERT_PROB_THRESHOLD,
    soft_alpha = SOFT_ALPHA,
    trained_on_years = paste0("<=", TRAIN_END_YEAR)
  )

  saveRDS(reg_bundle, file.path(MODEL_DIR, paste0("h", horizon, "_regressor.rds")))
  saveRDS(cls_bundle, file.path(MODEL_DIR, paste0("h", horizon, "_classifier.rds")))
  saveRDS(
    list(
      feature_cols = final_features,
      regressor_matrix_feature_names = final_reg$feature_names,
      classifier_matrix_feature_names = final_cls$feature_names,
      selected_keep_per_var = selected_keep,
      horizon = horizon,
      horizon_label = paste0("H+", horizon)
    ),
    file.path(MODEL_DIR, paste0("h", horizon, "_feature_spec.rds"))
  )

  list(
    metrics = final_metrics,
    predictions = final_predictions,
    settings = selected_settings,
    reg_importance = reg_importance,
    cls_importance = cls_importance
  )
}


# ============================================================
# 13. RUN H+0 TO H+12
# ============================================================

all_results <- purrr::map(FORECAST_HORIZONS, run_one_horizon)

all_metrics <- purrr::map_df(all_results, "metrics") %>%
  arrange(Horizon_number)

all_predictions <- purrr::map_df(all_results, "predictions") %>%
  arrange(Horizon_number, barangay, year, week)

all_settings <- purrr::map_df(all_results, "settings") %>%
  arrange(Horizon_number)

all_reg_importance <- purrr::map_df(all_results, "reg_importance") %>%
  arrange(Horizon_number, desc(Gain))

all_cls_importance <- purrr::map_df(all_results, "cls_importance") %>%
  arrange(Horizon_number, desc(Gain))


# ============================================================
# 14. SAVE FINAL OUTPUTS
# ============================================================
# App package policy: save only the prediction CSV in OUTPUT.
# Metrics are printed to the console for audit/review and are not saved as CSV.

metric_lookup <- all_metrics %>%
  transmute(
    Horizon_number,
    mae = MAE_raw,
    rmse = RMSE_raw,
    r2 = R2_raw
  )

app_predictions <- all_predictions %>%
  left_join(metric_lookup, by = "Horizon_number") %>%
  mutate(
    mode = "standard",
    model_scope = "barangay",
    horizon = Horizon_number,
    target_year = target_year_h,
    target_week = target_week_h,
    predicted_cases = soft_gated_xgboost_cases,
    predicted_log_incidence = soft_gated_xgboost_log_incidence,
    model_type = "Soft-gated XGBoost hybrid alpha=0.50",
    uses_autocorrelation_features = TRUE
  ) %>%
  arrange(mode, origin_year, origin_week, horizon, barangay)

# Final output safety repair:
# Standard barangay has classifier probabilities. This guarantees alert_level is never blank.
app_predictions <- app_predictions %>%
  mutate(
    predicted_cases = pmax(as.numeric(predicted_cases), 0),
    predicted_cases = ifelse(is.na(predicted_cases), 0, predicted_cases),
    soft_gated_xgboost_cases = ifelse(is.na(soft_gated_xgboost_cases), predicted_cases, soft_gated_xgboost_cases),
    outbreak_probability = pmin(pmax(as.numeric(outbreak_probability), 0), 1),
    outbreak_probability = ifelse(is.na(outbreak_probability), 0, outbreak_probability),
    alert_threshold = ALERT_PROB_THRESHOLD,
    predicted_outbreak_from_cases = as.integer(predicted_cases >= OUTBREAK_COUNT_THRESHOLD),
    predicted_outbreak_from_probability = as.integer(outbreak_probability >= alert_threshold),
    alert_level = make_alert_level(outbreak_probability)
  )


# Row-completion safety net:
# The model should already predict every barangay-origin-horizon row. If a row
# is still missing because of unexpected data completeness issues, keep the app
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

.expected_prediction_keys <- tidyr::crossing(
  tibble(barangay = sort(unique(as.character(df$barangay)))),
  .complete_expected_targets(.expected_origin_calendar_for_completion, FORECAST_HORIZONS)
)

.missing_prediction_keys <- .expected_prediction_keys %>%
  anti_join(
    app_predictions %>%
      transmute(
        barangay = as.character(barangay),
        origin_year = as.integer(origin_year),
        origin_week = as.integer(origin_week),
        horizon = as.integer(horizon),
        target_year = as.integer(target_year),
        target_week = as.integer(target_week)
      ),
    by = c("barangay", "origin_year", "origin_week", "horizon", "target_year", "target_week")
  )

if (nrow(.missing_prediction_keys) > 0) {
  warning("Adding ", nrow(.missing_prediction_keys), " conservative fallback rows so the app has a complete barangay forecast table.")
  .missing_rows <- app_predictions[rep(NA_integer_, nrow(.missing_prediction_keys)), , drop = FALSE]

  .set_if_exists <- function(tbl, col, value) {
    if (col %in% names(tbl)) tbl[[col]] <- value
    tbl
  }

  .missing_rows <- .set_if_exists(.missing_rows, "barangay", .missing_prediction_keys$barangay)
  .missing_rows <- .set_if_exists(.missing_rows, "year", .missing_prediction_keys$origin_year)
  .missing_rows <- .set_if_exists(.missing_rows, "week", .missing_prediction_keys$origin_week)
  .missing_rows <- .set_if_exists(.missing_rows, "origin_year", .missing_prediction_keys$origin_year)
  .missing_rows <- .set_if_exists(.missing_rows, "origin_week", .missing_prediction_keys$origin_week)
  .missing_rows <- .set_if_exists(.missing_rows, "horizon", .missing_prediction_keys$horizon)
  .missing_rows <- .set_if_exists(.missing_rows, "Horizon_number", .missing_prediction_keys$horizon)
  .missing_rows <- .set_if_exists(.missing_rows, "forecast_horizon", .missing_prediction_keys$horizon)
  .missing_rows <- .set_if_exists(.missing_rows, "Horizon", paste0("H+", .missing_prediction_keys$horizon))
  .missing_rows <- .set_if_exists(.missing_rows, "forecast_horizon_label", paste0("H+", .missing_prediction_keys$horizon))
  .missing_rows <- .set_if_exists(.missing_rows, "target_year", .missing_prediction_keys$target_year)
  .missing_rows <- .set_if_exists(.missing_rows, "target_week", .missing_prediction_keys$target_week)
  .missing_rows <- .set_if_exists(.missing_rows, "target_year_h", .missing_prediction_keys$target_year)
  .missing_rows <- .set_if_exists(.missing_rows, "target_week_h", .missing_prediction_keys$target_week)
  .missing_rows <- .set_if_exists(.missing_rows, "predicted_cases", 0)
  .missing_rows <- .set_if_exists(.missing_rows, "soft_gated_xgboost_cases", 0)
  .missing_rows <- .set_if_exists(.missing_rows, "environmental_xgboost_cases", 0)
  .missing_rows <- .set_if_exists(.missing_rows, "outbreak_probability", 0)
  .missing_rows <- .set_if_exists(.missing_rows, "alert_threshold", 0.50)
  .missing_rows <- .set_if_exists(.missing_rows, "predicted_outbreak_from_cases", 0L)
  .missing_rows <- .set_if_exists(.missing_rows, "predicted_outbreak_from_probability", 0L)
  .missing_rows <- .set_if_exists(.missing_rows, "alert_level", "Low")
  .missing_rows <- .set_if_exists(.missing_rows, "display_in_app_default", .missing_prediction_keys$horizon %in% DISPLAY_HORIZONS)

  app_predictions <- bind_rows(app_predictions, .missing_rows)
}

app_predictions <- app_predictions %>%
  arrange(mode, origin_year, origin_week, horizon, barangay)

expected_origin_calendar <- bind_rows(
  tibble(year = 2025L, week = 1:weeks_in_year(2025L)),
  tibble(year = 2026L, week = 1:CURRENT_FORECAST_ORIGIN_WEEK)
)
expected_prediction_rows <- length(unique(df$barangay)) * nrow(expected_origin_calendar) * length(FORECAST_HORIZONS)
actual_prediction_rows <- nrow(app_predictions)
cat("
Expected barangay standard prediction rows:", expected_prediction_rows, "
")
cat("Actual barangay standard prediction rows:", actual_prediction_rows, "
")
if (actual_prediction_rows < expected_prediction_rows) {
  warning("Barangay standard output has fewer rows than expected. Check feature/target completeness messages above.")
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

.prob_from_cases_poisson <- function(pred_cases, threshold_cases = 2) {
  lambda <- suppressWarnings(as.numeric(pred_cases))
  lambda[is.na(lambda) | is.nan(lambda) | is.infinite(lambda) | lambda < 0] <- 0
  threshold_cases <- suppressWarnings(as.numeric(threshold_cases))
  if (length(threshold_cases) == 1) threshold_cases <- rep(threshold_cases, length(lambda))
  threshold_cases[is.na(threshold_cases) | threshold_cases <= 0] <- 1
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

sanitize_barangay_app_predictions <- function(tbl, expected_mode, uses_autocorrelation) {
  if (!"mode" %in% names(tbl)) tbl$mode <- expected_mode
  tbl$mode[is.na(tbl$mode) | stringr::str_squish(as.character(tbl$mode)) == ""] <- expected_mode

  if (!"model_scope" %in% names(tbl)) tbl$model_scope <- "barangay"
  tbl$model_scope[is.na(tbl$model_scope) | stringr::str_squish(as.character(tbl$model_scope)) == ""] <- "barangay"

  actual_candidate <- .coalesce_numeric_cols(
    tbl,
    c("actual_cases", "target_cases_h", "target_cases", "dengue_cases"),
    default = NA_real_
  )
  tbl$actual_cases_available <- !is.na(actual_candidate)

  tbl$predicted_cases <- .coalesce_numeric_cols(
    tbl,
    c(
      "predicted_cases",
      "soft_gated_xgboost_cases",
      "environmental_xgboost_cases",
      "xgb_regressor_cases",
      "pure_xgboost_cases",
      "regressor_cases"
    ),
    default = 0
  )
  tbl$predicted_cases <- pmax(tbl$predicted_cases, 0)

  if ("soft_gated_xgboost_cases" %in% names(tbl)) {
    tbl$soft_gated_xgboost_cases <- .coalesce_numeric_cols(tbl, c("soft_gated_xgboost_cases", "predicted_cases"), 0)
  }
  if ("environmental_xgboost_cases" %in% names(tbl)) {
    tbl$environmental_xgboost_cases <- .coalesce_numeric_cols(tbl, c("environmental_xgboost_cases", "predicted_cases"), 0)
  }
  if ("xgb_regressor_cases" %in% names(tbl)) {
    tbl$xgb_regressor_cases <- .coalesce_numeric_cols(tbl, c("xgb_regressor_cases", "predicted_cases"), 0)
  }

  if (!"alert_threshold" %in% names(tbl)) tbl$alert_threshold <- ALERT_PROB_THRESHOLD
  tbl$alert_threshold <- .coalesce_numeric_cols(tbl, c("alert_threshold"), ALERT_PROB_THRESHOLD)
  tbl$alert_threshold[tbl$alert_threshold <= 0 | tbl$alert_threshold > 1] <- ALERT_PROB_THRESHOLD

  prob_existing <- .coalesce_numeric_cols(tbl, c("outbreak_probability"), default = NA_real_)
  prob_fallback <- .prob_from_cases_poisson(tbl$predicted_cases, OUTBREAK_COUNT_THRESHOLD)
  prob <- dplyr::coalesce(prob_existing, prob_fallback)
  prob[is.na(prob) | is.nan(prob) | is.infinite(prob)] <- 0
  tbl$outbreak_probability <- pmin(pmax(prob, 0), 1)

  tbl$predicted_outbreak_from_cases <- as.integer(tbl$predicted_cases >= OUTBREAK_COUNT_THRESHOLD)
  tbl$predicted_outbreak_from_probability <- as.integer(tbl$outbreak_probability >= tbl$alert_threshold)
  tbl$alert_level <- make_alert_level(tbl$outbreak_probability)
  tbl$alert_level[is.na(tbl$alert_level) | stringr::str_squish(tbl$alert_level) == ""] <- "Low"

  if (!"horizon" %in% names(tbl)) tbl$horizon <- .coalesce_numeric_cols(tbl, c("Horizon_number", "forecast_horizon"), 0)
  tbl$horizon <- .coalesce_numeric_cols(tbl, c("horizon", "Horizon_number", "forecast_horizon"), 0)
  if (!"Horizon_number" %in% names(tbl)) tbl$Horizon_number <- tbl$horizon
  if ("forecast_horizon" %in% names(tbl)) tbl$forecast_horizon <- tbl$horizon

  if ("Horizon" %in% names(tbl)) {
    tbl$Horizon[is.na(tbl$Horizon) | stringr::str_squish(tbl$Horizon) == ""] <- paste0("H+", tbl$horizon[is.na(tbl$Horizon) | stringr::str_squish(tbl$Horizon) == ""])
  }
  if ("forecast_horizon_label" %in% names(tbl)) {
    tbl$forecast_horizon_label[is.na(tbl$forecast_horizon_label) | stringr::str_squish(tbl$forecast_horizon_label) == ""] <- paste0("H+", tbl$horizon[is.na(tbl$forecast_horizon_label) | stringr::str_squish(tbl$forecast_horizon_label) == ""])
  }

  if (!"uses_autocorrelation_features" %in% names(tbl)) tbl$uses_autocorrelation_features <- uses_autocorrelation
  tbl$uses_autocorrelation_features[is.na(tbl$uses_autocorrelation_features)] <- uses_autocorrelation

  tbl$forecast_available <- TRUE
  tbl <- .fill_all_remaining_na_for_app(tbl)
  tbl
}

app_predictions <- sanitize_barangay_app_predictions(app_predictions, expected_mode = "standard", uses_autocorrelation = TRUE)

.na_audit_file <- file.path(OUTPUT_DIR, "forecast_barangay_standard_na_audit.csv")
.na_audit <- tibble::tibble(column = names(app_predictions), na_count = vapply(app_predictions, function(x) sum(is.na(x)), integer(1)))
readr::write_csv(.na_audit, .na_audit_file)
cat("\nNA audit saved to: ", .na_audit_file, "\n", sep = "")
if (any(.na_audit$na_count > 0)) {
  print(.na_audit %>% dplyr::filter(na_count > 0), n = Inf)
  stop("Final app forecast CSV still has NA values. See NA audit above: ", .na_audit_file)
}

prediction_file <- file.path(OUTPUT_DIR, "forecast_barangay_standard.csv")
readr::write_csv(app_predictions, prediction_file)

cat("
============================================================
")
cat("FINAL SOFT-GATED XGBOOST H+0 TO H+12 METRICS
")
cat("============================================================
")
print(as.data.frame(all_metrics))

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
cat("Use predicted_cases or soft_gated_xgboost_cases as the final barangay standard case forecast.
")
cat("Use outbreak_probability as the outbreak probability output.
")
cat("Use alert_level as the user-facing alert category.
")
cat("The final model is Soft-gated XGBoost hybrid with alpha = 0.50.
")
