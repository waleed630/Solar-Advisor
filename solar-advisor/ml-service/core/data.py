"""Load the bills, house details and weather, and build the clean training table.

Same steps as notebooks/01_explore_data.ipynb, so the notebook, retrain() and
the web app all use one version of the rules.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
MODELS = ROOT / "models"
CONFIG = ROOT / "config"

SEASON_OF = {4: "summer", 5: "summer", 6: "summer", 7: "summer", 8: "summer", 9: "summer",
             11: "winter", 12: "winter", 1: "winter", 2: "winter", 3: "mild", 10: "mild"}

ESTIMATED_STATUS = {"DF", "MC"}  # bill history status codes: defective meter, meter changed

# Months the owner confirmed are real but unusual (kept in data, flagged for testing)
OUTLIERS = {("H005", 2026, 8)}


def load_weather():
    return pd.read_csv(DATA / "weather_lahore_daily.csv", parse_dates=["date"], index_col="date")


def weather_for_bill(weather, year, month):
    """LESCO reads meters around the 20th, so a bill month covers the 30 days ending on the 20th."""
    end = pd.Timestamp(year=year, month=month, day=20)
    start = end - pd.DateOffset(months=1) + pd.DateOffset(days=1)
    w = weather.loc[start:end]
    return {
        "avg_temp": round(w["temp_avg_c"].mean(), 1),
        "max_temp": round(w["temp_max_c"].mean(), 1),
        "sun": round(w["sun_kwh_m2_day"].mean(), 2),
    }


def typical_month_weather(weather):
    """Average weather for each bill month across all years we have (used to predict a full year)."""
    rows = {}
    for m in range(1, 13):
        years = sorted({d.year for d in weather.index})
        vals = []
        for y in years:
            end = pd.Timestamp(year=y, month=m, day=20)
            if end - pd.DateOffset(months=1) >= weather.index.min() and end <= weather.index.max():
                vals.append(weather_for_bill(weather, y, m))
        rows[m] = {k: round(sum(v[k] for v in vals) / len(vals), 2) for k in ("avg_temp", "max_temp", "sun")}
    return rows


def build_monthly():
    """One row per house per bill month: all meters added up, weather and house details joined."""
    bills = pd.read_csv(DATA / "bills.csv")
    houses = pd.read_csv(DATA / "houses.csv")
    weather = load_weather()

    # DF = meter defective (units are LESCO's estimate), MC = meter changed (part of a month): not measured use
    bills["estimated"] = bills["bill_status"].isin(ESTIMATED_STATUS)
    monthly = (bills.groupby(["site_id", "year", "month"], as_index=False)
               .agg(units=("units", "sum"), sanctioned_load_kw=("sanctioned_load_kw", "sum"),
                    estimated=("estimated", "any")))
    w = monthly.apply(lambda r: pd.Series(weather_for_bill(weather, int(r.year), int(r.month))), axis=1)
    monthly = pd.concat([monthly, w], axis=1)
    monthly["season"] = monthly["month"].map(SEASON_OF)
    monthly["is_outlier"] = [(s, y, m) in OUTLIERS for s, y, m in zip(monthly.site_id, monthly.year, monthly.month)]
    return monthly.merge(houses, on="site_id", how="left")


def build_clean(drop_outliers=False):
    """Apply the data rules: no solar, all meters known, no near-zero months."""
    data = build_monthly()
    data["reason_out"] = ""
    data.loc[data["has_solar"] == 1, "reason_out"] = "has solar"
    missing = (data["reason_out"] == "") & (data["meters_with_bills"] < data["meters_total"])
    data.loc[missing, "reason_out"] = "missing meter bill"
    data.loc[(data["reason_out"] == "") & (data["units"] < 10), "reason_out"] = "near-zero month"
    data.loc[(data["reason_out"] == "") & data["estimated"], "reason_out"] = "meter defective or changed"
    clean = data[data["reason_out"] == ""].copy()
    if drop_outliers:
        clean = clean[~clean["is_outlier"]]
    return clean.reset_index(drop=True)
