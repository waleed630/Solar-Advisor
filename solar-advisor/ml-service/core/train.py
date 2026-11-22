"""retrain(): train the consumption models on all clean bills, keep each only if it is better.

Two models:

1. Seasonal model (used when the user has a bill, the normal case).
   It learns the SHAPE of a year: units / house's own average = a + b * temperature.
   The same shape works for small and big houses, so it learns well from few houses.

2. House model (used when the user has no bill, only answers questions).
   It predicts units from house details. It grows with the data:
       1 to 4 houses   -> LinearRegression, avg_temp + sanctioned_load_kw
       5 to 19 houses  -> Ridge, + ac_total, house_size_marla, people
       20+ houses      -> best of Ridge and RandomForest, all features
"""
import json
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import LeaveOneGroupOut

from .data import MODELS, build_clean

SMALL_FEATURES = ["avg_temp", "sanctioned_load_kw"]
MEDIUM_FEATURES = SMALL_FEATURES + ["ac_total", "house_size_marla", "people"]
ALL_FEATURES = MEDIUM_FEATURES + ["fans_total", "fridge_total", "ups", "max_temp"]

MODEL_FILE = MODELS / "consumption_model.joblib"
META_FILE = MODELS / "consumption_model.json"
HISTORY_FILE = MODELS / "history.csv"


def make_model(name):
    return {"LinearRegression": LinearRegression(),
            "Ridge": Ridge(alpha=1.0),
            "RandomForest": RandomForestRegressor(n_estimators=200, min_samples_leaf=3, random_state=0)}[name]


def candidates_for(n_houses):
    if n_houses < 5:
        return [("LinearRegression", SMALL_FEATURES)]
    if n_houses < 20:
        return [("Ridge", MEDIUM_FEATURES)]
    return [("Ridge", ALL_FEATURES), ("RandomForest", ALL_FEATURES)]


def evaluate(name, features, df):
    """Leave one house out: train on the other houses, test on the house the model has never seen."""
    df = df.dropna(subset=features + ["units"])
    X, y, groups = df[features], df["units"], df["site_id"]
    pred = pd.Series(np.nan, index=df.index)
    for train_idx, test_idx in LeaveOneGroupOut().split(X, y, groups):
        m = make_model(name).fit(X.iloc[train_idx], y.iloc[train_idx])
        pred.iloc[test_idx] = m.predict(X.iloc[test_idx])
    per_house = {s: round(mean_absolute_error(y[groups == s], pred[groups == s]), 1) for s in sorted(groups.unique())}
    return {"mae": round(mean_absolute_error(y, pred), 1),
            "r2": round(r2_score(y, pred), 3),
            "mae_per_house": per_house,
            "predictions": pred}


def current_meta():
    return json.loads(META_FILE.read_text()) if META_FILE.exists() else None


# ---------- 1. Seasonal model ----------

SEASONAL_FILE = MODELS / "seasonal_model.json"


def add_ratio(df):
    df = df.copy()
    df["house_mean"] = df.groupby("site_id")["units"].transform("mean")
    df["ratio"] = df["units"] / df["house_mean"]
    return df


# Shapes to try. None = straight line in temperature; a number = only degrees ABOVE it count
# ("cooling degrees": below that temperature nobody runs an AC, so use stays flat).
SEASONAL_BASE_TEMPS = [None, 18, 20, 22]
MIN_RATIO = 0.1


def temp_feature(temps, base_temp):
    return temps if base_temp is None else np.maximum(0, temps - base_temp)


def seasonal_ratio(model, temps):
    """Units / house average for these temperatures, from a saved seasonal model."""
    x = temp_feature(np.asarray(temps, dtype=float), model.get("base_temp"))
    return np.maximum(MIN_RATIO, model["intercept"] + model["per_degree"] * x)


def evaluate_seasonal(df, base_temp=None):
    """Leave one house out. The test house's own average is known (it comes from the user's bill)."""
    df = add_ratio(df)
    x = pd.DataFrame({"t": temp_feature(df["avg_temp"], base_temp)})
    pred = pd.Series(np.nan, index=df.index)
    for s in df["site_id"].unique():
        train, test = df["site_id"] != s, df["site_id"] == s
        m = LinearRegression().fit(x[train], df.loc[train, "ratio"])
        pred[test] = np.maximum(MIN_RATIO, m.predict(x[test])) * df.loc[test, "house_mean"]
    groups = df["site_id"]
    per_house = {s: round(mean_absolute_error(df.units[groups == s], pred[groups == s]), 1) for s in sorted(groups.unique())}
    pct = float((abs(df.units - pred) / df.units).mean())
    return {"mae": round(mean_absolute_error(df.units, pred), 1), "r2": round(r2_score(df.units, pred), 3),
            "mape": round(pct, 3), "mae_per_house": per_house, "predictions": pred, "base_temp": base_temp}


