# ============================================================
# CEBU CITY DENGUE FORECASTING APP
# Designer version — no black header/table, improved sidebar, no accuracy score
# ============================================================

import datetime as dt
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
import streamlit.components.v1 as components
from streamlit_folium import st_folium


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Dengue Risk Mapping and Early Warning System in Cebu City",
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

    html {
        scroll-behavior: smooth;
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
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: .72rem 1rem;
        border-radius: 999px;
        background: rgba(255,255,255,.74);
        border: 1px solid rgba(255,255,255,.88);
        color: #252733 !important;
        -webkit-text-fill-color: #252733 !important;
        font-weight: 850;
        font-size: .9rem;
        box-shadow: 0 12px 32px rgba(17, 24, 39, 0.06);
        text-decoration: none !important;
        cursor: pointer;
        transition: transform .18s ease, box-shadow .18s ease, background .18s ease;
    }

    .chip:hover {
        transform: translateY(-2px);
        background: rgba(255,255,255,.92);
        box-shadow: 0 18px 38px rgba(17, 24, 39, 0.10);
    }

    .chip:focus {
        outline: 3px solid rgba(37, 99, 235, .18);
        outline-offset: 3px;
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



    /* ========================= RESEARCH STORY SECTIONS ========================= */

    .story-section {
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid rgba(255, 255, 255, 0.88);
        border-radius: 30px;
        padding: 1.7rem 1.85rem;
        margin: 1.1rem 0 1.25rem 0;
        box-shadow: 0 20px 58px rgba(17, 24, 39, 0.07);
    }

    .story-kicker {
        display: inline-flex;
        align-items: center;
        gap: .45rem;
        border-radius: 999px;
        padding: .42rem .72rem;
        background: rgba(237, 233, 254, .78);
        border: 1px solid rgba(17, 24, 39, .06);
        color: #4c1d95 !important;
        -webkit-text-fill-color: #4c1d95 !important;
        font-size: .75rem;
        letter-spacing: .12em;
        text-transform: uppercase;
        font-weight: 950;
        margin-bottom: .85rem;
    }

    .story-title {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        font-size: clamp(1.3rem, 2.1vw, 2rem);
        line-height: 1.12;
        letter-spacing: -.045em;
        font-weight: 950;
        margin-bottom: .7rem;
    }

    .story-body {
        color: #374151 !important;
        -webkit-text-fill-color: #374151 !important;
        font-size: 1rem;
        line-height: 1.72;
        font-weight: 650;
        max-width: 1080px;
    }

    .story-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .85rem;
        margin-top: 1.05rem;
    }

    .story-tile {
        position: relative;
        overflow: hidden;
        min-height: 152px;
        background:
            radial-gradient(circle at 95% 5%, rgba(109, 40, 217, .16), transparent 34%),
            radial-gradient(circle at 5% 90%, rgba(20, 184, 166, .14), transparent 34%),
            rgba(255, 255, 255, .84);
        border: 1px solid rgba(17, 24, 39, .07);
        border-radius: 24px;
        padding: 1.1rem;
        box-shadow: 0 16px 34px rgba(17, 24, 39, .055);
    }

    .story-tile:before {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        background: linear-gradient(135deg, rgba(255,255,255,.82), rgba(255,255,255,0));
    }

    .story-tile-icon {
        position: relative;
        z-index: 1;
        width: 36px;
        height: 36px;
        display: grid;
        place-items: center;
        border-radius: 14px;
        background: linear-gradient(135deg, rgba(254, 226, 226, .90), rgba(237, 233, 254, .88), rgba(220, 252, 231, .88));
        border: 1px solid rgba(255,255,255,.92);
        box-shadow: 0 10px 20px rgba(17,24,39,.07);
        margin-bottom: .72rem;
        font-size: 1rem;
    }

    .story-tile-value {
        position: relative;
        z-index: 1;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        font-weight: 950;
        font-size: clamp(1.35rem, 2.2vw, 1.8rem);
        letter-spacing: -.055em;
        margin-bottom: .28rem;
        line-height: 1;
    }

    .story-tile-note {
        position: relative;
        z-index: 1;
        color: #4b5563 !important;
        -webkit-text-fill-color: #4b5563 !important;
        font-weight: 700;
        font-size: .9rem;
        line-height: 1.48;
    }

    .story-tile-source {
        position: relative;
        z-index: 1;
        display: inline-flex;
        margin-top: .72rem;
        padding: .34rem .56rem;
        border-radius: 999px;
        background: rgba(255,255,255,.78);
        border: 1px solid rgba(17,24,39,.07);
        color: #374151 !important;
        -webkit-text-fill-color: #374151 !important;
        font-size: .74rem;
        font-weight: 900;
    }

    .disclaimer-card {
        margin-top: 1rem;
        display: flex;
        align-items: flex-start;
        gap: .7rem;
        padding: .9rem 1rem;
        border-radius: 20px;
        background: rgba(254, 243, 199, .72);
        border: 1px solid rgba(245, 158, 11, .22);
        color: #78350f !important;
        -webkit-text-fill-color: #78350f !important;
        font-weight: 800;
        line-height: 1.55;
        max-width: 960px;
    }

    .sidebar-disclaimer {
        margin-top: .75rem;
        padding: .78rem .85rem;
        border-radius: 18px;
        background: rgba(254, 243, 199, .72);
        border: 1px solid rgba(245, 158, 11, .24);
        color: #78350f !important;
        -webkit-text-fill-color: #78350f !important;
        font-size: .81rem;
        line-height: 1.45;
        font-weight: 800;
    }

    .iso-card {
        background: rgba(255,255,255,.74);
        border: 1px solid rgba(255,255,255,.9);
        border-radius: 22px;
        padding: .95rem 1rem;
        box-shadow: 0 14px 34px rgba(17,24,39,0.055);
        margin: 1rem 0;
    }

    .iso-result {
        display: flex;
        justify-content: space-between;
        gap: .75rem;
        align-items: center;
        padding: .75rem .8rem;
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(237,233,254,.85), rgba(220,252,231,.78));
        border: 1px solid rgba(17,24,39,.06);
        font-weight: 950;
    }

    .alert-guide-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: .7rem;
        margin-top: .85rem;
    }

    .alert-guide-card {
        border-radius: 20px;
        padding: .92rem .9rem;
        border: 1px solid rgba(17, 24, 39, .08);
        box-shadow: 0 10px 24px rgba(17,24,39,.045);
        min-height: 135px;
    }

    .alert-guide-title {
        font-size: .9rem;
        font-weight: 950;
        margin-bottom: .45rem;
    }

    .alert-guide-text {
        font-size: .82rem;
        line-height: 1.45;
        font-weight: 760;
    }

    .scroll-anchor {
        scroll-margin-top: 92px;
    }

    .proponents-card {
        background: rgba(255,255,255,.74);
        border: 1px solid rgba(255,255,255,.88);
        border-radius: 28px;
        padding: 1.35rem 1.55rem;
        margin-top: 1.2rem;
        box-shadow: 0 18px 46px rgba(17,24,39,.06);
    }

    .proponents-name {
        font-weight: 950;
        letter-spacing: -.02em;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    .story-section {
        scroll-margin-top: 96px;
    }

    .limitation-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: .9rem;
        margin-top: 1rem;
    }

    .limitation-card {
        background: rgba(255,255,255,.82);
        border: 1px solid rgba(17,24,39,.075);
        border-radius: 24px;
        padding: 1rem 1.05rem;
        box-shadow: 0 14px 34px rgba(17,24,39,.055);
    }

    .limitation-card-title {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        font-weight: 950;
        font-size: 1rem;
        letter-spacing: -.025em;
        margin-bottom: .45rem;
    }

    .limitation-card-text {
        color: #4b5563 !important;
        -webkit-text-fill-color: #4b5563 !important;
        font-weight: 680;
        font-size: .92rem;
        line-height: 1.55;
    }

    .reference-list {
        display: grid;
        gap: .65rem;
        margin-top: 1rem;
    }

    .reference-link {
        display: block;
        padding: .88rem 1rem;
        border-radius: 20px;
        background: rgba(255,255,255,.82);
        border: 1px solid rgba(17,24,39,.075);
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        text-decoration: none !important;
        font-weight: 800;
        box-shadow: 0 12px 28px rgba(17,24,39,.045);
    }

    .reference-link:hover {
        background: rgba(255,255,255,.96);
        transform: translateY(-1px);
    }

    .reference-small {
        display: block;
        margin-top: .25rem;
        color: #6b7280 !important;
        -webkit-text-fill-color: #6b7280 !important;
        font-size: .82rem;
        font-weight: 650;
        line-height: 1.35;
    }

    div[data-baseweb="calendar"] *,
    div[data-baseweb="calendar"] div,
    div[data-baseweb="calendar"] button {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    div[data-baseweb="calendar"] [aria-disabled="true"] {
        background: #f3f4f6 !important;
        color: #9ca3af !important;
        -webkit-text-fill-color: #9ca3af !important;
    }



    /* ========================= DATE PICKER READABILITY PATCH ========================= */

    .stDateInput [data-baseweb="input"] > div,
    section[data-testid="stSidebar"] .stDateInput [data-baseweb="input"] > div {
        background: rgba(255, 255, 255, 0.96) !important;
        border: 1px solid rgba(17, 24, 39, 0.14) !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 24px rgba(17,24,39,0.055) !important;
    }

    .stDateInput input,
    section[data-testid="stSidebar"] .stDateInput input {
        background: transparent !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        caret-color: #111827 !important;
        font-weight: 800 !important;
    }

    .stDateInput [data-baseweb="input"] > div:focus-within,
    section[data-testid="stSidebar"] .stDateInput [data-baseweb="input"] > div:focus-within {
        border-color: rgba(220, 38, 38, 0.55) !important;
        box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.10), 0 10px 24px rgba(17,24,39,0.055) !important;
    }

    div[data-baseweb="calendar"],
    div[data-baseweb="calendar"] > div,
    div[data-baseweb="calendar"] [role="grid"],
    div[data-baseweb="calendar"] [role="row"],
    div[data-baseweb="calendar"] [role="gridcell"] {
        background: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    div[data-baseweb="calendar"] [role="gridcell"] > div,
    div[data-baseweb="calendar"] [role="gridcell"] button,
    div[data-baseweb="calendar"] button {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    div[data-baseweb="calendar"] [aria-disabled="true"],
    div[data-baseweb="calendar"] [aria-disabled="true"] *,
    div[data-baseweb="calendar"] [role="gridcell"][aria-disabled="true"],
    div[data-baseweb="calendar"] [role="gridcell"][aria-disabled="true"] * {
        background: #f9fafb !important;
        color: #9ca3af !important;
        -webkit-text-fill-color: #9ca3af !important;
    }

    div[data-baseweb="calendar"] [aria-selected="true"],
    div[data-baseweb="calendar"] [aria-selected="true"] *,
    div[data-baseweb="calendar"] button[aria-selected="true"],
    div[data-baseweb="calendar"] button[aria-selected="true"] * {
        background: #ef4444 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }



    /* Extra BaseWeb popover patch for Streamlit date calendars on dark-browser themes. */
    div[data-baseweb="popover"] [role="grid"],
    div[data-baseweb="popover"] [role="row"],
    div[data-baseweb="popover"] [role="gridcell"],
    div[data-baseweb="popover"] [role="gridcell"] > div {
        background: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    div[data-baseweb="popover"] [role="gridcell"] button,
    div[data-baseweb="popover"] [role="gridcell"] div,
    div[data-baseweb="popover"] [role="button"] {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    div[data-baseweb="popover"] [aria-disabled="true"],
    div[data-baseweb="popover"] [aria-disabled="true"] *,
    div[data-baseweb="popover"] [role="gridcell"][aria-disabled="true"],
    div[data-baseweb="popover"] [role="gridcell"][aria-disabled="true"] * {
        background: #f9fafb !important;
        color: #9ca3af !important;
        -webkit-text-fill-color: #9ca3af !important;
    }


    /* ========================= ACCURACY CHECK SECTION ========================= */

    .accuracy-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: .85rem;
        margin: 1rem 0 1.1rem 0;
    }

    .accuracy-card {
        position: relative;
        overflow: hidden;
        min-height: 122px;
        background:
            radial-gradient(circle at 92% 10%, rgba(109, 40, 217, .13), transparent 34%),
            radial-gradient(circle at 8% 95%, rgba(20, 184, 166, .13), transparent 35%),
            rgba(255, 255, 255, .82);
        border: 1px solid rgba(17, 24, 39, .075);
        border-radius: 24px;
        padding: 1rem 1.05rem;
        box-shadow: 0 16px 36px rgba(17, 24, 39, .055);
    }

    .accuracy-card.good {
        background: radial-gradient(circle at 92% 10%, rgba(22, 163, 74, .17), transparent 34%), rgba(255,255,255,.84);
    }

    .accuracy-card.warn {
        background: radial-gradient(circle at 92% 10%, rgba(245, 158, 11, .18), transparent 34%), rgba(255,255,255,.84);
    }

    .accuracy-card.bad {
        background: radial-gradient(circle at 92% 10%, rgba(220, 38, 38, .17), transparent 34%), rgba(255,255,255,.84);
    }

    .accuracy-value {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        font-size: clamp(1.45rem, 2.25vw, 2rem);
        font-weight: 950;
        line-height: 1;
        letter-spacing: -.055em;
        margin-bottom: .35rem;
    }

    .accuracy-label {
        color: #4b5563 !important;
        -webkit-text-fill-color: #4b5563 !important;
        font-size: .86rem;
        font-weight: 780;
        line-height: 1.45;
    }

    .accuracy-note {
        color: #6b7280 !important;
        -webkit-text-fill-color: #6b7280 !important;
        font-size: .82rem;
        line-height: 1.5;
        font-weight: 650;
        margin-top: .4rem;
    }

    .accuracy-pill {
        display: inline-flex;
        align-items: center;
        gap: .35rem;
        border-radius: 999px;
        padding: .34rem .58rem;
        font-size: .76rem;
        font-weight: 950;
        border: 1px solid rgba(17,24,39,.075);
        background: rgba(255,255,255,.82);
        margin: .2rem .25rem .2rem 0;
    }

    .accuracy-help-box {
        background: rgba(255, 255, 255, .76);
        border: 1px solid rgba(17, 24, 39, .08);
        border-radius: 22px;
        padding: .95rem 1rem;
        box-shadow: 0 14px 32px rgba(17, 24, 39, .045);
        margin: .9rem 0 1rem 0;
    }


    @media (max-width: 900px) {
        .story-grid,
        .limitation-grid,
        .alert-guide-grid {
            grid-template-columns: 1fr;
        }
    }

    @media (max-width: 980px) {
        .story-grid,
        .alert-guide-grid {
            grid-template-columns: 1fr;
        }
        .hero-card { padding: 2.1rem 1.4rem; }
    }




    /* Extra download-button safety patch for Streamlit/BaseWeb variants. */
    [data-testid="stDownloadButton"] button,
    [data-testid="stDownloadButton"] [data-testid="baseButton-secondary"],
    [data-testid="stDownloadButton"] [data-testid="baseButton-primary"],
    .stDownloadButton button,
    button[data-testid="baseButton-secondary"][kind="secondary"] {
        background: linear-gradient(90deg, #ffffff 0%, #f5f3ff 48%, #ecfdf5 100%) !important;
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border: 1px solid rgba(17,24,39,.12) !important;
        border-radius: 999px !important;
        box-shadow: 0 12px 28px rgba(17,24,39,.08) !important;
    }

    [data-testid="stDownloadButton"] button *,
    [data-testid="stDownloadButton"] [data-testid="baseButton-secondary"] *,
    [data-testid="stDownloadButton"] [data-testid="baseButton-primary"] *,
    .stDownloadButton button * {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        fill: #111827 !important;
    }

    [data-testid="stDownloadButton"] button:hover,
    [data-testid="stDownloadButton"] [data-testid="baseButton-secondary"]:hover,
    [data-testid="stDownloadButton"] [data-testid="baseButton-primary"]:hover,
    .stDownloadButton button:hover {
        background: linear-gradient(90deg, #ffffff 0%, #ede9fe 48%, #dcfce7 100%) !important;
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border-color: rgba(109,40,217,.25) !important;
    }

    .top-risk-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1rem;
        margin: 1rem 0 1.25rem 0;
    }

    .top-risk-card {
        position: relative;
        overflow: hidden;
        min-height: 315px;
        border-radius: 28px;
        padding: 1.25rem 1.25rem 1.15rem 1.25rem;
        background:
            radial-gradient(circle at 12% 10%, rgba(254, 226, 226, 0.72), transparent 31%),
            radial-gradient(circle at 90% 8%, rgba(237, 233, 254, 0.78), transparent 35%),
            radial-gradient(circle at 78% 92%, rgba(220, 252, 231, 0.66), transparent 38%),
            rgba(255,255,255,.88);
        border: 1px solid rgba(255,255,255,.96);
        box-shadow: 0 20px 54px rgba(17,24,39,.095);
    }

    .top-risk-card:before {
        content: "";
        position: absolute;
        inset: 0;
        border-top: 7px solid rgba(220, 38, 38, 0.46);
        pointer-events: none;
    }

    .top-risk-head {
        display: flex;
        align-items: center;
        gap: .75rem;
        margin-bottom: .9rem;
    }

    .top-risk-rank {
        min-width: 2.45rem;
        width: 2.45rem;
        height: 2.45rem;
        border-radius: 999px;
        display: inline-grid;
        place-items: center;
        font-weight: 950;
        font-size: 1rem;
        background: linear-gradient(135deg, #fee2e2, #ede9fe, #dcfce7);
        border: 1px solid rgba(17,24,39,.08);
        box-shadow: 0 10px 24px rgba(17,24,39,.08);
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    .top-risk-name {
        font-size: 1.18rem;
        line-height: 1.14;
        letter-spacing: -.04em;
        font-weight: 950;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    .top-risk-stats {
        display: grid;
        gap: .55rem;
        margin: .75rem 0 1rem 0;
    }

    .top-risk-stat {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: .75rem;
        padding: .62rem .72rem;
        border-radius: 18px;
        background: rgba(255,255,255,.80);
        border: 1px solid rgba(17,24,39,.07);
    }

    .top-risk-stat span:first-child {
        color: #6b7280 !important;
        -webkit-text-fill-color: #6b7280 !important;
        font-size: .78rem;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: .08em;
    }

    .top-risk-stat span:last-child {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        font-size: .95rem;
        font-weight: 950;
        text-align: right;
    }

    .top-risk-actions {
        margin-top: .75rem;
        padding-top: .85rem;
        border-top: 1px dashed rgba(17,24,39,.13);
    }

    .top-risk-actions-title {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        font-weight: 950;
        font-size: .88rem;
        margin-bottom: .45rem;
    }

    .top-risk-actions ul {
        margin: 0;
        padding-left: 1.05rem;
    }

    .top-risk-actions li {
        margin: .25rem 0;
        color: #374151 !important;
        -webkit-text-fill-color: #374151 !important;
        font-size: .86rem;
        font-weight: 750;
        line-height: 1.35;
    }

    @media (max-width: 1050px) {
        .top-risk-grid { grid-template-columns: 1fr; }
        .top-risk-card { min-height: unset; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Extra date-picker readability patch loaded after the main CSS.
st.markdown(
    """
    <style>
    div[data-testid="stDateInput"] div[data-baseweb="input"],
    div[data-testid="stDateInput"] div[data-baseweb="base-input"],
    div[data-testid="stDateInput"] div[data-baseweb="input"] > div,
    section[data-testid="stSidebar"] div[data-testid="stDateInput"] div[data-baseweb="input"],
    section[data-testid="stSidebar"] div[data-testid="stDateInput"] div[data-baseweb="base-input"],
    section[data-testid="stSidebar"] div[data-testid="stDateInput"] div[data-baseweb="input"] > div,
    section[data-testid="stSidebar"] div[data-testid="stDateInput"] input {
        background: #ffffff !important;
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        caret-color: #111827 !important;
        border-radius: 16px !important;
    }

    div[data-baseweb="popover"] [data-baseweb="calendar"],
    div[data-baseweb="popover"] [data-baseweb="calendar"] *,
    div[data-baseweb="calendar"],
    div[data-baseweb="calendar"] *,
    div[data-baseweb="popover"] [role="gridcell"],
    div[data-baseweb="popover"] [role="gridcell"] *,
    div[data-baseweb="calendar"] [role="gridcell"],
    div[data-baseweb="calendar"] [role="gridcell"] * {
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        box-shadow: none !important;
    }

    div[data-baseweb="popover"] [aria-disabled="true"],
    div[data-baseweb="popover"] [aria-disabled="true"] *,
    div[data-baseweb="calendar"] [aria-disabled="true"],
    div[data-baseweb="calendar"] [aria-disabled="true"] * {
        background-color: #f8fafc !important;
        color: #9ca3af !important;
        -webkit-text-fill-color: #9ca3af !important;
    }

    div[data-baseweb="popover"] [aria-selected="true"],
    div[data-baseweb="popover"] [aria-selected="true"] *,
    div[data-baseweb="calendar"] [aria-selected="true"],
    div[data-baseweb="calendar"] [aria-selected="true"] * {
        background-color: #ef4444 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        border-radius: 999px !important;
    }

    /* Streamlit download buttons: keep them light, not black. */
    div[data-testid="stDownloadButton"] {
        width: 100% !important;
        margin: .7rem 0 1.1rem 0 !important;
    }

    div[data-testid="stDownloadButton"] > button,
    div[data-testid="stDownloadButton"] button,
    button[kind="secondary"] {
        min-height: 3rem !important;
        border-radius: 999px !important;
        border: 1px solid rgba(17, 24, 39, .10) !important;
        background: linear-gradient(90deg, rgba(255,255,255,.96), rgba(237,233,254,.95), rgba(220,252,231,.92)) !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        font-weight: 950 !important;
        box-shadow: 0 14px 32px rgba(17,24,39,.075), 0 8px 18px rgba(109,40,217,.10) !important;
    }

    div[data-testid="stDownloadButton"] > button:hover,
    div[data-testid="stDownloadButton"] button:hover,
    button[kind="secondary"]:hover {
        transform: translateY(-1px);
        border-color: rgba(109,40,217,.22) !important;
        background: linear-gradient(90deg, #ffffff, #ede9fe, #dcfce7) !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        box-shadow: 0 18px 38px rgba(109,40,217,.15), 0 8px 18px rgba(20,184,166,.09) !important;
    }

    div[data-testid="stDownloadButton"] p,
    div[data-testid="stDownloadButton"] span,
    div[data-testid="stDownloadButton"] div,
    div[data-testid="stDownloadButton"] svg {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        fill: #111827 !important;
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
    if "very high" in alert_clean:
        return 5
    if "above outbreak" in alert_clean or alert_clean == "high":
        return 4
    if alert_clean == "moderate":
        return 3
    if alert_clean in ["watch", "warning"]:
        return 2
    if "below outbreak" in alert_clean or alert_clean == "low":
        return 1
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
            <div class="mini-label">How to read the map colors</div>
            <div class="small-note">
                The colors do not mean the model is declaring an official outbreak. They show how urgently a barangay should be checked and prepared based on the forecast output.
            </div>
            <div class="alert-guide-grid">
                <div class="alert-guide-card low">
                    <div class="alert-guide-title">Green · Low</div>
                    <div class="alert-guide-text">No strong warning signal. Continue routine monitoring, clean-up, and removal of standing water.</div>
                </div>
                <div class="alert-guide-card watch">
                    <div class="alert-guide-title">Yellow · Watch</div>
                    <div class="alert-guide-text">Early caution. Check common breeding sites and remind households before cases possibly rise.</div>
                </div>
                <div class="alert-guide-card moderate">
                    <div class="alert-guide-title">Orange · Moderate</div>
                    <div class="alert-guide-text">Noticeable risk. Inspect hotspots such as canals, schools, markets, and dense residential areas.</div>
                </div>
                <div class="alert-guide-card high">
                    <div class="alert-guide-title">Red · High</div>
                    <div class="alert-guide-text">Prioritize this barangay. Validate reports, intensify source reduction, and coordinate health response.</div>
                </div>
                <div class="alert-guide-card veryhigh">
                    <div class="alert-guide-title">Purple · Very high</div>
                    <div class="alert-guide-text">Urgent attention. Treat as a strong preparedness signal and coordinate with city health authorities.</div>
                </div>
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

        threshold_candidates = [
            "alert_threshold_cases",
            "alert_threshold",
            "outbreak_threshold_cases",
            "barangay_outbreak_threshold_cases",
            "learned_threshold",
            "learned_alert_threshold",
            "threshold_cases",
            "case_threshold",
        ]
        threshold_has_source = any(col in df.columns for col in threshold_candidates)
        df["alert_threshold_cases"] = as_numeric_series(
            coalesce_series(df, threshold_candidates, default=1),
            default=1,
        ).clip(lower=1)
        df["alert_threshold_source"] = (
            "Forecast CSV alert threshold" if threshold_has_source else "Fallback: ≥1 reported case"
        )

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
# ACTUAL CASE + ACCURACY CHECK HELPERS
# ============================================================

@st.cache_data(show_spinner=False)
def load_actual_case_data(path_text: str) -> Optional[pd.DataFrame]:
    """Load actual dengue cases from FINAL_DATASET.xlsx for post-hoc forecast checking."""
    path = Path(path_text)
    if not path.exists():
        return None

    try:
        actual_df = pd.read_excel(path)
    except Exception as exc:
        st.warning(
            "Could not read `data/FINAL_DATASET.xlsx` for the accuracy check. "
            "Install `openpyxl` if Streamlit says the Excel engine is missing."
        )
        st.code(str(exc))
        return None

    actual_df = actual_df.copy()
    actual_df.columns = [clean_column_name(c) for c in actual_df.columns]
    actual_df = collapse_duplicate_columns(actual_df)

    actual_df["barangay"] = coalesce_series(actual_df, ["barangay", "brgy", "barangay_name"], default="UNKNOWN")
    actual_df["year"] = as_numeric_series(coalesce_series(actual_df, ["year", "epi_year", "origin_year"], default=0), default=0).astype(int)
    actual_df["week"] = as_numeric_series(coalesce_series(actual_df, ["week", "epi_week", "origin_week"], default=0), default=0).astype(int)
    actual_df["actual_cases"] = as_numeric_series(
        coalesce_series(actual_df, ["dengue_cases", "actual_cases", "cases", "dengue"], default=0),
        default=0,
    ).clip(lower=0)

    actual_df["barangay"] = actual_df["barangay"].apply(standardize_barangay_name)
    actual_df = actual_df.loc[(actual_df["year"] > 0) & (actual_df["week"] > 0)].copy()
    actual_df = actual_df.groupby(["barangay", "year", "week"], as_index=False)["actual_cases"].sum()
    return actual_df


def actual_week_available(actual_df: Optional[pd.DataFrame], year: Any, week: Any) -> tuple[bool, str]:
    if actual_df is None or actual_df.empty:
        return False, "FINAL_DATASET.xlsx was not found or could not be read."

    try:
        y = int(year)
        w = int(week)
    except Exception:
        return False, "Target year/week could not be read."

    week_rows = actual_df.loc[(actual_df["year"] == y) & (actual_df["week"] == w)]
    if week_rows.empty:
        return False, f"No actual case rows found for {y} W{w}."

    # Known placeholder in the uploaded dataset: 2026 W19 is present but all dengue cases are zero
    # because actual data are not available yet.
    if y == 2026 and w == 19 and float(week_rows["actual_cases"].sum()) == 0:
        return False, "2026 W19 is excluded because the dataset contains placeholder zeroes, not actual reported cases."

    return True, "Actual case data available."


def prediction_warning_flag(row: pd.Series) -> bool:
    """Count only Moderate/High/Very High as a predicted outbreak.

    Watch/yellow is still shown in the app as an early monitoring signal, but it is
    not treated as an outbreak prediction for the accuracy check. This keeps the
    right/wrong score aligned with the question: "Did the model correctly predict
    an outbreak-level barangay?"
    """
    try:
        return alert_rank(row.get("alert_level")) >= 3
    except Exception:
        return False


def prediction_caution_flag(row: pd.Series) -> bool:
    """Count Watch/Warning and above as an early caution signal.

    This is separate from the strict outbreak alert. It answers a softer but useful
    public-health question: did the app at least tell the user to monitor the
    barangay more closely before/during an actual outbreak?
    """
    try:
        return alert_rank(row.get("alert_level")) >= 2
    except Exception:
        return False


def warning_accuracy_percent(tp: int, tn: int, total_barangays: int = 80) -> Optional[float]:
    """Overall warning accuracy requested as (true positives + true negatives) / 80."""
    try:
        total_barangays = int(total_barangays)
        if total_barangays <= 0:
            return None
        return (int(tp) + int(tn)) / total_barangays
    except Exception:
        return None


def build_accuracy_comparison(barangay_rows: pd.DataFrame, actual_df: pd.DataFrame, target_year: int, target_week: int) -> pd.DataFrame:
    actual_week = actual_df.loc[(actual_df["year"] == int(target_year)) & (actual_df["week"] == int(target_week))].copy()
    compare = barangay_rows.copy()
    compare["barangay"] = compare["barangay"].apply(standardize_barangay_name)

    # Forecast rows may already contain an `actual_cases` column in some CSV versions.
    # Drop it before merging so pandas does not rename the true actual column into
    # actual_cases_x / actual_cases_y and trigger KeyError: 'actual_cases'.
    compare = compare.drop(columns=["actual_cases", "actual_cases_x", "actual_cases_y"], errors="ignore")

    actual_case_col = None
    for candidate in ["actual_cases", "dengue_cases", "cases", "dengue"]:
        if candidate in actual_week.columns:
            actual_case_col = candidate
            break
    if actual_case_col is None:
        actual_week = actual_week.copy()
        actual_week["actual_cases"] = 0
        actual_case_col = "actual_cases"

    actual_week = actual_week[["barangay", actual_case_col]].copy()
    actual_week = actual_week.rename(columns={actual_case_col: "actual_cases"})
    actual_week["barangay"] = actual_week["barangay"].apply(standardize_barangay_name)
    actual_week["actual_cases"] = pd.to_numeric(actual_week["actual_cases"], errors="coerce").fillna(0).clip(lower=0)
    actual_week = actual_week.groupby("barangay", as_index=False)["actual_cases"].sum()

    compare = compare.merge(actual_week, on="barangay", how="left")
    if "actual_cases" not in compare.columns:
        compare["actual_cases"] = 0
    compare["actual_cases"] = pd.to_numeric(compare["actual_cases"], errors="coerce").fillna(0).clip(lower=0)

    if "alert_threshold_cases" not in compare.columns:
        compare["alert_threshold_cases"] = 1
    if "alert_threshold_source" not in compare.columns:
        compare["alert_threshold_source"] = "Fallback: ≥1 reported case"

    compare["alert_threshold_cases"] = pd.to_numeric(compare["alert_threshold_cases"], errors="coerce").fillna(1).clip(lower=1)
    compare["actual_outbreak"] = compare["actual_cases"] >= compare["alert_threshold_cases"]
    compare["predicted_warning"] = compare.apply(prediction_warning_flag, axis=1)
    compare["predicted_caution"] = compare.apply(prediction_caution_flag, axis=1)

    compare["prediction_result"] = "Correct low / no outbreak"
    compare.loc[compare["predicted_warning"] & compare["actual_outbreak"], "prediction_result"] = "Correct warning"
    compare.loc[compare["predicted_warning"] & ~compare["actual_outbreak"], "prediction_result"] = "False warning"
    compare.loc[~compare["predicted_warning"] & compare["actual_outbreak"], "prediction_result"] = "Missed outbreak"

    compare["absolute_error"] = (pd.to_numeric(compare["predicted_cases"], errors="coerce").fillna(0) - compare["actual_cases"]).abs()
    compare["range_lower"] = (pd.to_numeric(compare["predicted_cases"], errors="coerce").fillna(0) - pd.to_numeric(compare.get("selected_error_value", 0), errors="coerce").fillna(0)).clip(lower=0)
    compare["range_upper"] = (pd.to_numeric(compare["predicted_cases"], errors="coerce").fillna(0) + pd.to_numeric(compare.get("selected_error_value", 0), errors="coerce").fillna(0)).clip(lower=0)
    compare["actual_within_range"] = (compare["actual_cases"] >= compare["range_lower"]) & (compare["actual_cases"] <= compare["range_upper"])
    return compare


def safe_rate(numerator: float, denominator: float) -> Optional[float]:
    try:
        denominator = float(denominator)
        if denominator == 0:
            return None
        return float(numerator) / denominator
    except Exception:
        return None


def fmt_rate(value: Optional[float], digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value) * 100:.{digits}f}%"


def render_accuracy_cards(records: List[Dict[str, Any]]) -> None:
    total_tp = sum(int(r["correct_warnings"]) for r in records)
    total_fp = sum(int(r["false_warnings"]) for r in records)
    total_fn = sum(int(r["missed_outbreaks"]) for r in records)
    checked_horizons = len(records)

    card_html = f"""
    <div class="accuracy-grid">
        <div class="accuracy-card good">
            <div class="accuracy-value">{checked_horizons}</div>
            <div class="accuracy-label">forecast horizon(s) checked against actual reported cases</div>
        </div>
        <div class="accuracy-card good">
            <div class="accuracy-value">{total_tp}</div>
            <div class="accuracy-label">correct outbreak-level alert(s)</div>
            <div class="accuracy-note">Predicted Moderate/High/Very High and actual cases reached the threshold.</div>
        </div>
        <div class="accuracy-card warn">
            <div class="accuracy-value">{total_fp}</div>
            <div class="accuracy-label">false outbreak-level alert(s)</div>
            <div class="accuracy-note">Predicted Moderate/High/Very High, but actual cases did not reach the threshold.</div>
        </div>
        <div class="accuracy-card bad">
            <div class="accuracy-value">{total_fn}</div>
            <div class="accuracy-label">missed outbreak(s)</div>
            <div class="accuracy-note">Actual cases reached the threshold, but the app did not show an outbreak-level alert.</div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def render_accuracy_check(origin_barangay: pd.DataFrame, origin_city: pd.DataFrame, actual_df: Optional[pd.DataFrame]) -> None:
    st.markdown(
        """
        <div id="accuracy-section" class="scroll-anchor"></div>
        <section class="story-section">
            <div class="story-kicker">Accuracy check</div>
            <div class="story-title">How the forecast compared with actual reported dengue cases</div>
            <div class="story-body">
                When the target week already exists in <b>FINAL_DATASET.xlsx</b>, this section compares predicted outbreak-level barangay alerts with actual reported dengue cases. <b>Watch/yellow is treated as a monitoring signal, not an outbreak prediction</b>; Moderate, High, and Very High are counted as predicted outbreaks. It is not shown for target weeks without reliable actual data; specifically, <b>2026 W19 is excluded</b> because it is a placeholder all-zero week in the uploaded dataset.
            </div>
            <div class="accuracy-help-box">
                <span class="accuracy-pill">✅ Correct warning</span>
                <span class="accuracy-pill">⚠️ False warning</span>
                <span class="accuracy-pill">❌ Missed outbreak</span>
                <span class="accuracy-pill">✅ Correct low</span>
                <div class="accuracy-note">Actual outbreak is checked using the forecast CSV's alert threshold when available. If no threshold column exists, the app falls back to at least 1 reported case. Overall accuracy is computed as (true positives + true negatives) ÷ 80 barangays. False warning rate is computed as false outbreak-level alerts ÷ actual non-outbreak barangays.</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if actual_df is None or actual_df.empty:
        st.info("Accuracy check is hidden because `data/FINAL_DATASET.xlsx` was not found or could not be read.")
        return

    records: List[Dict[str, Any]] = []
    detail_tables: Dict[str, pd.DataFrame] = {}
    skipped_notes: List[str] = []

    for horizon in DISPLAY_HORIZONS:
        barangay_rows = origin_barangay.loc[pd.to_numeric(origin_barangay["horizon"], errors="coerce") == int(horizon)].copy()
        city_rows = origin_city.loc[pd.to_numeric(origin_city["horizon"], errors="coerce") == int(horizon)].copy()
        if barangay_rows.empty or city_rows.empty:
            continue

        city_row = city_rows.iloc[0]
        target_year = int(city_row["target_year"])
        target_week = int(city_row["target_week"])
        available, reason = actual_week_available(actual_df, target_year, target_week)
        label = f"{forecast_label_from_horizon(horizon)} · {target_year} W{target_week}"

        if not available:
            skipped_notes.append(f"{label}: {reason}")
            continue

        compare = build_accuracy_comparison(barangay_rows, actual_df, target_year, target_week)

        tp = int(((compare["predicted_warning"]) & (compare["actual_outbreak"])).sum())
        fp = int(((compare["predicted_warning"]) & (~compare["actual_outbreak"])).sum())
        fn = int(((~compare["predicted_warning"]) & (compare["actual_outbreak"])).sum())
        tn = int(((~compare["predicted_warning"]) & (~compare["actual_outbreak"])).sum())
        precision = safe_rate(tp, tp + fp)
        recall = safe_rate(tp, tp + fn)
        f1 = None if precision is None or recall is None or (precision + recall) == 0 else 2 * precision * recall / (precision + recall)
        overall_accuracy = warning_accuracy_percent(tp, tn, 80)
        false_warning_rate = safe_rate(fp, fp + tn)
        mae = compare["absolute_error"].mean()
        within_share = compare["actual_within_range"].mean()
        actual_city_cases = compare["actual_cases"].sum()
        predicted_city_cases = float(city_row.get("predicted_cases", 0))

        records.append({
            "horizon": horizon,
            "Forecast horizon": forecast_label_from_horizon(horizon),
            "Target week": f"{target_year} W{target_week}",
            "Actual city cases": int(round(actual_city_cases)),
            "Predicted city range": str(city_row.get("predicted_case_range", "—")),
            "City abs. error": round(abs(predicted_city_cases - actual_city_cases), 1),
            "correct_warnings": tp,
            "false_warnings": fp,
            "missed_outbreaks": fn,
            "correct_lows": tn,
            "Overall accuracy": fmt_rate(overall_accuracy),
            "False warning rate": fmt_rate(false_warning_rate),
            "Precision": fmt_rate(precision),
            "Recall": fmt_rate(recall),
            "F1": fmt_rate(f1),
            "Barangay MAE": round(float(mae), 2) if not pd.isna(mae) else "—",
            "Within range": fmt_rate(within_share),
        })

        result_order = {
            "Missed outbreak": 1,
            "False warning": 2,
            "Correct warning": 3,
            "Correct low / no outbreak": 4,
        }
        compare["result_order"] = compare["prediction_result"].map(result_order).fillna(9)
        detail = compare.sort_values(["result_order", "actual_cases", "predicted_cases"], ascending=[True, False, False]).copy()
        detail["Forecast target"] = f"{target_year} W{target_week}"
        detail["Predicted outbreak-level alert?"] = detail["predicted_warning"].map({True: "Yes", False: "No"})
        detail["Actual outbreak?"] = detail["actual_outbreak"].map({True: "Yes", False: "No"})
        detail["Actual cases"] = detail["actual_cases"].round(0).astype(int)
        detail["Outbreak threshold used"] = detail["alert_threshold_cases"].round(2)
        detail["Absolute error"] = detail["absolute_error"].round(2)
        detail["Within predicted range?"] = detail["actual_within_range"].map({True: "Yes", False: "No"})
        detail["Result"] = detail["prediction_result"].replace({
            "Correct warning": "✅ Correct warning",
            "False warning": "⚠️ False warning",
            "Missed outbreak": "❌ Missed outbreak",
            "Correct low / no outbreak": "✅ Correct low / no outbreak",
        })
        detail = detail.rename(columns={
            "barangay": "Barangay",
            "predicted_cases_display": "Predicted cases",
            "predicted_case_range": "Predicted case range",
            "alert_level": "Predicted alert level",
            "alert_threshold_source": "Threshold source",
        })[[
            "Barangay", "Forecast target", "Predicted cases", "Predicted case range",
            "Actual cases", "Predicted alert level", "Outbreak threshold used",
            "Predicted outbreak-level alert?", "Actual outbreak?", "Within predicted range?",
            "Result", "Absolute error", "Threshold source",
        ]]
        detail_tables[label] = detail

    if not records:
        st.info("No selected forecast target week has reliable actual data yet. " + (" ".join(skipped_notes[:3]) if skipped_notes else ""))
        return

    render_accuracy_cards(records)

    summary_df = pd.DataFrame(records)
    summary_display = summary_df[[
        "Forecast horizon", "Target week", "Actual city cases", "Predicted city range",
        "City abs. error", "correct_warnings", "false_warnings", "missed_outbreaks",
        "correct_lows", "Overall accuracy", "False warning rate", "Precision", "Recall", "F1", "Barangay MAE", "Within range",
    ]].rename(columns={
        "correct_warnings": "Correct warnings",
        "false_warnings": "False warnings",
        "missed_outbreaks": "Missed outbreaks",
        "correct_lows": "Correct lows",
    })
    st.markdown("#### Accuracy summary by forecast horizon")
    render_pretty_table(summary_display, max_rows=20)

    if skipped_notes:
        with st.expander("Skipped target weeks"):
            for note in skipped_notes:
                st.markdown(f"- {note}")

    st.markdown("#### Barangay-level right/wrong check")
    selected_detail_label = st.selectbox("Choose target week to inspect", list(detail_tables.keys()))
    render_pretty_table(detail_tables[selected_detail_label], max_rows=120)


def render_top_risk_cards(table: pd.DataFrame, count: int = 3) -> None:
    """Render only the highest-risk barangays as clean cards with actions."""
    if table.empty:
        st.info("No barangay prediction rows to show.")
        return

    top = table.head(count).copy()
    cards: List[str] = []
    for idx, row in enumerate(top.to_dict("records"), start=1):
        alert_level = str(row.get("Alert level", "—"))
        barangay = html.escape(str(row.get("Barangay", "—")))
        pred_range = html.escape(str(row.get("Predicted case range", "—")))
        probability = html.escape(str(row.get("Outbreak probability", "—")))
        alert_html = f'<span class="alert-badge {alert_badge_class(alert_level)}">{html.escape(alert_level)}</span>'
        actions = get_intervention_plan(alert_level)[:3]
        action_items = "".join(f"<li>{html.escape(str(action))}</li>" for action in actions)

        # Build the HTML as one non-indented string. This avoids Streamlit/Markdown
        # interpreting later cards as code blocks and showing raw HTML.
        card = (
            '<div class="top-risk-card">'
            '<div class="top-risk-head">'
            f'<div class="top-risk-rank">{idx}</div>'
            f'<div class="top-risk-name">{barangay}</div>'
            '</div>'
            '<div class="top-risk-stats">'
            f'<div class="top-risk-stat"><span>Predicted</span><span>{pred_range}</span></div>'
            f'<div class="top-risk-stat"><span>Probability</span><span>{probability}</span></div>'
            f'<div class="top-risk-stat"><span>Alert</span><span>{alert_html}</span></div>'
            '</div>'
            '<div class="top-risk-actions">'
            '<div class="top-risk-actions-title">Recommended preparedness actions</div>'
            f'<ul>{action_items}</ul>'
            '</div>'
            '</div>'
        )
        cards.append(card)

    st.markdown('<div class="top-risk-grid">' + ''.join(cards) + '</div>', unsafe_allow_html=True)


def render_accuracy_check_for_horizon(
    barangay_rows: pd.DataFrame,
    city_row: pd.Series,
    actual_df: Optional[pd.DataFrame],
    horizon: int,
) -> None:
    """Show a compact accuracy check inside each forecast-horizon tab.

    Strict outbreak alert = Moderate/High/Very High.
    Early caution signal = Watch/Warning/Moderate/High/Very High.
    """
    try:
        target_year = int(city_row["target_year"])
        target_week = int(city_row["target_week"])
    except Exception:
        st.info("Accuracy check is not available because the target year/week could not be read.")
        return

    st.markdown(
        f"""
        <div id="accuracy-section" class="scroll-anchor"></div>
        <div class="accuracy-help-box">
            <div class="mini-label">Accuracy check · {html.escape(forecast_label_from_horizon(horizon))} · {target_year} W{target_week}</div>
            <div class="accuracy-note">
                Strict outbreak accuracy counts <b>Moderate, High, and Very High</b> as predicted outbreak-level alerts.
                Early caution capture counts <b>Watch/Warning and above</b> as useful monitoring signals. This keeps the app fair: Watch is not treated as an outbreak declaration, but it is still recognized when it helps flag a barangay that later had an actual outbreak. False warning rate shows how often the model raised an outbreak-level alert in barangays that did not actually reach the outbreak threshold.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if actual_df is None or actual_df.empty:
        st.info("Accuracy check is hidden because `data/FINAL_DATASET.xlsx` was not found or could not be read.")
        return

    available, reason = actual_week_available(actual_df, target_year, target_week)
    if not available:
        st.info(f"Accuracy check not shown for {target_year} W{target_week}: {reason}")
        return

    compare = build_accuracy_comparison(barangay_rows, actual_df, target_year, target_week)

    tp = int(((compare["predicted_warning"]) & (compare["actual_outbreak"])).sum())
    fp = int(((compare["predicted_warning"]) & (~compare["actual_outbreak"])).sum())
    fn = int(((~compare["predicted_warning"]) & (compare["actual_outbreak"])).sum())
    tn = int(((~compare["predicted_warning"]) & (~compare["actual_outbreak"])).sum())

    actual_outbreaks = int(compare["actual_outbreak"].sum())
    strict_precision = safe_rate(tp, tp + fp)
    strict_recall = safe_rate(tp, tp + fn)
    false_warning_rate = safe_rate(fp, fp + tn)
    overall_accuracy = warning_accuracy_percent(tp, tn, 80)

    caution_hits = int(((compare["predicted_caution"]) & (compare["actual_outbreak"])).sum())
    caution_misses = int(((~compare["predicted_caution"]) & (compare["actual_outbreak"])).sum())
    caution_capture = safe_rate(caution_hits, actual_outbreaks)

    barangay_mae = compare["absolute_error"].mean()
    actual_city_cases = int(round(compare["actual_cases"].sum()))
    predicted_city_cases = float(city_row.get("predicted_cases", 0))
    city_abs_error = abs(predicted_city_cases - actual_city_cases)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric("Overall accuracy", fmt_rate(overall_accuracy))
    with c2:
        st.metric("Strict outbreak capture", fmt_rate(strict_recall))
    with c3:
        st.metric("False warning rate", fmt_rate(false_warning_rate))
    with c4:
        st.metric("Early caution capture", fmt_rate(caution_capture))
    with c5:
        st.metric("Missed outbreaks", fn)
    with c6:
        st.metric("Barangay MAE", fmt_number(barangay_mae, 2))

    st.caption(
        f"Overall accuracy includes correct non-outbreak barangays: ({tp} true positives + {tn} true negatives) / 80 = {fmt_rate(overall_accuracy)}. "
        f"Strict alerts: TP={tp}, FP={fp}, FN={fn}, TN={tn}; false warning rate = FP / (FP + TN) = {fmt_rate(false_warning_rate)}. "
        f"Early caution captured {caution_hits}/{actual_outbreaks} actual outbreak barangays; {caution_misses} had no caution signal. "
        f"Citywide actual cases={actual_city_cases}; predicted={fmt_number(predicted_city_cases, 1)}; absolute error={fmt_number(city_abs_error, 1)}."
    )

    result_order = {
        "Missed outbreak": 1,
        "False warning": 2,
        "Correct warning": 3,
        "Correct low / no outbreak": 4,
    }
    compare["result_order"] = compare["prediction_result"].map(result_order).fillna(9)
    detail = compare.sort_values(["result_order", "actual_cases", "predicted_cases"], ascending=[True, False, False]).copy()
    detail["Predicted outbreak-level alert?"] = detail["predicted_warning"].map({True: "Yes", False: "No"})
    detail["Early caution signal?"] = detail["predicted_caution"].map({True: "Yes", False: "No"})
    detail["Actual outbreak?"] = detail["actual_outbreak"].map({True: "Yes", False: "No"})
    detail["Actual cases"] = detail["actual_cases"].round(0).astype(int)
    detail["Outbreak threshold used"] = detail["alert_threshold_cases"].round(2)
    detail["Absolute error"] = detail["absolute_error"].round(2)
    detail["Within predicted range?"] = detail["actual_within_range"].map({True: "Yes", False: "No"})
    detail["Result"] = detail["prediction_result"].replace({
        "Correct warning": "✅ Correct outbreak alert",
        "False warning": "⚠️ False outbreak alert",
        "Missed outbreak": "❌ Missed strict outbreak alert",
        "Correct low / no outbreak": "✅ Correct non-outbreak",
    })
    detail = detail.rename(columns={
        "barangay": "Barangay",
        "predicted_cases_display": "Predicted cases",
        "predicted_case_range": "Predicted case range",
        "alert_level": "Predicted alert level",
        "alert_threshold_source": "Threshold source",
    })[[
        "Barangay", "Predicted cases", "Predicted case range", "Actual cases",
        "Predicted alert level", "Outbreak threshold used", "Predicted outbreak-level alert?",
        "Early caution signal?", "Actual outbreak?", "Within predicted range?",
        "Result", "Absolute error", "Threshold source",
    ]]

    csv = detail.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download full accuracy check CSV",
        data=csv,
        file_name=f"accuracy_check_{target_year}_W{target_week}_H{int(horizon)}.csv",
        mime="text/csv",
        use_container_width=True,
        key=f"accuracy_download_{target_year}_{target_week}_{int(horizon)}",
    )


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
# RESEARCH STORY SECTIONS
# ============================================================

def render_story_section(kicker: str, title: str, body: str, tiles: Optional[List[Dict[str, str]]] = None, anchor_id: Optional[str] = None) -> None:
    """Render a custom HTML section without Markdown indentation artifacts."""
    safe_anchor = f' id="{html.escape(anchor_id)}"' if anchor_id else ""
    tile_html = ""
    if tiles:
        parts = ["<div class='story-grid'>"]
        for tile in tiles:
            icon = html.escape(tile.get("icon", "•"))
            value = html.escape(tile.get("value", ""))
            note = html.escape(tile.get("note", ""))
            source = html.escape(tile.get("source", ""))
            source_html = f"<div class='story-tile-source'>{source}</div>" if source else ""
            parts.append(
                "<div class='story-tile'>"
                f"<div class='story-tile-icon'>{icon}</div>"
                f"<div class='story-tile-value'>{value}</div>"
                f"<div class='story-tile-note'>{note}</div>"
                f"{source_html}"
                "</div>"
            )
        parts.append("</div>")
        tile_html = "".join(parts)

    section_html = (
        f"<section{safe_anchor} class='story-section'>"
        f"<div class='story-kicker'>{html.escape(kicker)}</div>"
        f"<div class='story-title'>{html.escape(title)}</div>"
        f"<div class='story-body'>{body}</div>"
        f"{tile_html}"
        "</section>"
    )
    st.markdown(section_html, unsafe_allow_html=True)

def render_rationale_and_methods() -> None:
    render_story_section(
        "Rationale",
        "Why Cebu City needs an early dengue warning map",
        """
        Dengue remains a practical public health problem because risk can rise quickly, spread unevenly, and differ from one barangay to another. Globally, WHO reported record dengue transmission in 2024, while this study focuses that bigger problem into Cebu City by turning dengue, weather, flood, land-cover, population, and spatial signals into an easier-to-read preparedness dashboard. The app is not meant to declare outbreaks. It is meant to help users decide where to check first and where prevention work may be needed earlier.
        """,
        [
            {"icon": "🌍", "value": "14.6M+", "note": "Reported global dengue cases in 2024.", "source": "WHO"},
            {"icon": "🗺️", "value": "80", "note": "Cebu City barangays covered by the study dataset.", "source": "This study"},
            {"icon": "📈", "value": "27,518", "note": "Recorded Cebu City dengue cases used from 2015 to 2024.", "source": "This study"},
        ],
        anchor_id="rationale-section",
    )

    render_story_section(
        "Methodology",
        "How the forecasts were produced",
        """
        The study used weekly dengue records, weather and climate variables, rainfall and flood-related indicators, land-cover data, population measures, and spatial dengue features. Data were arranged by barangay and epidemiological week, then converted into lagged, rolling, seasonal, citywide, and neighboring-barangay predictors. The app reads the saved forecast CSV outputs and displays two linked views: a citywide forecast for overall burden and a barangay map for localized risk. The strongest practical use is short-term decision support: barangay forecasts are most defensible around the selected week to four weeks ahead, while citywide forecasts are strongest around the selected week to three weeks ahead.
        """,
        [
            {"icon": "🧾", "value": "2015–2024", "note": "Historical period used for model development and evaluation.", "source": "Data split"},
            {"icon": "⏳", "value": "H+0 to H+12", "note": "Forecast horizons prepared for short-term and longer planning windows.", "source": "Forecast design"},
            {"icon": "🧭", "value": "Map + table", "note": "Outputs are shown as case ranges, alerts, and barangay risk maps.", "source": "App output"},
        ],
        anchor_id="methods-section",
    )

def render_limitations_and_actions() -> None:
    st.markdown(
        """
        <section id="limitations-section" class="story-section">
            <div class="story-kicker">Limitations and what to do</div>
            <div class="story-title">Use the app as a guide, not as a final diagnosis</div>
            <div class="story-body">
                The forecast is useful because it summarizes risk signals, but it should still be checked against real barangay conditions. These are the main limits and the proper response to each one.
            </div>
            <div class="limitation-grid">
                <div class="limitation-card">
                    <div class="limitation-card-title">1. Underreporting and reporting delays</div>
                    <div class="limitation-card-text">Some dengue cases may be missed, self-managed at home, or reported late. A Punta Princesa, Cebu City study comparing active and passive surveillance reported a 21% cumulative reporting rate of symptomatic dengue infections, equivalent to an expansion factor of 4.7. <b>What to do:</b> confirm high-risk alerts using barangay health-center records, suspected-case logs, school reports, and field validation.</div>
                </div>
                <div class="limitation-card">
                    <div class="limitation-card-title">2. Longer horizons are less certain</div>
                    <div class="limitation-card-text">Forecasts farther from the selected week are more uncertain because weather, reporting, mosquito activity, and interventions can change. <b>What to do:</b> prioritize the selected week to the next few weeks for action, then treat later horizons as early awareness only.</div>
                </div>
                <div class="limitation-card">
                    <div class="limitation-card-title">3. Not all local risk factors are included</div>
                    <div class="limitation-card-text">The model does not yet include every barangay-level risk detail such as drainage hotspots, waste-collection issues, construction sites, schools, markets, larval indices, mosquito surveillance, and mobility. <b>What to do:</b> add these as new features in future versions.</div>
                </div>
                <div class="limitation-card">
                    <div class="limitation-card-title">4. The model needs updating</div>
                    <div class="limitation-card-text">Dengue patterns can shift over time. A model trained on older patterns may weaken if reporting systems, climate, population, or local interventions change. <b>What to do:</b> retrain and recheck the model when new weekly case records and updated environmental data are available.</div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_proponents() -> None:
    st.markdown(
        """
        <div class="proponents-card">
            <div class="mini-label">Proponents</div>
            <div class="story-body">
                <span class="proponents-name">Calo, Christopher S.</span>; 
                <span class="proponents-name">Capistrano, Niño Marchnil F.</span>; 
                <span class="proponents-name">Lacandula, Kaizer Kian G.</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_references() -> None:
    st.markdown(
        """
        <section id="references-section" class="story-section">
            <div class="story-kicker">References</div>
            <div class="story-title">Sources used for the app notes</div>
            <div class="reference-list">
                <a class="reference-link" href="https://www.who.int/news-room/fact-sheets/detail/dengue-and-severe-dengue" target="_blank" rel="noopener noreferrer">World Health Organization. Dengue and severe dengue fact sheet.<span class="reference-small">Used for global dengue burden, prevention notes, and underreporting context.</span></a>
                <a class="reference-link" href="https://www.who.int/publications/i/item/who-wer10052-665-678" target="_blank" rel="noopener noreferrer">World Health Organization. Dengue: global situation, surveillance and progress – 2024 update.<span class="reference-small">Used for the 2024 global dengue surveillance figures.</span></a>
                <a class="reference-link" href="https://doi.org/10.4269/ajtmh.16-0488" target="_blank" rel="noopener noreferrer">Undurraga et al. (2017). Disease burden of dengue in the Philippines: adjusting for underreporting by comparing active and passive dengue surveillance in Punta Princesa, Cebu City.<span class="reference-small">Used for the Cebu City underreporting limitation.</span></a>
                <a class="reference-link" href="https://doi.org/10.5194/isprs-archives-XLVIII-4-W8-2023-417-2024" target="_blank" rel="noopener noreferrer">Rejuso et al. (2024). Spatiotemporal analysis of dengue cases in Cebu City from year 2015 to 2022.<span class="reference-small">Used for Cebu City dengue spatial-temporal context.</span></a>
                <a class="reference-link" href="https://doi.org/10.1186/s12879-018-3066-0" target="_blank" rel="noopener noreferrer">Carvajal et al. (2018). Machine learning methods reveal temporal patterns of dengue incidence using meteorological factors in metropolitan Manila.<span class="reference-small">Used for dengue forecasting and meteorological predictor context.</span></a>
                <a class="reference-link" href="https://doi.org/10.1371/journal.pntd.0001908" target="_blank" rel="noopener noreferrer">Hii et al. (2012). Forecast of dengue incidence using temperature and rainfall.<span class="reference-small">Used for climate-lag and weather-related dengue forecasting context.</span></a>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def scroll_to_prediction_results() -> None:
    components.html(
        """
        <script>
        const target = window.parent.document.getElementById('prediction-results');
        if (target) {
            setTimeout(() => {
                target.scrollIntoView({behavior: 'smooth', block: 'start'});
            }, 180);
        }
        </script>
        """,
        height=0,
    )


def activate_navigation_chips() -> None:
    components.html(
        """
        <script>
        const doc = window.parent.document;
        function bindChipScroll() {
            doc.querySelectorAll('a.chip-scroll').forEach((chip) => {
                if (chip.dataset.boundScroll === '1') return;
                chip.dataset.boundScroll = '1';
                chip.addEventListener('click', function(event) {
                    event.preventDefault();
                    const targetId = chip.getAttribute('data-target') || (chip.getAttribute('href') || '').replace('#', '');
                    const target = doc.getElementById(targetId);
                    if (target) {
                        target.scrollIntoView({behavior: 'smooth', block: 'start'});
                    }
                });
            });
        }
        bindChipScroll();
        setTimeout(bindChipScroll, 500);
        setTimeout(bindChipScroll, 1500);
        </script>
        """,
        height=0,
    )

# ============================================================
# HERO
# ============================================================

def hero() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-pill">🦟 Cebu City barangay-level decision-support app</div>
            <h1 class="hero-title">
                <span class="hero-red">Dengue</span>
                <span class="hero-gradient">Risk Mapping and Early Warning System in Cebu City</span>
            </h1>
            <div class="hero-subtitle">
                A clean, barangay-level dashboard for reading dengue risk signals, citywide case ranges, and localized preparedness priorities across short-term planning windows.
            </div>
            <div class="disclaimer-card">
                <span>⚠️</span>
                <span>These predictions are not perfect and should not be used as official outbreak declarations. Use them as a guide together with actual health reports, field validation, and public health judgment.</span>
            </div>
            <div class="chip-row">
                <a class="chip chip-scroll" href="#rationale-section" data-target="rationale-section">Rationale</a>
                <a class="chip chip-scroll" href="#methods-section" data-target="methods-section">Methods</a>
                <a class="chip chip-scroll" href="#prediction-results" data-target="prediction-results">Predicted cases</a>
                <a class="chip chip-scroll" href="#prediction-results" data-target="prediction-results">Barangay map</a>
                <a class="chip chip-scroll" href="#accuracy-section" data-target="accuracy-section">Accuracy check</a>
                <a class="chip chip-scroll" href="#limitations-section" data-target="limitations-section">Limitations</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# MAIN APP
# ============================================================

hero()
activate_navigation_chips()
render_rationale_and_methods()

forecasts = load_all_forecasts()
shape_gdf = load_barangay_shapefile()
actual_cases_df = load_actual_case_data(str(DATASET_PATH))

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
            <div class="sidebar-title">Dengue Risk Mapping and Early Warning System in Cebu City</div>
            <div class="sidebar-subtitle">
                Choose a model and origin week. The prediction section will open automatically after you press Predict.
            </div>
            <div class="sidebar-disclaimer">
                Predictions are estimates only. Use them as a preparedness guide, not as a replacement for official surveillance or field validation.
            </div>
            <div class="game-chip-row">
                <span class="game-chip">ISO WEEK</span>
                <span class="game-chip">MAP</span>
                <span class="game-chip">EARLY WARNING</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="iso-card">
            <div class="mini-label">What week is today?</div>
            <div class="small-note">Use this if you know the date but not the epidemiological/ISO week.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    date_to_convert = st.date_input("Date to convert", value=dt.date.today())
    iso_year, iso_week, iso_day = date_to_convert.isocalendar()
    st.markdown(
        f"""
        <div class="iso-result">
            <span>{date_to_convert.strftime('%b %d, %Y')}</span>
            <span>ISO {iso_year} W{iso_week:02d}</span>
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
                st.session_state["scroll_to_predictions"] = True

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

    st.info("Use the sidebar to choose a model and origin week, then click **Predict Dengue Cases**. The app will jump to the predicted cases and barangay risk map section automatically.")
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

st.markdown('<div id="prediction-results" class="scroll-anchor"></div>', unsafe_allow_html=True)
if st.session_state.pop("scroll_to_predictions", False):
    scroll_to_prediction_results()

st.markdown('<div class="section-title">Predicted cases and barangay risk map</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="small-note" style="margin-bottom:1rem; max-width:1000px;">
        Read the numbers as estimated case ranges and preparedness signals. The map helps answer: which barangays should be checked first?
    </div>
    """,
    unsafe_allow_html=True,
)
render_alert_legend()

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

st.markdown('<div class="section-title">Citywide forecast summary</div>', unsafe_allow_html=True)

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

# Accuracy check output is shown inside each forecast horizon tab before the small
# barangay prediction table. This anchor lets the top navigation jump to that area.
st.markdown('<div id="accuracy-section" class="scroll-anchor"></div>', unsafe_allow_html=True)

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

        st.markdown("#### Accuracy check against actual reported cases")
        render_accuracy_check_for_horizon(barangay_rows, city_row, actual_cases_df, horizon)

        st.markdown("#### Top 3 highest-risk barangays")
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
        render_top_risk_cards(table, count=3)
        prediction_csv = table.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Download full barangay prediction table CSV",
            data=prediction_csv,
            file_name=f"barangay_predictions_{mode_short_label(selected_mode).replace(' ', '_').lower()}_{target_year}_W{target_week}_H{int(horizon)}.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"prediction_download_{selected_mode}_{target_year}_{target_week}_{int(horizon)}",
        )


render_limitations_and_actions()
render_proponents()
render_references()

st.markdown(
    '<div class="footer-note">Dengue Risk Mapping and Early Warning System in Cebu City · Predictions are planning guides, not official outbreak declarations.</div>',
    unsafe_allow_html=True,
)
