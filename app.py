# ============================================================
# CEBU CITY DENGUE FORECASTING APP
# Designer version — no black header/table, improved sidebar, no accuracy score
# ============================================================

import html
import json
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Cebu City Dengue Forecasting App",
    page_icon="🦟",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
METADATA_DIR = BASE_DIR / "model_metadata"
OUTPUTS_DIR = BASE_DIR / "outputs"

DATASET_PATH = DATA_DIR / "FINAL_DATASET.xlsx"
SHAPE_ZIP_PATH = DATA_DIR / "cebu_city_barangays.zip"

DISPLAY_HORIZONS = [0, 1, 2, 3, 4, 8, 12]


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800;900&display=swap');

    :root {
        --ink: #111827;
        --muted: #4b5563;
        --soft-muted: #6b7280;
        --purple: #6d28d9;
        --blue: #2563eb;
        --green: #16a34a;
        --red: #dc2626;
        --amber: #f59e0b;
        --panel: rgba(255, 255, 255, 0.72);
        --panel-strong: rgba(255, 255, 255, 0.88);
        --line: rgba(17, 24, 39, 0.10);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        color: var(--ink) !important;
    }

    .stApp {
        background:
            radial-gradient(circle at 10% 8%, rgba(255, 186, 73, 0.44), transparent 28%),
            radial-gradient(circle at 92% 8%, rgba(124, 58, 237, 0.28), transparent 33%),
            radial-gradient(circle at 70% 82%, rgba(20, 184, 166, 0.22), transparent 38%),
            linear-gradient(135deg, #fff7ed 0%, #f8fafc 44%, #eef2ff 100%);
    }

    /* Removes the heavy black top bar and replaces it with a soft aurora strip. */
    header[data-testid="stHeader"] {
        background:
            linear-gradient(90deg, rgba(255, 247, 237, 0.92), rgba(238, 242, 255, 0.92), rgba(236, 253, 245, 0.92)) !important;
        backdrop-filter: blur(18px) !important;
        border-bottom: 1px solid rgba(17, 24, 39, 0.08) !important;
    }

    header[data-testid="stHeader"] * {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }

    [data-testid="stToolbar"] * {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }

    /* App max width */
    .block-container {
        padding-top: 3.4rem !important;
        padding-bottom: 3rem !important;
        max-width: 1480px !important;
    }

    /* ========================= SIDEBAR ========================= */

    section[data-testid="stSidebar"] {
        background:
            radial-gradient(circle at 15% 5%, rgba(109, 40, 217, 0.12), transparent 26%),
            radial-gradient(circle at 85% 20%, rgba(22, 163, 74, 0.11), transparent 30%),
            linear-gradient(180deg, #fff7ed 0%, #f8fafc 46%, #eef2ff 100%) !important;
        border-right: 1px solid rgba(17, 24, 39, 0.10);
        box-shadow: 15px 0 45px rgba(17, 24, 39, 0.06);
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 2rem !important;
    }

    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }

    .sidebar-title-card {
        background: rgba(255,255,255,0.76);
        border: 1px solid rgba(255,255,255,0.92);
        border-radius: 26px;
        padding: 1.1rem 1.15rem;
        box-shadow: 0 16px 38px rgba(17,24,39,0.08);
        margin-bottom: 1rem;
    }

    .sidebar-title {
        font-size: 1.18rem;
        letter-spacing: -0.03em;
        font-weight: 950;
        color: var(--ink);
        margin-bottom: .25rem;
    }

    .sidebar-subtitle {
        color: var(--muted);
        font-size: .86rem;
        line-height: 1.45;
        font-weight: 600;
    }

    .game-chip-row {
        display: flex;
        gap: .45rem;
        flex-wrap: wrap;
        margin-top: .8rem;
    }

    .game-chip {
        background: linear-gradient(135deg, rgba(237,233,254,.95), rgba(220,252,231,.95));
        border: 1px solid rgba(255,255,255,.9);
        color: var(--ink);
        border-radius: 999px;
        padding: .34rem .58rem;
        font-weight: 900;
        font-size: .72rem;
    }

    section[data-testid="stSidebar"] [role="radiogroup"] {
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(255,255,255,0.9);
        border-radius: 24px;
        padding: .85rem .9rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.8), 0 16px 40px rgba(17,24,39,.07);
    }

    section[data-testid="stSidebar"] [data-testid="stRadio"] label {
        background: rgba(255,255,255,0.80);
        border: 1px solid rgba(17,24,39,0.08);
        border-radius: 18px;
        padding: .72rem .8rem;
        margin-bottom: .55rem;
        box-shadow: 0 10px 24px rgba(17,24,39,0.045);
    }

    section[data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: rgba(255,255,255,0.92) !important;
        border: 1px solid rgba(17, 24, 39, 0.12) !important;
        border-radius: 18px !important;
        min-height: 3.1rem !important;
        box-shadow: 0 12px 28px rgba(17,24,39,0.055) !important;
    }

    section[data-testid="stSidebar"] [data-baseweb="select"] * {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }

    div[data-baseweb="popover"],
    div[data-baseweb="popover"] *,
    ul[role="listbox"],
    li[role="option"] {
        background-color: #ffffff !important;
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }

    li[role="option"]:hover {
        background-color: #f3f4f6 !important;
        color: var(--ink) !important;
    }

    .stButton {
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
    }

    .stButton>button {
        width: 96% !important;
        min-height: 3.35rem !important;
        border-radius: 999px !important;
        padding: .9rem 1.25rem !important;
        font-weight: 950 !important;
        font-size: 1rem !important;
        border: 1px solid rgba(17,24,39,.10) !important;
        background:
            linear-gradient(90deg, rgba(255,255,255,.92), rgba(237,233,254,.96), rgba(220,252,231,.92)) !important;
        color: var(--ink) !important;
        box-shadow: 0 18px 42px rgba(109, 40, 217, 0.18), 0 8px 18px rgba(22, 163, 74, 0.10) !important;
    }

    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 22px 48px rgba(109, 40, 217, 0.24), 0 10px 22px rgba(22, 163, 74, 0.12) !important;
    }

    .stButton>button p,
    .stButton>button span,
    .stButton>button div {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }

    .status-card {
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(255,255,255,0.9);
        border-radius: 22px;
        padding: .95rem 1rem;
        box-shadow: 0 14px 34px rgba(17,24,39,0.06);
        margin-top: 1rem;
    }

    .status-line {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: .5rem;
        padding: .34rem 0;
        border-bottom: 1px dashed rgba(17,24,39,.08);
        color: var(--muted);
        font-weight: 700;
        font-size: .88rem;
    }

    .status-line:last-child { border-bottom: none; }
    .status-ok { color: #15803d; font-weight: 950; }
    .status-bad { color: #b91c1c; font-weight: 950; }

    /* ========================= HERO ========================= */

    .hero-card {
        position: relative;
        margin: 1rem 0 1.7rem 0;
        padding: 3rem 3.1rem;
        border-radius: 34px;
        overflow: hidden;
        background:
            radial-gradient(circle at 12% 18%, rgba(255, 183, 77, 0.42), transparent 28%),
            radial-gradient(circle at 88% 16%, rgba(124, 58, 237, 0.24), transparent 32%),
            radial-gradient(circle at 76% 78%, rgba(20, 184, 166, 0.20), transparent 38%),
            rgba(255, 255, 255, 0.70);
        border: 1px solid rgba(255, 255, 255, 0.84);
        box-shadow: 0 24px 80px rgba(17, 24, 39, 0.10);
    }

    .hero-pill {
        display: inline-flex;
        gap: .5rem;
        align-items: center;
        padding: .72rem 1.1rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid rgba(255, 255, 255, 0.9);
        font-size: .88rem;
        font-weight: 850;
        color: #20212a;
        margin-bottom: 2rem;
        box-shadow: 0 12px 32px rgba(17,24,39,.06);
    }

    .hero-title {
        max-width: 1120px;
        font-size: clamp(2.2rem, 4.0vw, 4.1rem);
        line-height: 1.03;
        letter-spacing: -0.065em;
        font-weight: 950;
        color: var(--ink);
        margin: 0;
    }

    .hero-purple {
        color: var(--purple) !important;
        -webkit-text-fill-color: var(--purple) !important;
        text-shadow: 0 14px 42px rgba(109, 40, 217, 0.12);
    }

    .hero-red {
        color: var(--red) !important;
        -webkit-text-fill-color: var(--red) !important;
        text-shadow: 0 12px 40px rgba(220, 38, 38, 0.14);
    }

    .hero-gradient {
        background: linear-gradient(90deg, #2563eb 0%, #0891b2 45%, #16a34a 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-subtitle {
        max-width: 860px;
        margin-top: 1.7rem;
        font-size: 1.08rem;
        line-height: 1.75;
        color: var(--muted);
        font-weight: 600;
    }

    .chip-row {
        display: flex;
        gap: .7rem;
        flex-wrap: wrap;
        margin-top: 1.7rem;
    }

    .chip {
        padding: .72rem 1rem;
        border-radius: 999px;
        background: rgba(255,255,255,.74);
        border: 1px solid rgba(255,255,255,.88);
        color: #252733;
        font-weight: 850;
        font-size: .9rem;
        box-shadow: 0 12px 32px rgba(17, 24, 39, 0.06);
    }

    /* ========================= CARDS + TABLES ========================= */

    .glass-card {
        background: rgba(255, 255, 255, 0.74);
        border: 1px solid rgba(255, 255, 255, 0.86);
        box-shadow: 0 20px 60px rgba(17, 24, 39, 0.08);
        border-radius: 28px;
        padding: 1.65rem;
        margin-bottom: 1rem;
    }

    .mini-label {
        color: #78716c;
        font-size: .75rem;
        text-transform: uppercase;
        letter-spacing: .17em;
        font-weight: 900;
        margin-bottom: .6rem;
    }

    .big-value {
        color: var(--ink);
        font-size: 2.1rem;
        font-weight: 950;
        line-height: 1.05;
        letter-spacing: -0.045em;
        margin-bottom: .5rem;
    }

    .small-note {
        color: var(--muted);
        line-height: 1.6;
        font-size: .95rem;
        font-weight: 600;
    }

    .section-title {
        margin: 1.8rem 0 1rem 0;
        color: var(--ink);
        font-size: 1.65rem;
        letter-spacing: -0.04em;
        font-weight: 950;
    }

    .map-shell {
        border-radius: 26px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,.88);
        box-shadow: 0 18px 60px rgba(15, 23, 42, 0.11);
        background: rgba(255,255,255,.76);
        padding: .7rem;
    }

    .legend-box {
        background: rgba(255,255,255,.74);
        border: 1px solid rgba(255,255,255,.88);
        border-radius: 22px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 16px 38px rgba(17,24,39,.05);
    }

    .legend-pill {
        display: inline-block;
        padding: .45rem .8rem;
        border-radius: 999px;
        margin: .22rem .25rem .22rem 0;
        font-weight: 900;
        font-size: .82rem;
    }

    .low { background:#dcfce7; color:#166534; }
    .watch { background:#fef3c7; color:#92400e; }
    .moderate { background:#ffedd5; color:#9a3412; }
    .high { background:#fee2e2; color:#991b1b; }
    .veryhigh { background:#f3e8ff; color:#6b21a8; }

    .alert-badge {
        display: inline-block;
        border-radius: 999px;
        padding: .35rem .7rem;
        font-size: .83rem;
        font-weight: 900;
    }

    .pretty-table-wrap {
        width: 100%;
        overflow-x: auto;
        border-radius: 24px;
        border: 1px solid rgba(17,24,39,.08);
        background: rgba(255,255,255,.74);
        box-shadow: 0 18px 52px rgba(17,24,39,.07);
        margin: 1rem 0 1.5rem 0;
    }

    table.pretty-table {
        width: 100%;
        border-collapse: collapse;
        color: var(--ink) !important;
        background: transparent;
        overflow: hidden;
    }

    table.pretty-table thead th {
        background: linear-gradient(90deg, rgba(237,233,254,.95), rgba(219,234,254,.95), rgba(220,252,231,.95));
        color: var(--ink) !important;
        font-weight: 950;
        text-align: left;
        padding: .95rem 1rem;
        font-size: .87rem;
        border-bottom: 1px solid rgba(17,24,39,.09);
        white-space: nowrap;
    }

    table.pretty-table tbody td {
        background: rgba(255,255,255,.70);
        color: var(--ink) !important;
        padding: .85rem 1rem;
        font-size: .9rem;
        font-weight: 650;
        border-bottom: 1px solid rgba(17,24,39,.065);
        vertical-align: top;
    }

    table.pretty-table tbody tr:nth-child(even) td {
        background: rgba(248,250,252,.78);
    }

    table.pretty-table tbody tr:hover td {
        background: rgba(254,243,199,.62);
    }

    .footer-note {
        margin-top: 2rem;
        padding: 1.2rem;
        text-align: center;
        color: var(--soft-muted);
        font-size: .9rem;
        font-weight: 650;
    }

    [data-testid="stMetricValue"] {
        color: var(--ink) !important;
        font-weight: 900 !important;
        letter-spacing: -0.045em !important;
    }

    [data-testid="stMetricLabel"] {
        color: #374151 !important;
        font-weight: 750 !important;
    }

    div[data-testid="stDataFrame"] * {
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }


    /* ========================= CUSTOM LOADING CARD ========================= */

    .forecast-loading-card {
        position: relative;
        overflow: hidden;
        border-radius: 30px;
        padding: 1.45rem 1.6rem;
        margin: 1.2rem 0 1.4rem 0;
        background:
            radial-gradient(circle at 10% 20%, rgba(255, 183, 77, 0.32), transparent 30%),
            radial-gradient(circle at 86% 20%, rgba(109, 40, 217, 0.22), transparent 34%),
            radial-gradient(circle at 70% 85%, rgba(20, 184, 166, 0.18), transparent 34%),
            rgba(255, 255, 255, 0.78);
        border: 1px solid rgba(255, 255, 255, 0.92);
        box-shadow: 0 22px 70px rgba(17, 24, 39, 0.10);
    }

    .forecast-loading-card:before {
        content: "";
        position: absolute;
        inset: -80px;
        background: conic-gradient(from 180deg, rgba(109,40,217,.0), rgba(109,40,217,.18), rgba(37,99,235,.18), rgba(20,184,166,.16), rgba(109,40,217,.0));
        animation: forecast-spin 4.2s linear infinite;
        z-index: 0;
    }

    .forecast-loading-card:after {
        content: "";
        position: absolute;
        inset: 2px;
        border-radius: 28px;
        background: rgba(255, 255, 255, 0.72);
        backdrop-filter: blur(18px);
        z-index: 1;
    }

    @keyframes forecast-spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    .forecast-loading-content {
        position: relative;
        z-index: 2;
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 1rem;
        align-items: center;
    }

    .forecast-orb {
        width: 58px;
        height: 58px;
        border-radius: 22px;
        display: grid;
        place-items: center;
        font-size: 1.55rem;
        background: linear-gradient(135deg, #ede9fe, #dbeafe, #dcfce7);
        border: 1px solid rgba(255, 255, 255, 0.92);
        box-shadow: 0 12px 30px rgba(109, 40, 217, 0.16);
        animation: forecast-pulse 1.5s ease-in-out infinite;
    }

    @keyframes forecast-pulse {
        0%, 100% { transform: scale(1); filter: saturate(1); }
        50% { transform: scale(1.06); filter: saturate(1.25); }
    }

    .forecast-loading-title {
        color: var(--ink);
        font-size: 1.2rem;
        font-weight: 950;
        letter-spacing: -0.035em;
        margin-bottom: .25rem;
    }

    .forecast-loading-subtitle {
        color: var(--muted);
        font-weight: 650;
        line-height: 1.45;
        font-size: .95rem;
    }

    .forecast-loading-chips {
        position: relative;
        z-index: 2;
        margin-top: 1rem;
        display: flex;
        flex-wrap: wrap;
        gap: .55rem;
    }

    .forecast-loading-chip {
        border-radius: 999px;
        padding: .48rem .78rem;
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid rgba(17, 24, 39, 0.08);
        color: var(--ink);
        font-size: .78rem;
        font-weight: 900;
        box-shadow: 0 8px 22px rgba(17,24,39,.055);
    }

    div[data-testid="stProgress"] > div {
        background: rgba(17, 24, 39, 0.08) !important;
        border-radius: 999px !important;
        height: 12px !important;
        overflow: hidden !important;
    }

    div[data-testid="stProgress"] > div > div {
        background: linear-gradient(90deg, #6d28d9, #2563eb, #14b8a6, #16a34a) !important;
        border-radius: 999px !important;
    }





    /* ========================= FULL-SCREEN LOADING OVERLAY ========================= */

    .forecast-loading-overlay {
        position: fixed;
        inset: 0;
        z-index: 999999;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        background:
            radial-gradient(circle at 18% 18%, rgba(255, 202, 138, 0.70), transparent 32%),
            radial-gradient(circle at 84% 18%, rgba(124, 58, 237, 0.34), transparent 35%),
            radial-gradient(circle at 72% 82%, rgba(20, 184, 166, 0.24), transparent 36%),
            linear-gradient(135deg, rgba(255, 247, 237, 0.94), rgba(248, 250, 252, 0.94), rgba(238, 242, 255, 0.94));
        backdrop-filter: blur(20px);
    }

    .forecast-loading-overlay-card {
        position: relative;
        overflow: hidden;
        width: min(820px, 92vw);
        border-radius: 38px;
        padding: 2.4rem 2.2rem;
        background:
            radial-gradient(circle at 12% 20%, rgba(255, 183, 77, 0.26), transparent 34%),
            radial-gradient(circle at 88% 16%, rgba(109, 40, 217, 0.20), transparent 34%),
            radial-gradient(circle at 72% 88%, rgba(20, 184, 166, 0.18), transparent 36%),
            rgba(255, 255, 255, 0.88);
        border: 1px solid rgba(255, 255, 255, 0.96);
        box-shadow: 0 34px 100px rgba(17, 24, 39, 0.20);
        text-align: center;
    }

    .forecast-loading-overlay-card:before {
        content: "";
        position: absolute;
        inset: -120px;
        background: conic-gradient(from 180deg, rgba(220,38,38,0), rgba(220,38,38,.13), rgba(109,40,217,.18), rgba(37,99,235,.16), rgba(20,184,166,.15), rgba(220,38,38,0));
        animation: forecast-overlay-spin 4.8s linear infinite;
        z-index: 0;
    }

    .forecast-loading-overlay-card:after {
        content: "";
        position: absolute;
        inset: 3px;
        border-radius: 35px;
        background: rgba(255, 255, 255, 0.76);
        backdrop-filter: blur(18px);
        z-index: 1;
    }

    @keyframes forecast-overlay-spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    .forecast-loading-overlay-content {
        position: relative;
        z-index: 2;
    }

    .forecast-loading-orb-wrap {
        display: flex;
        justify-content: center;
        margin-bottom: 1.25rem;
    }

    .forecast-loading-orb {
        width: 96px;
        height: 96px;
        border-radius: 32px;
        display: grid;
        place-items: center;
        font-size: 2.05rem;
        background: linear-gradient(135deg, #fee2e2, #ede9fe, #dbeafe, #dcfce7);
        border: 1px solid rgba(255, 255, 255, 0.98);
        box-shadow: 0 18px 52px rgba(109, 40, 217, 0.20);
        animation: forecast-overlay-pulse 1.25s ease-in-out infinite;
    }

    @keyframes forecast-overlay-pulse {
        0%, 100% { transform: translateY(0) scale(1); filter: saturate(1); }
        50% { transform: translateY(-4px) scale(1.045); filter: saturate(1.25); }
    }

    .forecast-loading-overlay-title {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        font-size: clamp(1.75rem, 3vw, 2.65rem);
        line-height: 1.05;
        letter-spacing: -0.06em;
        font-weight: 950;
        margin-bottom: .75rem;
    }

    .forecast-loading-overlay-subtitle {
        color: #4b5563 !important;
        -webkit-text-fill-color: #4b5563 !important;
        max-width: 650px;
        margin: 0 auto 1.35rem auto;
        font-size: 1.02rem;
        line-height: 1.65;
        font-weight: 650;
    }

    .forecast-loading-overlay-steps {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: .78rem;
        margin-top: 1rem;
    }

    .forecast-loading-overlay-step {
        padding: .9rem .85rem;
        border-radius: 20px;
        background: linear-gradient(135deg, rgba(255,255,255,0.94), rgba(240,253,244,0.84));
        border: 1px solid rgba(17, 24, 39, 0.07);
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        font-weight: 900;
        font-size: .88rem;
        box-shadow: 0 12px 26px rgba(17,24,39,0.055);
    }

    .forecast-loading-overlay-progress {
        height: 13px;
        border-radius: 999px;
        background: rgba(17, 24, 39, 0.08);
        overflow: hidden;
        margin-top: 1.45rem;
    }

    .forecast-loading-overlay-progress-bar {
        height: 100%;
        width: 38%;
        border-radius: 999px;
        background: linear-gradient(90deg, #dc2626, #7c3aed, #2563eb, #14b8a6, #16a34a);
        animation: forecast-overlay-slide 1.15s ease-in-out infinite alternate;
    }

    @keyframes forecast-overlay-slide {
        0% { transform: translateX(-25%); width: 35%; }
        100% { transform: translateX(175%); width: 46%; }
    }

    @media (max-width: 850px) {
        .forecast-loading-overlay-steps {
            grid-template-columns: 1fr;
        }
    }


    /* ========================= NO WHITE TEXT SAFETY PATCH =========================
       Keeps every normal Streamlit/app label dark and readable. Special hero/alert
       classes are restored immediately after this block. */
    .stApp p,
    .stApp div,
    .stApp span,
    .stApp label,
    .stApp li,
    .stApp td,
    .stApp th,
    .stApp button,
    .stApp [data-testid="stMarkdownContainer"],
    .stApp [data-testid="stMarkdownContainer"] *,
    .stApp [data-testid="stMetricLabel"],
    .stApp [data-testid="stMetricValue"],
    .stApp [data-testid="stMetricDelta"],
    .stApp [data-testid="stWidgetLabel"],
    .stApp [data-baseweb="radio"] *,
    .stApp [data-baseweb="select"] *,
    section[data-testid="stSidebar"] * {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    /* Restore intentional hero colors after the safety patch. */
    .hero-purple,
    .hero-purple * {
        color: #6d28d9 !important;
        -webkit-text-fill-color: #6d28d9 !important;
    }

    .hero-red,
    .hero-red * {
        color: #dc2626 !important;
        -webkit-text-fill-color: #dc2626 !important;
    }

    .hero-gradient,
    .hero-gradient * {
        background: linear-gradient(90deg, #2563eb 0%, #16a34a 100%) !important;
        -webkit-background-clip: text !important;
        background-clip: text !important;
        color: transparent !important;
        -webkit-text-fill-color: transparent !important;
    }

    /* Restore alert/legend readable colors. */
    .low { background:#dcfce7 !important; color:#166534 !important; -webkit-text-fill-color:#166534 !important; }
    .watch { background:#fef3c7 !important; color:#92400e !important; -webkit-text-fill-color:#92400e !important; }
    .moderate { background:#ffedd5 !important; color:#9a3412 !important; -webkit-text-fill-color:#9a3412 !important; }
    .high { background:#fee2e2 !important; color:#991b1b !important; -webkit-text-fill-color:#991b1b !important; }
    .veryhigh { background:#f3e8ff !important; color:#6b21a8 !important; -webkit-text-fill-color:#6b21a8 !important; }

    /* Keep custom light tables readable, not black/white. */
    .pretty-table-wrap,
    .pretty-table,
    .pretty-table thead,
    .pretty-table tbody,
    .pretty-table tr,
    .pretty-table th,
    .pretty-table td {
        background: transparent !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    .pretty-table th {
        background: linear-gradient(90deg, rgba(237,233,254,.92), rgba(220,252,231,.85)) !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    .pretty-table td {
        background: rgba(255,255,255,.74) !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    /* Loading card text must stay dark. */
    .loading-card,
    .loading-card *,
    .loading-step,
    .loading-step * {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# BASIC HELPERS
# ============================================================

def standardize_barangay_name(value: Any) -> str:
    return str(value).upper().strip()


def clean_alert(alert: Any) -> str:
    return str(alert).lower().replace("_", " ").strip()


def alert_rank(alert: Any) -> int:
    alert_clean = clean_alert(alert)
    ranks = {
        "low": 1,
        "watch": 2,
        "warning": 2,
        "moderate": 3,
        "high": 4,
        "very high": 5,
    }
    return ranks.get(alert_clean, 0)


def alert_color(alert: Any) -> str:
    alert_clean = clean_alert(alert)

    if alert_clean == "low":
        return "#22c55e"
    if alert_clean in ["watch", "warning"]:
        return "#facc15"
    if alert_clean == "moderate":
        return "#fb923c"
    if alert_clean == "high":
        return "#ef4444"
    if alert_clean == "very high":
        return "#a855f7"

    return "#cbd5e1"


def alert_badge_class(alert: Any) -> str:
    alert_clean = clean_alert(alert)

    if alert_clean == "low":
        return "low"
    if alert_clean in ["watch", "warning"]:
        return "watch"
    if alert_clean == "moderate":
        return "moderate"
    if alert_clean == "high":
        return "high"
    if alert_clean == "very high":
        return "veryhigh"

    return "watch"


def fmt_number(value: Any, digits: int = 1) -> str:
    try:
        if value is None or pd.isna(value):
            return "—"
        return f"{float(value):,.{digits}f}"
    except Exception:
        return "—"


def fmt_percent(value: Any, digits: int = 1) -> str:
    try:
        if value is None or pd.isna(value):
            return "—"
        return f"{float(value) * 100:.{digits}f}%"
    except Exception:
        return "—"


def make_prediction_range(predicted_cases: Any, error_value: Any) -> str:
    try:
        if predicted_cases is None or pd.isna(predicted_cases):
            return "Not available"

        pred = float(predicted_cases)

        if error_value is None or pd.isna(error_value):
            rounded = int(round(max(0, pred)))
            return f"{rounded} case(s)"

        err = abs(float(error_value))

        lower = max(0, pred - err)
        upper = max(0, pred + err)

        lower_i = int(round(lower))
        upper_i = int(round(upper))

        if lower_i == upper_i:
            return f"{lower_i} case(s)"

        return f"{lower_i}–{upper_i} cases"

    except Exception:
        return "Not available"


def horizon_label(horizon_result: Dict[str, Any]) -> str:
    h = int(horizon_result.get("horizon", horizon_result.get("forecast_horizon", 0)))

    labels = {
        0: "Selected week",
        1: "1 week after",
        2: "2 weeks after",
        3: "3 weeks after",
        4: "4 weeks after",
        8: "8 weeks after",
        12: "12 weeks after",
    }

    return labels.get(h, f"{h} weeks after")


def horizon_sort_key(horizon_result: Dict[str, Any]) -> int:
    try:
        return int(horizon_result.get("horizon", horizon_result.get("forecast_horizon", 999)))
    except Exception:
        return 999


def ensure_probability(row: Dict[str, Any]) -> Optional[float]:
    for key in [
        "outbreak_probability",
        "estimated_outbreak_probability",
        "probability",
        "predicted_risk",
        "mean_outbreak_probability",
    ]:
        if key in row and row[key] is not None:
            try:
                value = float(row[key])
                return min(max(value, 0.0), 1.0)
            except Exception:
                pass

    return None


def get_intervention_plan(alert_level: Any) -> List[str]:
    alert = clean_alert(alert_level)

    if "above outbreak" in alert:
        alert = "high"
    elif "below outbreak" in alert:
        alert = "low"

    if alert == "low":
        return [
            "Continue routine weekly dengue monitoring.",
            "Maintain regular clean-up activities.",
            "Remind households to remove standing water and cover water containers.",
        ]

    if alert in ["watch", "warning"]:
        return [
            "Increase dengue information reminders in the barangay.",
            "Inspect common mosquito breeding sites.",
            "Coordinate clean-up reminders with purok or community leaders.",
        ]

    if alert == "moderate":
        return [
            "Conduct targeted source reduction in high-risk sitios.",
            "Inspect schools, markets, drainage areas, and construction sites.",
            "Prepare health-center monitoring for possible increases in dengue cases.",
        ]

    if alert == "high":
        return [
            "Prioritize barangay vector-control operations.",
            "Intensify larval source reduction and household clean-up checks.",
            "Coordinate with city health staff for focused hotspot response.",
        ]

    if alert == "very high":
        return [
            "Activate urgent barangay dengue response.",
            "Deploy intensified vector surveillance and source reduction.",
            "Coordinate with city health authorities for outbreak response planning.",
        ]

    return [
        "Review the forecast output and verify available case and environmental data.",
        "Continue routine surveillance and community dengue prevention reminders.",
    ]


def interventions_to_html(items: List[str]) -> str:
    safe_items = [html.escape(str(item)) for item in items]
    return "<ul>" + "".join([f"<li>{item}</li>" for item in safe_items]) + "</ul>"


def render_alert_legend() -> None:
    st.markdown(
        """
        <div class="legend-box">
            <div class="mini-label">Map legend</div>
            <span class="legend-pill low">Low</span>
            <span class="legend-pill watch">Watch</span>
            <span class="legend-pill moderate">Moderate</span>
            <span class="legend-pill high">High</span>
            <span class="legend-pill veryhigh">Very high</span>
            <div class="small-note" style="margin-top:.55rem;">
                Colors represent dengue alert levels generated from model outputs.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(title: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="mini-label">{html.escape(title)}</div>
            <div class="big-value">{html.escape(value)}</div>
            <div class="small-note">{html.escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_pretty_table(df: pd.DataFrame, max_rows: int = 120) -> None:
    if df.empty:
        st.info("No rows to display.")
        return

    display_df = df.head(max_rows).copy()

    header_html = "".join(
        f"<th>{html.escape(str(col))}</th>" for col in display_df.columns
    )

    body_rows = []
    for _, row in display_df.iterrows():
        cells = "".join(
            f"<td>{html.escape(str(row[col]))}</td>" for col in display_df.columns
        )
        body_rows.append(f"<tr>{cells}</tr>")

    caption = ""
    if len(df) > max_rows:
        caption = f"<div class='small-note' style='padding:.85rem 1rem;'>Showing first {max_rows} of {len(df)} rows.</div>"

    st.markdown(
        f"""
        <div class="pretty-table-wrap">
            <table class="pretty-table">
                <thead><tr>{header_html}</tr></thead>
                <tbody>{''.join(body_rows)}</tbody>
            </table>
            {caption}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================

# CSV FORECAST OUTPUT HELPERS
# ============================================================

FORECAST_FILE_MAP = {
    "standard": {
        "barangay": OUTPUTS_DIR / "forecast_barangay_standard.csv",
        "city": OUTPUTS_DIR / "forecast_city_standard.csv",
    },
    "environmental_only": {
        "barangay": OUTPUTS_DIR / "forecast_barangay_environmental_only.csv",
        "city": OUTPUTS_DIR / "forecast_city_environmental_only.csv",
    },
}

MODE_LABELS = {
    "standard": "Standard model — uses recent dengue case data",
    "environmental_only": "Environmental-only model — use when recent case data are unavailable",
}

MODE_SHORT = {
    "standard": "Standard",
    "environmental_only": "Environmental-only",
}


def mode_label_from_key(mode: str) -> str:
    return MODE_LABELS.get(mode, str(mode).replace("_", " ").title())


def mode_short_label(mode: str) -> str:
    return MODE_SHORT.get(mode, str(mode).replace("_", " ").title())


def clean_column_name(col: Any) -> str:
    """Normalize CSV headers without destroying separate horizon fields.

    Important: R outputs may contain both `horizon` / `forecast_horizon`
    as numeric fields and `Horizon` as a text label like `H+1`. A simple
    lowercase cleaner turns both `horizon` and `Horizon` into the same name,
    which collapses H+1/H+2 labels into the numeric horizon column and makes
    every horizon read as 0. This is why only the Selected week tab appears.
    """
    raw = str(col).strip()

    # Preserve the user-facing R label column separately from numeric horizon.
    if raw == "Horizon":
        return "horizon_label"

    text = re.sub(r"[^0-9A-Za-z]+", "_", raw)
    text = re.sub(r"_+", "_", text).strip("_").lower()
    return text


def coalesce_series(df: pd.DataFrame, candidates: List[str], default: Any = None) -> pd.Series:
    """Return the first non-missing value across possible column names.

    Some CSVs can create duplicate column names after normalization, for example
    `MAE_raw` and `mae raw` both becoming `mae_raw`. In pandas, df[col]
    returns a DataFrame when duplicate names exist, and later numeric conversion
    can fail with: 'DataFrame' object has no attribute 'dtype'. This helper
    safely collapses duplicate-name matches row-wise before coalescing.
    """
    out = pd.Series([pd.NA] * len(df), index=df.index)
    for col in candidates:
        if col in df.columns:
            value = df.loc[:, df.columns == col]
            if isinstance(value, pd.DataFrame):
                if value.shape[1] == 1:
                    value = value.iloc[:, 0]
                else:
                    value = value.bfill(axis=1).iloc[:, 0]
            out = out.combine_first(value)
    if default is not None:
        out = out.fillna(default)
    return out


def collapse_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse duplicate column names by taking the first non-missing value per row."""
    if not df.columns.duplicated().any():
        return df

    collapsed = {}
    for col in dict.fromkeys(df.columns):
        value = df.loc[:, df.columns == col]
        if isinstance(value, pd.DataFrame):
            if value.shape[1] == 1:
                collapsed[col] = value.iloc[:, 0]
            else:
                collapsed[col] = value.bfill(axis=1).iloc[:, 0]
        else:
            collapsed[col] = value

    return pd.DataFrame(collapsed, index=df.index)


def as_numeric_series(series: pd.Series, default: Optional[float] = None) -> pd.Series:
    out = pd.to_numeric(series, errors="coerce")
    if default is not None:
        out = out.fillna(default)
    return out


def parse_horizon_to_int(value: Any) -> Optional[int]:
    """Parse horizon values from 0, "0", "H+0", "H0", or "Selected week" into int.

    This prevents the app from saying a horizon is missing when the city CSV and
    barangay CSV store the same horizon with slightly different types/labels.
    """
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().lower()
    if text in ["selected week", "same week", "current week"]:
        return 0
    match = re.search(r"-?\d+", text)
    if match:
        try:
            return int(match.group(0))
        except Exception:
            return None
    return None


def force_horizon_int(df: pd.DataFrame) -> pd.DataFrame:
    """Create a reliable integer horizon column, preserving the public name `horizon`.

    Important fix:
    For barangay CSVs, the app may already have a temporary `horizon` column
    that was created from a default/fallback value during normalization. If we
    read that column first, all barangay rows can incorrectly become horizon 0.
    So we intentionally prioritize the original R output columns:
        Horizon_number -> forecast_horizon -> forecast_horizon_label/Horizon -> horizon
    """
    df = df.copy()

    candidate_cols = [
        "horizon_number",
        "forecast_horizon",
        "forecast_horizon_label",
        "horizon_label",
        "horizon",
    ]

    parsed = pd.Series([pd.NA] * len(df), index=df.index)

    for col in candidate_cols:
        if col not in df.columns:
            continue

        value = df.loc[:, df.columns == col]
        if isinstance(value, pd.DataFrame):
            value = value.bfill(axis=1).iloc[:, 0]

        candidate = value.apply(parse_horizon_to_int)
        parsed = parsed.combine_first(candidate)

    df["horizon"] = pd.to_numeric(parsed, errors="coerce").fillna(-1).astype(int)
    return df


def normalize_forecast_df(df: pd.DataFrame, mode: str, scope: str) -> pd.DataFrame:
    df = df.copy()
    df.columns = [clean_column_name(c) for c in df.columns]
    df = collapse_duplicate_columns(df)

    df["mode"] = mode
    df["model_scope"] = scope

    df["origin_year"] = as_numeric_series(
        coalesce_series(df, ["origin_year", "year", "origin_year_h"], default=0),
        default=0,
    ).astype(int)
    df["origin_week"] = as_numeric_series(
        coalesce_series(df, ["origin_week", "week", "origin_week_h"], default=0),
        default=0,
    ).astype(int)

    # Temporary horizon value only; the final `force_horizon_int()` pass below
    # reparses the original R horizon columns in the safest order.
    df["horizon"] = as_numeric_series(
        coalesce_series(df, ["horizon_number", "forecast_horizon", "horizon"], default=0),
        default=0,
    ).astype(int)

    df["forecast_horizon_label"] = coalesce_series(
        df,
        ["forecast_horizon_label", "horizon_label", "horizon_name"],
        default="",
    ).astype(str)
    blank_label = df["forecast_horizon_label"].str.strip().isin(["", "nan", "None"])
    df.loc[blank_label, "forecast_horizon_label"] = "H+" + df.loc[blank_label, "horizon"].astype(str)

    df["target_year"] = as_numeric_series(
        coalesce_series(df, ["target_year", "target_year_h"], default=0),
        default=0,
    ).astype(int)
    df["target_week"] = as_numeric_series(
        coalesce_series(df, ["target_week", "target_week_h"], default=0),
        default=0,
    ).astype(int)

    df["predicted_cases"] = as_numeric_series(
        coalesce_series(
            df,
            [
                "predicted_cases",
                "total_predicted_cases",
                "soft_gated_xgboost_cases",
                "environmental_xgboost_cases",
                "pure_lightgbm_cases",
                "environmental_lightgbm_cases",
                "xgb_regressor_cases",
                "lightgbm_cases",
                "regressor_cases",
            ],
            default=0,
        ),
        default=0,
    ).clip(lower=0)

    df["outbreak_probability"] = as_numeric_series(
        coalesce_series(
            df,
            [
                "outbreak_probability",
                "estimated_outbreak_probability",
                "probability",
                "predicted_risk",
                "mean_outbreak_probability",
            ],
            default=0,
        ),
        default=0,
    ).clip(lower=0, upper=1)

    df["alert_level"] = coalesce_series(
        df,
        ["alert_level", "alert_status", "city_status", "alert_level_from_cases"],
        default="Low",
    ).astype(str)
    df["alert_level"] = df["alert_level"].replace({"": "Low", "nan": "Low", "None": "Low"})

    df["mae"] = as_numeric_series(coalesce_series(df, ["mae", "mae_raw", "overall_mae"], default=0), default=0)
    df["rmse"] = as_numeric_series(coalesce_series(df, ["rmse", "rmse_raw"], default=0), default=0)
    df["r2"] = as_numeric_series(coalesce_series(df, ["r2", "r2_raw"], default=0), default=0)

    if scope == "barangay":
        if "barangay" not in df.columns:
            df["barangay"] = "UNKNOWN"
        df["barangay"] = df["barangay"].apply(standardize_barangay_name)

    if scope == "city":
        df["city_outbreak_threshold_cases"] = as_numeric_series(
            coalesce_series(df, ["city_outbreak_threshold_cases", "outbreak_threshold_cases"], default=0),
            default=0,
        )

    df["display_in_app_default"] = coalesce_series(df, ["display_in_app_default"], default=True)

    # Final safety pass: guarantee the horizon is an integer parsed from either
    # numeric horizon columns or label columns like H+1. This is the key fix for
    # false "This horizon is missing" messages.
    df = force_horizon_int(df)

    return df


@st.cache_data(show_spinner=False)
def load_forecast_csv(path_text: str, mode: str, scope: str) -> Optional[pd.DataFrame]:
    path = Path(path_text)
    if not path.exists():
        return None
    try:
        return normalize_forecast_df(pd.read_csv(path), mode=mode, scope=scope)
    except Exception as exc:
        st.error(f"Could not read `{path.name}`.")
        st.code(str(exc))
        return None


@st.cache_data(show_spinner=False)
def load_all_forecasts() -> Dict[str, Dict[str, Optional[pd.DataFrame]]]:
    out: Dict[str, Dict[str, Optional[pd.DataFrame]]] = {}
    for mode, files in FORECAST_FILE_MAP.items():
        out[mode] = {}
        for scope, path in files.items():
            out[mode][scope] = load_forecast_csv(str(path), mode, scope)
    return out


@st.cache_data(show_spinner=False)
def load_barangay_shapefile() -> Optional[gpd.GeoDataFrame]:
    if not SHAPE_ZIP_PATH.exists():
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(SHAPE_ZIP_PATH, "r") as zip_ref:
            zip_ref.extractall(tmpdir)

        shp_files = list(Path(tmpdir).glob("*.shp"))
        if not shp_files:
            return None

        gdf = gpd.read_file(shp_files[0])
        gdf.columns = [str(c).lower().strip() for c in gdf.columns]

        possible_name_columns = [
            "barangay", "brgy", "name", "adm4_en", "adm4_name",
            "bgy_name", "barangay_n", "brgy_name",
        ]

        name_col = next((col for col in possible_name_columns if col in gdf.columns), None)
        if name_col is None:
            return None

        gdf["barangay"] = gdf[name_col].apply(standardize_barangay_name)

        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326, allow_override=True)
        else:
            gdf = gdf.to_crs(epsg=4326)

        return gdf[["barangay", "geometry"]].copy()


# ============================================================
# DISPLAY + MAP HELPERS FOR CSV ROWS
# ============================================================


def forecast_label_from_horizon(horizon: int) -> str:
    labels = {
        0: "Selected week",
        1: "1 week from now",
        2: "2 weeks from now",
        3: "3 weeks from now",
        4: "4 weeks from now",
        8: "8 weeks from now",
        12: "12 weeks from now",
    }
    return labels.get(int(horizon), f"{int(horizon)} weeks from now")


def add_barangay_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["predicted_cases_display"] = df["predicted_cases"].apply(lambda x: fmt_number(x, 2))
    df["probability_display"] = df["outbreak_probability"].apply(lambda x: fmt_percent(x, 1))
    df["selected_error_value"] = df["mae"].fillna(0)
    df["range_basis"] = "Predicted cases ± MAE"
    df["predicted_case_range"] = df.apply(
        lambda row: make_prediction_range(row["predicted_cases"], row["selected_error_value"]),
        axis=1,
    )
    df["target_period"] = df.apply(
        lambda row: f"{forecast_label_from_horizon(row['horizon'])} · {int(row['target_year'])} W{int(row['target_week'])}",
        axis=1,
    )
    df["intervention_html"] = df["alert_level"].apply(lambda a: interventions_to_html(get_intervention_plan(a)))
    df["recommended_intervention"] = df["alert_level"].apply(lambda a: " ".join(get_intervention_plan(a)))
    df["alert_rank"] = df["alert_level"].apply(alert_rank)
    return df


def add_city_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["selected_error_value"] = df["mae"].fillna(0)
    df["range_basis"] = "Predicted cases ± MAE"
    df["predicted_case_range"] = df.apply(
        lambda row: make_prediction_range(row["predicted_cases"], row["selected_error_value"]),
        axis=1,
    )
    df["probability_display"] = df["outbreak_probability"].apply(lambda x: fmt_percent(x, 1))
    return df


def create_barangay_prediction_map(shape_gdf: gpd.GeoDataFrame, barangay_rows: pd.DataFrame) -> folium.Map:
    barangay_rows = add_barangay_display_columns(barangay_rows)
    map_gdf = shape_gdf.merge(barangay_rows, on="barangay", how="left")

    fill_defaults = {
        "predicted_cases": 0,
        "predicted_cases_display": "0.00",
        "probability_display": "—",
        "alert_level": "Unknown",
        "predicted_case_range": "Not available",
        "range_basis": "Predicted cases ± MAE",
        "intervention_html": "<ul><li>No recommendation available.</li></ul>",
        "target_period": "—",
    }

    for col, val in fill_defaults.items():
        if col not in map_gdf.columns:
            map_gdf[col] = val
        else:
            map_gdf[col] = map_gdf[col].fillna(val)

    m = folium.Map(
        location=[10.3157, 123.8854],
        zoom_start=11,
        tiles="CartoDB positron",
        control_scale=True,
    )

    def style_function(feature):
        alert = feature["properties"].get("alert_level", "Unknown")
        return {
            "fillColor": alert_color(alert),
            "color": "#ffffff",
            "weight": 1,
            "fillOpacity": 0.74,
        }

    def highlight_function(feature):
        return {"color": "#111827", "weight": 3, "fillOpacity": 0.90}

    tooltip = folium.GeoJsonTooltip(
        fields=["barangay", "predicted_case_range", "probability_display", "alert_level"],
        aliases=["Barangay:", "Predicted case range:", "Outbreak probability:", "Alert level:"],
        sticky=True,
        style=(
            "background-color: rgba(255,255,255,0.96); color: #111827; "
            "font-family: Inter, Arial; font-size: 13px; padding: 10px; "
            "border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.12);"
        ),
    )

    popup = folium.GeoJsonPopup(
        fields=[
            "barangay", "target_period", "predicted_cases_display", "predicted_case_range",
            "range_basis", "probability_display", "alert_level", "intervention_html",
        ],
        aliases=[
            "Barangay:", "Forecast period:", "Predicted cases:", "Predicted case range:",
            "Range based on:", "Outbreak probability:", "Alert level:", "Recommended interventions:",
        ],
        localize=True,
        labels=True,
        max_width=430,
    )

    folium.GeoJson(
        map_gdf,
        name="Barangay dengue forecast",
        style_function=style_function,
        highlight_function=highlight_function,
        popup=popup,
        tooltip=tooltip,
    ).add_to(m)

    return m


# ============================================================
# HERO
# ============================================================

def hero() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-pill">🦟 Cebu City Dengue Forecasting App</div>
            <h1 class="hero-title">
                <span class="hero-purple">View</span>
                <span class="hero-red">dengue forecasts</span>
                <span class="hero-purple">across</span>
                <span class="hero-gradient">all planning horizons.</span>
            </h1>
            <div class="hero-subtitle">
                Select an origin week and prediction mode, then click Predict. The app reads the saved CSV outputs
                and displays barangay intensity maps across forecast horizons: selected week, +1, +2, +3, +4, +8, and +12 weeks.
            </div>
            <div class="chip-row">
                <div class="chip">Barangay shapefile map</div>
                <div class="chip">Citywide forecast</div>
                <div class="chip">All horizon tabs</div>
                <div class="chip">Predicted case ranges</div>
                <div class="chip">Alert levels</div>
                <div class="chip">Predict button workflow</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MAIN APP
# ============================================================

hero()

forecasts = load_all_forecasts()
shape_gdf = load_barangay_shapefile()

if "forecast_loaded" not in st.session_state:
    st.session_state["forecast_loaded"] = False
if "forecast_selection_key" not in st.session_state:
    st.session_state["forecast_selection_key"] = None

available_modes = []
for mode in ["standard", "environmental_only"]:
    if forecasts.get(mode, {}).get("barangay") is not None and forecasts.get(mode, {}).get("city") is not None:
        available_modes.append(mode)

with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-title-card">
            <div class="sidebar-title">Forecast Command Center</div>
            <div class="sidebar-subtitle">
                Choose a saved model mode and origin week, then press Predict to display the saved forecast outputs.
            </div>
            <div class="game-chip-row">
                <span class="game-chip">CSV</span>
                <span class="game-chip">2025–2026</span>
                <span class="game-chip">PREDICT</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not available_modes:
        st.error("No complete forecast CSV set was found. Each mode needs both city and barangay CSV files.")
        selected_mode = None
        selected_year = None
        selected_week = None
        barangay_df = None
        city_df = None
    else:
        mode_options = {mode_label_from_key(m): m for m in available_modes}
        prediction_mode_label = st.radio("Prediction mode", list(mode_options.keys()), index=0)
        selected_mode = mode_options[prediction_mode_label]

        barangay_df = forecasts[selected_mode]["barangay"]
        city_df = forecasts[selected_mode]["city"]

        valid_pairs = barangay_df[["origin_year", "origin_week"]].drop_duplicates()
        city_pairs = city_df[["origin_year", "origin_week"]].drop_duplicates()
        valid_pairs = valid_pairs.merge(city_pairs, on=["origin_year", "origin_week"], how="inner")
        valid_pairs = valid_pairs[valid_pairs["origin_year"].isin([2025, 2026])]

        if valid_pairs.empty:
            st.error("No complete 2025–2026 origin weeks were found in both city and barangay CSV files.")
            selected_year = None
            selected_week = None
        else:
            available_years = sorted(valid_pairs["origin_year"].unique().tolist())
            selected_year = st.selectbox("Origin year", available_years, index=len(available_years) - 1)

            available_weeks = sorted(
                valid_pairs.loc[valid_pairs["origin_year"] == selected_year, "origin_week"].unique().tolist()
            )
            selected_week = st.selectbox("Origin week", available_weeks, index=len(available_weeks) - 1)

            current_selection_key = f"{selected_mode}|{int(selected_year)}|{int(selected_week)}"
            if st.session_state.get("forecast_selection_key") != current_selection_key:
                st.session_state["forecast_selection_key"] = current_selection_key
                st.session_state["forecast_loaded"] = False

            predict_clicked = st.button(
                "Predict Dengue Cases",
                type="primary",
                use_container_width=True,
            )
            if predict_clicked:
                st.session_state["forecast_loaded"] = True

    outputs_found = bool(available_modes)
    shape_found = SHAPE_ZIP_PATH.exists()
    standard_found = FORECAST_FILE_MAP["standard"]["barangay"].exists() and FORECAST_FILE_MAP["standard"]["city"].exists()
    env_found = FORECAST_FILE_MAP["environmental_only"]["barangay"].exists() and FORECAST_FILE_MAP["environmental_only"]["city"].exists()

    st.markdown(
        f"""
        <div class="status-card">
            <div class="mini-label">System status</div>
            <div class="status-line"><span>Standard CSV set</span><span class="{'status-ok' if standard_found else 'status-bad'}">{'Found' if standard_found else 'Missing'}</span></div>
            <div class="status-line"><span>Environmental CSV set</span><span class="{'status-ok' if env_found else 'status-bad'}">{'Found' if env_found else 'Missing'}</span></div>
            <div class="status-line"><span>Shapefile</span><span class="{'status-ok' if shape_found else 'status-bad'}">{'Found' if shape_found else 'Missing'}</span></div>
            <div class="status-line"><span>Predict button</span><span class="status-ok">Enabled</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if not available_modes:
    st.warning("Place the forecast CSV files inside the `outputs/` folder, then reload the app.")
    st.code("outputs/forecast_barangay_standard.csv\noutputs/forecast_city_standard.csv\noutputs/forecast_barangay_environmental_only.csv\noutputs/forecast_city_environmental_only.csv")
    st.stop()

if selected_mode is None or selected_year is None or selected_week is None:
    st.stop()

if not st.session_state.get("forecast_loaded", False):
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        render_metric_card(
            "Prediction mode",
            mode_short_label(selected_mode),
            "Ready to read saved CSV forecasts generated by the R scripts.",
        )
    with col_b:
        render_metric_card(
            "Selected origin week",
            f"{int(selected_year)} W{int(selected_week)}",
            "Press Predict to display citywide and barangay forecasts.",
        )
    with col_c:
        render_metric_card(
            "Forecast tabs",
            "0 to +12",
            "After prediction, use the tabs to compare barangay intensity per horizon.",
        )

    st.info("Click **Predict Dengue Cases** in the sidebar to show the barangay intensity maps and citywide forecasts.")
    st.stop()

# Filter to selected origin week, then show all requested horizons.
# The extra numeric conversion below is intentional. Some CSV versions store
# horizon as 0/1/2 while others expose H+0/H+1 labels; forcing the value here
# prevents false missing-horizon warnings.
barangay_df = force_horizon_int(barangay_df)
city_df = force_horizon_int(city_df)

origin_barangay = barangay_df.loc[
    (pd.to_numeric(barangay_df["origin_year"], errors="coerce") == int(selected_year)) &
    (pd.to_numeric(barangay_df["origin_week"], errors="coerce") == int(selected_week)) &
    (pd.to_numeric(barangay_df["horizon"], errors="coerce").isin(DISPLAY_HORIZONS))
].copy()

origin_city = city_df.loc[
    (pd.to_numeric(city_df["origin_year"], errors="coerce") == int(selected_year)) &
    (pd.to_numeric(city_df["origin_week"], errors="coerce") == int(selected_week)) &
    (pd.to_numeric(city_df["horizon"], errors="coerce").isin(DISPLAY_HORIZONS))
].copy()

origin_barangay["horizon"] = pd.to_numeric(origin_barangay["horizon"], errors="coerce").fillna(-1).astype(int)
origin_city["horizon"] = pd.to_numeric(origin_city["horizon"], errors="coerce").fillna(-1).astype(int)

if origin_barangay.empty:
    st.warning("No barangay forecast rows were found for this selected mode/year/week.")
    st.stop()

if origin_city.empty:
    st.warning("No citywide forecast rows were found for this selected mode/year/week.")
    st.stop()

origin_barangay = add_barangay_display_columns(origin_barangay)
origin_city = add_city_display_columns(origin_city)

available_horizons = sorted(set(origin_city["horizon"].unique()).intersection(set(origin_barangay["horizon"].unique())))
available_horizons = [h for h in DISPLAY_HORIZONS if h in available_horizons]

col_a, col_b, col_c = st.columns(3)
with col_a:
    render_metric_card(
        "Prediction mode",
        mode_short_label(selected_mode),
        "Forecasts are loaded from saved CSV files generated by the R scripts.",
    )
with col_b:
    render_metric_card(
        "Selected origin week",
        f"{int(selected_year)} W{int(selected_week)}",
        "Use the tabs below to inspect barangay intensity across forecast horizons.",
    )
with col_c:
    render_metric_card(
        "Forecast windows",
        str(len(available_horizons)),
        "Selected week, 1 week from now, and later planning windows up to 12 weeks.",
    )

st.markdown('<div class="section-title">Forecast summary</div>', unsafe_allow_html=True)

summary_table = origin_city[[
    "horizon", "target_year", "target_week", "predicted_case_range", "probability_display", "alert_level", "range_basis"
]].copy()
summary_table["Forecast horizon"] = summary_table["horizon"].apply(forecast_label_from_horizon)
summary_table = summary_table.rename(columns={
    "target_year": "Target year",
    "target_week": "Target week",
    "predicted_case_range": "Citywide case range",
    "probability_display": "Outbreak probability",
    "alert_level": "Alert level/status",
    "range_basis": "Range basis",
})[["Forecast horizon", "Target year", "Target week", "Citywide case range", "Outbreak probability", "Alert level/status", "Range basis"]]
render_pretty_table(summary_table, max_rows=20)

if not available_horizons:
    st.warning("The selected origin week exists, but none of the display horizons are available in both city and barangay CSVs.")
    st.stop()

# Always show the full horizon navigation requested by the app design.
# If one horizon is unexpectedly missing from the CSV, its tab will explain it
# instead of making the tab disappear.
labels = [forecast_label_from_horizon(h) for h in DISPLAY_HORIZONS]
tabs = st.tabs(labels)

for tab, horizon in zip(tabs, DISPLAY_HORIZONS):
    with tab:
        city_rows = origin_city.loc[pd.to_numeric(origin_city["horizon"], errors="coerce") == int(horizon)].copy()
        barangay_rows = origin_barangay.loc[pd.to_numeric(origin_barangay["horizon"], errors="coerce") == int(horizon)].copy()

        if city_rows.empty or barangay_rows.empty:
            city_found = sorted(pd.to_numeric(origin_city["horizon"], errors="coerce").dropna().astype(int).unique().tolist())
            brgy_found = sorted(pd.to_numeric(origin_barangay["horizon"], errors="coerce").dropna().astype(int).unique().tolist())
            st.warning(
                "This horizon is missing either citywide or barangay forecast rows. "
                f"Debug: city horizons found = {city_found}; barangay horizons found = {brgy_found}."
            )
            continue

        city_row = city_rows.iloc[0]
        label = forecast_label_from_horizon(horizon)
        target_year = int(city_row["target_year"])
        target_week = int(city_row["target_week"])

        st.markdown(
            f'<div class="section-title">{html.escape(label)} · {target_year} W{target_week}</div>',
            unsafe_allow_html=True,
        )

        # Citywide section
        st.markdown("### Citywide dengue forecast")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Predicted citywide case range", str(city_row["predicted_case_range"]))
        with c2:
            st.metric("Outbreak probability", str(city_row["probability_display"]))
        with c3:
            st.metric("Alert level/status", str(city_row["alert_level"]))

        city_table = pd.DataFrame({
            "Forecast period": [label],
            "Target year": [target_year],
            "Target week": [target_week],
            "Predicted citywide cases": [fmt_number(city_row["predicted_cases"], 2)],
            "Predicted citywide case range": [city_row["predicted_case_range"]],
            "Range basis": [city_row["range_basis"]],
            "Outbreak probability": [city_row["probability_display"]],
            "Alert level/status": [str(city_row["alert_level"])],
        })
        render_pretty_table(city_table)

        st.markdown("#### Citywide recommended interventions")
        for item in get_intervention_plan(city_row["alert_level"]):
            st.markdown(f"- {item}")

        st.divider()

        # Barangay section
        st.markdown("### Barangay dengue intensity map")

        total_pred = barangay_rows["predicted_cases"].sum()
        mean_prob = barangay_rows["outbreak_probability"].dropna().mean()
        high_count = barangay_rows[
            barangay_rows["alert_level"].apply(lambda x: clean_alert(x) in ["high", "very high", "very_high"])
        ].shape[0]
        top_row = barangay_rows.sort_values(["alert_rank", "outbreak_probability", "predicted_cases"], ascending=False).iloc[0]

        b1, b2, b3 = st.columns(3)
        with b1:
            st.metric("Total predicted cases", fmt_number(total_pred, 1))
        with b2:
            st.metric("Mean outbreak probability", fmt_percent(mean_prob, 1))
        with b3:
            st.metric("High / very high barangays", str(high_count))

        st.markdown(
            f"""
            <div class="glass-card">
                <div class="mini-label">Highest-risk barangay</div>
                <div class="big-value">{html.escape(str(top_row['barangay']))}</div>
                <div class="small-note">
                    Predicted case range: <b>{html.escape(str(top_row['predicted_case_range']))}</b><br>
                    Outbreak probability: <b>{html.escape(fmt_percent(top_row.get('outbreak_probability'), 1))}</b><br>
                    Alert level:
                    <span class="alert-badge {alert_badge_class(top_row['alert_level'])}">
                        {html.escape(str(top_row['alert_level']))}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        render_alert_legend()

        if shape_gdf is None:
            st.error("Could not load `data/cebu_city_barangays.zip`.")
        else:
            st.markdown('<div class="map-shell">', unsafe_allow_html=True)
            prediction_map = create_barangay_prediction_map(shape_gdf, barangay_rows)
            st_folium(prediction_map, width=None, height=690, returned_objects=[])
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("#### Barangay prediction table")
        table = barangay_rows[[
            "barangay", "predicted_cases_display", "predicted_case_range", "range_basis",
            "probability_display", "alert_level", "alert_rank", "predicted_cases",
        ]].copy()
        table = table.sort_values(["alert_rank", "predicted_cases"], ascending=False)
        table = table.drop(columns=["alert_rank", "predicted_cases"])
        table = table.rename(columns={
            "barangay": "Barangay",
            "predicted_cases_display": "Predicted cases",
            "predicted_case_range": "Predicted case range",
            "range_basis": "Range basis",
            "probability_display": "Outbreak probability",
            "alert_level": "Alert level",
        })
        render_pretty_table(table)

        st.markdown("#### Barangay recommended interventions")
        selected_alert = str(top_row["alert_level"])
        st.caption(f"Shown for the highest current alert level in this horizon: {selected_alert}")
        for item in get_intervention_plan(selected_alert):
            st.markdown(f"- {item}")

st.markdown(
    '<div class="footer-note">Cebu City Dengue Early Warning System · CSV-loaded forecasts for planning support</div>',
    unsafe_allow_html=True,
)