def retrain_seasonal(df, force=False):
    # Try each shape; keep the one with the lowest leave-one-house-out error
    tried = [evaluate_seasonal(df, b) for b in SEASONAL_BASE_TEMPS]
    score = min(tried, key=lambda s: s["mae"])
    base = score["base_temp"]

    # Fair comparison: the saved model's recipe, refit and tested the same way on the same data
    old = json.loads(SEASONAL_FILE.read_text()) if SEASONAL_FILE.exists() else None
    old_mae = evaluate_seasonal(df, old.get("base_temp"))["mae"] if old else None
    replace = force or old is None or score["mae"] <= old_mae

    d = add_ratio(df)
    m = LinearRegression().fit(pd.DataFrame({"t": temp_feature(d["avg_temp"], base)}), d["ratio"])
    if replace:
        SEASONAL_FILE.write_text(json.dumps({
            "base_temp": base, "intercept": round(float(m.intercept_), 4), "per_degree": round(float(m.coef_[0]), 4),
            "n_houses": int(df["site_id"].nunique()), "n_rows": int(len(df)),
            "mae": score["mae"], "r2": score["r2"], "mape": score["mape"], "mae_per_house": score["mae_per_house"],
            "shapes_tried": {str(s["base_temp"]): s["mae"] for s in tried},
            "trained_at": datetime.now().isoformat(timespec="seconds")}, indent=2))
    return {"replaced": replace, "base_temp": base, "mae": score["mae"], "r2": score["r2"], "mape": score["mape"],
            "old_mae": old_mae, "per_degree": round(float(m.coef_[0]), 4)}


def load_seasonal():
    if not SEASONAL_FILE.exists():
        retrain()
    return json.loads(SEASONAL_FILE.read_text())


# ---------- 2. House model + retrain() ----------

def retrain(drop_outliers=False, force=False):
    df = build_clean(drop_outliers=drop_outliers)
    n_houses = df["site_id"].nunique()
    seasonal = retrain_seasonal(df, force=force)

    # Best candidate for this amount of data
    results = []
    for name, features in candidates_for(n_houses):
        results.append((name, features, evaluate(name, features, df)))
    name, features, score = min(results, key=lambda r: r[2]["mae"])

    # Score the current model's recipe on the SAME data, so the comparison is fair
    old = current_meta()
    old_mae = None
    if old:
        old_mae = evaluate(old["model"], old["features"], df)["mae"]
    replace = force or old is None or score["mae"] <= old_mae

    if replace:
        # Homes added from the app may leave some details blank: train only on rows that have every feature
        fit_df = df.dropna(subset=features + ["units"])
        model = make_model(name).fit(fit_df[features], fit_df["units"])
        MODELS.mkdir(exist_ok=True)
        joblib.dump(model, MODEL_FILE)
        coefs = {}
        if hasattr(model, "coef_"):
            coefs = {f: round(float(c), 2) for f, c in zip(features, model.coef_)}
            coefs["intercept"] = round(float(model.intercept_), 2)
        meta = {"model": name, "features": features, "n_houses": int(n_houses), "n_rows": int(len(df)),
                "mae": score["mae"], "r2": score["r2"], "mae_per_house": score["mae_per_house"],
                "coefficients": coefs, "drop_outliers": drop_outliers,
                "trained_at": datetime.now().isoformat(timespec="seconds")}
        META_FILE.write_text(json.dumps(meta, indent=2))

    row = pd.DataFrame([{"time": datetime.now().isoformat(timespec="seconds"), "n_houses": n_houses,
                         "n_rows": len(df), "seasonal_mae": seasonal["mae"], "seasonal_r2": seasonal["r2"],
                         "house_model": name, "house_mae": score["mae"], "house_r2": score["r2"],
                         "house_old_mae": old_mae, "house_replaced": replace}])
    row.to_csv(HISTORY_FILE, mode="a", header=not HISTORY_FILE.exists(), index=False)

    return {"n_houses": int(n_houses), "n_rows": int(len(df)),
            "seasonal": seasonal,
            "house_model": {"replaced": replace, "model": name, "features": features,
                            "mae": score["mae"], "r2": score["r2"], "old_mae": old_mae,
                            "mae_per_house": score["mae_per_house"]}}


def load_model():
    if not MODEL_FILE.exists():
        retrain()
    return joblib.load(MODEL_FILE), current_meta()
